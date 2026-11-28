import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CountryPicker, orderCountries } from "./CountryPicker";

const all = [{ code: "NL", name: "Netherlands", jobs: 900 }, { code: "DE", name: "Germany", jobs: 300 }, { code: "BE", name: "Belgium", jobs: 50 }, { code: "FR", name: "France", jobs: 0 }];

describe("country picker", () => {
  it("lists chosen countries first, then the busiest, and hides empty ones", () => {
    expect(orderCountries(all, ["BE"], "").map((c) => c.code)).toEqual(["BE", "NL", "DE"]);
    expect(orderCountries(all, [], "ger").map((c) => c.code)).toEqual(["DE"]);
  });
  it("adds a country to the choice and can clear it", () => {
    const onChange = vi.fn();
    render(<CountryPicker countries={all} selected={["NL"]} onChange={onChange} clearLabel="All countries" />);
    fireEvent.click(screen.getByLabelText(/Germany/));
    expect(onChange).toHaveBeenLastCalledWith(["NL", "DE"]);
    fireEvent.click(screen.getByText("All countries"));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });
});
