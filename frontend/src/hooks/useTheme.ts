import { useEffect } from "react";
import { useLocalStorage } from "./useLocalStorage";

export type Theme = "light" | "dark";
const THEME_STORAGE_KEY = "vjf_theme_v1";

/** Light/dark theme persisted to localStorage and applied via a `.dark` class
 * on <html>. No system/network calls — purely local. */
export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useLocalStorage<Theme>(THEME_STORAGE_KEY, "light");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const toggle = () => setTheme(theme === "dark" ? "light" : "dark");
  return [theme, toggle];
}
