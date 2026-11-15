<script>
  /**
   * CompetenceTable — Layer C matrix: sortable species × evidence table,
   * row click opens the species risk card (Phase 8 goal artifact):
   * measured competence, per-clade stratification, extracted roles,
   * evidence holes, taxonomic proxy for data-poor species.
   */
  import { t } from '../../stores/i18n.svelte.js';
  import { onMount } from 'svelte';
  import { announce } from '../../stores/a11y.svelte.js';
  import Modal from '../common/Modal.svelte';

  let { doc, commonNames, papersIndex, synthesis, vaxDoc } = $props();
  let movement = $state(/** @type {any | null} */ (null));
  onMount(() => {
    fetch('data/movement_lookup.json')
      .then((r) => r.ok ? r.json() : null)
      .then((d) => (movement = d))
      .catch(() => {});
  });
  const cardMovement = $derived.by(() => {
    if (!movement?.species || !card) return null;
    return movement.species[card.species] ?? null;
  });

  let query = $state('');
  let sortKey = $state('papers');
  let sortDir = $state(-1);
  let cardSpecies = $state(null);

  const EVIDENCE = [
    'mortality', 'shedding', 'field_outbreak', 'experimental',
    'surveillance', 'serology', 'susceptibility', 'detections', 'llm_roles',
  ];

  const gapBySpecies = $derived(
    new Map((doc?.coverage?.gap_matrix ?? []).map((g) => [g.species, g]))
  );
  const proxyBySpecies = $derived(
    new Map((doc?.proxies?.for_thin_species ?? []).map((p) => [p.species, p]))
  );

  const rows = $derived.by(() => {
    const q = query.trim().toLowerCase();
    let list = (doc?.species ?? []).map((s) => {
      const g = gapBySpecies.get(s.species);
      return {
        ...s,
        common: commonNames?.get(s.species) ?? '',
        holes: g?.holes ?? null,
        evidence: g?.evidence ?? {},
        filled: g ? EVIDENCE.length - g.holes : null,
      };
    });
    if (q) {
      list = list.filter((s) =>
        (s.species + ' ' + s.common + ' ' + Object.keys(s.llm_roles?.roles ?? {}).join(' ') + ' ' + (s.llm_roles?.clades ?? []).join(' '))
          .toLowerCase()
          .includes(q)
      );
    }
    const dir = sortDir;
    list.sort((a, b) => {
      let av, bv;
      if (sortKey === 'species') {
        return dir * a.species.localeCompare(b.species);
      }
      if (sortKey === 'mortality') {
        av = a.mortality_pct?.median ?? -1;
        bv = b.mortality_pct?.median ?? -1;
      } else if (sortKey === 'roles') {
        av = a.llm_roles?.papers ?? -1;
        bv = b.llm_roles?.papers ?? -1;
      } else {
        av = a.papers?.count ?? 0;
        bv = b.papers?.count ?? 0;
      }
      return dir * (av - bv) || a.species.localeCompare(b.species);
    });
    return list;
  });

  $effect(() => {
    if (doc) announce(t('a11y.announce.species.results', { n: rows.length }));
  });

  function setSort(k) {
    if (sortKey === k) sortDir = -sortDir;
    else {
      sortKey = k;
      sortDir = -1;
    }
  }
  const ariaSort = (k) => (sortKey === k ? (sortDir === -1 ? 'descending' : 'ascending') : 'none');

  const card = $derived(rows.find((r) => r.species === cardSpecies) ?? null);
  const cardProxy = $derived(card ? proxyBySpecies.get(card.species) : null);
  // conservation cross-references: has this species been vaccinated, and
  // does the corpus document population impact for it?
  const cardVax = $derived.by(() => {
    if (!card) return [];
    const sci = card.species.toLowerCase();
    const com = (card.common || '').toLowerCase();
    const genus = sci.split(' ')[0];
    // vaccine_outcomes items are vaccination-only by construction; match on
    // target species (common name / genus / scientific)
    return [...(vaxDoc?.vaccination?.items ?? []),
             ...(vaxDoc?.wild_programs ?? [])]
      .filter((it) => {
        const t = (it.target_species || '').toLowerCase();
        return t.includes(genus) || (com && t.includes(com)) || t.includes(sci);
      });
  });
  const cardImpact = $derived.by(() => {
    if (!card || !synthesis) return [];
    const sci = card.species.toLowerCase();
    const com = (card.common || '').toLowerCase();
    const genus = sci.split(' ')[0];
    return (synthesis.impact_recovery?.items ?? []).filter((it) => {
      const t = (it.species || '').toLowerCase();
      return t.includes(genus) || (com && t.includes(com)) || t.includes(sci);
    });
  });

  function displayName(s) {
    return s.common ? `${s.common} (${s.species})` : s.species;
  }
