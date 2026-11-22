import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/shared/api/client";

type F = { company_id: number };
/** Follow an employer: you get an alert (in-app and by e-mail) whenever it posts a new job. */
export function FollowButton({ companyId, name }: { companyId: number; name: string }) {
  const qc = useQueryClient(); const q = useQuery({ queryKey: ["following"], queryFn: () => api.get<F[]>("/me/following"), staleTime: 60_000 });
  const on = !!q.data?.some((f) => f.company_id === companyId);
  const m = useMutation({ mutationFn: () => on ? api.del(`/me/following/${companyId}`) : api.post(`/me/following/${companyId}`, {}), onSuccess: () => { qc.invalidateQueries({ queryKey: ["following"] }); qc.invalidateQueries({ queryKey: ["searches"] }); toast.success(on ? `Unfollowed ${name}` : `Following ${name}: you will be alerted about new jobs`); } });
  return <button className={`btn ghost${on ? " on" : ""}`} onClick={() => m.mutate()} disabled={m.isPending} aria-pressed={on}>{on ? "✓ Following" : "Follow company"}</button>;
}
