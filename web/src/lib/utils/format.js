/**
 * Formatting utilities for display
 */

/**
 * Convert BigInt to Number safely (DuckDB returns BigInt for counts)
 */
function toNumber(n) {
  if (typeof n === 'bigint') return Number(n);
  return n;
}

/**
 * Format a number with locale-specific separators
 */
export function formatNumber(n, options = {}) {
  if (n === null || n === undefined) return '—';
  return toNumber(n).toLocaleString('en-US', options);
}

/**
 * Format a large number with K/M suffixes
 */
export function formatCompact(n) {
  if (n === null || n === undefined) return '—';
  n = toNumber(n);
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

/**
 * Parse an ISO 8601 week date (e.g. 2026-W13-1) into a Date —
 * week 13, weekday 1 (Monday). JS Date cannot parse these natively.
 */
function parseIsoWeekDate(s) {
  const m = /^(\d{4})-W(\d{2})-(\d)$/.exec(s);
  if (!m) return null;
  const [, year, week, day] = m;
  // Jan 4 is always in week 1
  const jan4 = new Date(Date.UTC(+year, 0, 4));
  const day1 = new Date(jan4);
  day1.setUTCDate(jan4.getUTCDate() - ((jan4.getUTCDay() + 6) % 7) + (+week - 1) * 7 + (+day - 1));
  return day1;
}

/**
 * Format a date as YYYY-MM-DD. Defensive: returns the raw value for
 * unparseable input instead of throwing (RangeError: Invalid time value).
 */
export function formatDate(d) {
  if (!d) return '—';
  if (typeof d === 'string') {
    if (/^\d{4}-W\d{2}-\d$/.test(d)) d = parseIsoWeekDate(d);
    else d = new Date(d);
  }
  if (!d || isNaN(d?.getTime?.())) return '—';
  return d.toISOString().split('T')[0];
}

/**
 * Format a date as "Month Day, Year" — defensive like formatDate
 */
import { getLocale } from '../stores/i18n.svelte.js';

export function formatDateLong(d) {
  if (!d) return '—';
  if (typeof d === 'string') {
    if (/^\d{4}-W\d{2}-\d$/.test(d)) d = parseIsoWeekDate(d);
    else d = new Date(d);
  }
  if (!d || isNaN(d?.getTime?.())) return '—';
  return d.toLocaleDateString(getLocale() === 'zh' ? 'zh-CN' : getLocale() === 'ko' ? 'ko-KR' : getLocale() === 'ja' ? 'ja-JP' : getLocale() === 'hi' ? 'hi-IN' : getLocale() === 'fr' ? 'fr-FR' : getLocale() === 'es' ? 'es-ES' : 'en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
}

/**
 * Format a date as relative time ("3 days ago")
 */
export function formatRelativeTime(d) {
  if (!d) return '—';
  if (typeof d === 'string') {
    if (/^\d{4}-W\d{2}-\d$/.test(d)) d = parseIsoWeekDate(d);
    else d = new Date(d);
  }
  if (!d || isNaN(d?.getTime?.())) return '—';

  const now = new Date();
  const diff = now - d;
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days} days ago`;
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
  if (days < 365) return `${Math.floor(days / 30)} months ago`;
  return `${Math.floor(days / 365)} years ago`;
}

/**
 * Format bytes as human-readable size
 */
export function formatBytes(bytes) {
  if (!bytes || isNaN(bytes) || bytes <= 0) return '';
  bytes = toNumber(bytes);
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Format a percentage
 */
export function formatPercent(n, decimals = 1) {
  if (n === null || n === undefined) return '—';
  return `${(n * 100).toFixed(decimals)}%`;
}

/**
 * Truncate text with ellipsis
 */
export function truncate(text, maxLength = 100) {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
}

/**
 * Format scientific name with italics placeholder
 * Returns object with genus and species parts
 */
export function parseScientificName(name) {
  if (!name) return { genus: '', species: '', full: '' };
  const parts = name.split(' ');
  return {
    genus: parts[0] || '',
    species: parts.slice(1).join(' ') || '',
    full: name
  };
}

/**
 * Format taxonomy breadcrumb
 */
export function formatTaxonomy(order, family, genus) {
  const parts = [order, family, genus].filter(Boolean);
  return parts.join(' › ');
}

/**
 * Format assembly level with badge color
 */
export function getAssemblyLevelInfo(level) {
  const levels = {
    'Chromosome': { label: 'Chromosome', color: 'green', rank: 4 },
    'Complete Genome': { label: 'Complete', color: 'green', rank: 4 },
    'Scaffold': { label: 'Scaffold', color: 'yellow', rank: 3 },
    'Contig': { label: 'Contig', color: 'orange', rank: 2 },
    'Unknown': { label: 'Unknown', color: 'gray', rank: 1 }
  };
  return levels[level] || levels['Unknown'];
}

/**
 * Format susceptibility class with color
 */
export function getSusceptibilityInfo(classLabel) {
  const classes = {
    'High': { label: 'High', color: 'red', description: 'High susceptibility based on gene presence and mortality data' },
    'Medium': { label: 'Medium', color: 'yellow', description: 'Moderate susceptibility' },
    'Low': { label: 'Low', color: 'green', description: 'Lower susceptibility' },
    'Unknown': { label: 'Unknown', color: 'gray', description: 'Insufficient data to assess' }
  };
  return classes[classLabel] || classes['Unknown'];
}

/**
 * Format gene presence status
 */
export function getGeneStatusInfo(status) {
  const statuses = {
    'present': { label: 'Present', color: 'green', icon: '✓' },
    'absent': { label: 'Absent', color: 'red', icon: '✗' },
    'partial': { label: 'Partial', color: 'yellow', icon: '~' },
    'unknown': { label: 'Unknown', color: 'gray', icon: '?' }
  };
  return statuses[status] || statuses['unknown'];
}

/**
 * Format N50 with appropriate units
 */
export function formatN50(n50) {
  if (!n50) return '—';
  n50 = toNumber(n50);
  if (n50 >= 1_000_000_000) return `${(n50 / 1_000_000_000).toFixed(2)} Gb`;
  if (n50 >= 1_000_000) return `${(n50 / 1_000_000).toFixed(1)} Mb`;
  if (n50 >= 1_000) return `${(n50 / 1_000).toFixed(1)} kb`;
  return `${n50} bp`;
}

/**
 * Format country code to name (basic mapping)
 */
const countryNames = {
  US: 'United States', CA: 'Canada', GB: 'United Kingdom', UK: 'United Kingdom',
  DE: 'Germany', FR: 'France', IT: 'Italy', ES: 'Spain', NL: 'Netherlands',
  BE: 'Belgium', AT: 'Austria', CH: 'Switzerland', PL: 'Poland', SE: 'Sweden',
  NO: 'Norway', DK: 'Denmark', FI: 'Finland', IE: 'Ireland', IS: 'Iceland',
  JP: 'Japan', CN: 'China', KR: 'South Korea', AU: 'Australia', NZ: 'New Zealand',
  ZA: 'South Africa', BR: 'Brazil', MX: 'Mexico', AR: 'Argentina', CL: 'Chile'
};

export function formatCountry(code) {
  if (!code) return '—';
  return countryNames[code.toUpperCase()] || code;
}

/**
 * Pluralize a word
 */
export function pluralize(count, singular, plural = null) {
  if (count === 1) return singular;
  return plural || `${singular}s`;
}

/**
 * IUCN Red List category information
 */
const IUCN_CATEGORIES = {
  'EX': { code: 'EX', name: 'Extinct', color: 'black', bg: 'bg-black', text: 'text-white' },
  'EW': { code: 'EW', name: 'Extinct in the Wild', color: 'black', bg: 'bg-black', text: 'text-white' },
  'CR': { code: 'CR', name: 'Critically Endangered', color: 'red', bg: 'bg-red-600', text: 'text-white' },
  'EN': { code: 'EN', name: 'Endangered', color: 'orange', bg: 'bg-orange-700', text: 'text-white' },
  'VU': { code: 'VU', name: 'Vulnerable', color: 'yellow', bg: 'bg-yellow-500', text: 'text-black' },
  'NT': { code: 'NT', name: 'Near Threatened', color: 'lime', bg: 'bg-lime-500', text: 'text-black' },
  'LC': { code: 'LC', name: 'Least Concern', color: 'green', bg: 'bg-green-700', text: 'text-white' },
  'DD': { code: 'DD', name: 'Data Deficient', color: 'gray', bg: 'bg-gray-500', text: 'text-white' },
  'NE': { code: 'NE', name: 'Not Evaluated', color: 'gray', bg: 'bg-gray-600', text: 'text-white' },
};

/**
 * Get IUCN category info for display
 */
export function getIUCNInfo(code) {
  return IUCN_CATEGORIES[code] || IUCN_CATEGORIES['NE'];
}

/**
 * Population trend icon and info
 */
const TRENDS = {
  'increasing': { icon: '↑', label: 'Increasing', color: 'text-green-700 dark:text-green-400' },
  'stable': { icon: '→', label: 'Stable', color: 'text-gray-600 dark:text-gray-400' },
  'decreasing': { icon: '↓', label: 'Decreasing', color: 'text-red-600 dark:text-red-400' },
  'unknown': { icon: '?', label: 'Unknown', color: 'text-gray-600 dark:text-gray-400' },
};

/**
 * Get population trend info for display
 */
export function getTrendInfo(trend) {
  return TRENDS[trend] || TRENDS['unknown'];
}
