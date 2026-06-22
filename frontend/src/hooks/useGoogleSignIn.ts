import { useCallback, useEffect, useRef, useState } from "react";

// Google's official, supported customization (data-theme/shape/size/etc) only
// goes so far — there is no documented API to pop the real GIS credential
// flow from an arbitrary custom button click. The supported pattern for a
// fully custom button is to render Google's real (functional) button into
// an off-screen container and forward clicks to it programmatically, so the
// visible UI stays exactly what the design calls for while the actual
// sign-in flow — popup, consent, ID token issuance — is 100% real Google
// code, not a reimplementation.
// https://developers.google.com/identity/gsi/web/guides/display-button

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
          }) => void;
          renderButton: (parent: HTMLElement, options: Record<string, unknown>) => void;
          prompt: () => void;
        };
      };
    };
  }
}

const GIS_SCRIPT_SRC = "https://accounts.google.com/gsi/client";
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

let scriptLoadPromise: Promise<void> | null = null;

function loadGisScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (scriptLoadPromise) return scriptLoadPromise;

  scriptLoadPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${GIS_SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () =>
        reject(new Error("Failed to load Google Identity Services")),
      );
      return;
    }
    const script = document.createElement("script");
    script.src = GIS_SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google Identity Services"));
    document.head.appendChild(script);
  });

  return scriptLoadPromise;
}

interface UseGoogleSignInOptions {
  onSuccess: (idToken: string) => void;
  onError?: (error: Error) => void;
}

/**
 * Returns `{ trigger, ready }`. Call `trigger()` from your own button's
 * onClick — it forwards the click to a real, hidden Google sign-in button,
 * so the visible UI is untouched but the popup/consent/token flow is
 * genuine Google Identity Services, not a custom reimplementation.
 */
export function useGoogleSignIn({ onSuccess, onError }: UseGoogleSignInOptions) {
  const [ready, setReady] = useState(false);
  const hiddenContainerRef = useRef<HTMLDivElement | null>(null);
  const realButtonRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) {
      console.error(
        "VITE_GOOGLE_CLIENT_ID is not set — Google sign-in cannot be initialized. " +
          "Add it to your frontend .env (see .env.example).",
      );
      return;
    }

    let cancelled = false;

    loadGisScript()
      .then(() => {
        if (cancelled || !window.google) return;

        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: (response) => onSuccess(response.credential),
          cancel_on_tap_outside: true,
        });

        const container = document.createElement("div");
        container.style.position = "fixed";
        container.style.top = "-9999px";
        container.style.left = "-9999px";
        container.style.opacity = "0";
        container.style.pointerEvents = "none";
        document.body.appendChild(container);
        hiddenContainerRef.current = container;

        window.google.accounts.id.renderButton(container, {
          type: "standard",
          theme: "outline",
          size: "large",
        });

        // The real clickable element Google renders is nested a couple of
        // levels inside the container we handed it.
        realButtonRef.current = container.querySelector('div[role="button"]');
        setReady(true);
      })
      .catch((err: Error) => {
        if (!cancelled) onError?.(err);
      });

    return () => {
      cancelled = true;
      hiddenContainerRef.current?.remove();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const trigger = useCallback(() => {
    if (!realButtonRef.current) {
      onError?.(new Error("Google sign-in isn't ready yet — please try again in a moment."));
      return;
    }
    realButtonRef.current.click();
  }, [onError]);

  return { trigger, ready };
}
