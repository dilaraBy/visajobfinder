/**
 * Tests for useLocalStorage hook.
 * Asserts that values persist to localStorage and survive simulated reload.
 */
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useLocalStorage } from "./useLocalStorage";

const KEY = "test_vjf_key";

// In jsdom under vitest, localStorage may be a stub without .clear().
// Provide a minimal in-memory mock so tests are self-contained.
const localStorageStore: Record<string, string> = {};
const localStorageMock = {
  getItem: (k: string) => localStorageStore[k] ?? null,
  setItem: (k: string, v: string) => { localStorageStore[k] = v; },
  removeItem: (k: string) => { delete localStorageStore[k]; },
  clear: () => { Object.keys(localStorageStore).forEach((k) => delete localStorageStore[k]); },
};

vi.stubGlobal("localStorage", localStorageMock);

beforeEach(() => {
  localStorageMock.clear();
});

describe("useLocalStorage", () => {
  it("returns default value when key is not set", () => {
    const { result } = renderHook(() =>
      useLocalStorage(KEY, { visa_situation: "unknown" })
    );
    expect(result.current[0]).toEqual({ visa_situation: "unknown" });
  });

  it("persists value to localStorage on set", () => {
    const { result } = renderHook(() =>
      useLocalStorage(KEY, { visa_situation: "unknown" })
    );
    act(() => {
      result.current[1]({ visa_situation: "graduate_route" });
    });
    expect(result.current[0]).toEqual({ visa_situation: "graduate_route" });
    expect(JSON.parse(localStorage.getItem(KEY)!)).toEqual({
      visa_situation: "graduate_route",
    });
  });

  it("reads persisted value from localStorage on first render", () => {
    localStorage.setItem(KEY, JSON.stringify({ visa_situation: "needs_sponsorship_before_start" }));
    const { result } = renderHook(() =>
      useLocalStorage(KEY, { visa_situation: "unknown" })
    );
    expect(result.current[0]).toEqual({
      visa_situation: "needs_sponsorship_before_start",
    });
  });

  it("clear() restores to default and removes key from localStorage", () => {
    const { result } = renderHook(() =>
      useLocalStorage(KEY, { visa_situation: "unknown" })
    );
    act(() => {
      result.current[1]({ visa_situation: "graduate_route" });
    });
    act(() => {
      result.current[2]();
    });
    expect(result.current[0]).toEqual({ visa_situation: "unknown" });
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it("survives bad JSON in localStorage gracefully", () => {
    localStorage.setItem(KEY, "NOT_VALID_JSON{{");
    const { result } = renderHook(() =>
      useLocalStorage(KEY, { visa_situation: "unknown" })
    );
    expect(result.current[0]).toEqual({ visa_situation: "unknown" });
  });
});
