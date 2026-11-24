import { useEffect } from "react";
import { getScoringCv, setScoringCv, useDocs } from "@/features/fit/api";
import { useAuth } from "@/features/auth/AuthContext";

/** Which CV of the library scores a job. Shown only when the account has more than one CV; the choice is remembered. */
export function CvPicker({ value, onChange, label = "Score with" }: { value: number | null; onChange(id: number | null): void; label?: string }) {
  const { user } = useAuth(); const docs = useDocs("cv", !!user); const list = docs.data ?? [];
  const valid = value === null || list.some((d) => d.id === value);
  useEffect(() => { if (docs.data && !valid) { setScoringCv(null); onChange(null); } }, [docs.data, valid]);   // eslint-disable-line react-hooks/exhaustive-deps
  if (list.length < 2) return null;
  const def = list.find((d) => d.is_default);
  return (<label className="small row" style={{ gap: 6 }}><span className="muted">{label}</span>
    <select aria-label="CV used for AI scoring" value={valid && value !== null ? String(value) : ""} onChange={(e) => { const v = e.target.value ? +e.target.value : null; setScoringCv(v); onChange(v); }}>
      <option value="">{def ? `${def.name} (default)` : "Default CV"}</option>
      {list.filter((d) => !d.is_default).map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
    </select></label>);
}
export { getScoringCv };
