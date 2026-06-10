/**
 * Tests for EvidencePanel component.
 * Asserts:
 *  - found evidence items render
 *  - missing evidence items are shown prominently (not hidden)
 *  - both found and missing evidence are visible simultaneously
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EvidencePanel } from "./EvidencePanel";
import type { EvidenceItem } from "../engine/types";

const FOUND_PHRASE: EvidenceItem = {
  type: "phrase_signal",
  category: "no_sponsorship",
  severity: "red",
  text: "cannot provide visa sponsorship",
  start_index: 0,
  end_index: 30,
  rule_id: "no_sponsor_unable_001",
};

const FOUND_SPONSOR: EvidenceItem = {
  type: "sponsor_register",
  category: "sponsor_match",
  text: "Sponsor-register match found: Acme Ltd (high confidence).",
};

const MISSING_PHRASE: EvidenceItem = {
  type: "missing_evidence",
  category: "jd_phrase",
  text: "No visa-risk phrase matched the current deterministic phrase rules.",
};

const MISSING_SPONSOR: EvidenceItem = {
  type: "missing_evidence",
  category: "sponsor_match",
  text: "No reliable sponsor-register match found in the loaded sponsor data.",
};

describe("EvidencePanel", () => {
  it("renders found evidence items", () => {
    render(<EvidencePanel evidence={[FOUND_PHRASE, FOUND_SPONSOR]} />);
    expect(screen.getByText(/cannot provide visa sponsorship/i)).toBeInTheDocument();
    expect(screen.getByText(/Sponsor-register match found/i)).toBeInTheDocument();
  });

  it("renders missing evidence items visibly", () => {
    render(<EvidencePanel evidence={[MISSING_PHRASE, MISSING_SPONSOR]} />);
    const missing = screen.getAllByTestId("missing-evidence-item");
    expect(missing.length).toBe(2);
  });

  it("shows the missing evidence group heading", () => {
    render(<EvidencePanel evidence={[MISSING_PHRASE]} />);
    expect(screen.getByTestId("missing-evidence-group")).toBeInTheDocument();
    expect(screen.getByText(/missing evidence/i)).toBeInTheDocument();
  });

  it("shows both found and missing evidence simultaneously", () => {
    render(<EvidencePanel evidence={[FOUND_PHRASE, MISSING_PHRASE]} />);
    // found item
    expect(screen.getByText(/cannot provide visa sponsorship/i)).toBeInTheDocument();
    // missing item
    expect(screen.getByTestId("missing-evidence-group")).toBeInTheDocument();
    expect(screen.getByTestId("missing-evidence-item")).toBeInTheDocument();
  });

  it("missing evidence is NOT hidden from the DOM", () => {
    render(<EvidencePanel evidence={[MISSING_SPONSOR]} />);
    const group = screen.getByTestId("missing-evidence-group");
    // The element must not be hidden via display:none or visibility:hidden.
    // getByTestId only returns visible elements by default; if it throws it is hidden.
    expect(group).toBeVisible();
  });

  it("renders zero evidence gracefully", () => {
    render(<EvidencePanel evidence={[]} />);
    // No crash; the heading still shows...
    expect(
      screen.getByRole("heading", { name: /evidence/i })
    ).toBeInTheDocument();
    // ...and a classification with no evidence must be flagged as unreliable,
    // never silently empty (CLAUDE.md: evidence is required).
    expect(screen.getByTestId("evidence-empty")).toBeInTheDocument();
    expect(
      screen.getByText(/classification without evidence is not reliable/i)
    ).toBeInTheDocument();
  });

  it("renders the evidence text verbatim", () => {
    render(<EvidencePanel evidence={[MISSING_PHRASE]} />);
    expect(
      screen.getByText(
        "No visa-risk phrase matched the current deterministic phrase rules."
      )
    ).toBeInTheDocument();
  });
});
