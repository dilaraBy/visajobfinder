import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { JobInterests } from "./JobInterests";

describe("JobInterests", () => {
  it("renders a chip per category and reflects selection via aria-pressed", () => {
    render(
      <JobInterests
        categories={["psychology graduate", "finance graduate"]}
        keyword="psychology graduate"
        onKeywordChange={() => {}}
        onToggleCategory={() => {}}
      />
    );
    const psych = screen.getByRole("button", { name: "psychology graduate" });
    const finance = screen.getByRole("button", { name: "finance graduate" });
    expect(psych).toHaveAttribute("aria-pressed", "true");
    expect(finance).toHaveAttribute("aria-pressed", "false");
  });

  it("calls onToggleCategory with the chip label", () => {
    const onToggle = vi.fn();
    render(
      <JobInterests
        categories={["finance graduate"]}
        keyword=""
        onKeywordChange={() => {}}
        onToggleCategory={onToggle}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "finance graduate" }));
    expect(onToggle).toHaveBeenCalledWith("finance graduate");
  });

  it("calls onKeywordChange when typing", () => {
    const onChange = vi.fn();
    render(
      <JobInterests
        categories={[]}
        keyword=""
        onKeywordChange={onChange}
        onToggleCategory={() => {}}
      />
    );
    fireEvent.change(
      screen.getByLabelText(/filter and rank jobs by interest/i),
      { target: { value: "data analyst" } }
    );
    expect(onChange).toHaveBeenCalledWith("data analyst");
  });
});
