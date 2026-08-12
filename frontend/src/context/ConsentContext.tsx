import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { disableGoogleAnalytics, loadGoogleAnalytics } from "@/lib/analytics";

export type ConsentStatus = "granted" | "denied" | "undecided";

const STORAGE_KEY = "verseid-analytics-consent";

// Public by nature (it ships to the browser regardless), so it lives in
// VITE_-prefixed client config rather than .server.ts. Unset in an
// environment (e.g. local dev without a real GA property) simply means
// analytics never loads — consent still works, there's just nothing to
// turn on.
const GA_MEASUREMENT_ID = import.meta.env.VITE_GA_MEASUREMENT_ID;

function readStoredConsent(): ConsentStatus {
  if (typeof window === "undefined") return "undecided";
  const raw = window.localStorage.getItem(STORAGE_KEY);
  return raw === "granted" || raw === "denied" ? raw : "undecided";
}

interface ConsentContextValue {
  /** The user's analytics choice. "undecided" means they haven't been
   * asked yet (or haven't answered) — this is also always the value
   * during SSR, since it depends on localStorage. */
  consent: ConsentStatus;
  /** True once the client has checked localStorage for a real prior
   * choice. Before this, `consent` is just the SSR default and should
   * not be used to decide whether to show the consent banner — doing so
   * would flash the banner on every load, including for users who
   * already answered. */
  hydrated: boolean;
  /** Records acceptance, persists it, and loads Google Analytics. */
  grantConsent: () => void;
  /** Records decline, persists it, and makes sure GA stays off. */
  declineConsent: () => void;
}

const ConsentContext = createContext<ConsentContextValue | null>(null);

export function ConsentProvider({ children }: { children: ReactNode }) {
  const [consent, setConsent] = useState<ConsentStatus>("undecided");
  const [hydrated, setHydrated] = useState(false);

  // Deliberately NOT read in a useState initializer (unlike ThemeContext):
  // whether the consent banner renders is visible UI, so if the initial
  // client render read localStorage directly, a returning user's first
  // paint could disagree with the server-rendered markup (always
  // "undecided") and trigger a hydration mismatch. Reading it in an
  // effect instead means the server and the client's first render always
  // agree — the real value applies one tick later, which is invisible in
  // practice.
  useEffect(() => {
    const stored = readStoredConsent();
    setConsent(stored);
    setHydrated(true);

    if (!GA_MEASUREMENT_ID) return;
    if (stored === "granted") {
      loadGoogleAnalytics(GA_MEASUREMENT_ID);
    } else if (stored === "denied") {
      disableGoogleAnalytics(GA_MEASUREMENT_ID);
    }
  }, []);

  const grantConsent = useCallback(() => {
    setConsent("granted");
    window.localStorage.setItem(STORAGE_KEY, "granted");
    if (GA_MEASUREMENT_ID) loadGoogleAnalytics(GA_MEASUREMENT_ID);
  }, []);

  const declineConsent = useCallback(() => {
    setConsent("denied");
    window.localStorage.setItem(STORAGE_KEY, "denied");
    if (GA_MEASUREMENT_ID) disableGoogleAnalytics(GA_MEASUREMENT_ID);
  }, []);

  return (
    <ConsentContext.Provider value={{ consent, hydrated, grantConsent, declineConsent }}>
      {children}
    </ConsentContext.Provider>
  );
}

export function useConsent() {
  const ctx = useContext(ConsentContext);
  if (!ctx) throw new Error("useConsent must be used within a ConsentProvider");
  return ctx;
}