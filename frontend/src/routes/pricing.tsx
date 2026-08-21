import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, Check, Crown, Sparkles, Users } from "lucide-react";
import { useState } from "react";
import { useBachsPricing } from "@/hooks/queries/useNotificationsBilling";

export const Route = createFileRoute("/pricing")({
  head: () => ({
    meta: [
      { title: "Pricing - VerseID" },
      {
        name: "description",
        content:
          "VerseID pricing: 6 free verse identifications a day with KJV & WEB, or go Pro for unlimited searches with KJV, WEB & ASV, or Family to share every translation with up to 5 people. Priced in Naira or USD.",
      },
      { property: "og:title", content: "VerseID Pricing" },
      {
        property: "og:description",
        content:
          "6 free verse identifications a day, Pro for unlimited searches, or Family to share with up to 5 people. Naira or USD.",
      },
      { property: "og:url", content: "https://verseid.top/pricing" },
      {
        "script:ld+json": {
          "@context": "https://schema.org",
          "@type": "Product",
          name: "VerseID Pro",
          description:
            "Unlimited Bible verse identifications, KJV, WEB & ASV translations, full search history, custom collections, and priority support.",
          offers: [
            {
              "@type": "Offer",
              name: "Pro Monthly (NGN)",
              price: "1000",
              priceCurrency: "NGN",
              url: "https://verseid.top/pricing",
            },
            {
              "@type": "Offer",
              name: "Pro Annual (NGN)",
              price: "9000",
              priceCurrency: "NGN",
              url: "https://verseid.top/pricing",
            },
            {
              "@type": "Offer",
              name: "Family Monthly (NGN)",
              price: "2500",
              priceCurrency: "NGN",
              url: "https://verseid.top/pricing",
            },
            {
              "@type": "Offer",
              name: "Family Annual (NGN)",
              price: "22500",
              priceCurrency: "NGN",
              url: "https://verseid.top/pricing",
            },
            {
              "@type": "Offer",
              name: "Pro Monthly (USD)",
              price: "1.00",
              priceCurrency: "USD",
              url: "https://verseid.top/pricing",
            },
            {
              "@type": "Offer",
              name: "Pro Annual (USD)",
              price: "6.67",
              priceCurrency: "USD",
              url: "https://verseid.top/pricing",
            },
            {
              "@type": "Offer",
              name: "Family Monthly (USD)",
              price: "1.85",
              priceCurrency: "USD",
              url: "https://verseid.top/pricing",
            },
            {
              "@type": "Offer",
              name: "Family Annual (USD)",
              price: "16.67",
              priceCurrency: "USD",
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
  "KJV & WEB translations",
  "Saved verses",
  "Sign in on 1 device at a time",
];

const PRO_FEATURES = [
  "Unlimited verse identifications",
  "KJV, WEB & ASV translations",
  "Full search history & unlimited collections",
  "Daily verse notifications",
  "Priority support",
  "Sign in on 1 device at a time",
];

const FAMILY_FEATURES = [
  "Everything in Pro",
  "Every translation, including DRA",
  "Sign in on multiple devices at once",
  "Built for up to 5 people",
  "Priority support",
];

function Pricing() {
  const [currency, setCurrency] = useState<"NGN" | "USD">("NGN");
  const [interval, setInterval] = useState<"monthly" | "annual">("annual");
  const { data: bachsPricing, isLoading } = useBachsPricing();

  const proMonthlyNaira = bachsPricing?.currencies.NGN.plans.Pro.monthly.naira ?? 1000;
  const proAnnualNaira = bachsPricing?.currencies.NGN.plans.Pro.annual.naira ?? 9000;
  const proAnnualMonthlyNaira = Math.round(proAnnualNaira / 12);
  const proSavingsNaira = bachsPricing?.currencies.NGN.plans.Pro.annual.savings ?? "Save ₦3,000";

  const familyMonthlyNaira = bachsPricing?.currencies.NGN.plans.Family.monthly.naira ?? 2500;
  const familyAnnualNaira = bachsPricing?.currencies.NGN.plans.Family.annual.naira ?? 22500;
  const familyAnnualMonthlyNaira = Math.round(familyAnnualNaira / 12);
  const familySavingsNaira =
    bachsPricing?.currencies.NGN.plans.Family.annual.savings ?? "Save ₦7,500";

  const proMonthlyUsd = bachsPricing?.currencies.USD.plans.Pro.monthly.dollars ?? 1.0;
  const proAnnualUsd = bachsPricing?.currencies.USD.plans.Pro.annual.dollars ?? 6.67;
  const proAnnualMonthlyUsd = Math.round((proAnnualUsd / 12) * 100) / 100;
  const proSavingsUsd = bachsPricing?.currencies.USD.plans.Pro.annual.savings ?? "Save $5.33";

  const familyMonthlyUsd = bachsPricing?.currencies.USD.plans.Family.monthly.dollars ?? 1.85;
  const familyAnnualUsd = bachsPricing?.currencies.USD.plans.Family.annual.dollars ?? 16.67;
  const familyAnnualMonthlyUsd = Math.round((familyAnnualUsd / 12) * 100) / 100;
  const familySavingsUsd = bachsPricing?.currencies.USD.plans.Family.annual.savings ?? "Save $5.53";
  const symbol = currency === "USD" ? "$" : "₦";
  const locale = currency === "USD" ? "en-US" : "en-NG";
  const proMonthly = currency === "USD" ? proMonthlyUsd : proMonthlyNaira;
  const proAnnual = currency === "USD" ? proAnnualUsd : proAnnualNaira;
  const proAnnualMonthly = currency === "USD" ? proAnnualMonthlyUsd : proAnnualMonthlyNaira;
  const proSavings = currency === "USD" ? proSavingsUsd : proSavingsNaira;
  const familyMonthly = currency === "USD" ? familyMonthlyUsd : familyMonthlyNaira;
  const familyAnnual = currency === "USD" ? familyAnnualUsd : familyAnnualNaira;
  const familyAnnualMonthly =
    currency === "USD" ? familyAnnualMonthlyUsd : familyAnnualMonthlyNaira;
  const familySavings = currency === "USD" ? familySavingsUsd : familySavingsNaira;
  const gatewayName = "Bachs";

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-4xl px-5 py-8">
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
            <p className="text-xs text-muted-foreground">Simple plans, in Naira or USD.</p>
          </div>
        </div>

        <div className="mb-6 flex flex-wrap gap-3">
          {/* Currency toggle */}
          <div className="inline-flex p-1 rounded-full glass-strong shadow-card">
            {(["NGN", "USD"] as const).map((c) => (
              <button
                key={c}
                onClick={() => setCurrency(c)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition ${
                  currency === c
                    ? "bg-gradient-primary text-white shadow-glow"
                    : "text-muted-foreground"
                }`}
              >
                {c === "NGN" ? "₦ Naira" : "$ USD"}
              </button>
            ))}
          </div>

          {/* Monthly/annual toggle — applies to both paid tiers below */}
          <div className="inline-flex p-1 rounded-full glass-strong shadow-card">
            {(["monthly", "annual"] as const).map((p) => (
              <button
                key={p}
                onClick={() => setInterval(p)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition ${
                  interval === p
                    ? "bg-gradient-primary text-white shadow-glow"
                    : "text-muted-foreground"
                }`}
              >
                {p === "monthly" ? "Monthly" : "Annual"}
              </button>
            ))}
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-5">
          {/* Free plan */}
          <div className="rounded-[2rem] p-7 glass-strong shadow-card">
            <h2 className="font-display text-lg font-semibold">Free</h2>
            <p className="mt-1 text-3xl font-display font-semibold">{symbol}0</p>
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

              <p className="mt-4 text-3xl font-display font-semibold">
                {symbol}
                {isLoading
                  ? "…"
                  : (interval === "monthly" ? proMonthly : proAnnualMonthly).toLocaleString(locale)}
                <span className="text-base font-normal">/mo</span>
              </p>
              {interval === "annual" && !isLoading && (
                <p className="text-xs text-white/75">
                  Billed as {symbol}
                  {proAnnual.toLocaleString(locale)}/year · {proSavings}
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
                Secure payment via {gatewayName} · Cancel any time
              </p>
            </div>
          </div>

          {/* Family plan */}
          <div className="relative overflow-hidden rounded-[2rem] p-7 glass-strong shadow-card border border-primary/20">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-primary" />
              <h2 className="font-display text-lg font-semibold">Family</h2>
            </div>

            <p className="mt-4 text-3xl font-display font-semibold">
              {symbol}
              {isLoading
                ? "…"
                : (interval === "monthly" ? familyMonthly : familyAnnualMonthly).toLocaleString(
                    locale,
                  )}
              <span className="text-base font-normal text-muted-foreground">/mo</span>
            </p>
            {interval === "annual" && !isLoading && (
              <p className="text-xs text-muted-foreground">
                Billed as {symbol}
                {familyAnnual.toLocaleString(locale)}/year · {familySavings}
              </p>
            )}

            <ul className="mt-5 space-y-2.5">
              {FAMILY_FEATURES.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm">
                  <Users className="h-4 w-4 text-primary shrink-0 mt-0.5" />
                  {f}
                </li>
              ))}
            </ul>

            <Link
              to="/auth"
              search={{ redirect: "subscription" }}
              className="mt-7 flex items-center justify-center h-12 rounded-full bg-gradient-primary text-white font-medium text-sm shadow-glow hover:scale-[1.02] transition-transform"
            >
              Get Family
            </Link>
            <p className="mt-3 text-center text-[11px] text-muted-foreground">
              Secure payment via {gatewayName} · Cancel any time
            </p>
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