import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";
import { useShortcuts } from "./useShortcuts";

function Probe({ fn }: { fn: () => void }) { useShortcuts({ j: fn }); return <input aria-label="box" />; }

describe("useShortcuts", () => {
  it("fires on a bare key", () => { const fn = vi.fn(); render(<Probe fn={fn} />); fireEvent.keyDown(window, { key: "j" }); expect(fn).toHaveBeenCalledTimes(1); });
  it("ignores keys typed into inputs and keys with modifiers", () => {
    const fn = vi.fn(); const { getByLabelText } = render(<Probe fn={fn} />);
    fireEvent.keyDown(getByLabelText("box"), { key: "j" }); fireEvent.keyDown(window, { key: "j", metaKey: true }); expect(fn).not.toHaveBeenCalled();
  });
});
