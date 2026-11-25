import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { setSample } from "@/shared/api/client";
import { CrawlerPage } from "@/features/admin/CrawlerPage";
import { BLOCKED, DemoBlocked, crawlerSample } from "./crawlerSample";
import { REPO } from "./useDemo";

const KEYS = ["admin-", "co", "jobs-admin", "source-health", "preview", "board-plan"];
const blocked = () => toast.info(BLOCKED, { id: "demo-blocked" });
const install = () => setSample((method, path, query) => crawlerSample(method, path, query, blocked));

/** The whole Crawler page for demo visitors, fed with invented data so they can look around every tab. */
export function CrawlerDemo() {
  const qc = useQueryClient(); useState(install);
  useEffect(() => {
    install();
    const quiet = (e: PromiseRejectionEvent) => { if (e.reason instanceof DemoBlocked) e.preventDefault(); };   // the toast already explained it
    window.addEventListener("unhandledrejection", quiet);
    return () => { window.removeEventListener("unhandledrejection", quiet); setSample(null); qc.removeQueries({ predicate: (q) => KEYS.some((k) => String(q.queryKey[0]).startsWith(k)) }); };
  }, [qc]);
  return (<div className="stack crawler-demo">
    <div className="demo-sample" role="note">
      <span className="demo-sample-tag">Sample data</span>
      <div><b>This Crawler page is a dummy.</b> Nothing is being crawled: every employer, number, task and account below is made up so you can see what it does. The real crawler runs on your own computer.</div>
      <a className="btn ghost small" href={REPO} target="_blank" rel="noreferrer">Run it yourself ↗</a>
    </div>
    <CrawlerPage preview />
  </div>);
}
