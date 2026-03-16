import { getToken } from "./auth";

export const API_BASE =
  ((globalThis as any).process?.env?.NEXT_PUBLIC_API_BASE as string | undefined) ||
  "http://127.0.0.1:8000";

export type JobStatus = "QUEUED" | "RUNNING" | "FAILED" | "SUCCEEDED";

export type AssetItem = {
  id: string;
  uri: string;
  meta: Record<string, any>;
};

export type JobStatusResponse = {
  id: string;
  document_id: string;
  mode: string;
  status: JobStatus;
  progress: Record<string, any>;
  artifacts: Record<string, AssetItem[]>;
  segments?: Array<{
    id: string;
    segment_index: number;
    title?: string | null;
    objective?: string | null;
    status: string;
    duration_target_sec?: number | null;
  }>;
  created_at?: string;
  finished_at?: string;
};

export type LibraryJobItem = {
  id: string;
  document_id: string;
  filename?: string | null;
  title?: string | null;
  created_at?: string | null;
  finished_at?: string | null;
  video_asset_id?: string | null;
  thumb_asset_id?: string | null;
  duration_sec?: number | null;
};

function authHeaders(): Record<string, string> {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers as HeadersInit);
  const extra = authHeaders();
  for (const [k, v] of Object.entries(extra)) {
    if (v != null) headers.set(k, v);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

export function assetUrl(assetId: string): string {
  const t = getToken();
  const u = new URL(`${API_BASE}/assets/${assetId}`);
  if (t) u.searchParams.set("token", t);
  return u.toString();
}

export function jobStreamUrl(jobId: string): string {
  const t = getToken();
  const u = new URL(`${API_BASE}/jobs/${jobId}/stream`);
  if (t) u.searchParams.set("token", t);
  return u.toString();
}

export async function uploadDocument(file: File): Promise<{ document_id: string; sha256: string }> {
  const fd = new FormData();
  fd.append("file", file, file.name);
  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST",
    body: fd,
    headers: {
      ...authHeaders(),
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return (await res.json()) as { document_id: string; sha256: string };
}

export async function createPromptDocument(
  text: string,
  title?: string
): Promise<{ document_id: string; sha256: string; filename: string }> {
  return apiFetch<{ document_id: string; sha256: string; filename: string }>("/documents/prompt", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, title }),
  });
}

export async function createJob(document_id: string, mode: string = "quick"): Promise<{ job_id: string }> {
  return apiFetch<{ job_id: string }>("/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id, mode }),
  });
}

export async function getJob(job_id: string): Promise<JobStatusResponse> {
  return apiFetch<JobStatusResponse>(`/jobs/${job_id}`);
}

export async function getLibrary(limit: number = 20): Promise<LibraryJobItem[]> {
  return apiFetch<LibraryJobItem[]>(`/jobs/library?limit=${limit}`);
}

export async function deleteJob(job_id: string): Promise<{ ok: boolean }> {
  return apiFetch<{ ok: boolean }>(`/jobs/${job_id}`, { method: "DELETE" });
}

export async function fetchJsonAsset<T>(assetId: string): Promise<T> {
  const res = await fetch(assetUrl(assetId));
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function fetchTextAsset(assetId: string): Promise<string> {
  const res = await fetch(assetUrl(assetId));
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `HTTP ${res.status}`);
  }
  return await res.text();
}

export async function uploadAndCreateJob(file: File, mode: "quick" | "deep" = "quick") {
  const { document_id } = await uploadDocument(file);
  const { job_id } = await createJob(document_id, mode);
  return { job_id, document_id };
}

export async function promptAndCreateJob(text: string, mode: "quick" | "deep" = "quick", title?: string) {
  const { document_id } = await createPromptDocument(text, title);
  const { job_id } = await createJob(document_id, mode);
  return { job_id, document_id };
}

// Backward-compatible alias used in earlier drafts.
export async function uploadAndCreateQuickJob(file: File) {
  return uploadAndCreateJob(file, "quick");
}