</script>

<div class="flex flex-wrap items-center gap-3 mb-4">
  <label class="sr-only" for="competence-search">{t('spread.competence.search.label')}</label>
  <input
    id="competence-search"
    type="search"
    class="px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-sm w-64"
    placeholder={t('spread.competence.search.placeholder')}
    bind:value={query}
  />
  <span class="text-sm text-slate-500 dark:text-slate-400" aria-live="polite">
    {t('spread.competence.rows', { n: rows.length.toLocaleString() })}
  </span>
</div>

<div class="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
  <table class="w-full text-sm">
    <caption class="sr-only">{t('spread.competence.table.caption')}</caption>
    <thead class="bg-slate-100 dark:bg-slate-800 text-left sticky top-0 z-10">
      <tr>
        <th scope="col" aria-sort={ariaSort('species')} class="px-3 py-2 font-semibold">
          <button class="underline decoration-dotted" onclick={() => setSort('species')}>{t('spread.competence.col.species')}</button>
        </th>
        <th scope="col" aria-sort={ariaSort('mortality')} class="px-3 py-2 font-semibold">
          <button class="underline decoration-dotted" onclick={() => setSort('mortality')}>{t('spread.competence.col.mortality')}</button>
        </th>
        <th scope="col" class="px-3 py-2 font-semibold">{t('spread.competence.col.shedding')}</th>
        <th scope="col" aria-sort={ariaSort('roles')} class="px-3 py-2 font-semibold">
          <button class="underline decoration-dotted" onclick={() => setSort('roles')}>{t('spread.competence.col.roles')}</button>
        </th>
        <th scope="col" aria-sort={ariaSort('papers')} class="px-3 py-2 font-semibold">
          <button class="underline decoration-dotted" onclick={() => setSort('papers')}>{t('spread.competence.col.papers')}</button>
        </th>
        <th scope="col" class="px-3 py-2 font-semibold">{t('spread.competence.col.evidence')}</th>
      </tr>
    </thead>
    <tbody class="divide-y divide-slate-100 dark:divide-slate-700/50 odd:bg-slate-50/60 dark:odd:bg-slate-800/30">
      {#each rows as r (r.species)}
        <tr
          class="bg-white dark:bg-slate-900 hover:bg-blue-50 dark:hover:bg-slate-800 cursor-pointer"
          onclick={() => (cardSpecies = r.species)}
          onkeydown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              cardSpecies = r.species;
            }
          }}
          tabindex="0"
          role="button"
          aria-label={t('spread.competence.row.open', { species: displayName(r) })}
        >
          <td class="px-3 py-2">
            <span class="font-medium text-slate-900 dark:text-slate-100 italic">{r.species}</span>
            {#if r.common}<span class="ml-2 text-xs text-slate-500 dark:text-slate-400">{r.common}</span>{/if}
          </td>
          <td class="px-3 py-2 text-slate-800 dark:text-slate-100">
            {#if r.mortality_pct}
              {r.mortality_pct.median}% <span class="text-xs text-slate-400">({r.mortality_pct.studies})</span>
            {:else}—{/if}
          </td>
          <td class="px-3 py-2 text-slate-800 dark:text-slate-100">
            {#if r.shedding_days?.length}{Math.min(...r.shedding_days)}–{Math.max(...r.shedding_days)}{t('units.days.short')}{:else}—{/if}
          </td>
          <td class="px-3 py-2">
            {#if r.llm_roles}
              {#each Object.entries(r.llm_roles.roles).slice(0, 3) as [role, n] (role)}
                <span class="inline-block text-xs px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-200 mr-1">{role} ×{n}</span>
              {/each}
            {:else}—{/if}
          </td>
          <td class="px-3 py-2 text-slate-800 dark:text-slate-100 tabular-nums">{r.papers?.count ?? 0}</td>
          <td class="px-3 py-2" title={t('spread.competence.evidence.dots')}>
            <span class="inline-flex gap-0.5" aria-hidden="true">
              {#each EVIDENCE as ev (ev)}
                <span class="w-1.5 h-4 rounded-sm {r.evidence[ev] ? 'bg-emerald-500' : 'bg-slate-200 dark:bg-slate-700'}"></span>
              {/each}
            </span>
            <span class="sr-only">{t('spread.competence.evidence.sr', { n: r.filled ?? 0, m: EVIDENCE.length })}</span>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>

{#if card}
  <Modal open={true} ariaLabel={displayName(card)} onclose={() => (cardSpecies = null)}>
    <div class="space-y-4 max-w-2xl">
      <header>
        <h2 class="text-lg font-bold text-slate-900 dark:text-slate-50 italic">{card.species}</h2>
        {#if card.common}<p class="text-sm text-slate-500 dark:text-slate-400">{card.common}</p>{/if}
      </header>

      <section>
        <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{t('spread.card.competence')}</h3>
        <dl class="mt-2 grid grid-cols-2 gap-3 text-sm">
          <div class="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-3">
            <dt class="text-xs text-slate-500 dark:text-slate-400">{t('spread.card.mortality')}</dt>
            <dd class="text-slate-900 dark:text-slate-100">
              {#if card.mortality_pct}{card.mortality_pct.median}% ({t('spread.card.range')} {card.mortality_pct.min}–{card.mortality_pct.max}%, {t('spread.card.studies', { n: card.mortality_pct.studies })}){:else}{t('spread.card.no.data')}{/if}
            </dd>
          </div>
          <div class="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-3">
            <dt class="text-xs text-slate-500 dark:text-slate-400">{t('spread.card.shedding')}</dt>
            <dd class="text-slate-900 dark:text-slate-100">
              {#if card.shedding_days?.length}{t('spread.card.days.list', { s: card.shedding_days.join(', ') })}{:else}{t('spread.card.no.data')}{/if}
            </dd>
          </div>
          {#if card.susceptibility}
            <div class="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-3" title={t('susc.legacy.tip')}>
              <dt class="text-xs text-slate-500 dark:text-slate-400">{t('spread.card.susceptibility')} · {t('susc.legacy.short')}</dt>
              <dd class="text-slate-900 dark:text-slate-100">{card.susceptibility.score} — {card.susceptibility.class}</dd>
            </div>
          {/if}
          {#if card.detections}
            <div class="rounded-lg bg-slate-50 dark:bg-slate-800/60 p-3">
              <dt class="text-xs text-slate-500 dark:text-slate-400">{t('spread.card.detections')}</dt>
              <dd class="text-slate-900 dark:text-slate-100">{card.detections.count.toLocaleString()} · {t('spread.card.since')} {card.detections.first}</dd>
            </div>
          {/if}
        </dl>
      </section>

      {#if card.mortality_by_clade}
        <section>
          <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{t('spread.card.by.clade')}</h3>
          <ul class="mt-2 flex flex-wrap gap-2">
            {#each Object.entries(card.mortality_by_clade) as [cl, m] (cl)}
              <li class="text-xs px-2 py-1 rounded bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200">
                {cl}: <strong>{m.median}%</strong> ({t('spread.card.studies', { n: m.studies })})
              </li>
            {/each}
          </ul>
        </section>
      {/if}

      {#if card.llm_roles}
        <section>
          <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{t('spread.card.roles')}</h3>
          <p class="mt-2 text-sm text-slate-700 dark:text-slate-200">
            {#each Object.entries(card.llm_roles.roles) as [role, n] (role)}{role} ×{n}; {/each}
          </p>
          {#if card.llm_roles.clades.length}
            <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">{t('spread.card.clades')}: {card.llm_roles.clades.join(', ')}</p>
          {/if}
          <p class="mt-1 text-xs text-slate-400">{t('spread.card.roles.provenance', { n: card.llm_roles.papers, g: card.llm_roles.grounded, m: card.llm_roles.items })}</p>
        </section>
      {/if}

      {#if cardProxy}
        <section class="rounded-lg border border-dashed border-amber-400 dark:border-amber-500 p-3">
          <h3 class="text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">{t('spread.card.proxy.title')}</h3>
          <p class="mt-1 text-sm text-slate-700 dark:text-slate-200">
            {t('spread.card.proxy.body', { level: cardProxy.level, donors: cardProxy.donors.join(', ') })}
          </p>
          {#if cardProxy.mortality_median != null}
            <p class="mt-1 text-sm text-slate-700 dark:text-slate-200">{t('spread.card.proxy.mortality', { n: cardProxy.mortality_median })}</p>
          {/if}
          <p class="mt-1 text-xs text-slate-400">{t('spread.card.proxy.note')}</p>
        </section>
      {/if}

      {#if cardMovement}
        <section class="rounded-lg border border-slate-200 dark:border-slate-700 p-3">
          <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{t('spread.card.movement')}</h3>
          {#if cardMovement.tracked}
            <p class="mt-1 text-sm text-emerald-700 dark:text-emerald-300">
              📍 {t('spread.card.movement.tracked', { n: cardMovement.n_studies, m: cardMovement.n_individuals.toLocaleString() })}
            </p>
          {:else if cardMovement.genus_tracked}
            <p class="mt-1 text-sm text-amber-700 dark:text-amber-300">
              ⚠ {t('spread.card.movement.genus', { n: cardMovement.genus_studies })}
            </p>
          {:else}
            <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">{t('spread.card.movement.none')}</p>
          {/if}
        </section>
      {/if}

      {#if cardVax?.length}
        <section>
          <h3 class="text-xs font-semibold uppercase tracking-wide text-green-700 dark:text-green-300">{t('spread.card.vax.title')}</h3>
          <ul class="mt-2 space-y-1.5">
            {#each cardVax.slice(0, 4) as v, i (v.paper_id + i)}
              <li class="text-sm text-slate-700 dark:text-slate-200">
                <span class="px-1.5 py-0.5 rounded {v.outcome === 'worked' ? 'bg-green-100 dark:bg-green-950/60 text-green-700 dark:text-green-300' : 'bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300'}">{v.outcome}</span>
                <span class="ml-1.5">{(v.metric || '').slice(0, 120)}</span>
                <span class="text-xs text-slate-400 ml-1.5">{v.paper_id}</span>
              </li>
            {/each}
          </ul>
        </section>
      {/if}

      {#if cardImpact.length}
        <section>
          <h3 class="text-xs font-semibold uppercase tracking-wide text-rose-700 dark:text-rose-300">{t('spread.card.impact.title')}</h3>
          <ul class="mt-2 space-y-1.5">
            {#each cardImpact.slice(0, 3) as im, i (im.paper_id + i)}
              <li class="text-sm text-slate-700 dark:text-slate-200">
                {(im.loss || '').slice(0, 140)}
                {#if im.recovery}<span class="text-green-700 dark:text-green-300"> — {t('spread.card.impact.recovery')}: {(im.recovery || '').slice(0, 80)}</span>{/if}
                <span class="block text-xs text-slate-400">{im.location ?? ''} {im.timeframe ?? ''}</span>
              </li>
            {/each}
          </ul>
        </section>
      {/if}

      <section>
        <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{t('spread.card.evidence.grid')}</h3>
        <ul class="mt-2 grid grid-cols-3 gap-1 text-xs">
          {#each EVIDENCE as ev (ev)}
            <li class="flex items-center gap-1.5 {card.evidence[ev] ? 'text-slate-700 dark:text-slate-200' : 'text-slate-400 dark:text-slate-500'}">
              <span class="w-2 h-2 rounded-full {card.evidence[ev] ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'}" aria-hidden="true"></span>
              {t(`spread.evidence.${ev}`)}
            </li>
          {/each}
        </ul>
      </section>

      <footer class="text-xs text-slate-400 border-t border-slate-200 dark:border-slate-700 pt-2">
        <a class="underline hover:text-blue-600 dark:hover:text-blue-400" href={`#/susceptibility/${encodeURIComponent(card.species)}`}>{t('susceptibility.link.page')}</a>
        <span class="mx-1">·</span>
        {t('spread.card.papers.total', { n: card.papers?.count ?? 0 })}
        {#if card.records?.by_kind}
          · {#each Object.entries(card.records.by_kind) as [k, n] (k)}{t(`spread.kind.${k}`)} {n} {/each}
        {/if}
      </footer>
    </div>
  </Modal>
{/if}
