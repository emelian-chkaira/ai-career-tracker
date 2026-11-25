import { Icon } from "@/shared/ui/Icon";
import { PageHeader } from "@/shared/ui";
import { useState } from "react";
import { useInfiniteQuery, keepPreviousData } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "@/shared/api/client";
import type { Company } from "@/shared/api/types";
import { useSentinel, ListEnd } from "@/shared/lib/useSentinel";
import { sponsorChip } from "@/features/jobs/JobCard";

export function CompaniesPage({ sponsors = false }: { sponsors?: boolean }) {
  const [q, setQ] = useState(""); const [hiring, setHiring] = useState(true);
  const cq = useInfiniteQuery({ queryKey: ["companies", q, hiring, sponsors], initialPageParam: 1, placeholderData: keepPreviousData,
    queryFn: ({ pageParam }) => api.get<{ items: Company[]; total: number; limit: number; page: number }>("/companies", { q, hiring, page: pageParam, ...(sponsors ? { sponsor: true } : {}) }),
    getNextPageParam: (l) => (l.page * l.limit < l.total ? l.page + 1 : undefined) });
  const data = cq.data && { ...cq.data.pages[0], items: cq.data.pages.flatMap((p) => p.items) };
  const sentinel = useSentinel(() => { if (cq.hasNextPage && !cq.isFetching) cq.fetchNextPage(); }, !!cq.hasNextPage);
  return (<div className="stack"><PageHeader eyebrow={sponsors ? "NL IND register" : "Employers"} icon={<Icon name="company" size={17} />} title={sponsors ? "Visa sponsor lookup" : "Companies"} subtitle={<>{data ? `${data.total.toLocaleString()} ${hiring ? "companies hiring right now" : "tech companies"}, each one read from its own careers page.${sponsors ? " Sponsor status comes from the public NL IND register of recognised sponsors; always confirm with the employer." : ""}` : "Loading…"}</>} />
    <div className="row csearch"><input type="search" className="grow tool" placeholder="Search by company name" value={q} onChange={(e) => { setQ(e.target.value); }} />
      <label className="row small"><input type="checkbox" checked={hiring} onChange={(e) => { setHiring(e.target.checked); }} />Only companies hiring now</label></div>
    <div className="cgrid">{data?.items.map((c) => <div key={c.id} className="ccard">
      {c.logo ? <img className="logo" src={c.logo.startsWith("/") || c.logo.startsWith("http") ? c.logo : `/logos/${c.logo}`} alt="" /> : <div className="logo">{c.name[0]}</div>}
      <div className="grow" style={{ minWidth: 0 }}><strong>{c.name}</strong><div>{sponsorChip(c.sponsor_status)}</div><div className="small muted">{[c.city, `${c.open_jobs ?? 0} open ${c.open_jobs === 1 ? "role" : "roles"}`].filter(Boolean).join(" · ")}</div>
        <div className="small"><Link to={`/?company_id=${c.id}`}>View jobs</Link>{c.careers_url && <> · <a href={c.careers_url} target="_blank" rel="noreferrer noopener">Careers page ↗</a></>}</div></div></div>)}</div>
    {data && <ListEnd sentinel={sentinel} more={!!cq.hasNextPage} loading={cq.isFetchingNextPage} count={data.items.length} total={data.total} />}
  </div>);
}
