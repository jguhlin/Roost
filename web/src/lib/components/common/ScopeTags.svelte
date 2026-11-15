<script>
  import { t } from '../../stores/i18n.svelte.js';
  /**
   * Host-scope tags — renders one tag per host class in the evidence base.
   * 'both' renders as two tags: [avian] [mammalian].
   * Props: scope ('avian' | 'both' | 'mammalian' | 'viral' | 'unknown'),
   *        avianPapers / mammalianPapers (optional, for tooltips).
   */
  let { scope = 'unknown', avianPapers = null, mammalianPapers = null } = $props();

  let tags = $derived.by(() => {
    const avianTitle = avianPapers !== null ? `${avianPapers} ` + (t('scope.avian.papers') || 'papers with avian hosts') : (t('scope.avian.evidence') || 'avian host evidence');
    const mamTitle = mammalianPapers !== null ? `${mammalianPapers} ` + (t('scope.mammal.papers') || 'papers with mammalian hosts') : (t('scope.mammal.evidence') || 'mammalian host evidence');
    switch (scope) {
      case 'avian': return [{ label: 'avian', cls: 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300', title: avianTitle }];
      case 'mammalian': return [{ label: 'mammalian', cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300', title: mamTitle }];
      case 'both': return [
        { label: 'avian', cls: 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-300', title: avianTitle },
        { label: 'mammalian', cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300', title: mamTitle }
      ];
      case 'viral': return [{ label: 'viral only', cls: 'bg-gray-100 text-gray-600 dark:text-gray-400 dark:bg-gray-700 dark:text-gray-300', title: 'no host species recorded' }];
      default: return [{ label: 'unknown', cls: 'bg-gray-100 text-gray-600 dark:text-gray-400 dark:bg-gray-700 dark:text-gray-300', title: 'host scope not determined' }];
    }
  });
</script>

{#each tags as tag}
  <span class="px-2 py-0.5 text-xs rounded-full font-medium {tag.cls}" title={tag.title}>{tag.label}</span>
{/each}
