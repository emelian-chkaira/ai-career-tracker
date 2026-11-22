import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/shared/api/client";

interface Status { connected: boolean; base_url: string | null; default_url: string }
interface RrResume { id: string; name: string; updated_at?: string }

/** Connect a Reactive Resume account (hosted or self-hosted) with an API key, then import a resume into this studio or push the CV there. */
export function RrPanel({ cv, template, paper, onImport, connectOnly = false }: { cv?: unknown; template?: string; paper?: string; onImport?(cv: unknown): void; connectOnly?: boolean }) {
  const qc = useQueryClient(); const st = useQuery({ queryKey: ["rr"], queryFn: () => api.get<Status>("/me/rr") });
  const list = useQuery({ queryKey: ["rr-list"], enabled: !!st.data?.connected, queryFn: () => api.get<RrResume[]>("/me/rr/resumes"), retry: false });
  const [url, setUrl] = useState(""); const [key, setKey] = useState(""); const [msg, setMsg] = useState(""); const [err, setErr] = useState(""); const [busy, setBusy] = useState("");
  const run = async (n: string, fn: () => Promise<void>) => { setBusy(n); setErr(""); setMsg(""); try { await fn(); } catch (e) { setErr((e as Error).message); } finally { setBusy(""); } };
  const connect = () => run("c", async () => { await api.put("/me/rr", { base_url: url || st.data?.default_url, api_key: key }); setKey(""); await qc.invalidateQueries({ queryKey: ["rr"] }); setMsg("Connected."); });
  const c = st.data;
  return (<div className="stack"><h2 style={{ margin: 0 }}>Reactive Resume</h2>
    <div className="small muted">Reactive Resume is a free, open source resume builder. Connect it with an API key to pull a resume into this studio or send your CV there for its templates. The key is stored encrypted and is never shown again.</div>
    {err && <div className="notice err">{err}</div>}{msg && <div className="notice">{msg}</div>}
    {!c?.connected ? <div className="stack" style={{ gap: 8 }}>
      <label className="field"><span>Instance address</span><input type="text" value={url} placeholder={c?.default_url ?? "https://rxresu.me"} onChange={(e) => setUrl(e.target.value)} /></label>
      <label className="field"><span>API key</span><input type="password" autoComplete="off" value={key} placeholder="Create one in Reactive Resume: Settings, Developer, API keys" onChange={(e) => setKey(e.target.value)} /></label>
      <div className="row"><button className="btn" disabled={key.length < 8 || !!busy} onClick={connect}>{busy === "c" ? "Checking…" : "Connect"}</button></div></div>
      : <div className="stack" style={{ gap: 10 }}>
        <div className="row"><span className="chip ok">Connected</span><span className="small muted">{c.base_url}</span><button className="btn ghost small right" onClick={() => run("d", async () => { await api.del("/me/rr"); await qc.invalidateQueries({ queryKey: ["rr"] }); })}>Disconnect</button></div>
        {connectOnly ? <div className="small muted">Open CV Studio, Reactive Resume to import or send a CV.</div> : <><div className="row"><button className="btn" disabled={!!busy || !cv} onClick={() => run("p", async () => { const r = await api.post<{ url: string }>("/me/rr/push", { cv, template, paper, name: "CV from NL Career Tracker" }); setMsg(`Sent. Open it in Reactive Resume: ${r.url}`); await list.refetch(); })}>{busy === "p" ? "Sending…" : "Send this CV to Reactive Resume"}</button>
          <span className="small muted">Creates a new resume; nothing existing is overwritten.</span></div>
        <h3 style={{ margin: "6px 0 0" }}>Your resumes</h3>
        {list.isError && <div className="small err">{(list.error as Error).message}</div>}
        {list.data?.length === 0 && <div className="small muted">No resumes found.</div>}
        <ul className="plain stack" style={{ gap: 6 }}>{list.data?.map((r) => <li key={r.id} className="irow"><div className="irow-main"><b>{r.name}</b>{r.updated_at && <div className="small muted">Updated {new Date(r.updated_at).toLocaleDateString()}</div>}</div>
          <button className="btn ghost small" disabled={!!busy} onClick={() => run("i" + r.id, async () => { const d = await api.post<{ cv: unknown }>(`/me/rr/import/${r.id}`); onImport?.(d.cv); setMsg(`Imported “${r.name}”. Review it in the sections on the left.`); })}>Import</button>
          <button className="btn ghost small" disabled={!!busy} onClick={() => run("f" + r.id, async () => { const d = await api.get<{ pdf_b64: string }>(`/me/rr/pdf/${r.id}`); const u = URL.createObjectURL(new Blob([Uint8Array.from(atob(d.pdf_b64), (x) => x.charCodeAt(0))], { type: "application/pdf" })); window.open(u, "_blank", "noopener"); })}>PDF</button></li>)}</ul></>}</div>}
  </div>);
}
