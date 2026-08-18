import { createFileRoute, Link, useNavigate, useSearch } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Check, Crown, Sparkles, Users, X, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { z } from "zod";
import { useAuth } from "@/context/AuthContext";
import { authApi } from "@/services/api";
import {
  useVerifyPayment,
  useCancelSubscription,
  useBachsPricing,
  useBachsInitiatePayment,
} from "@/hooks/queries/useNotificationsBilling";

export const Route = createFileRoute("/app/subscription")({
  validateSearch: z.object({
    status: z.string().optional(),
    reference: z.string().optional(),
    gateway: z.string().optional(),
  }),
  head: () => ({ meta: [{ title: "Upgrade - VerseID" }] }),
  component: Subscription,
});

const PLAN_FEATURES: Record<"Pro" | "Family", string[]> = {
  Pro: [
    "Unlimited verse identifications",
    "KJV, WEB & ASV translations",
    "Full search history & unlimited collections",
    "Daily verse notifications",
    "Priority support",
  ],
  Family: [
    "Everything in Pro",
    "Every translation, including DRA",
    "Use on multiple devices at once",
    "Built for up to 5 people",
    "Priority support",
  ],
};

const FALLBACK_PRICING: Record<
  "NGN" | "USD",
  Record<"Pro" | "Family", { monthly: number; annual: number; savings: string }>
> = {
  NGN: {
    Pro: { monthly: 1000, annual: 9000, savings: "Save ₦3,000" },
    Family: { monthly: 2500, annual: 22500, savings: "Save ₦7,500" },
  },
  USD: {
    Pro: { monthly: 5, annual: 45, savings: "Save $15" },
    Family: { monthly: 12, annual: 108, savings: "Save $36" },
  },
};

