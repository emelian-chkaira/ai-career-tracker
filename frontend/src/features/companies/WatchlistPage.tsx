import { Icon } from "@/shared/ui/Icon";
import { PageHeader } from "@/shared/ui";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/shared/api/client";

interface F { company_id: number; name: string; alert_frequency: string }

/** Employers you follow: you get an alert (in-app and by e-mail) when any of them posts a new job. */
export function WatchlistPage() {
  const qc = useQueryClient(); const q = useQuery({ queryKey: ["following"], queryFn: () => api.get<F[]>("/me/following") });
  const un = useMutation({ mutationFn: (id: number) => api.del(`/me/following/${id}`), onSuccess: () => { qc.invalidateQueries({ queryKey: ["following"] }); toast.success("Unfollowed"); } });
  return (<div className="stack"><PageHeader eyebrow="Following" icon={<Icon name="bell" size={17} />} title="Watchlist" subtitle="Employers you follow. New jobs from them reach you as an alert, so you can apply before the crowd." />
    {q.isLoading && <div className="skel" style={{ height: 80 }} />}
    {q.data && !q.data.length && <div className="card empty">You are not following any employer yet. Open a company or a job and press “Follow company”, or <Link to="/companies">browse companies</Link>.</div>}
    <ul className="plain stack" style={{ gap: 8 }}>{q.data?.map((f) => <li key={f.company_id} className="irow"><div className="irow-main"><b>{f.name}</b><div className="small muted">Alerts: {f.alert_frequency}</div></div>
      <Link className="btn ghost small" to={`/?company_id=${f.company_id}`}>See jobs</Link><button className="btn ghost small" disabled={un.isPending} onClick={() => un.mutate(f.company_id)}>Unfollow</button></li>)}</ul></div>);
}
