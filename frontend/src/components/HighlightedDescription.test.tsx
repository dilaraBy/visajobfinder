/**
 * Tests for HighlightedDescription component.
 * Asserts that matched phrase signals are highlighted using start/end indices.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { HighlightedDescription } from "./HighlightedDescription";
import type { PhraseSignal } from "../engine/types";

const TEXT =
  "We are hiring. We cannot provide visa sponsorship. Please apply.";
// "We cannot provide visa sponsorship." starts at index 16 in the string above.
const SIGNAL_START = TEXT.indexOf("We cannot");
const SIGNAL_END = TEXT.indexOf(". Please");

const SIGNALS: PhraseSignal[] = [
  {
    category: "no_sponsorship",
    severity: "red",
    text: "cannot provide visa sponsorship",
    start_index: SIGNAL_START,
    end_index: SIGNAL_END,
    rule_id: "no_sponsor_unable_001",
  },
];

describe("HighlightedDescription", () => {
  it("renders all text content (non-highlighted parts present)", () => {
    render(<HighlightedDescription text={TEXT} signals={SIGNALS} />);
    // The surrounding non-highlighted text should be present in the rendered output
    expect(document.body.textContent).toContain("We are hiring.");
    expect(document.body.textContent).toContain(". Please apply.");
  });

  it("renders a highlighted mark element for the matched phrase", () => {
    render(<HighlightedDescription text={TEXT} signals={SIGNALS} />);
    const highlights = screen.getAllByTestId("phrase-highlight");
    expect(highlights).toHaveLength(1);
    expect(highlights[0].textContent).toBe(TEXT.slice(SIGNAL_START, SIGNAL_END));
  });

  it("applies the correct severity class to the highlight", () => {
    render(<HighlightedDescription text={TEXT} signals={SIGNALS} />);
    const highlight = screen.getByTestId("phrase-highlight");
    expect(highlight).toHaveAttribute("data-severity", "red");
    expect(highlight.className).toContain("severity-red");
  });

  it("renders no highlights when signals array is empty", () => {
    render(<HighlightedDescription text={TEXT} signals={[]} />);
    const highlights = screen.queryAllByTestId("phrase-highlight");
    expect(highlights).toHaveLength(0);
  });

  it("renders empty output when text is empty", () => {
    render(<HighlightedDescription text="" signals={SIGNALS} />);
    const highlights = screen.queryAllByTestId("phrase-highlight");
    expect(highlights).toHaveLength(0);
  });

  it("renders multiple highlights for multiple signals", () => {
    const text = "british citizenship is required and we cannot provide visa sponsorship";
    const sig1Start = text.indexOf("british citizenship");
    const sig1End = sig1Start + "british citizenship is required".length;
    const sig2Start = text.indexOf("cannot");
    const sig2End = text.length;

    const signals: PhraseSignal[] = [
      {
        category: "citizenship_required",
        severity: "red",
        text: "british citizenship is required",
        start_index: sig1Start,
        end_index: sig1End,
        rule_id: "citizenship_british_required_001",
      },
      {
        category: "no_sponsorship",
        severity: "red",
        text: "cannot provide visa sponsorship",
        start_index: sig2Start,
        end_index: sig2End,
        rule_id: "no_sponsor_unable_001",
      },
    ];

    render(<HighlightedDescription text={text} signals={signals} />);
    const highlights = screen.getAllByTestId("phrase-highlight");
    expect(highlights).toHaveLength(2);
  });
});
