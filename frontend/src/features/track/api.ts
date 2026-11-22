import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";

export type TrackEvent = { id: number; kind: string; title: string; body: string | null; at: string; meta: Record<string, unknown> };
export type Track = { stage: string; notes: string | null; applied_at: string | null; follow_up_at: string | null; follow_up_note: string | null; contact: string | null; offer_details: string | null };
export type Stats = { total: number; by_stage: Record<string, number>; funnel: Record<string, number>; active: number; response_rate: number | null; avg_days_to_response: number | null; follow_ups_due: number; applications_per_day?: { day: string; count: number }[] };

export const useTrack = (id: number, enabled = true) => useQuery({ queryKey: ["track", id], enabled, queryFn: () => api.get<{ track: Track | null; events: TrackEvent[] }>(`/me/jobs/${id}/track`) });
export const useStats = (days = 30) => useQuery({ queryKey: ["stats", days], queryFn: () => api.get<Stats>("/me/stats", { days }) });

export function useTrackActions(id: number) {
  const qc = useQueryClient();
  const done = () => { for (const k of ["track", "pipeline", "stats", "jobs", "job"]) qc.invalidateQueries({ queryKey: [k] }); };
  return {
    patch: useMutation({ mutationFn: (b: Record<string, unknown>) => api.patch(`/me/jobs/${id}/track`, b), onSuccess: done }),
    addEvent: useMutation({ mutationFn: (b: { kind: string; title: string; body?: string; at?: string }) => api.post(`/me/jobs/${id}/events`, b), onSuccess: done }),
    delEvent: useMutation({ mutationFn: (eid: number) => api.del(`/me/jobs/${id}/events/${eid}`), onSuccess: done }),
  };
}

export type JobTask = { id: number; job_id: number; title: string; due_at: string | null; done: boolean; job_title?: string; company?: string };
export const useTasks = (jobId: number) => useQuery({ queryKey: ["tasks", jobId], queryFn: () => api.get<JobTask[]>(`/me/jobs/${jobId}/tasks`) });
export function useTaskActions(jobId: number) {
  const qc = useQueryClient(); const done = () => { qc.invalidateQueries({ queryKey: ["tasks"] }); qc.invalidateQueries({ queryKey: ["stats"] }); };
  return {
    add: useMutation({ mutationFn: (b: { title: string; due_at?: string }) => api.post(`/me/jobs/${jobId}/tasks`, b), onSuccess: done }),
    toggle: useMutation({ mutationFn: (t: JobTask) => api.patch(`/me/tasks/${t.id}`, { done: !t.done }), onSuccess: done }),
    remove: useMutation({ mutationFn: (id: number) => api.del(`/me/tasks/${id}`), onSuccess: done }),
  };
}
