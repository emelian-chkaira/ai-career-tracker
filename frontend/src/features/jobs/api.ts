import { useMutation, useQuery, useQueryClient, keepPreviousData, useInfiniteQuery, type InfiniteData } from "@tanstack/react-query";
import { useEffect } from "react";
import { api } from "@/shared/api/client";
import type { Job, SearchParams, SearchResult } from "@/shared/api/types";

export const useJobSearch = (p: SearchParams) =>
  useQuery({ queryKey: ["jobs", p], queryFn: () => api.get<SearchResult>("/jobs", p as Record<string, unknown>), placeholderData: keepPreviousData });
/** All pages so far, one after the other. Changing the search starts again at page 1. */
export function useJobFeed(p: SearchParams) {
  const { page: _drop, ...base } = p; void _drop;
  const q = useInfiniteQuery({
    queryKey: ["jobs", base], initialPageParam: 1, placeholderData: keepPreviousData,
    queryFn: ({ pageParam }) => api.get<SearchResult>("/jobs", { ...base, page: pageParam } as Record<string, unknown>),
    getNextPageParam: (last) => (last.page * last.limit < last.total ? last.page + 1 : undefined) });
  const first = q.data?.pages[0];
  const data: SearchResult | undefined = first && { ...first, items: q.data!.pages.flatMap((x) => x.items) };
  return { data, isFetching: q.isFetching, loadingMore: q.isFetchingNextPage, error: q.error, more: !!q.hasNextPage, next: () => { if (q.hasNextPage && !q.isFetching) q.fetchNextPage(); } };
}
/** Opening a job can reveal its posting date (read from the employer's page): the cards already on screen must say the same. */
export function useJob(id: number | null) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["job", id], enabled: id != null, queryFn: () => api.get<Job>(`/jobs/${id}`) });
  const found = q.data?.posted_at;
  useEffect(() => {
    if (id == null || !found) return;
    const fix = (r: SearchResult): SearchResult => (r.items.some((j) => j.id === id && j.posted_at !== found) ? { ...r, items: r.items.map((j) => (j.id === id ? { ...j, posted_at: found } : j)) } : r);
    qc.setQueriesData<SearchResult | InfiniteData<SearchResult>>({ queryKey: ["jobs"] }, (d) => {
      if (!d) return d;
      if (!("pages" in d)) return fix(d);
      const pages = d.pages.map(fix);
      return pages.some((p, i) => p !== d.pages[i]) ? { ...d, pages } : d;
    });
  }, [id, found, qc]);
  return q;
}
export const useSuggest = (q: string) =>
  useQuery({ queryKey: ["suggest", q], enabled: q.trim().length >= 2, queryFn: () => api.get<{ skills: string[]; companies: string[]; titles: string[] }>("/jobs/suggest", { q }), staleTime: 60_000 });

export function useSetStage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, stage, notes }: { id: number; stage?: string; notes?: string }) => api.put(`/me/jobs/${id}`, { stage, notes }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["jobs"] }); qc.invalidateQueries({ queryKey: ["job"] }); qc.invalidateQueries({ queryKey: ["pipeline"] }); qc.invalidateQueries({ queryKey: ["track"] }); qc.invalidateQueries({ queryKey: ["stats"] }); },
  });
}
export const liveSearch = (q: string) => api.post<{ task_id: number }>("/jobs/live-search", {}, { q });
export const taskStatus = (id: number) => api.get<{ id: number; status: string; progress: Record<string, unknown> | null }>(`/tasks/${id}`);
