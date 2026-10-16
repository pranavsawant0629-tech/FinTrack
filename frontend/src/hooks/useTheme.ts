import { useEffect, useState } from "react";

export type ThemePreference = "dark" | "light" | "system";

const THEME_STORAGE_KEY = "finova_theme";

function applyTheme(pref: ThemePreference) {
  const root = document.documentElement;
  const isDark =
    pref === "dark" ||
    (pref === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);

  if (isDark) {
    root.setAttribute("data-theme", "dark");
    root.classList.remove("light");
    root.classList.add("dark");
  } else {
    root.setAttribute("data-theme", "light");
    root.classList.remove("dark");
    root.classList.add("light");
  }
}

export function useTheme() {
  const [theme, setThemeState] = useState<ThemePreference>(() => {
    const saved = localStorage.getItem(THEME_STORAGE_KEY) as ThemePreference | null;
    return saved === "dark" || saved === "light" || saved === "system" ? saved : "dark";
  });

  const setTheme = (newTheme: ThemePreference) => {
    setThemeState(newTheme);
    localStorage.setItem(THEME_STORAGE_KEY, newTheme);
    applyTheme(newTheme);
  };

  useEffect(() => {
    applyTheme(theme);

    if (theme === "system") {
      const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
      const handler = () => applyTheme("system");
      mediaQuery.addEventListener("change", handler);
      return () => mediaQuery.removeEventListener("change", handler);
    }
  }, [theme]);

  return { theme, setTheme };
}
