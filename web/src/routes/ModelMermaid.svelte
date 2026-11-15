<script>
  /**
   * Model — the avian H5N1 response model as an interactive research surface.
   * Route: #/model
   *
   * Config-driven: stages/axes/gaps come from /data/avian_h5n1_model.json
   * (ever-growing data file). Badges are live corpus counts. The sensor
   * matrix renders from the gene-presence parquet via DuckDB. Node detail drawers will surface
   * mined context packs (mine_model_nodes.py) when available.
   */
  import { onMount } from 'svelte';
  import { updateParams, subscribe as routerSubscribe, getRoute } from '../lib/stores/router.js';
  import Mermaid from '../lib/components/common/Mermaid.svelte';
  import { t, tc } from '../lib/stores/i18n.svelte.js';
  import { phylopicIndex, phylopicPath } from '../lib/utils/phylopic.js';
  import { db } from '../lib/stores/db.js';
  import { fetchGeneCatalogue, pivotCallsBySpecies } from '../lib/utils/presence.js';

  let model = $state(null);
  let counts = $state(null);
  let insights = $state([]);
  let presence = $state(null);
  let silhouettes = $state(null);
  let openStage = $state(null);

  let modelTab = $state('infection'); // infection | spread
  let spreadModel = $state(null);

  // --- Species-aware model view (D74) ---
  let selSpecies = $state(null);        // scientific name of chosen species
  let absence = $state(null);           // gene_absence_summary.json
  let geneEvidence = $state(null);      // gene selected for evidence drawer

  const SPECIES_CLASS = {
    // all 15 sequenced species are avian today; mammalian branch ready
    'Gallus gallus': 'avian', 'Anas platyrhynchos': 'avian',
    'Taeniopygia guttata': 'avian', 'Meleagris gallopavo': 'avian',
    'Strigops habroptila': 'avian', 'Porphyrio hochstetteri': 'avian',
    'Nestor notabilis': 'avian', 'Apteryx mantelli': 'avian',
    'Apteryx rowi': 'avian', 'Apteryx haastii': 'avian',
    'Apteryx owenii': 'avian', 'Megadyptes antipodes antipodes': 'avian',
    'Cyanoramphus novaezelandiae': 'avian', 'Gallirallus australis': 'avian',
    'Notiomystis cincta': 'avian',
  };
  const SPECIES_ORDER = {
    'Gallus gallus': 'Galliformes', 'Meleagris gallopavo': 'Galliformes',
    'Anas platyrhynchos': 'Anseriformes',
    'Megadyptes antipodes antipodes': 'Sphenisciformes',
    'Apteryx mantelli': 'Apterygiformes', 'Apteryx rowi': 'Apterygiformes',
    'Apteryx haastii': 'Apterygiformes', 'Apteryx owenii': 'Apterygiformes',
    'Strigops habroptila': 'Psittaciformes', 'Nestor notabilis': 'Psittaciformes',
    'Cyanoramphus novaezelandiae': 'Psittaciformes',
    'Taeniopygia guttata': 'Passeriformes', 'Notiomystis cincta': 'Passeriformes',
    'Porphyrio hochstetteri': 'Gruiformes', 'Gallirallus australis': 'Gruiformes',
  };
  const SPECIES_COMMON = {
    'Gallus gallus': 'Chicken', 'Anas platyrhynchos': 'Mallard duck',
    'Taeniopygia guttata': 'Zebra finch', 'Meleagris gallopavo': 'Turkey',
    'Strigops habroptila': 'Kākāpō', 'Porphyrio hochstetteri': 'Takahē',
    'Nestor notabilis': 'Kea', 'Apteryx mantelli': 'North Island brown kiwi',
    'Apteryx rowi': 'Okarito kiwi', 'Apteryx haastii': 'Great spotted kiwi',
    'Apteryx owenii': 'Little spotted kiwi',
    'Megadyptes antipodes antipodes': 'Yellow-eyed penguin',
    'Cyanoramphus novaezelandiae': 'Red-crowned kākāriki',
    'Gallirallus australis': 'Weka', 'Notiomystis cincta': 'Stitchbird',
  };


  /** Split a statement into text and [paper_id] citation parts for linkifying */
  function splitCitations(text) {
    const parts = [];
    const re = /\[([a-z0-9_][a-z0-9_.\- ]*?)\]/gi;
    let last = 0, m;
    while ((m = re.exec(text)) !== null) {
      if (m.index > last) parts.push({ text: text.slice(last, m.index) });
      parts.push({ pid: m[1].trim() });
      last = m.index + m[0].length;
    }
    if (last < text.length) parts.push({ text: text.slice(last) });
    return parts;
  }

  /** Presence status of a gene in the selected species */
  function presenceOf(sym) {
    if (!selSpecies || !presence?.species?.[selSpecies]) return null;
    // model uses aliases (RIG-I↔DDX58, MDA5↔IFIH1, PKR↔OASL...)
    const call = presence.species[selSpecies][sym]
      || presence.species[selSpecies][aliasOf(sym)];
    return call?.status || null;
  }
  const ALIAS = { 'RIG-I': 'DDX58', 'MDA5': 'IFIH1', 'LGP2': 'DHX58',
                  'PKR': 'OASL', 'MAVS': 'IPS1', 'TLR3': 'TLR3' };
  function aliasOf(sym) { return ALIAS[sym] || sym; }

  /** Chip styling per presence status (red=absent, amber=fragment) */
  function presenceChip(sym) {
    const st = presenceOf(sym);
    if (!st) return '';
    if (st === 'NOT_FOUND' || st === 'E2')
      return 'border-red-400 bg-red-50 dark:bg-red-900/20 dark:border-red-700';
    if (st === 'FRAGMENT' || st === 'E3')
      return 'border-amber-400 border-dashed bg-amber-50 dark:bg-amber-900/20';
    return 'border-green-300 bg-green-50/50 dark:bg-green-900/20';
  }
  function presenceLabel(sym) {
    const st = presenceOf(sym);
    if (!st) return null;
    if (st === 'NOT_FOUND' || st === 'E2') return 'absent';
    if (st === 'FRAGMENT' || st === 'E3') return 'fragment';
    return 'present';
  }

  /** Literature absence evidence for a gene, filtered by species class,
      exact-species first, then same-order, then same-class (tagged) */
  function absenceEvidence(sym) {
    if (!absence || !selSpecies) return [];
    const key = Object.keys(absence).find(k => k === sym || k === aliasOf(sym));
    if (!key) return [];
    const cls = SPECIES_CLASS[selSpecies] || 'avian';
    const recs = absence[key][cls] || [];
    const spCommon = SPECIES_COMMON[selSpecies];
    const spOrder = SPECIES_ORDER[selSpecies];
    return recs.map(r => {
      const host = (r.host || '').toLowerCase();
      const hostNorm = host.replace(/[^a-z\s]/g, '');
      const spNorm = selSpecies.toLowerCase() + ' ' + (spCommon || '').toLowerCase();
      const exact = hostNorm && (spNorm.includes(hostNorm) ||
        (hostNorm.includes('chicken') && selSpecies === 'Gallus gallus') ||
        (hostNorm.includes('duck') && selSpecies === 'Anas platyrhynchos'));
      let tag = 'reported in ' + (r.host || 'other species');
      if (exact) tag = 'this species';
      else if (spOrder && new RegExp(spOrder + '|' + orderKeyword(spOrder), 'i').test(r.host || ''))
        tag += ' · same order';
      return { ...r, exact, tag };
    }).sort((a, b) => (b.exact ? 1 : 0) - (a.exact ? 1 : 0));
  }
  function orderKeyword(order) {
    return { Galliformes: 'chicken|poultry|quail|turkey',
             Anseriformes: 'duck|goose|mallard|swan',
             Psittaciformes: 'parrot|kākāpō|kea|parakeet|kākāriki',
             Passeriformes: 'finch|sparrow|songbird|passerine',
             Apterygiformes: 'kiwi', Gruiformes: 'rail|takahē|weka|coot',
             Sphenisciformes: 'penguin' }[order] || order;
  }

  onMount(async () => {
    try {
      const [m, c, i, s, sp, ab, cat] = await Promise.all([
        fetch('data/avian_h5n1_model.json').then(r => r.json()),
        fetch('data/gene_evidence_counts.json').then(r => r.json()),
        fetch('data/synthesis_insights.json').then(r => r.ok ? r.json() : []),
        phylopicIndex(),
        fetch('data/h5n1_spread_model.json').then(r => r.ok ? r.json() : null).catch(() => null),
        fetch('data/gene_absence_summary.json').then(r => r.ok ? r.json() : {}).catch(() => ({})),
        fetchGeneCatalogue(),
      ]);
      model = m; counts = c; insights = i; silhouettes = s; spreadModel = sp; absence = ab;
      // Presence matrix from DuckDB — only the sensor genes (+aliases)
      const sensorGenes = m.sensor_matrix?.genes || [];
      const wanted = [...new Set([...sensorGenes, ...sensorGenes.map(aliasOf)])];
      const rows = await db.getPresenceCallsForGenes(wanted);
      presence = {
        gene_catalogue: cat?.gene_catalogue || {},
        species: pivotCallsBySpecies(rows),
      };
    } catch { /* page degrades gracefully */ }
  });

  function badge(sym) {
    if (!counts) return { cls: 'bg-gray-100 text-gray-600 dark:text-gray-400', label: '…' };
    const c = counts[sym];
    if (!c || !c.papers) return { cls: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300', label: 'gap' };
    if (c.studied >= 2) return { cls: 'bg-green-100 text-green-700 dark:text-green-400 dark:bg-green-900/30 dark:text-green-300', label: `${c.papers} papers` };
    if (c.studied === 1) return { cls: 'bg-green-100 text-green-700 dark:text-green-400 dark:bg-green-900/30 dark:text-green-300', label: '1 study' };
    return { cls: 'bg-amber-100 text-amber-700 dark:text-amber-400 dark:bg-amber-900/30 dark:text-amber-300', label: `${c.papers} mentions` };
  }

  // stage evidence coverage: distribution of node badges
  function coverage(stage) {
    let green = 0, amber = 0, red = 0;
    for (const [sym] of stage.genes) {
      const c = counts?.[sym];
      if (!c || !c.papers) red++;
      else if (c.studied >= 1) green++;
      else amber++;
    }
    const total = green + amber + red || 1;
    return { green, amber, red, pct: Math.round(100 * (green + 0.5 * amber) / total) };
  }

  // sensor matrix from live presence data
  let matrix = $derived.by(() => {
    if (!model || !presence) return null;
    const genes = model.sensor_matrix?.genes || [];
    const species = Object.keys(presence.species || {});
    return { genes, species };
  });

  let diagramView = $state('recognition'); // recognition | signalling | storm | viral

  const diagrams = {
    recognition: `flowchart TD
      subgraph surface["📍 Cell Surface"]
        SA["α2,3 sialic acid<br/>AVIAN RECEPTOR"]
        HA["🦠 Viral HA binds"] --> SA
        FURIN["FURIN<br/>cleaves HPAI HA<br/>→ SYSTEMIC SPREAD"]
      end
      subgraph endosome["🫧 Endosome"]
        TLR3["TLR3<br/>dsRNA"]
        TLR7["TLR7<br/>ssRNA genomes"]
        TLR21["TLR21<br/>CpG DNA (bird-specific)"]
        UNC93B1["UNC93B1<br/>TLR trafficking"]
      end
      subgraph cytosol["🔵 Cytosol"]
        DDX58["⭐ RIG-I / DDX58<br/>5'ppp short RNA<br/>Z-LINKED<br/>❌ LOST: Galliformes"]
        IFIH1["MDA5 / IFIH1<br/>long dsRNA<br/>✅ UNIVERSAL"]
        OASL["🦆 OASL<br/>duck RIG-I mimic<br/>NS1-RESISTANT"]
        TRIM25["TRIM25<br/>activates RIG-I"] --> DDX58
        OASL -.enhances.-> DDX58
        DDX58 & IFIH1 --> MAVS["MAVS<br/>mitochondrial adaptor"]
      end
      surface -->|virus enters| endosome
      TLR3 -->|TRIF| TRIF["→ TRIF → IRF3"]
      TLR7 & TLR21 -->|MyD88| MYD["→ MyD88 → NF-κB"]
      classDef lost fill:#fecaca,stroke:#ef4444
      classDef bird fill:#dcfce7,stroke:#22c55e
      class DDX58 lost
      class OASL,TLR21 bird`,

    signalling: `flowchart TD
      subgraph cytosol["🔵 Cytosol — Signal transduction"]
        MAVS["MAVS<br/>(from RIG-I/MDA5)"] --> TBK1["TBK1 kinase"]
        MYD88["MyD88<br/>(from TLRs)"] --> IRAK["IRAK/TRAF6"]
        TBK1 --> IRF3["IRF3<br/>primary gatekeeper"]
        TBK1 --> IRF7["IRF7<br/>amplifier"]
        IRAK --> NFKB["NF-κB"]
      end
      subgraph nucleus["🟣 Nucleus — Gene activation"]
        IRF3 --> IFNB["IFN-β gene ON"]
        IRF7 --> IFNA["IFN-α genes ON"]
        NFKB --> CYTOKINES["TNF · IL6 · IL1β ON"]
      end
      subgraph paracrine["📡 Paracrine IFN loop"]
        IFNB --> IFNR["IFN receptor"]
        IFNA --> IFNR
        IFNR --> JAK1["JAK1 / TYK2"] --> STAT["STAT1+STAT2<br/>→ ISGF3 complex"]
        SOCS1["SOCS1 ✕<br/>NEGATIVE FEEDBACK"] -.-> JAK1
      end
      subgraph isgs["🛡️ Interferon-Stimulated Genes"]
        STAT --> MX1["MX1<br/>blocks viral transcription"]
        STAT --> IFITM3["IFITM3<br/>blocks entry/fusion"]
        STAT --> RSAD2["Viperin<br/>disrupts budding"]
        STAT --> PKR["PKR<br/>translation shutoff"]
        STAT --> IFIT5["IFIT5<br/>degrades viral RNA"]
      end
      classDef eff fill:#dcfce7,stroke:#22c55e
      classDef brake fill:#fef3c7,stroke:#f59e0b
      class MX1,IFITM3,RSAD2,PKR,IFIT5 eff
      class SOCS1 brake`,

    storm: `flowchart TD
      subgraph trigger["⚡ Infection triggers"]
        VIRUS["🦠 H5N1 replication"] --> SENSORS["RIG-I / MDA5 / TLRs"]
        SENSORS --> NFKB["NF-κB activation"]
        SENSORS --> IRF3["IRF3 activation"]
      end
      subgraph antiviral["🟢 Antiviral path (what SHOULD happen)"]
        IRF3 --> IFNB["IFN-β → controlled\nantiviral state → clearance"]
      end
      subgraph storm_path["🔴 Cytokine storm path (what KILLS)"]
        NFKB --> TNF["TNF-α<br/>29pp studied"]
        NFKB --> IL6["IL-6<br/>45pp studied"]
        NFKB --> IL1B_PRE["pro-IL-1β"]
        NLRP3["NLRP3<br/>inflammasome sensor"] --> CASP1["Caspase-1"] --> IL1B["IL-1β ACTIVE<br/>32pp studied"]
        IL1B_PRE --> NLRP3
        TNF & IL6 & IL1B --> STORM["💥 CYTOKINE STORM<br/>massive inflammation<br/>vascular leak · organ failure"]
        STORM --> DEATH["☠️ DEATH<br/>hours-days post-infection"]
      end
      subgraph tolerance["🦆 Why ducks survive"]
        DUCK_REG["Tolerant species:<br/>SOCS1/IL10 regulate NF-κB<br/>antiviral IFN WITHOUT storm"]
        DUCK_REG -.suppresses.-> STORM
      end
      subgraph susceptible["🐔 Why chickens die"]
        CHICK_REG["Susceptible species:<br/>unregulated IL-6 response<br/>no effective brake"]
        CHICK_REG -.fails to stop.-> STORM
      end
      classDef good fill:#dcfce7,stroke:#22c55e
      classDef bad fill:#fecaca,stroke:#ef4444
      classDef warn fill:#ffedd5,stroke:#ea580c
      class IFNB good
      class STORM,DEATH bad
      class TNF,IL6,IL1B warn`,

    viral: `flowchart LR
      subgraph host["🧬 Host Cell"]
        subgraph nucleus["🟣 Nucleus"]
          ANP32A["ANP32A<br/>33-aa insertion<br/>✅ kākāpō CONFIRMED"] --> POL["🦠 Viral polymerase<br/>PB2+PB1+PA"]
          POL --> VRNA["vRNA → cRNA → new vRNA<br/>→ budding"]
        end
        subgraph cytosol["🔵 Cytosol"]
          IRF3["IRF3<br/>(antiviral gate)"]
          OASL["OASL<br/>(duck RIG-I enhancer)"]
          JAK1["JAK1<br/>(IFN signalling)"]
          NLRP3["NLRP3<br/>(inflammasome)"]
          IFNB["IFN-β production"]
        end
      end
      subgraph counter["🦠 Viral Antagonism Arsenal"]
        NS1["NS1<br/>① Blocks IRF3 activation<br/>② Blocks OASL (except duck OASL)<br/>③ Antagonizes IFN production"]
        PB2["PB2 (mammalian-adapted)<br/>Degrades JAK1<br/>→ IFN signalling fails"]
        PB1F2["PB1-F2<br/>Induces apoptosis<br/>in immune cells<br/>→ kills the responders"]
        PAX["PA-X<br/>Host mRNA shutoff<br/>→ cell can't make IFN"]
      end
      NS1 -.①.-> IRF3
      NS1 -.②.-> OASL
      PB2 -.-> JAK1
      PB1F2 -.-> NLRP3
      PAX -.-> IFNB
      classDef viralNode fill:#fef3c7,stroke:#f59e0b,color:#78350f
      classDef hostDep fill:#fecaca,stroke:#ef4444
      classDef antag fill:#ffedd5,stroke:#ea580c,color:#7c2d12
      class ANP32A hostDep
      class NS1,PB2,PB1F2,PAX antag`,
  };

  // Tab ↔ URL sync: #/model?tab=spread is the canonical spread-model link
  onMount(() => {
    const apply = (route) => {
      if (route?.page === 'model' && route?.params?.tab && ['infection', 'spread'].includes(route.params.tab)) {
        modelTab = route.params.tab;
      }
    };
    apply(getRoute());
    return routerSubscribe(apply);
  });
</script>

<svelte:head><title>{t('model.title') || 'H5N1 Spread & Migration Model'} — Roost</title></svelte:head>

<div class="max-w-6xl mx-auto space-y-10">
  <div>
    <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">{t('model.title')}</h1>
    <p class="text-gray-600 dark:text-gray-300">
      {t('model.subtitle') || 'Working models from the Roost corpus — every node links to its evidence.'}
      {t('model.badges') || 'Badges:'}: <span class="text-green-700 dark:text-green-400">{t('routes_Model.studied')}</span>,
      <span class="text-amber-700 dark:text-amber-400">{t('routes_Model.mentioned')}</span>,
      <span class="text-red-600 dark:text-red-400">{t('routes_Model.gap')}</span>.
      {#if model}<span class="text-xs text-gray-500 dark:text-gray-400">infection v{model.version} · {model.updated}</span>{/if}
      {#if spreadModel}<span class="text-xs text-gray-500 dark:text-gray-400"> · spread v{spreadModel.version} · {spreadModel.updated}</span>{/if}
    </p>
  </div>

  <!-- Model tabs -->
  <div class="flex gap-1 border-b border-gray-200 dark:border-gray-700 mb-6">
    <button
      class="px-4 py-2 font-medium text-sm border-b-2 transition-colors {modelTab === 'infection'
        ? 'border-blue-600 text-blue-600 dark:text-blue-400'
        : 'border-transparent text-gray-500 hover:text-gray-900 dark:hover:text-white'}"
      onclick={() => { modelTab = 'infection'; updateParams({ tab: 'infection' }); }}
    >
      🧬 Infection Model
    </button>
    <button
      class="px-4 py-2 font-medium text-sm border-b-2 transition-colors {modelTab === 'spread'
        ? 'border-blue-600 text-blue-600 dark:text-blue-400'
        : 'border-transparent text-gray-500 hover:text-gray-900 dark:hover:text-white'}"
      onclick={() => { modelTab = 'spread'; updateParams({ tab: 'spread' }); }}
    >
      🌍 Spread Model
    </button>
  </div>

  <!-- SPREAD MODEL TAB -->
  {#if modelTab === 'spread' && spreadModel}
    <section class="space-y-6">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">{t('routes.modelmermaid.spread.migration.model') || 'H5N1 Spread & Migration Model'}</h2>
        <p class="text-sm text-gray-500 dark:text-gray-400 max-w-3xl">
          {t('spread.intro') || 'How H5N1 moves through wild bird populations, poultry systems, and into mammals.'}
          {t('spread.built.from') || 'Built from'} {spreadModel.source}. {t('spread.each.stage.links') || 'Each stage links to the papers that inform it.'}
        </p>
      </div>

      <!-- Overview diagram -->
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
        <Mermaid source={`flowchart TD
          subgraph wild["${t('mermaid.sub.wild') || 'Wild bird cycle'}"]
            reservoir["${t('mermaid.reservoir') || '1· Reservoir<br/>waterfowl'}"] --> amplification["${t('mermaid.amplification') || '2· Amplification<br/>colonial seabirds'}"]
            reservoir --> bridge["${t('mermaid.bridge') || '3· Bridge hosts<br/>gulls, shorebirds'}"]
          end
          subgraph movement["${t('mermaid.sub.movement') || 'Movement'}"]
            routes["${t('mermaid.flyways') || '4· Flyways'}"] --> timing["${t('mermaid.seasonality') || '5· Seasonality'}"]
          end
          subgraph env["${t('mermaid.sub.env') || 'Environment'}"]
            environmental["${t('mermaid.persistence') || '6· Persistence'}"]
            anthropogenic["${t('mermaid.anthropogenic') || '7· Anthropogenic<br/>trade, markets'}"]
          end
          subgraph mammals["${t('mermaid.sub.mammals') || 'Mammalian spillover'}"]
            spillover["${t('mermaid.spillover') || '8· Spillover chains'}"]
          end
          regional_risk["${t('mermaid.regional') || '9· Regional\n risk'}"]

          routes --> reservoir
          timing --> routes
          reservoir --> amplification
          reservoir --> bridge
          bridge --> anthropogenic
          amplification --> spillover
          routes --> regional_risk

          classDef stage fill:#dbeafe,stroke:#60a5fa
          class reservoir,amplification,bridge,routes,timing,environmental,anthropogenic,spillover,regional_risk stage`}
        id="spread-overview" />
      </div>

      <!-- Stage sections -->
      {#each spreadModel.stages as stage (stage.id)}
        <section class="space-y-3">
          <div>
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">{tc(`model.spread.${stage.id}.title`) || stage.title}</h3>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-3xl">{tc(`model.spread.${stage.id}.desc`) || stage.desc}</p>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {#each stage.elements as [name, note] (name)}
              <div class="p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                <div class="font-medium text-gray-900 dark:text-white text-sm">{name}</div>
                <div class="text-[11px] text-gray-500 dark:text-gray-400 mt-1">{note}</div>
              </div>
            {/each}
          </div>
        </section>
      {/each}

      <!-- Connections -->
      <section class="space-y-3">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Stage connections</h3>
        <div class="space-y-1">
          {#each spreadModel.connections as c}
            <div class="flex items-baseline gap-2 text-sm">
              <span class="font-mono text-xs text-blue-600 dark:text-blue-400">{c.from}</span>
              <span class="text-gray-500 dark:text-gray-400">→</span>
              <span class="font-mono text-xs text-blue-600 dark:text-blue-400">{c.to}</span>
              <span class="text-gray-500 dark:text-gray-400 text-xs">{c.note}</span>
            </div>
          {/each}
        </div>
      </section>
    

    <!-- Spread additions ledger -->
    {#if spreadModel?.additions?.length}
      <section class="space-y-2">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">{t('model.lit.adds') || 'What the literature adds'}</h3>
          <span class="text-xs text-gray-500 dark:text-gray-400">verification campaign · {spreadModel.version || 'v0.3'}</span>
        </div>
        <div class="space-y-2">
          {#each spreadModel.additions as a (a.topic)}
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4 border-green-400">
              <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">{a.topic} <span class="text-[10px] font-mono text-gray-500 dark:text-gray-400">· {a.stage}</span></div>
              <p class="text-sm text-gray-700 dark:text-gray-300">{a.statement}</p>
              <div class="flex flex-wrap gap-2 mt-2 text-[11px]">
                {#each a.citations as pid}
                  <a href="#/papers/{pid}" class="text-blue-600 dark:text-blue-400 hover:underline">[{pid}]</a>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      </section>
    {/if}

    <!-- Spread diverges (verification campaign v0.3) -->
    {#if spreadModel?.diverges?.length}
      <section class="space-y-2">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">{t('model.lit.disagrees') || 'Where the literature disagrees'}</h3>
          <span class="text-xs text-gray-500 dark:text-gray-400">verification campaign v{spreadModel.version || '0.3'} · grounded quotes in model_verdicts.jsonl</span>
        </div>
        {#each spreadModel.diverges as d (d.topic)}
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4 border-red-400">
            <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">{d.topic} <span class="text-[10px] font-mono text-gray-500 dark:text-gray-400">· {d.stage}</span></div>
            <p class="text-sm text-gray-700 dark:text-gray-300">{#each splitCitations(d.statement) as part}{#if part.pid}<a href="#/papers/{part.pid}" class="text-blue-600 dark:text-blue-400 hover:underline">[{part.pid}]</a>{:else}{part.text}{/if}{/each}</p>
          </div>
        {/each}
      </section>
    {/if}
  </section>
  {/if}

  <!-- INFECTION MODEL CONTENT (existing, shown when modelTab === 'infection') -->
  {#if modelTab === 'infection' && !model}
    <div class="animate-pulse py-16"><div class="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div></div>
  {:else if modelTab === 'infection'}

  <!-- Diagram sub-view selector -->
  <div class="flex flex-wrap gap-2">
    {#each Object.entries({recognition: '📍 Entry & Sensing', signalling: '📡 IFN Response', storm: '🔴 Cytokine Storm', viral: '🦠 Viral Antagonism'}) as [key, label]}
      <button
        class="px-3 py-1.5 rounded-lg text-sm font-medium {diagramView === key
          ? 'bg-blue-600 text-white shadow'
          : 'bg-white dark:bg-gray-800 shadow text-gray-600 dark:text-gray-300 hover:shadow-md'}"
        onclick={() => diagramView = key}
      >{label}</button>
    {/each}
  </div>

  <!-- Species-aware model context (D74): choose a species → chips re-style,
       gene evidence drawer shows lit-first absence phenotypes with citations -->
  <div class="flex flex-wrap items-center gap-3 bg-white dark:bg-gray-800 rounded-xl shadow p-3">
    <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Species context:</span>
    <select
      class="text-sm border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
      bind:value={selSpecies}
      onchange={() => geneEvidence = null}
    >
      <option value={null}>{t('routes.modelmermaid.none.model.only') || '— none (model only) —'}</option>
      {#each Object.keys(presence?.species || {}) as sp}
        <option value={sp}>{SPECIES_COMMON[sp] || sp} <em class="text-gray-500 dark:text-gray-400">({sp})</em></option>
      {/each}
    </select>
    {#if selSpecies}
      <span class="text-xs text-gray-500 dark:text-gray-400">
        {SPECIES_ORDER[selSpecies] || ''} · {t('model.species_strip.legend')}
      </span>
      <a href="#/species-full/{encodeURIComponent(selSpecies)}" class="text-xs text-blue-600 dark:text-blue-400 hover:underline">{t('model.full_gene_panel')}</a>
    {/if}
  </div>

  <!-- Infection model diagram (selected view) -->
  <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
    <Mermaid source={diagrams[diagramView]} id={`model-${diagramView}`} />
  </div>

  <!-- Sensor matrix -->
  {#if matrix}
    <section class="space-y-3">
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">Sensor matrix — {matrix.species.length} species</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400">{t('model.presence.calls') || 'Presence calls from the evidence-ladder pipeline. Click a species for its full gene panel.'}</p>
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4 overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
              <th class="py-2 pr-3">{t('lib_components_species_SpeciesFullPage.species')}</th>
              {#each matrix.genes as g}<th class="py-2 px-2 text-center">{presence.gene_catalogue?.[g]?.name || g}</th>{/each}
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
            {#each matrix.species as sp (sp)}
              <tr class="hover:bg-gray-50 dark:hover:bg-gray-700/40">
                <td class="py-2 pr-3">
                  <a href="#/species-full/{encodeURIComponent(sp)}" class="flex items-center gap-2 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-400">
                    {#if phylopicPath(sp, silhouettes)}
                      <img src={phylopicPath(sp, silhouettes)} alt="" class="h-4 w-4 object-contain dark:invert opacity-60" />
                    {/if}
                    <span class="italic truncate max-w-[180px]">{sp}</span>
                  </a>
                </td>
                {#each matrix.genes as g (g)}
                  {@const st = presence.species?.[sp]?.[g]?.status}
                  <td class="py-2 px-2 text-center">
                    <span title={`${g}: ${st || (t('presence.no.call') || 'no call')}`} class="inline-block w-5 h-5 leading-5 rounded text-xs
                      {st === 'FULL' ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                      : st === 'FRAGMENT' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
                      : 'bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-300'}">
                      {st === 'FULL' ? '✓' : st === 'FRAGMENT' ? '~' : '✗'}
                    </span>
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}

  <!-- Stage sections -->
  {#each model?.stages || [] as stage (stage.id)}
    {@const cov = coverage(stage)}
    <section class="space-y-3">
      <div class="flex items-start justify-between gap-4 cursor-pointer" onclick={() => openStage = openStage === stage.id ? null : stage.id}>
        <div>
          <h2 class="text-xl font-semibold text-gray-900 dark:text-white">{tc(`model.spread.${stage.id}.title`) || stage.title}</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-3xl">{tc(`model.spread.${stage.id}.desc`) || stage.desc}</p>
          {#if stage.note}<p class="text-xs text-amber-700 dark:text-amber-400 mt-1">{tc(`model.spread.${stage.id}.note`) || stage.note}</p>{/if}
          {#if stage.reading?.length}
            <div class="flex flex-wrap gap-2 mt-1">
              {#each stage.reading as [book, ch] (ch)}
                <a href="#/papers?q={encodeURIComponent(ch.split(' — ')[0].split('—')[0].trim().slice(0, 40))}"
                   class="text-[11px] px-2 py-1 rounded-full bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900/50"
                   title={`${t('model.reference.reading') || 'Reference reading'}: ${book}`}>📖 {ch}</a>
              {/each}
            </div>
          {/if}
        </div>
        <div class="flex flex-col items-end gap-1 min-w-[140px]">
          <div class="w-full h-2 rounded-full overflow-hidden flex bg-gray-200 dark:bg-gray-700">
            <div class="bg-green-500" style="width: {100 * cov.green / (cov.green + cov.amber + cov.red)}%"></div>
            <div class="bg-amber-400" style="width: {100 * cov.amber / (cov.green + cov.amber + cov.red)}%"></div>
            <div class="bg-red-400" style="width: {100 * cov.red / (cov.green + cov.amber + cov.red)}%"></div>
          </div>
          <span class="text-[10px] text-gray-500 dark:text-gray-400">{cov.green} {t('routes_Model.studied') || 'studied'} · {cov.amber} {t('routes_Model.mentioned') || 'mentioned'} · {cov.red} {t('model.gap') || 'gap'}</span>
        </div>
      </div>
      {#if openStage === stage.id || true}
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {#each stage.genes as [sym, note] (sym)}
            {@const b = badge(sym)}
            {@const pst = presenceLabel(sym)}
            {@const pcls = presenceChip(sym)}
            <button
              onclick={() => geneEvidence = geneEvidence?.sym === sym ? null : { sym, note }}
              class="flex items-center justify-between gap-2 p-2.5 rounded-lg border bg-white dark:bg-gray-800 hover:shadow-md transition-shadow text-left {pcls || 'border-gray-200 dark:border-gray-700'}"
              title={selSpecies ? `${sym} — ${pst || (t('presence.no.call') || 'no call')} in ${SPECIES_COMMON[selSpecies]}` : sym}
            >
              <div class="min-w-0">
                <div class="font-mono text-sm font-semibold text-gray-900 dark:text-white">{sym}</div>
                <div class="text-[11px] text-gray-500 dark:text-gray-400 truncate">{tc(`model.spread.${stage.id}.${sym}`) || note}</div>
              </div>
              <div class="flex flex-col items-end gap-0.5 shrink-0">
                {#if pst === 'absent'}
                  <span class="text-[10px] px-1.5 py-0.5 rounded-full bg-red-600 text-white">absent</span>
                {:else if pst === 'fragment'}
                  <span class="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500 text-white">fragment</span>
                {/if}
                <span class="text-[10px] px-1.5 py-0.5 rounded-full whitespace-nowrap {b.cls}">{b.label}</span>
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </section>
  {/each}

  <!-- Gene evidence drawer (species-aware, D74) -->
  {#if geneEvidence}
    {@const ev = absenceEvidence(geneEvidence.sym)}
    <div class="fixed inset-x-0 bottom-0 z-40 bg-white dark:bg-gray-800 border-t-2 border-blue-500 shadow-2xl p-4 max-h-[45vh] overflow-y-auto">
      <div class="max-w-5xl mx-auto">
        <div class="flex items-start justify-between gap-4">
          <div>
            <div class="font-mono text-lg font-bold text-gray-900 dark:text-white">
              {geneEvidence.sym}
              {#if selSpecies}
                <span class="text-sm font-normal text-gray-500 dark:text-gray-400">
                  in {SPECIES_COMMON[selSpecies]} — {presenceLabel(geneEvidence.sym) || (t('presence.no.call') || 'no call')}
                </span>
              {/if}
            </div>
            <div class="text-sm text-gray-600 dark:text-gray-300">{geneEvidence.note}</div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <a href="#/genes/{geneEvidence.sym}" class="text-xs text-blue-600 dark:text-blue-400 hover:underline">{t('routes.modelmermaid.gene.page') || 'gene page →'}</a>
            <button class="text-gray-500 dark:text-gray-400 hover:text-gray-600 text-xl leading-none" onclick={() => geneEvidence = null}>×</button>
          </div>
        </div>

        {#if ev.length}
          <div class="mt-3 space-y-2">
            <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              Literature — absence/loss-of-function evidence ({SPECIES_CLASS[selSpecies] || 'avian'})
            </div>
            {#each ev as r}
              <div class="text-sm border-l-2 {r.exact ? 'border-blue-500' : 'border-gray-300 dark:border-gray-600'} pl-3">
                <div class="text-gray-900 dark:text-gray-100">
                  <span class="font-medium">{r.manipulation}</span> in <span class="italic">{r.host}</span>
                  — {r.phenotype}
                </div>
                <div class="text-xs text-gray-500 dark:text-gray-400 flex flex-wrap items-center gap-2 mt-0.5">
                  <span class="px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 {r.exact ? 'text-blue-600 dark:text-blue-300 font-medium' : ''}">{r.tag}</span>
                  <a href="#/papers/{r.paper_id}" class="text-blue-600 dark:text-blue-400 hover:underline">[{r.paper_id}{r.year ? ', ' + r.year : ''}]</a>
                </div>
                {#if r.quote}
                  <div class="text-xs text-gray-500 dark:text-gray-400 italic mt-0.5">“{r.quote}”</div>
                {/if}
              </div>
            {/each}
          </div>
          <!-- curated speculation shown ONLY with literature backing (D74 q8) -->
          {#if presence?.gene_catalogue?.[geneEvidence.sym]?.impact_if_absent}
            <div class="mt-3 text-sm text-gray-600 dark:text-gray-300 bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 border border-amber-200 dark:border-amber-800">
              <span class="text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">{t('routes.modelmermaid.curated.hypothesis.not.species') || 'Curated hypothesis (not species-specific)'}</span>
              <div class="mt-1">{presence.gene_catalogue[geneEvidence.sym].impact_if_absent}</div>
            </div>
          {/if}
        {:else if selSpecies}
          <div class="mt-3 text-sm text-gray-500 dark:text-gray-400">
            No {SPECIES_CLASS[selSpecies] || 'avian'} literature absence evidence mined yet for this gene.
            {#if presence?.gene_catalogue?.[geneEvidence.sym]?.impact_if_absent}
              <span class="text-xs">{t('model.speculation.hidden') || '(Curated speculation exists but is hidden without literature backing — see gene page.)'}</span>
            {/if}
          </div>
        {:else}
          <div class="mt-3 text-sm text-gray-500 dark:text-gray-400">{t('model.select.species') || 'Select a species above to see literature absence evidence.'}</div>
        {/if}
      </div>
    </div>
  {/if}

  <!-- Cross-cutting axes -->
  <section class="space-y-3">
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white">Cross-cutting axes</h2>
    <div class="grid md:grid-cols-3 gap-3">
      {#each model?.axes || [] as axis (axis.id)}
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <h3 class="font-semibold text-gray-900 dark:text-white text-sm">{axis.title}</h3>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{axis.desc}</p>
          {#if axis.genes.length}
            <div class="flex flex-wrap gap-1 mt-2">
              {#each axis.genes as g}
                <a href="#/genes/{g}" class="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 hover:bg-blue-100 dark:hover:bg-blue-900/40 font-mono">{g}</a>
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  </section>


    <!-- Additions ledger (verification campaign: 373 adds clustered) -->
    {#if model?.additions?.length}
      <section class="space-y-2">
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-semibold text-gray-900 dark:text-white">{t('model.lit.adds') || 'What the literature adds'}</h2>
          <span class="text-xs text-gray-500 dark:text-gray-400">verification campaign · {model.version || 'v0.6'} · 373 adds clustered</span>
        </div>
        <div class="grid md:grid-cols-2 gap-2">
          {#each model.additions as a (a.topic)}
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4 border-green-400">
              <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">{a.topic} <span class="text-[10px] font-mono text-gray-500 dark:text-gray-400">· {a.stage}</span></div>
              <p class="text-sm text-gray-700 dark:text-gray-300">{a.statement}</p>
              <div class="flex flex-wrap gap-2 mt-2 text-[11px]">
                {#each a.citations as pid}
                  <a href="#/papers/{pid}" class="text-blue-600 dark:text-blue-400 hover:underline">[{pid}]</a>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      </section>
    {/if}

  <!-- Gaps -->
  <section class="space-y-3">
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white">Gap registry</h2>
    <div class="grid md:grid-cols-2 gap-2">
      {#each model?.gaps || [] as g (g.id)}
        <div class="flex items-center justify-between gap-2 p-3 rounded-lg border {g.kind === 'lit-search'
          ? 'border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20'
          : 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20'}">
          <div class="min-w-0">
            <div class="text-sm text-gray-900 dark:text-white">
              <span class="font-mono text-[10px] opacity-60 mr-1">{g.id}</span>
              {g.what}
            </div>
            <div class="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">
              {g.kind === 'lit-search' ? 'lit-search target — evidence likely exists' : 'true gap — little/no literature'}
            </div>
          </div>
          {#if g.sym}
            <a href="#/genes/{g.sym}" class="text-[10px] px-2 py-1 rounded bg-white dark:bg-gray-800 shadow text-blue-600 dark:text-blue-400 whitespace-nowrap">{t('routes.modelmermaid.view.gene') || 'view gene →'}</a>
          {/if}
        </div>
      {/each}
    </div>
  </section>

  <!-- Disagreements -->
  <section class="space-y-3">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">{t('model.lit.disagrees') || 'Where the literature disagrees'}</h2>
      <span class="text-xs text-gray-500 dark:text-gray-400">synthesis engine · unverified · triage required</span>
    </div>

    <!-- Verification-campaign diverges (grounded quotes in model_verdicts.jsonl) -->
    {#if (model?.diverges?.length) || (spreadModel?.diverges?.length)}
      <div class="space-y-2">
        {#if model?.diverges?.length}
          <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Infection model · verification campaign v{model.version || '0.6'}</div>
        {/if}
        {#each model?.diverges || [] as d (d.topic)}
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4 border-red-400">
            <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">{d.topic} <span class="text-[10px] font-mono text-gray-500 dark:text-gray-400">· {d.stage}</span></div>
            <p class="text-sm text-gray-700 dark:text-gray-300">{#each splitCitations(d.statement) as part}{#if part.pid}<a href="#/papers/{part.pid}" class="text-blue-600 dark:text-blue-400 hover:underline">[{part.pid}]</a>{:else}{part.text}{/if}{/each}</p>
          </div>
        {/each}
        {#if spreadModel?.diverges?.length}
          <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide pt-2">Spread model · verification campaign v{spreadModel.version || '0.3'}</div>
        {/if}
        {#each spreadModel?.diverges || [] as d (d.topic)}
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4 border-red-400">
            <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">{d.topic} <span class="text-[10px] font-mono text-gray-500 dark:text-gray-400">· {d.stage}</span></div>
            <p class="text-sm text-gray-700 dark:text-gray-300">{#each splitCitations(d.statement) as part}{#if part.pid}<a href="#/papers/{part.pid}" class="text-blue-600 dark:text-blue-400 hover:underline">[{part.pid}]</a>{:else}{part.text}{/if}{/each}</p>
          </div>
        {/each}
      </div>
    {/if}
    {#if insights.filter(i => i.kind === 'contradiction' || i.kind === 'temporal').length === 0}
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 text-sm text-gray-500 dark:text-gray-400">
        {t('model.no.contradictions') || 'No contradictions mined yet — run'}
        <code class="text-xs bg-gray-100 dark:bg-gray-700 px-1 rounded">synthesize.py --strategy contradiction</code>
        {t('model.to.populate') || 'to populate this panel.'}
      </div>
    {:else}
      <div class="space-y-2">
        {#each insights.filter(i => i.kind === 'contradiction' || i.kind === 'temporal') as ins}
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
            <p class="text-sm text-gray-900 dark:text-white">{ins.insight}</p>
            <div class="flex flex-wrap gap-2 mt-2 text-[11px] text-blue-600 dark:text-blue-400">
              {#each ins.papers as pid, j}
                <span title={ins.titles?.[j]}>{pid}</span>
              {/each}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </section>
  {/if}
</div>
