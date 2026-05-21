import type { AssetItem, JobStatusResponse } from "./api";

export function findAsset(job: JobStatusResponse, type: string, kind?: string): AssetItem | null {
  const arr = job.artifacts?.[type] || [];
  if (!arr.length) return null;
  if (kind) {
    const m = arr.find(a => a.meta && a.meta.kind === kind);
    if (m) return m;
  }
  // Heuristic defaults: prefer final render artifacts over intermediate ones.
  if (type === "video") {
    const preferredKinds = ["whiteboard_mp4", "slideshow_mp4", "mp4"];
    for (const k of preferredKinds) {
      const m = arr.find(a => a.meta && a.meta.kind === k);
      if (m) return m;
    }
  }
  return arr[0];
}

export function humanBytes(n: number | null | undefined): string {
  if (n === null || n === undefined) return "-";
  const units = ["B", "KB", "MB", "GB"];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export function prettyJson(obj: any): string {
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

// Small utility to compose class names. Used as `cx(a, b && 'x', { 'is-active': cond })`.
export function cx(...parts: Array<string | false | null | undefined | Record<string, any> | Array<string | false | null | undefined>>): string {
  const out: string[] = [];
  for (const p of parts) {
    if (!p) continue;
    if (typeof p === "string") {
      out.push(p);
    } else if (Array.isArray(p)) {
      const s = cx(...p as any);
      if (s) out.push(s);
    } else if (typeof p === "object") {
      for (const k of Object.keys(p)) {
        // @ts-ignore
        if (p[k]) out.push(k);
      }
    }
  }
  return out.join(" ");
}
