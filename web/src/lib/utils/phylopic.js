/**
 * PhyloPic silhouette lookup — images are pre-downloaded to
 * /images/phylopic/{slug}.png by scripts/fetch_phylopic.py so the site
 * never hits the PhyloPic API at runtime.
 */
let index = null;
let loading = null;

export async function phylopicIndex() {
  if (index) return index;
  if (!loading) {
    loading = fetch('data/phylopic.json')
      .then(r => r.json())
      .then(d => {
        index = {};
        for (const [slug, info] of Object.entries(d)) {
          if (info.status === 'ok') index[info.sci] = slug;
        }
        return index;
      })
      .catch(() => { index = {}; return index; });
  }
  return loading;
}

export function phylopicPath(sci, idx) {
  if (!sci || !idx) return null;
  let slug = idx[sci];
  if (!slug) {
    // presence matrices key species with underscores sometimes
    const alt = sci.replace(/ /g, '_');
    slug = idx[alt] || idx[sci.replace(/_/g, ' ')];
  }
  return slug ? `images/phylopic/${slug}.png` : null;
}