function Subscription() {
  const navigate = useNavigate();
  const { status, reference, gateway } = useSearch({ from: "/app/subscription" });
  const { user, refreshUser } = useAuth();
  const [currency, setCurrency] = useState<"NGN" | "USD">("NGN");
  const [selectedPlan, setSelectedPlan] = useState<"Pro" | "Family">("Pro");
  const [interval, setInterval] = useState<"monthly" | "annual">("annual");
  const [cancelConfirm, setCancelConfirm] = useState(false);
  const [bachsSyncState, setBachsSyncState] = useState<"idle" | "syncing" | "done" | "timeout">(
    "idle",
  );

  const { data: bachsPricing, isLoading: pricingLoading } = useBachsPricing();
  const bachsInitiatePayment = useBachsInitiatePayment();
  const verifyPayment = useVerifyPayment(); // legacy Paystack success-link fallback, see useEffect below
  const cancelSub = useCancelSubscription();

  const isSubscribed = user?.plan === "Pro" || user?.plan === "Family";

  // Handle redirect-back. Every current checkout goes through Bachs now
  // (both currencies), which has no verify-by-reference endpoint —
  // entitlement is granted asynchronously by its webhook, so this
  // bounded-poll for refreshUser() to reflect the upgrade stands in for a
  // verify call that doesn't exist. Stops once the plan shows up, or
  // after ~9s if it hasn't (still refreshed one more time on the way to
  // /app/profile, in case it lands right after the poll gives up).
  //
  // The `reference`-based branch below is now unreachable from this
  // page's own UI (nothing here links to Paystack checkout anymore) —
  // kept only so an old bookmarked or emailed
  // ?status=success&reference=... link from before this migration still
  // resolves correctly for an existing Paystack subscriber, rather than
  // silently doing nothing.
  useEffect(() => {
    if (status !== "success") return;

    if (gateway === "bachs") {
      setBachsSyncState("syncing");
      let cancelled = false;

      const poll = async (attempt: number) => {
        const fresh = await authApi.me().catch(() => null);
        if (cancelled) return;
        const active = fresh?.plan === "Pro" || fresh?.plan === "Family";
        if (active) {
          await refreshUser();
          setBachsSyncState("done");
          setTimeout(() => navigate({ to: "/app/profile", replace: true }), 1500);
        } else if (attempt >= 6) {
          setBachsSyncState("timeout");
        } else {
          setTimeout(() => poll(attempt + 1), 1500);
        }
      };
      poll(0);

      return () => {
        cancelled = true;
      };
    }

    if (reference) {
      verifyPayment.mutate(reference, {
        onSuccess: async () => {
          await refreshUser();
          setTimeout(() => {
            navigate({ to: "/app/profile", replace: true });
          }, 1500);
        },
      });
    }
  }, [status, reference, gateway]);

  const handleUpgrade = () => {
    bachsInitiatePayment.mutate({ plan: selectedPlan, interval, currency });
  };

  const handleCancel = async () => {
    await cancelSub.mutateAsync();
    setCancelConfirm(false);
    navigate({ to: "/app/profile" });
  };

  const currencyPricing = bachsPricing?.currencies[currency];
  const planPricing = currencyPricing?.plans[selectedPlan];
  const fallback = FALLBACK_PRICING[currency][selectedPlan];
  const monthly =
    (currency === "USD" ? planPricing?.monthly.dollars : planPricing?.monthly.naira) ??
    fallback.monthly;
  const annual =
    (currency === "USD" ? planPricing?.annual.dollars : planPricing?.annual.naira) ??
    fallback.annual;
  const annualMonthly =
    currency === "USD" ? Math.round((annual / 12) * 100) / 100 : Math.round(annual / 12);
  const savings = planPricing?.annual.savings ?? fallback.savings;
  const freeLimit = bachsPricing?.freeLimit ?? 6;
  const symbol = currency === "USD" ? "$" : "₦";
  const isPending = pricingLoading;

  return (
    <div>
      <Link
        to="/app/profile"
        aria-label="Back to Profile"
        className="h-10 w-10 rounded-full glass grid place-items-center"
      >
        <ArrowLeft className="h-4.5 w-4.5" />
      </Link>

      {/* Payment success banner */}
      {status === "success" && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 p-4 rounded-2xl bg-primary/10 border border-primary/20 text-sm text-primary font-medium text-center"
        >
          {gateway === "bachs" ? (
            bachsSyncState === "done" ? (
              `🎉 Welcome to ${user?.plan ?? selectedPlan}! All features are now unlocked.`
            ) : bachsSyncState === "timeout" ? (
              <>
                Payment received — still finalizing on our end. This can take a minute; check{" "}
                <Link to="/app/profile" className="underline">
                  your profile
                </Link>{" "}
                shortly.
              </>
            ) : (
              "Payment received — activating your account…"
            )
          ) : verifyPayment.isPending ? (
            "Verifying your payment…"
          ) : verifyPayment.isSuccess ? (
            verifyPayment.data?.status === "already_verified" ? (
              `Payment already verified — you're on ${verifyPayment.data.user.plan}.`
            ) : (
              `🎉 Welcome to ${verifyPayment.data?.user.plan ?? selectedPlan}! All features are now unlocked.`
            )
          ) : (
            "Payment received - refreshing your account…"
          )}
        </motion.div>
      )}

      {status === "cancelled" && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 p-4 rounded-2xl bg-muted text-sm text-muted-foreground text-center"
        >
          Payment cancelled - you can try again any time.
        </motion.div>
      )}

      <div className="mt-6 text-center">
        <div className="mx-auto h-14 w-14 rounded-2xl bg-gradient-primary grid place-items-center shadow-glow">
          <Crown className="h-7 w-7 text-white" />
        </div>
        <h1 className="mt-5 font-display text-3xl font-semibold tracking-tight">
          Upgrade to <span className="text-gradient">{selectedPlan}</span>
        </h1>
        <p className="mt-2 text-muted-foreground">
          {selectedPlan === "Family"
            ? "Unlimited searches · Every translation · Shared with your household"
            : "Unlimited searches · All features · Choose your currency"}
        </p>
      </div>

      {/* Currency toggle — both NGN and USD now go through Bachs. */}
      <div className="mt-5 flex justify-center">
        <div className="inline-flex p-1 rounded-full glass-strong shadow-card">
          {(["NGN", "USD"] as const).map((c) => (
            <button
              key={c}
              onClick={() => setCurrency(c)}
              className={`px-4 py-1.5 rounded-full text-xs font-medium transition ${
                currency === c
                  ? "bg-gradient-primary text-white shadow-glow"
                  : "text-muted-foreground"
              }`}
            >
              {c === "NGN" ? "₦ Naira" : "$ USD"}
            </button>
          ))}
        </div>
      </div>

      {/* Plan tier selector */}
      <div className="mt-6 grid grid-cols-2 gap-3">
        {(["Pro", "Family"] as const).map((p) => (
          <button
            key={p}
            onClick={() => setSelectedPlan(p)}
            className={`p-4 rounded-2xl text-left transition ${
              selectedPlan === p
                ? "bg-gradient-primary text-white shadow-glow"
                : "glass-strong shadow-card"
            }`}
          >
            {p === "Pro" ? (
              <Sparkles
                className={`h-4.5 w-4.5 ${selectedPlan === p ? "text-white" : "text-primary"}`}
              />
            ) : (
              <Users
                className={`h-4.5 w-4.5 ${selectedPlan === p ? "text-white" : "text-primary"}`}
              />
            )}
            <div className="mt-2 font-display text-base font-semibold">{p}</div>
            <div
              className={`text-xs mt-0.5 ${selectedPlan === p ? "text-white/80" : "text-muted-foreground"}`}
            >
              {p === "Pro" ? "Just for you" : "Up to 5 people"}
            </div>
          </button>
        ))}
      </div>

      {/* Interval toggle */}
      <div className="mt-4 relative flex p-1 rounded-2xl glass-strong shadow-card">
        {(["monthly", "annual"] as const).map((p) => (
          <button
            key={p}
            onClick={() => setInterval(p)}
            className="relative flex-1 py-2.5 text-sm font-medium"
          >
            {interval === p && (
              <motion.div
                layoutId="interval-pill"
                className="absolute inset-0 bg-gradient-primary rounded-xl shadow-glow"
                transition={{ type: "spring", stiffness: 340, damping: 30 }}
              />
            )}
            <span
              className={`relative capitalize ${interval === p ? "text-white" : "text-muted-foreground"}`}
            >
              {p === "monthly" ? "Monthly" : `Annual · ${savings}`}
            </span>
          </button>
        ))}
      </div>

      {/* Price card */}
      <motion.div
        key={`${currency}-${selectedPlan}-${interval}`}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-5 p-6 rounded-3xl glass-strong shadow-card"
      >
        <div className="flex items-end justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-primary font-medium">
              {selectedPlan}
            </div>
            {isPending ? (
              <div className="mt-1 h-10 w-32 rounded-xl glass animate-pulse" />
            ) : (
              <div className="mt-1 font-display text-4xl font-semibold">
                {symbol}
                {(interval === "monthly" ? monthly : annualMonthly).toLocaleString(
                  currency === "NGN" ? "en-NG" : "en-US",
                )}
                <span className="text-base text-muted-foreground font-normal">/mo</span>
              </div>
            )}
            {interval === "annual" && !isPending && (
              <div className="text-xs text-muted-foreground mt-0.5">
                Billed as {symbol}
                {annual.toLocaleString(currency === "NGN" ? "en-NG" : "en-US")}/year
              </div>
            )}
          </div>
          {selectedPlan === "Family" ? (
            <Users className="h-5 w-5 text-primary" />
          ) : (
            <Sparkles className="h-5 w-5 text-primary" />
          )}
        </div>
        <ul className="mt-5 space-y-2.5">
          {PLAN_FEATURES[selectedPlan].map((f) => (
            <li key={f} className="flex items-center gap-2.5 text-sm">
              <span className="h-5 w-5 rounded-full bg-primary-soft grid place-items-center shrink-0">
                <Check className="h-3 w-3 text-primary" strokeWidth={3} />
              </span>
              {f}
            </li>
          ))}
        </ul>
      </motion.div>

      {/* Free plan note */}
      <div className="mt-4 p-4 rounded-2xl glass text-sm text-muted-foreground text-center">
        Free plan includes <span className="text-foreground font-medium">{freeLimit} searches</span>{" "}
        per day.
      </div>

      {isSubscribed ? (
        <>
          <div className="mt-6 p-4 rounded-2xl bg-primary/10 border border-primary/20 text-center">
            <Crown className="h-5 w-5 text-primary mx-auto mb-1" />
            <p className="text-sm font-medium text-primary">You're on {user?.plan}</p>
            {user?.planExpiresAt && (
              <p className="text-xs text-muted-foreground mt-1">
                Renews{" "}
                {new Date(user.planExpiresAt).toLocaleDateString("en-NG", {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}
              </p>
            )}
          </div>
          <button
            onClick={() => setCancelConfirm(true)}
            className="mt-3 w-full h-12 rounded-2xl glass-strong text-sm text-destructive font-medium"
          >
            Cancel subscription
          </button>
        </>
      ) : (
        <>
          <button
            onClick={handleUpgrade}
            disabled={bachsInitiatePayment.isPending || isPending}
            className="mt-6 w-full h-14 rounded-2xl bg-gradient-primary text-white font-medium shadow-glow disabled:opacity-70"
          >
            {bachsInitiatePayment.isPending ? "Redirecting to payment…" : "Subscribe with Bachs"}
          </button>
          <p className="mt-3 text-center text-[11px] text-muted-foreground">
            Secure payment via Bachs · {currency} pricing · Cancel any time
          </p>
        </>
      )}

      {/* Cancel confirmation modal */}
      <AnimatePresence>
        {cancelConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm grid place-items-end sm:place-items-center px-4 pb-6"
            onClick={() => setCancelConfirm(false)}
          >
            <motion.div
              initial={{ y: 40, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 40, opacity: 0 }}
              transition={{ type: "spring", stiffness: 360, damping: 32 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-sm rounded-3xl bg-surface shadow-card p-6"
            >
              <div className="flex items-start gap-3">
                <div className="h-11 w-11 rounded-2xl bg-destructive/10 grid place-items-center">
                  <ShieldAlert className="h-5 w-5 text-destructive" />
                </div>
                <div className="flex-1">
                  <div className="font-display text-lg font-semibold">Cancel {user?.plan}?</div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    You'll keep {user?.plan} features until the end of your billing period, then
                    revert to {freeLimit} searches/day.
                  </p>
                </div>
                <button
                  onClick={() => setCancelConfirm(false)}
                  aria-label="Close"
                  className="h-8 w-8 rounded-full grid place-items-center hover:bg-muted"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-5 grid grid-cols-2 gap-2">
                <button
                  onClick={() => setCancelConfirm(false)}
                  className="h-12 rounded-2xl glass-strong font-medium text-sm"
                >
                  Keep {user?.plan}
                </button>
                <button
                  onClick={handleCancel}
                  disabled={cancelSub.isPending}
                  className="h-12 rounded-2xl bg-destructive text-white font-medium text-sm shadow-card disabled:opacity-60"
                >
                  {cancelSub.isPending ? "Cancelling…" : "Cancel"}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}