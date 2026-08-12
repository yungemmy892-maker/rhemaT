import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";

import appCss from "../styles.css?url";
import { AuthProvider } from "../context/AuthContext";
import { ThemeProvider } from "../context/ThemeContext";
import { ConsentProvider } from "../context/ConsentContext";
import { ConsentBanner } from "../components/ConsentBanner";

// Runs before first paint (inline, blocking) so the correct theme class is
// present on <html> immediately — otherwise there'd be a flash of the light
// theme before React hydrates and ThemeProvider applies the real one.
// Keep the storage key in sync with ThemeContext.tsx.
const THEME_INIT_SCRIPT = `
(function () {
  try {
    var mode = localStorage.getItem("verseid-theme") || "system";
    var isDark = mode === "dark" || (mode === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    if (isDark) document.documentElement.classList.add("dark");
  } catch (e) {}
})();
`.trim();

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">Page not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          This page didn't load
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Something went wrong on our end. You can try refreshing or head back home.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Try again
          </button>
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1, viewport-fit=cover" },
      { name: "theme-color", content: "#A855F7" },
      { title: "VerseID — Find Any Bible Verse Instantly" },
      {
        name: "description",
        content:
          "Hear it. Speak it. Discover it. VerseID identifies any Bible verse from your voice or a few words.",
      },
      { name: "author", content: "VerseID" },
      { property: "og:title", content: "VerseID - Find Any Bible Verse Instantly" },
      {
        property: "og:description",
        content: "Shazam for Bible verses. Speak or type - VerseID finds it.",
      },
      { property: "og:type", content: "website" },
      { property: "og:url", content: "https://www.verseid.top/" },
      { property: "og:site_name", content: "VerseID" },
      {
        property: "og:image",
        content: "https://www.verseid.top/og-image.png",
      },
      { property: "og:image:width", content: "1200" },
      { property: "og:image:height", content: "630" },
      { property: "og:image:alt", content: "VerseID - Find Any Bible Verse Instantly" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:title", content: "VerseID - Find Any Bible Verse Instantly" },
      {
        name: "twitter:description",
        content: "Shazam for Bible verses. Speak or type - VerseID finds it.",
      },
      { name: "twitter:image", content: "https://www.verseid.top/og-image.png" },
      {
        "script:ld+json": {
          "@context": "https://schema.org",
          "@graph": [
            {
              "@type": "Organization",
              "@id": "https://www.verseid.top/",
              name: "VerseID",
              url: "https://www.verseid.top/",
              logo: "https://www.verseid.top/logo.png",
            },
            {
              "@type": "WebSite",
              "@id": "https://www.verseid.top/#website",
              name: "VerseID",
              url: "https://www.verseid.top/",
              description:
                "VerseID identifies any Bible verse from your voice or a few words - speak or type a phrase you remember, and VerseID finds the exact verse.",
              publisher: { "@id": "https://www.verseid.top/" },
              inLanguage: "en",
            },
            {
              "@type": "WebApplication",
              name: "VerseID",
              url: "https://www.verseid.top/",
              applicationCategory: "LifestyleApplication",
              operatingSystem: "Any (web-based)",
              description:
                "Hear it. Speak it. Discover it. VerseID identifies any Bible verse from your voice or a few words.",
              offers: [
                {
                  "@type": "Offer",
                  name: "Free",
                  price: "0",
                  priceCurrency: "NGN",
                },
                {
                  "@type": "Offer",
                  name: "Pro",
                  price: "1000",
                  priceCurrency: "NGN",
                  priceValidUntil: "2027-12-31",
                },
              ],
            },
          ],
        },
      },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "icon", href: "/favicon.ico", sizes: "48x48" },
      { rel: "icon", href: "/favicon-32.png", sizes: "32x32", type: "image/png" },
      { rel: "icon", href: "/favicon-16.png", sizes: "16x16", type: "image/png" },
      { rel: "apple-touch-icon", href: "/apple-touch-icon.png" },
      { rel: "manifest", href: "/manifest.json" },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap",
      },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .register("/sw.js")
        .catch((err) => console.warn("SW registration failed:", err));
    }
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ConsentProvider>
          <AuthProvider>
            <Outlet />
            <ConsentBanner />
          </AuthProvider>
        </ConsentProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}