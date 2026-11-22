/** Small square marks for the job boards (plain letters in each board's colour, not their logos). */
const MARK: Record<string, [string, string, string]> = {
  linkedin: ["in", "#0A66C2", "LinkedIn"], indeed: ["i", "#2557A7", "Indeed"], glassdoor: ["G", "#0CAA41", "Glassdoor"],
  google: ["G", "#EA4335", "Google Jobs"], bayt: ["b", "#E8590C", "Bayt"], site: ["⌂", "#6B7280", "Employer's own site"],
};
export const boardName = (key?: string | null) => MARK[(key ?? "").replace(/^board:/, "")]?.[2] ?? key ?? "";

export function BoardIcon({ board, size = 18, title }: { board?: string | null; size?: number; title?: string }) {
  const k = (board ?? "site").replace(/^board:/, ""); const [txt, bg, name] = MARK[k] ?? MARK.site;
  return (<span className="bicon" role="img" aria-label={title ?? name} title={title ?? name}
    style={{ width: size, height: size, fontSize: Math.round(size * (txt.length > 1 ? 0.5 : 0.62)), background: bg, borderRadius: Math.round(size * 0.24) }}>{txt}</span>);
}
