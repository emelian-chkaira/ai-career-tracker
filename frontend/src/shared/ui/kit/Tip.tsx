import * as T from "@radix-ui/react-tooltip";
import type { ReactNode } from "react";

/** Tooltip that works with keyboard focus too. Wrap once near the app root with <T.Provider> (TipProvider). */
export const TipProvider = ({ children }: { children: ReactNode }) => <T.Provider delayDuration={250}>{children}</T.Provider>;
export function Tip({ text, children }: { text: string; children: ReactNode }) {
  return (<T.Root><T.Trigger asChild>{children as JSX.Element}</T.Trigger><T.Portal><T.Content className="ktip" sideOffset={6}>{text}</T.Content></T.Portal></T.Root>);
}
