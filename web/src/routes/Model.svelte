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
  import ModelCyto from './ModelCyto.svelte';
  import SpreadCyto from './SpreadCyto.svelte';
  import SpeciesSearch from '../lib/components/common/SpeciesSearch.svelte';
  import { t, tc, ft } from '../lib/stores/i18n.svelte.js';
  import { phylopicIndex, phylopicPath } from '../lib/utils/phylopic.js';
  import { db } from '../lib/stores/db.js';
  import { fetchGeneCatalogue, pivotCallsBySpecies } from '../lib/utils/presence.js';

  let model = $state(null);
  let counts = $state(null);
  let insights = $state([]);
  let presence = $state(/** @type {any | null} */ (null));
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
      // Presence matrix from DuckDB — only the sensor genes (+aliases),
      // not the whole table (Phase 2 Step 3)
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
    if (c.studied >= 2) return { cls: 'bg-green-100 text-green-700 dark:text-green-400 dark:bg-green-900/30 dark:text-green-300', label: t('model.n_papers', {n: c.papers}) };
    if (c.studied === 1) return { cls: 'bg-green-100 text-green-700 dark:text-green-400 dark:bg-green-900/30 dark:text-green-300', label: t('model.one_study') };
    return { cls: 'bg-amber-100 text-amber-700 dark:text-amber-400 dark:bg-amber-900/30 dark:text-amber-300', label: t('model.n_mentions', {n: c.papers}) };
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

  // --- sensor-matrix table state: search + column sort + pagination ---
  const STATUS_RANK = { FULL: 2, FRAGMENT: 1 };
  let matrixQuery = $state('');
  let matrixPage = $state(0);
  let matrixPageSize = $state(25);
  let matrixSortKey = $state('species'); // 'species' or a gene symbol
  let matrixSortDir = $state(1);         // 1 = asc; gene columns default desc (FULL first)
  const matrixRows = $derived.by(() => {
    if (!matrix) return [];
    const q = matrixQuery.trim().toLowerCase();
    let list = matrix.species;
    if (q) list = list.filter((sp) => sp.toLowerCase().includes(q));
    const dir = matrixSortDir;
    const key = matrixSortKey;
    list = [...list].sort((a, b) => {
      if (key === 'species') return dir * a.localeCompare(b);
      const ra = STATUS_RANK[presence.species?.[a]?.[key]?.status] ?? 0;
      const rb = STATUS_RANK[presence.species?.[b]?.[key]?.status] ?? 0;
      return dir * (rb - ra) || a.localeCompare(b);
    });
    return list;
  });
  const matrixPageCount = $derived(
    Math.max(1, Math.ceil(matrixRows.length / matrixPageSize)));
  $effect(() => { matrixQuery; matrixPage = 0; });
  function matrixSort(k) {
    if (matrixSortKey === k) matrixSortDir = -matrixSortDir;
    else { matrixSortKey = k; matrixSortDir = k === 'species' ? 1 : -1; }
  }
  const matrixAriaSort = (k) =>
    matrixSortKey === k ? (matrixSortDir === 1 ? 'ascending' : 'descending') : 'none';

  let diagramView = $state('recognition'); // recognition | signalling | storm | viral

  // Literature-backed mechanism edges (from pathway_edges.json — the
  // aggregation layer). Automatically enriches when build_aggregation.py
  // re-runs with more verified mechanisms.
  let pathwayEdges = $state(null);
  onMount(async () => {
    try {
      const r = await fetch('data/pathway_edges.json');
      if (r.ok) pathwayEdges = await r.json();
    } catch { /* panel stays hidden */ }
  });
  // per-gene evidence counts (for view genes without mechanism edges)
  let geneEvCounts = $state(null);
  onMount(async () => {
    try {
      const r = await fetch('data/gene_evidence_counts.json');
      if (r.ok) geneEvCounts = await r.json();
    } catch { /* stays hidden */ }
  });
  // genes visible in each diagram view (for filtering edges)
  const LIT_VIEW_GENES = {
    recognition: ['DDX58', 'IFIH1', 'TLR3', 'TLR7', 'TLR21', 'MAVS', 'TRIM25', 'OASL', 'UNC93B1', 'TRIF', 'MYD88', 'ST6GAL1', 'ST3GAL4', 'HA', 'NA', 'FURIN'],
    signalling: ['MAVS', 'TBK1', 'IRF3', 'IRF7', 'IFNB', 'IFNA', 'NFKB', 'NFKB1', 'RELA', 'MYD88', 'STAT1', 'STAT2', 'IRAK', 'DDX58', 'IFIH1', 'TLR3', 'TLR7'],
    storm: ['IL6', 'TNF', 'IL1B', 'IL10', 'SOCS1', 'NFKB', 'NFKB1', 'RELA', 'STAT3', 'CCL2', 'CXCL10', 'IL6', 'TNF'],
    viral: ['NS1', 'PB2', 'PB1', 'PA', 'NP', 'HA', 'NA', 'M1', 'M2', 'ANP32A', 'NEP', 'PB1-F2', 'PA-X'],
  };
  // relevant edges AND papers for the current view's genes
  const relevantEdges = $derived.by(() => {
    if (!pathwayEdges?.edges || !LIT_VIEW_GENES[diagramView]) return [];
    const genes = new Set(LIT_VIEW_GENES[diagramView]);
    return pathwayEdges.edges.filter(e => genes.has(e.from) || genes.has(e.to));
  });
  // papers for view genes that have evidence but no mechanism edges
  const relevantPapers = $derived.by(() => {
    if (!geneEvCounts || !LIT_VIEW_GENES[diagramView]) return [];
    const genes = new Set(LIT_VIEW_GENES[diagramView]);
    const edgeGenes = new Set(relevantEdges.flatMap(e => [e.from, e.to]));
    return [...genes].filter(g => !edgeGenes.has(g) && geneEvCounts[g]);
  });

  // Key model genes surfaced per diagram view — the species context
  // subgraph annotates these with the selected species' presence calls so
  // the mermaid visibly re-renders on species change (D122).
  const VIEW_GENES = {
    recognition: ['RIG-I', 'MDA5', 'TLR3', 'IFITM3'],
    signalling: ['JAK1', 'IRF3', 'OASL', 'IFITM3'],
    storm: ['IL6', 'TNF', 'IL1B', 'NLRP3', 'SOCS1', 'IL10'],
    viral: ['ANP32A', 'OASL', 'JAK1', 'IRF3', 'NLRP3'],
  };
  const SPECIES_EMOJI = {
    'Anas platyrhynchos': '🦆', 'Gallus gallus': '🐔',
    'Strigops habroptila': '🦜', 'Nestor notabilis': '🦜',
    'Apteryx mantelli': '🥝', 'Mus musculus': '🐁',
  };

  /** Mermaid fragment annotating a view's genes with the selected
      species' presence calls — appended to the static diagram source. */
  function speciesContextBlock(view) {
    if (!selSpecies) return '';
    const rows = (VIEW_GENES[view] || [])
      .map((g) => ({ gene: g, label: presenceLabel(g) }))
      .filter((r) => r.label);
    if (!rows.length) return '';
    const name = SPECIES_COMMON[selSpecies] || selSpecies;
    const emoji = SPECIES_EMOJI[selSpecies] || '🧬';
    const nodes = rows.map((r, i) => {
      const id = `SPCTX_${view.toUpperCase()}_${i}`;
      const mark = r.label === 'present' ? '✓' : r.label === 'fragment' ? '◌' : '✗';
      return `    ${id}["${r.gene} — ${r.label} ${mark}"]`;
    }).join('\n');
    const classes = rows.map((r, i) => {
      const id = `SPCTX_${view.toUpperCase()}_${i}`;
      const cls = r.label === 'present' ? 'sppresent'
        : r.label === 'fragment' ? 'spfrag' : 'spabsent';
      return `  class ${id} ${cls}`;
    }).join('\n');
    return `\n  subgraph spctx_${view}["${emoji} ${name} — species context"]\n${nodes}\n  end\n  classDef sppresent fill:#dcfce7,stroke:#16a34a,color:#14532d\n  classDef spabsent fill:#fecaca,stroke:#dc2626,color:#7f1d1d\n  classDef spfrag fill:#ffedd5,stroke:#d97706,color:#7c2d12\n${classes}\n`;
  }

  const STATIC_DIAGRAMS = {
    recognition: `flowchart TD
      subgraph surface["📍 Cell Surface — Entry"]
        ST3GAL4["ST3GAL4<br/>α2,3 sialyltransferase<br/>🦆 AVIAN RECEPTOR"]
        ST6GAL1["ST6GAL1<br/>α2,6 sialyltransferase<br/>HUMAN-TYPE RECEPTOR"]
        SA23["α2,3 sialic acid<br/>AVIAN RECEPTOR"]
        SA26["α2,6 sialic acid<br/>HUMAN-TYPE RECEPTOR"]
        ST3GAL4 --> SA23
        ST6GAL1 --> SA26
        HA["🦠 Viral HA binds"] --> SA23
        HA -.->|switch| SA26
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
      subgraph counter["🦠 {t('model.view.antagonism') || 'Viral Antagonism'} Arsenal"]
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

  // D122: diagrams are now species-aware — choosing a species appends a
  // context subgraph with per-gene presence calls, so the mermaid visibly
  // re-renders (previously a static const: species selection did nothing).
  let diagrams = $derived.by(() => {
    const out = {};
    for (const [key, src] of Object.entries(STATIC_DIAGRAMS)) {
      out[key] = src + speciesContextBlock(key);
    }
    return out;
  });
  // --- Species differences (D122): reference species vs selected ---
  let refSpecies = $state('Gallus gallus');
  const SPECIES_PHENOTYPE = {
    'Anas platyrhynchos': { label: '🦆 ' + t('model.pheno.tolerant'), note: t('model.pheno.tolerant.note') },
    'Gallus gallus': { label: '🐔 ' + t('model.pheno.susceptible'), note: t('model.pheno.susceptible.note') },
    'Mus musculus': { label: '🐁 ' + t('model.pheno.mammalian'), note: t('model.pheno.mammalian.note') },
  };

  function presenceLabelFor(sp, sym) {
    if (!sp || !presence?.species?.[sp]) return null;
    const call = presence.species[sp][sym] || presence.species[sp][aliasOf(sym)];
    const st = call?.status;
    if (!st) return null;
    if (st === 'NOT_FOUND' || st === 'E2') return 'absent';
    if (st === 'FRAGMENT' || st === 'E3') return 'fragment';
    return 'present';
  }

  let diffGenes = $derived.by(() => {
    if (!selSpecies || !refSpecies || selSpecies === refSpecies) return [];
    const genes = new Set([
      ...Object.keys(presence?.species?.[refSpecies] || {}),
      ...Object.keys(presence?.species?.[selSpecies] || {}),
    ]);
    const rows = [];
    for (const g of genes) {
      const a = presenceLabelFor(refSpecies, g);
      const b = presenceLabelFor(selSpecies, g);
      if (!a || !b || a === b) continue;
      rows.push({ gene: g, ref: a, sel: b });
    }
    const rank = { absent: 0, fragment: 1, present: 2 };
    rows.sort((x, y) => (rank[x.sel] - rank[y.sel]) || x.gene.localeCompare(y.gene));
    return rows;
  });

  const DIFF_BADGE = {
    absent: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    fragment: 'bg-amber-100 text-amber-700 dark:text-amber-400 dark:bg-amber-900/30 dark:text-amber-300',
    present: 'bg-green-100 text-green-700 dark:text-green-400 dark:bg-green-900/30 dark:text-green-300',
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
      {t('model.badges') || 'Badges:'} <span class="text-green-700 dark:text-green-400">{t('routes_Model.studied')}</span>,
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
        : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'}"
      onclick={() => { modelTab = 'infection'; updateParams({ tab: 'infection' }); }}
    >
      🧬 {t('model.infection')}
    </button>
    <button
      class="px-4 py-2 font-medium text-sm border-b-2 transition-colors {modelTab === 'spread'
        ? 'border-blue-600 text-blue-600 dark:text-blue-400'
        : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'}"
      onclick={() => { modelTab = 'spread'; updateParams({ tab: 'spread' }); }}
    >
      🌍 {t('model.spread')}
    </button>
    <a href="#/vaccines" data-testid="nav-vaccines-tab"
       class="px-4 py-2 font-medium text-sm border-b-2 border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors">
      💉 {t('model.vaccine')} →
    </a>
  </div>

  <!-- SPREAD MODEL TAB -->
  {#if modelTab === 'spread' && spreadModel}
    <section class="space-y-6">
      <div>
        <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-2">{t('routes.model.spread.migration.model') || 'H5N1 Spread & Migration Model'}</h2>
        <p class="text-sm text-gray-500 dark:text-gray-400 max-w-3xl">
          {t('spread.intro') || 'How H5N1 moves through wild bird populations, poultry systems, and into mammals.'}
          {t('spread.built.from') || 'Built from'} {spreadModel.source}. {t('spread.each.stage.links') || 'Each stage links to the papers that inform it.'}
          <a href="#/spread-cyto" class="text-blue-600 dark:text-blue-400 underline ml-1">{t('routes.model.view.as.interactive.graph') || 'View as interactive graph (beta) →'}</a>
          <a href="#/spread-layers" class="text-blue-600 dark:text-blue-400 underline ml-2">{t('spread.layers.link') || 'Eras & host competence →'}</a>
        </p>
      </div>

      <!-- Overview diagram — DEPRECATED mermaid render (2026-10-15):
           the inline flowchart source below is kept for reference but NO
           LONGER RENDERED (unreferenced → tree-shaken). The interactive
           SpreadCyto viewer replaces it (timeline scrubber, per-edge
           corpus evidence drawers, era bands). -->
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-2 sm:p-4">
        <SpreadCyto embedded />
      </div>

      <!-- Stage sections -->
      {#each spreadModel.stages as stage (stage.id)}
        {@const stagePapers = (() => {
          const ev = spreadModel.evidence?.edges ?? {};
          const ids = new Set();
          for (const [key, b] of Object.entries(ev)) {
            const [from, to] = key.split('->');
            if (from === stage.id || to === stage.id) for (const p of b.papers ?? []) ids.add(p);
          }
          return ids.size;
        })()}
        <section class="space-y-3">
          <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-white">{tc(`model.spread.${stage.id}.title`) || stage.title}</h3>
            {#if stagePapers}
              <span class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300" title={t('model.spread.stage.papers.tip')}>
                {stagePapers.toLocaleString()} {t('model.spread.evidence.papers')}
              </span>
            {/if}
            <p class="basis-full text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-3xl">{tc(`model.spread.${stage.id}.desc`) || stage.desc}</p>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {#each stage.elements as [name, note] (name)}
              <div class="p-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                <div class="font-medium text-gray-900 dark:text-white text-sm">{name}</div>
                <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">{note}</div>
              </div>
            {/each}
          </div>
        </section>
      {/each}

      <!-- Connections (enriched with v2 corpus evidence) -->
      <section class="space-y-3">
        <div class="flex flex-wrap items-baseline justify-between gap-2">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white">{t('model.spread.connections.title') || 'Stage connections'}</h3>
          {#if spreadModel.evidence?.provenance}
            <span class="text-xs text-gray-500 dark:text-gray-400">
              {Object.values(spreadModel.evidence.edges).reduce((n, e) => n + e.count, 0).toLocaleString()}
              {t('model.spread.evidence.links')} · <a class="underline hover:text-blue-600 dark:hover:text-blue-400" href="#/spread-layers">{t('spread.layers.link') || 'Eras & host competence →'}</a>
            </span>
          {/if}
        </div>
        <div class="space-y-2.5">
          {#each spreadModel.connections as c}
            {@const ev = spreadModel.evidence?.edges?.[`${c.from}->${c.to}`]}
            <div class="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-sm">
              <span class="font-mono text-xs text-blue-600 dark:text-blue-400">{c.from}</span>
              <span class="text-gray-500 dark:text-gray-400">→</span>
              <span class="font-mono text-xs text-blue-600 dark:text-blue-400">{c.to}</span>
              <span class="text-gray-500 dark:text-gray-400 text-xs">{c.note}</span>
              {#if ev}
                <span class="text-xs px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-950/50 text-blue-700 dark:text-blue-300" title={t('model.spread.evidence.papers.tip')}>
                  {ev.count.toLocaleString()} {t('model.spread.evidence.papers')}{#if ev.grounded} · {ev.grounded.toLocaleString()} {t('model.spread.evidence.grounded')}{/if}
                </span>
                {@const pars = spreadModel.evidence?.parameters?.[`${c.from}->${c.to}`]?.summary}
                {#if pars?.n_params}
                  <span class="text-xs px-1.5 py-0.5 rounded bg-purple-50 dark:bg-purple-950/50 text-purple-700 dark:text-purple-300" title={t('model.spread.params.tip')}>
                    {t('model.spread.params.chip', { n: pars.n_params })}{#if pars.min != null && pars.max != null} · {pars.min}–{pars.max}{/if}
                  </span>
                {/if}
                {#each Object.keys(ev.mechanisms ?? {}) as sec (sec)}
                  <span class="text-xs px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">{sec}</span>
                {/each}
                {#if ev.contested}
                  <span class="text-xs px-1.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300" title={t('model.spread.evidence.contested.tip')}>★ {t('model.spread.evidence.contested')}</span>
                {/if}
              {:else if spreadModel.evidence}
                <span class="text-xs text-gray-400">{t('model.spread.evidence.none')}</span>
              {/if}
            </div>
          {/each}
        </div>
        {#if spreadModel.evidence?.provenance}
          <p class="text-sm text-gray-400">{spreadModel.evidence.provenance}</p>
        {/if}
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
              <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">{a.topic} <span class="text-xs font-mono text-gray-500 dark:text-gray-400">· {a.stage}</span></div>
              <p class="text-sm text-gray-700 dark:text-gray-300">{a.statement}</p>
              <div class="flex flex-wrap gap-2 mt-2 text-sm">
                {#each a.citations as pid}
                  <a href="#/papers/{pid}" class="text-blue-600 dark:text-blue-400 underline">[{pid}]</a>
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
            <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">{d.topic} <span class="text-xs font-mono text-gray-500 dark:text-gray-400">· {d.stage}</span></div>
            <p class="text-sm text-gray-700 dark:text-gray-300">{#each splitCitations(d.statement) as part}{#if part.pid}<a href="#/papers/{part.pid}" class="text-blue-600 dark:text-blue-400 underline">[{part.pid}]</a>{:else}{part.text}{/if}{/each}</p>
          </div>
        {/each}
      </section>
    {/if}
  </section>
  {/if}

  <!-- INFECTION MODEL CONTENT (existing, shown when modelTab === 'infection') -->
  <div class="flex justify-end">
    <a href="#/model-cyto" class="text-xs px-3 py-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-300 hover:shadow">
      ⚡ {t('model.cyto.link') || 'Try the interactive graph (Cytoscape)'} →
    </a>
  </div>
  {#if modelTab === 'infection' && !model}
    <div class="animate-pulse py-16"><div class="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div></div>
  {:else if modelTab === 'infection'}

  <!-- Diagram sub-view selector -->
  <div class="flex flex-wrap gap-2">
    {#each Object.entries({recognition: `📍 ${t('model.view.entry') || 'Entry & Sensing'}`, signalling: `📡 ${t('model.view.ifn') || 'IFN Response'}`, storm: `🔴 ${t('model.view.cytokine') || 'Cytokine Storm'}`, viral: `🦠 ${t('model.view.antagonism') || 'Viral Antagonism'}`}) as [key, label]}
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
    <span class="text-sm font-medium text-gray-700 dark:text-gray-300">{t('model.species.context') || 'Species context:'}</span>
    <SpeciesSearch
      bind:value={selSpecies}
      species={Object.keys(presence?.species || {})}
      commonNames={SPECIES_COMMON}
      placeholder={t('routes.model.search.species') || 'Search species… (254)'}
      onPick={() => (geneEvidence = null)}
    />
    {#if selSpecies}
      <span class="text-xs text-gray-500 dark:text-gray-400">
        {SPECIES_ORDER[selSpecies] || ''} · {t('model.species_strip.legend')}
      </span>
      <a href="#/species-full/{encodeURIComponent(selSpecies)}" class="text-xs text-blue-600 dark:text-blue-400 underline">{t('model.full_gene_panel')}</a>
    {/if}
  </div>

  <!-- Species differences (D122): reference vs selected, presence-level
       contrast + phenotype framing — the "what actually differs" answer -->
  {#if selSpecies}
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
      <div class="flex flex-wrap items-center gap-3 mb-3">
        <h3 class="text-sm font-semibold text-gray-900 dark:text-white">{t('model.species_differences')}</h3>
        <div class="flex items-center gap-2 text-sm">
          <span class="text-gray-500 dark:text-gray-400 text-xs">{t('model.compare')}</span>
          <SpeciesSearch
            bind:value={refSpecies}
            species={Object.keys(presence?.species || {}).filter(sp => sp !== selSpecies)}
            commonNames={SPECIES_COMMON}
            allowEmpty={false}
            placeholder={t('model.reference_species')}
          />
          <span class="text-gray-500 dark:text-gray-400 text-xs">↔ {SPECIES_COMMON[selSpecies] || selSpecies}</span>
        </div>
        {#if diffGenes.length}
          <span class="px-2 py-0.5 text-xs rounded-full bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">
            {diffGenes.length} gene{diffGenes.length !== 1 ? 's' : ''} differ
          </span>
        {/if}
      </div>
      <div class="grid md:grid-cols-2 gap-3 mb-3">
        {#each [refSpecies, selSpecies] as sp}
          <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-2.5">
            <div class="text-sm font-medium text-gray-900 dark:text-white">{SPECIES_COMMON[sp] || sp}</div>
            {#if SPECIES_PHENOTYPE[sp]}
              <div class="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                <span class="font-semibold">{SPECIES_PHENOTYPE[sp].label}</span> — {SPECIES_PHENOTYPE[sp].note}
              </div>
            {:else}
              <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{t('model.not_curated')}</div>
            {/if}
          </div>
        {/each}
      </div>
      {#if diffGenes.length}
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-xs text-gray-500 dark:text-gray-400 uppercase">
                <th class="py-1.5 pr-3">Gene</th>
                <th class="py-1.5 pr-3">{SPECIES_COMMON[refSpecies] || refSpecies}</th>
                <th class="py-1.5 pr-3">{SPECIES_COMMON[selSpecies] || selSpecies}</th>
                <th class="py-1.5">Δ</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
              {#each diffGenes.slice(0, 24) as d}
                <tr>
                  <td class="py-1.5 pr-3">
                    <a href="#/genes/{d.gene}" class="text-blue-600 dark:text-blue-400 underline font-medium">{d.gene}</a>
                  </td>
                  <td class="py-1.5 pr-3"><span class="px-1.5 py-0.5 text-xs rounded {DIFF_BADGE[d.ref]}">{d.ref}</span></td>
                  <td class="py-1.5 pr-3"><span class="px-1.5 py-0.5 text-xs rounded {DIFF_BADGE[d.sel]}">{d.sel}</span></td>
                  <td class="py-1.5 text-xs text-gray-500 dark:text-gray-400">{d.ref} → {d.sel}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        {#if diffGenes.length > 24}
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">+ {diffGenes.length - 24} more — see the sensor matrix below</p>
        {/if}
      {:else}
        <p class="text-sm text-gray-500 dark:text-gray-400">
          No presence-call differences against {SPECIES_COMMON[refSpecies] || refSpecies} —
          these species share the same gene panel calls.
        </p>
      {/if}
    </div>
  {/if}

  <!-- Literature-backed mechanism edges for this view -->
  {#if relevantEdges.length > 0}
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4 mb-4">
      <div class="flex items-center justify-between mb-2">
        <h2 class="text-xs font-semibold text-gray-600 dark:text-gray-300">
          📚 {t('model.lit.mechanisms') || 'Literature-backed mechanisms in this view'}
          <span class="font-normal text-gray-500 dark:text-gray-400">({t('model.edges_from_papers', {e: relevantEdges.length, p: new Set(relevantEdges.map(e2 => e2.paper_id)).size})})</span>
        </h2>
        <span class="text-[9px] px-1.5 py-0.5 rounded bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300 font-medium">{t('model.auto_extracted')}</span>
      </div>
      <div class="space-y-1 max-h-40 overflow-y-auto">
        {#each relevantEdges.slice(0, 10) as e, i (i)}
          <div class="flex items-start gap-2 text-xs">
            <span class="font-mono font-semibold text-teal-700 dark:text-teal-400 shrink-0">{e.from}</span>
            <span class="text-gray-500 dark:text-gray-400 shrink-0">—{e.interaction}→</span>
            <span class="font-mono font-semibold text-teal-700 dark:text-teal-400 shrink-0">{e.to}</span>
            <span class="text-gray-500 dark:text-gray-400 truncate">{ft(e.eh) || e.effect}</span>
            <a href="#/papers/{e.paper_id}" class="text-blue-600 dark:text-blue-400 underline text-xs shrink-0">[paper]</a>
          </div>
        {/each}
        {#if relevantEdges.length > 10}
          <p class="text-xs text-gray-500 dark:text-gray-400">+{relevantEdges.length - 10} {t('model.more')}</p>
        {/if}
      </div>
      {#if relevantPapers.length > 0}
        <div class="mt-3 pt-2 border-t border-gray-100 dark:border-gray-700">
          <p class="text-xs text-gray-500 dark:text-gray-400 mb-1">{t('model.also.studied') || 'Also studied in this view'} ({relevantPapers.length} genes with papers but no mechanistic edges yet):</p>
          <div class="flex flex-wrap gap-1">
            {#each relevantPapers.slice(0, 12) as gene, i (i)}
              <a href="#/genes/{gene}" class="px-1.5 py-0.5 rounded text-xs bg-teal-50 dark:bg-teal-900/20 text-teal-700 dark:text-teal-400 hover:bg-teal-100">
                {gene} {#if geneEvCounts?.[gene]?.total}{t('model.n_papers', {n: geneEvCounts[gene].total})}{/if}
              </a>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Infection model diagram — DEPRECATED mermaid render (2026-10-15):
       the diagrams{} sources in the script are kept for reference but NO
       LONGER RENDERED; unreferenced, they tree-shake out of the live
       bundle. The interactive Cytoscape viewer replaces them (pan/zoom,
       per-species presence styling, tap-to-drawer evidence). The view
       chips above now filter only the literature-evidence panel. -->
  <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-2 sm:p-4">
    <ModelCyto embedded />
  </div>

  <!-- Sensor matrix -->
  {#if matrix}
    <section class="space-y-3">
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">Sensor matrix — {matrixRows.length.toLocaleString()}/{matrix.species.length.toLocaleString()} species</h2>
      <p class="text-sm text-gray-500 dark:text-gray-400">{t('model.presence.calls') || 'Presence calls from the evidence-ladder pipeline. Click a species for its full gene panel.'}</p>
      <div class="flex flex-wrap items-center gap-3">
        <label class="sr-only" for="matrix-search">{t('spread.competence.search.label')}</label>
        <input id="matrix-search" type="search" class="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm w-64"
          placeholder={t('susceptibility.search.placeholder')} bind:value={matrixQuery} />
        <label class="text-sm text-gray-600 dark:text-gray-300" for="matrix-page-size">{t('matrix.page.size')}</label>
        <select id="matrix-page-size" class="px-2 py-1.5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm" bind:value={matrixPageSize}>
          {#each [25, 50, 100] as n (n)}<option value={n}>{n}</option>{/each}
        </select>
        <span class="text-sm text-gray-500 dark:text-gray-400" aria-live="polite">
          {t('matrix.page.of', { p: Math.min(matrixPage + 1, matrixPageCount), n: matrixPageCount })}
        </span>
      </div>
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow p-4 overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="sticky top-0">
            <tr class="text-left text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
              <th class="py-2 pr-3" aria-sort={matrixAriaSort('species')}>
                <button class="font-semibold underline decoration-dotted" onclick={() => matrixSort('species')}>{t('lib_components_species_SpeciesFullPage.species')}</button>
              </th>
              {#each matrix.genes as g}<th class="py-2 px-2 text-center" aria-sort={matrixAriaSort(g)}>
                <button class="font-semibold underline decoration-dotted" onclick={() => matrixSort(g)}>{presence.gene_catalogue?.[g]?.name || g}</button>
              </th>{/each}
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
            {#each matrixRows.slice(matrixPage * matrixPageSize, (matrixPage + 1) * matrixPageSize) as sp (sp)}
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
      <div class="flex items-center gap-2">
        <button class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-40"
          disabled={matrixPage === 0} onclick={() => (matrixPage = Math.max(0, matrixPage - 1))}>{t('matrix.prev')}</button>
        <button class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-40"
          disabled={matrixPage >= matrixPageCount - 1} onclick={() => (matrixPage = Math.min(matrixPageCount - 1, matrixPage + 1))}>{t('matrix.next')}</button>
      </div>
    </section>
  {/if}

  <!-- Stage sections -->
  {#each model?.stages || [] as stage (stage.id)}
    {@const cov = coverage(stage)}
    <section class="space-y-3">
      <div
        class="flex items-start justify-between gap-4 cursor-pointer"
        role="button"
        tabindex="0"
        aria-expanded={openStage === stage.id}
        onclick={() => (openStage = openStage === stage.id ? null : stage.id)}
        onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openStage = openStage === stage.id ? null : stage.id; } }}
      >
        <div>
          <h2 class="text-xl font-semibold text-gray-900 dark:text-white">{tc(`model.stage.${stage.id}.title`) || stage.title}</h2>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-3xl">{tc(`model.stage.${stage.id}.desc`) || stage.desc}</p>
          {#if stage.note}<p class="text-xs text-amber-700 dark:text-amber-400 mt-1">{tc(`model.stage.${stage.id}.note`) || stage.note}</p>{/if}
        </div>
        <div class="flex flex-col items-end gap-1 min-w-[140px]">
          <div class="w-full h-2 rounded-full overflow-hidden flex bg-gray-200 dark:bg-gray-700">
            <div class="bg-green-500" style="width: {100 * cov.green / (cov.green + cov.amber + cov.red)}%"></div>
            <div class="bg-amber-400" style="width: {100 * cov.amber / (cov.green + cov.amber + cov.red)}%"></div>
            <div class="bg-red-400" style="width: {100 * cov.red / (cov.green + cov.amber + cov.red)}%"></div>
          </div>
          <span class="text-xs text-gray-500 dark:text-gray-400">{cov.green} {t('routes_Model.studied') || 'studied'} · {cov.amber} {t('routes_Model.mentioned') || 'mentioned'} · {cov.red} {t('model.gap') || 'gap'}</span>
        </div>
      </div>
      <!-- reading chips live OUTSIDE the clickable header (no nested
           interactive elements inside a role=button) -->
      {#if stage.reading?.length}
        <div class="flex flex-wrap gap-2 mt-2">
          {#each stage.reading as [book, ch] (ch)}
            <a href="#/papers?q={encodeURIComponent(ch.split(' — ')[0].split('—')[0].trim().slice(0, 40))}"
               class="text-sm px-2 py-1 rounded-full bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900/50"
               title={`Reference reading: ${book}`}>📖 {ch}</a>
          {/each}
        </div>
      {/if}
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
                <div class="text-sm text-gray-500 dark:text-gray-400 truncate">{tc(`model.spread.${stage.id}.${sym}`) || note}</div>
              </div>
              <div class="flex flex-col items-end gap-0.5 shrink-0">
                {#if pst === 'absent'}
                  <span class="text-xs px-1.5 py-0.5 rounded-full bg-red-600 text-white">absent</span>
                {:else if pst === 'fragment'}
                  <span class="text-xs px-1.5 py-0.5 rounded-full bg-amber-500 text-white">fragment</span>
                {/if}
                <span class="text-xs px-1.5 py-0.5 rounded-full whitespace-nowrap {b.cls}">{b.label}</span>
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
            <a href="#/genes/{geneEvidence.sym}" class="text-xs text-blue-600 dark:text-blue-400 underline">{t('routes.model.gene.page') || 'gene page →'}</a>
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
                  <a href="#/papers/{r.paper_id}" class="text-blue-600 dark:text-blue-400 underline">[{r.paper_id}{r.year ? ', ' + r.year : ''}]</a>
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
              <span class="text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">{t('routes.model.curated.hypothesis.not.species') || 'Curated hypothesis (not species-specific)'}</span>
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
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white">{t('model.cross_cutting_axes')}</h2>
    <div class="grid md:grid-cols-3 gap-3">
      {#each model?.axes || [] as axis (axis.id)}
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <h3 class="font-semibold text-gray-900 dark:text-white text-sm">{axis.title}</h3>
          <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{axis.desc}</p>
          {#if axis.genes.length}
            <div class="flex flex-wrap gap-1 mt-2">
              {#each axis.genes as g}
                <a href="#/genes/{g}" class="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-blue-100 dark:hover:bg-blue-900/40 font-mono">{g}</a>
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
              <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">{a.topic} <span class="text-xs font-mono text-gray-500 dark:text-gray-400">· {a.stage}</span></div>
              <p class="text-sm text-gray-700 dark:text-gray-300">{a.statement}</p>
              <div class="flex flex-wrap gap-2 mt-2 text-sm">
                {#each a.citations as pid}
                  <a href="#/papers/{pid}" class="text-blue-600 dark:text-blue-400 underline">[{pid}]</a>
                {/each}
              </div>
            </div>
          {/each}
        </div>
      </section>
    {/if}

  <!-- Gaps -->
  <section class="space-y-3">
    <h2 class="text-xl font-semibold text-gray-900 dark:text-white">{t('model.gap_registry')}</h2>
    <div class="grid md:grid-cols-2 gap-2">
      {#each model?.gaps || [] as g (g.id)}
        <div class="flex items-center justify-between gap-2 p-3 rounded-lg border {g.kind === 'lit-search'
          ? 'border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20'
          : 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20'}">
          <div class="min-w-0">
            <div class="text-sm text-gray-900 dark:text-white">
              <span class="font-mono text-xs opacity-60 mr-1">{g.id}</span>
              {g.what}
            </div>
            <div class="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
              {g.kind === 'lit-search' ? 'lit-search target — evidence likely exists' : 'true gap — little/no literature'}
            </div>
          </div>
          {#if g.sym}
            <a href="#/genes/{g.sym}" class="text-xs px-2 py-1 rounded bg-white dark:bg-gray-800 shadow text-blue-600 dark:text-blue-400 whitespace-nowrap">{t('routes.model.view.gene') || 'view gene →'}</a>
          {/if}
        </div>
      {/each}
    </div>
  </section>

  <!-- Disagreements -->
  <section class="space-y-3">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold text-gray-900 dark:text-white">{t('model.lit.disagrees') || 'Where the literature disagrees'}</h2>
      <span class="text-xs text-gray-500 dark:text-gray-400">{t('model.synthesis_disclaimer')}</span>
    </div>

    <!-- Verification-campaign diverges (grounded quotes in model_verdicts.jsonl) -->
    {#if (model?.diverges?.length) || (spreadModel?.diverges?.length)}
      <div class="space-y-2">
        {#if model?.diverges?.length}
          <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Infection model · verification campaign v{model.version || '0.6'}</div>
        {/if}
        {#each model?.diverges || [] as d (d.topic)}
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4 border-red-400">
            <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">{d.topic} <span class="text-xs font-mono text-gray-500 dark:text-gray-400">· {d.stage}</span></div>
            <p class="text-sm text-gray-700 dark:text-gray-300">{#each splitCitations(d.statement) as part}{#if part.pid}<a href="#/papers/{part.pid}" class="text-blue-600 dark:text-blue-400 underline">[{part.pid}]</a>{:else}{part.text}{/if}{/each}</p>
          </div>
        {/each}
        {#if spreadModel?.diverges?.length}
          <div class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide pt-2">Spread model · verification campaign v{spreadModel.version || '0.3'}</div>
        {/if}
        {#each spreadModel?.diverges || [] as d (d.topic)}
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border-l-4 border-red-400">
            <div class="text-sm font-medium text-gray-900 dark:text-white mb-1">{d.topic} <span class="text-xs font-mono text-gray-500 dark:text-gray-400">· {d.stage}</span></div>
            <p class="text-sm text-gray-700 dark:text-gray-300">{#each splitCitations(d.statement) as part}{#if part.pid}<a href="#/papers/{part.pid}" class="text-blue-600 dark:text-blue-400 underline">[{part.pid}]</a>{:else}{part.text}{/if}{/each}</p>
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
            <div class="flex flex-wrap gap-2 mt-2 text-sm text-blue-600 dark:text-blue-400">
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
