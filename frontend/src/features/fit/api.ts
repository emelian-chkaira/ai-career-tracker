import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/shared/api/client";
import { uget, uset } from "@/shared/lib/userStore";
import type { AiFit } from "@/shared/api/types";

export const useStoredCv = (enabled = true) => useQuery({
  queryKey: ["stored-cv"], enabled, staleTime: 60_000,
  queryFn: async () => { try { return await api.get<{ cv: Record<string, unknown>; updated_at: string }>("/me/cv"); } catch (e) { if (e instanceof ApiError && e.status === 404) return null; throw e; } },
});
export const saveStoredCv = (cv: unknown) => api.put<{ ok: boolean }>("/me/cv", { cv });
export const deleteStoredCv = () => api.del("/me/cv");
export const scoreJob = (id: number, consent: boolean, force = false, cvId?: number | null) => api.post<AiFit>(`/me/fit/${id}`, { consent, force, cv_id: cvId ?? null });

/** CV Studio library: several CVs and cover letters per account. */
export interface DocMeta { id: number; kind: "cv" | "cover"; name: string; is_default: boolean; folder: string; job_id: number | null; note: string; updated_at: string }
export const useDocs = (kind: "cv" | "cover", enabled = true) => useQuery({ queryKey: ["docs", kind], enabled, staleTime: 30_000, queryFn: async () => (await api.get<{ docs: DocMeta[] }>("/me/docs", { kind })).docs });
export const useRefreshDocs = () => { const qc = useQueryClient(); return () => { qc.invalidateQueries({ queryKey: ["docs"] }); qc.invalidateQueries({ queryKey: ["stored-cv"] }); }; };
/** The CV chosen for scoring (remembered per account); null = the default CV. */
export const getScoringCv = (): number | null => { const v = uget("scoring-cv"); return v ? +v : null; };
export const setScoringCv = (id: number | null) => uset("scoring-cv", id ? String(id) : null);

export type BatchState = { status: string; progress: { total?: number; done?: number; scored?: number; cached?: number; failed?: number; error?: string } | null; error?: string | null };
export async function runBatch(ids: number[], consent: boolean, onTick: (s: BatchState) => void, cvId?: number | null): Promise<BatchState> {
  const { task_id } = await api.post<{ task_id: number }>("/me/fit-batch", { job_ids: ids, consent, cv_id: cvId ?? null });
  for (let i = 0; i < 900; i++) {
    await new Promise((r) => setTimeout(r, 1500));
    const s = await api.get<BatchState>(`/me/fit-batch/${task_id}`); onTick(s);
    if (s.status !== "running") return s;
  }
  throw new Error("Still running in the background; reload in a minute.");
}
export const useRefreshJobs = () => { const qc = useQueryClient(); return () => { qc.invalidateQueries({ queryKey: ["jobs"] }); qc.invalidateQueries({ queryKey: ["job"] }); qc.invalidateQueries({ queryKey: ["pipeline"] }); }; };

/** Consent to send this account's CV to an external AI provider: remembered per account, never for everyone on the browser. */
export const getConsent = () => uget("ai-consent") === "1";
export const setConsentStored = (v: boolean) => uset("ai-consent", v ? "1" : null);

/** Folders of the CV Studio library: "" is the default folder. */
export const folderLabel = (f: string) => f || "Default";
export const foldersOf = (docs: DocMeta[]) => [...new Set(docs.map((d) => d.folder).filter(Boolean))].sort((a, b) => a.localeCompare(b));
