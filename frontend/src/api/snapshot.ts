/**
 * GitHub Pages static demo: map /api URLs to pre-exported JSON under public/gh-pages-snapshot/.
 * Filenames must match scripts/export_gh_pages_snapshot.py (url_to_snapshot_filename).
 */

const V = import.meta.env.VITE_STATIC_SNAPSHOT;
export const isStaticSnapshot = V === 'true' || V === '1';

export function snapshotFilenameForApiUrl(url: string): string {
  const u = new URL(url, 'http://vbc.snapshot.local');
  const parts = u.pathname.split('/').filter(Boolean);
  let key = parts.join('_');
  const params = new URLSearchParams(u.search);
  const sortedKeys = [...params.keys()].sort();
  if (sortedKeys.length) {
    const abbrev: Record<string, string> = { page: 'p', page_size: 'ps' };
    const qs = sortedKeys.map((k) => `${abbrev[k] ?? k}${params.get(k) ?? ''}`).join('_');
    key = `${key}_${qs}`;
  }
  return `${key.replace(/[^a-zA-Z0-9_.-]+/g, '_')}.json`;
}

export async function fetchSnapshotJson<T>(apiPath: string): Promise<T> {
  const base = import.meta.env.BASE_URL;
  const name = snapshotFilenameForApiUrl(apiPath);
  const res = await fetch(`${base}gh-pages-snapshot/${name}`);
  if (!res.ok) {
    throw new Error(`Snapshot missing or error (${res.status}): ${name}`);
  }
  return res.json() as Promise<T>;
}
