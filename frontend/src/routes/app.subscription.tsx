import { createFileRoute, Link, useNavigate, useSearch } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Check, Crown, Sparkles, Users, X, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { z } from "zod";
import { useAuth } from "@/context/AuthContext";
import {
  usePricing,
  useInitiatePayment,
  useVerifyPayment,
  useCancelSubscription,
} from "@/hooks/queries/useNotificationsBilling";

export const Route = createFileRoute("/app/subscription")({
  validateSearch: z.object({ status: z.string().optional(), reference: z.string().optional() }),
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

const FALLBACK_NAIRA: Record<
  "Pro" | "Family",
  { monthly: number; annual: number; savings: string }
> = {
  Pro: { monthly: 1000, annual: 9000, savings: "Save ₦3,000" },
  Family: { monthly: 2500, annual: 22500, savings: "Save ₦7,500" },
};

function Subscription() {
  const navigate = useNavigate();
  const { status, reference } = useSearch({ from: "/app/subscription" });
  const { user, refreshUser } = useAuth();
  const [selectedPlan, setSelectedPlan] = useState<"Pro" | "Family">("Pro");
  const [interval, setInterval] = useState<"monthly" | "annual">("annual");
  const [cancelConfirm, setCancelConfirm] = useState(false);

  const { data: pricing, isLoading: pricingLoading } = usePricing();
  const initiatePayment = useInitiatePayment();
  const verifyPayment = useVerifyPayment();
  const cancelSub = useCancelSubscription();

  const isSubscribed = user?.plan === "Pro" || user?.plan === "Family";

  // Handle Paystack redirect-back with a reference to verify
  useEffect(() => {
    if (status === "success" && reference) {
      verifyPayment.mutate(reference, {
        onSuccess: async () => {
          await refreshUser();
          // Leave the success message on screen just long enough to
          // register, then move off this URL entirely — refreshing,
          // sharing, or hitting back on a page parked at
          // ?status=success&reference=... would otherwise silently
          // re-run verification against a reference that's already been
          // processed every time.
          setTimeout(() => {
            navigate({ to: "/app/profile", replace: true });
          }, 1500);
        },
      });
    }
  }, [status, reference]);

  const handleUpgrade = () => {
    initiatePayment.mutate({ plan: selectedPlan, interval });
  };

  const handleCancel = async () => {
    await cancelSub.mutateAsync();
    setCancelConfirm(false);
    navigate({ to: "/app/profile" });
  };

  const planPricing = pricing?.plans[selectedPlan];
  const fallback = FALLBACK_NAIRA[selectedPlan];
  const monthlyNaira = planPricing?.monthly.naira ?? fallback.monthly;
  const annualNaira = planPricing?.annual.naira ?? fallback.annual;
  const annualMonthly = Math.round(annualNaira / 12);
  const savings = planPricing?.annual.savings ?? fallback.savings;

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
          {verifyPayment.isPending
            ? "Verifying your payment…"
            : verifyPayment.isSuccess
              ? verifyPayment.data?.status === "already_verified"
                ? `Payment already verified — you're on ${verifyPayment.data.user.plan}.`
                : `🎉 Welcome to ${verifyPayment.data?.user.plan ?? selectedPlan}! All features are now unlocked.`
              : "Payment received - refreshing your account…"}
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
            : "Unlimited searches · All features · Nigerian pricing"}
        </p>
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
        key={`${selectedPlan}-${interval}`}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-5 p-6 rounded-3xl glass-strong shadow-card"
      >
        <div className="flex items-end justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-primary font-medium">
              {selectedPlan}
            </div>
            {pricingLoading ? (
              <div className="mt-1 h-10 w-32 rounded-xl glass animate-pulse" />
            ) : (
              <div className="mt-1 font-display text-4xl font-semibold">
                ₦
                {interval === "monthly"
                  ? monthlyNaira.toLocaleString("en-NG")
                  : annualMonthly.toLocaleString("en-NG")}
                <span className="text-base text-muted-foreground font-normal">/mo</span>
              </div>
            )}
            {interval === "annual" && !pricingLoading && (
              <div className="text-xs text-muted-foreground mt-0.5">
                Billed as ₦{annualNaira.toLocaleString("en-NG")}/year
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
        Free plan includes{" "}
        <span className="text-foreground font-medium">{pricing?.freeLimit ?? 6} searches</span> per
        day.
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
            disabled={initiatePayment.isPending || pricingLoading}
            className="mt-6 w-full h-14 rounded-2xl bg-gradient-primary text-white font-medium shadow-glow disabled:opacity-70"
          >
            {initiatePayment.isPending ? "Redirecting to payment…" : "Subscribe with Paystack"}
          </button>
          <p className="mt-3 text-center text-[11px] text-muted-foreground">
            Secure payment via Paystack · NGN pricing · Cancel any time
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
                    revert to {pricing?.freeLimit ?? 6} searches/day.
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