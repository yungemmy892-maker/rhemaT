import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

export type ThemeMode = "system" | "light" | "dark";

// Also written by the anti-flash inline script in __root.tsx — keep in sync.
const STORAGE_KEY = "verseid-theme";

function systemPrefersDark(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function applyThemeClass(mode: ThemeMode) {
  const isDark = mode === "dark" || (mode === "system" && systemPrefersDark());
  document.documentElement.classList.toggle("dark", isDark);
}

interface ThemeContextValue {
  /** The user's chosen mode — "system" follows the OS, "light"/"dark" override it. */
  theme: ThemeMode;
  /** Updates the mode locally (instant repaint) and caches it for next load. Does NOT sync to the backend — callers combine this with useUpdateSettings for that. */
  setTheme: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>(() => {
    if (typeof window === "undefined") return "system";
    const cached = window.localStorage.getItem(STORAGE_KEY);
    return cached === "light" || cached === "dark" || cached === "system" ? cached : "system";
  });

  useEffect(() => {
    applyThemeClass(theme);
  }, [theme]);

  // While in "system" mode, react live to the OS preference changing
  // (e.g. the device switches to Dark Mode at sunset) without a reload.
  useEffect(() => {
    if (theme !== "system") return;
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => applyThemeClass("system");
    mql.addEventListener("change", handleChange);
    return () => mql.removeEventListener("change", handleChange);
  }, [theme]);

  const setTheme = useCallback((mode: ThemeMode) => {
    setThemeState(mode);
    window.localStorage.setItem(STORAGE_KEY, mode);
  }, []);

  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
