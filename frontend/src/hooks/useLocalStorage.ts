/**
 * Simple typed hook to read and write a value in localStorage.
 * Personal data stays browser-local per CLAUDE.md Data Principles.
 */
import { useState } from "react";

export function useLocalStorage<T>(key: string, defaultValue: T): [T, (value: T) => void, () => void] {
  const [state, setState] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw === null) return defaultValue;
      return JSON.parse(raw) as T;
    } catch {
      return defaultValue;
    }
  });

  function set(value: T) {
    setState(value);
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // quota exceeded or private mode — silently continue
    }
  }

  function clear() {
    setState(defaultValue);
    try {
      localStorage.removeItem(key);
    } catch {
      // ignore
    }
  }

  return [state, set, clear];
}
