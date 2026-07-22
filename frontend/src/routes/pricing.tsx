import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, Check, Crown, Sparkles } from "lucide-react";
import { useState } from "react";
import { usePricing } from "@/hooks/queries/useNotificationsBilling";

export const Route = createFileRoute("/pricing")({
  head: () => ({
    meta: [
      { title: "Pricing - VerseID" },
      {
        name: "description",
        content:
          "VerseID pricing: 6 free verse identifications a day, or go Pro for unlimited searches, both KJV & WEB translations, and priority support.",
      },
      { property: "og:title", content: "VerseID Pricing" },
      {
        property: "og:description",
        content: "6 free verse identifications a day, or go Pro for unlimited searches and more.",
      },
      { property: "og:url", content: "https://verseid.top/pricing" },
      {
        "script:ld+json": {
          "@context": "https://schema.org",
          "@type": "Product",
          name: "VerseID Pro",
          description:
            "Unlimited Bible verse identifications, both KJV & WEB translations, full search history, custom collections, and priority support.",
          offers: [
            {
              "@type": "Offer",
              name: "Monthly",
              price: "1000",
              priceCurrency: "NGN",
              url: "https://verseid.top/pricing",
            },
            {
              "@type": "Offer",
              name: "Annual",
              price: "9000",
              priceCurrency: "NGN",
              url: "https://verseid.top/pricing",
            },
          ],
        },
      },
    ],
    links: [{ rel: "canonical", href: "https://verseid.top/pricing" }],
  }),
  component: Pricing,
});

const FREE_FEATURES = [
  "6 verse identifications a day",
  "Saved verses",
  "Full search history",
  "Custom collections",
];

const PRO_FEATURES = [
  "Unlimited verse identifications",
  "Both KJV & WEB translations",
  "Full search history",
  "Custom collections",
  "Daily verse notifications",
  "Priority support",
];

function Pricing() {
  const [plan, setPlan] = useState<"monthly" | "annual">("annual");
  const { data: pricing, isLoading } = usePricing();

  const monthlyNaira = pricing?.plans.monthly.naira ?? 1000;
  const annualNaira = pricing?.plans.annual.naira ?? 9000;
  const annualMonthly = Math.round(annualNaira / 12);
  const savings = pricing?.plans.annual.savings ?? "Save ₦3,000";

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-2xl px-5 py-8">
        <div className="flex items-center gap-3 mb-8">
          <Link
            to="/"
            aria-label="Back"
            className="h-10 w-10 rounded-full glass grid place-items-center"
          >
            <ArrowLeft className="h-4.5 w-4.5" />
          </Link>
          <div>
            <h1 className="font-display text-2xl font-semibold">Pricing</h1>
            <p className="text-xs text-muted-foreground">Simple, Nigerian-priced plans.</p>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-5">
          {/* Free plan */}
          <div className="rounded-[2rem] p-7 glass-strong shadow-card">
            <h2 className="font-display text-lg font-semibold">Free</h2>
            <p className="mt-1 text-3xl font-display font-semibold">₦0</p>
            <p className="text-xs text-muted-foreground mb-5">forever</p>
            <ul className="space-y-2.5">
              {FREE_FEATURES.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm">
                  <Check className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                  {f}
                </li>
              ))}
            </ul>
            <Link
              to="/auth"
              className="mt-7 flex items-center justify-center h-12 rounded-full glass font-medium text-sm hover:bg-primary-soft transition"
            >
              Get started free
            </Link>
          </div>

          {/* Pro plan */}
          <div className="relative overflow-hidden rounded-[2rem] p-7 bg-gradient-primary shadow-glow text-white">
            <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_30%_20%,white,transparent_40%)]" />
            <div className="relative">
              <div className="flex items-center gap-2">
                <Crown className="h-5 w-5" />
                <h2 className="font-display text-lg font-semibold">Pro</h2>
              </div>

              {/* Monthly / annual toggle */}
              <div className="mt-4 inline-flex p-1 rounded-full bg-white/15">
                {(["monthly", "annual"] as const).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPlan(p)}
                    className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition ${
                      plan === p ? "bg-white text-primary" : "text-white/80"
                    }`}
                  >
                    {p === "monthly" ? "Monthly" : `Annual · ${savings}`}
                  </button>
                ))}
              </div>

              <p className="mt-4 text-3xl font-display font-semibold">
                ₦
                {isLoading
                  ? "…"
                  : (plan === "monthly" ? monthlyNaira : annualMonthly).toLocaleString("en-NG")}
                <span className="text-base font-normal">/mo</span>
              </p>
              {plan === "annual" && !isLoading && (
                <p className="text-xs text-white/75">
                  Billed as ₦{annualNaira.toLocaleString("en-NG")}/year
                </p>
              )}

              <ul className="mt-5 space-y-2.5">
                {PRO_FEATURES.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <Sparkles className="h-4 w-4 shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>

              {/* Sends a logged-out visitor to sign in, then straight to the
                  Subscription screen to actually complete checkout — rather
                  than dropping them on the generic home screen after login
                  and making them find their way back here. */}
              <Link
                to="/auth"
                search={{ redirect: "subscription" }}
                className="mt-7 flex items-center justify-center h-12 rounded-full bg-white text-primary font-medium text-sm hover:scale-[1.02] transition-transform"
              >
                Get Pro
              </Link>
              <p className="mt-3 text-center text-[11px] text-white/70">
                Secure payment via Paystack · Cancel any time
              </p>
            </div>
          </div>
        </div>

        <div className="mt-12 flex gap-4 text-xs text-muted-foreground">
          <Link to="/terms" className="hover:text-foreground transition">
            Terms
          </Link>
          <Link to="/privacy" className="hover:text-foreground transition">
            Privacy Policy
          </Link>
          <Link to="/help" className="hover:text-foreground transition">
            Help
          </Link>
          <Link to="/" className="hover:text-foreground transition">
            Home
          </Link>
        </div>
      </div>
    </div>
  );
}
