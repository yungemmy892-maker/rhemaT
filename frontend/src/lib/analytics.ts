declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

let injected = false;

/** Injects gtag.js and starts sending pageview/event data. Safe to call
 * more than once — only the first call does anything. */
export function loadGoogleAnalytics(measurementId: string) {
  if (injected || typeof window === "undefined" || !measurementId) return;
  injected = true;

  // Make sure any previous opt-out from this session doesn't linger.
  delete (window as unknown as Record<string, boolean>)[`ga-disable-${measurementId}`];

  window.dataLayer = window.dataLayer || [];
  window.gtag = function gtag(...args: unknown[]) {
    window.dataLayer!.push(args);
  };
  window.gtag("js", new Date());
  window.gtag("config", measurementId, {
    // Explicit rather than relying on the GA default, since that default
    // is Google's to change, not something this app controls.
    anonymize_ip: true,
  });

  const script = document.createElement("script");
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
  document.head.appendChild(script);
}

/** Stops any further hits from being recorded */
export function disableGoogleAnalytics(measurementId: string) {
  if (typeof window === "undefined" || !measurementId) return;
  (window as unknown as Record<string, boolean>)[`ga-disable-${measurementId}`] = true;
}