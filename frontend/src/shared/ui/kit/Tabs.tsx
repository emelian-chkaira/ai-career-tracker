import * as T from "@radix-ui/react-tabs";
import type { ReactNode } from "react";

export type TabDef = { value: string; label: ReactNode; content: ReactNode };
/** Accessible tabs (arrow keys, roving focus). */
export function Tabs({ tabs, value, onValueChange, defaultValue, vertical = false }: { tabs: TabDef[]; value?: string; onValueChange?(v: string): void; defaultValue?: string; vertical?: boolean }) {
  return (<T.Root value={value} onValueChange={onValueChange} defaultValue={defaultValue ?? tabs[0]?.value} className={"ktabs" + (vertical ? " v" : "")} orientation={vertical ? "vertical" : "horizontal"}>
    <T.List className="ktabs-list">{tabs.map((t) => <T.Trigger key={t.value} value={t.value} className="ktab">{t.label}</T.Trigger>)}</T.List>
    {tabs.map((t) => <T.Content key={t.value} value={t.value} className="ktabs-body">{t.content}</T.Content>)}
  </T.Root>);
}
