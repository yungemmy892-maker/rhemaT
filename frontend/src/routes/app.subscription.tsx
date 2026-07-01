import { createFileRoute, Link, useNavigate, useSearch } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Check, Crown, Sparkles, X, ShieldAlert } from "lucide-react";
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
  head: () => ({ meta: [{ title: "Upgrade to Pro — VerseID" }] }),
  component: Subscription,
});

const FEATURES = [
  "Unlimited verse identifications",
  "Both KJV & WEB translations",
  "Full search history",
  "Custom collections",
  "Daily verse notifications",
  "Priority support",
];

function Subscription() {
  const navigate = useNavigate();
  const { status, reference } = useSearch({ from: "/app/subscription" });
  const { user, refreshUser } = useAuth();
  const [plan, setPlan] = useState<"monthly" | "annual">("annual");
  const [cancelConfirm, setCancelConfirm] = useState(false);

  const { data: pricing, isLoading: pricingLoading } = usePricing();
  const initiatePayment = useInitiatePayment();
  const verifyPayment = useVerifyPayment();
  const cancelSub = useCancelSubscription();

  const isPro = user?.plan === "Pro";

  // Handle Paystack redirect-back with a reference to verify
  useEffect(() => {
    if (status === "success" && reference) {
      verifyPayment.mutate(reference, {
        onSuccess: () => refreshUser(),
      });
    }
  }, [status, reference]);

  const handleUpgrade = () => {
    initiatePayment.mutate({ interval: plan });
  };

  const handleCancel = async () => {
    await cancelSub.mutateAsync();
    setCancelConfirm(false);
    navigate({ to: "/app/profile" });
  };

  const monthlyNaira = pricing?.plans.monthly.naira ?? 1000;
  const annualNaira = pricing?.plans.annual.naira ?? 9000;
  const annualMonthly = Math.round(annualNaira / 12);
  const savings = pricing?.plans.annual.savings ?? "Save ₦3,000";

  return (
    <div>
      <Link to="/app/profile" className="h-10 w-10 rounded-full glass grid place-items-center">
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
              ? "🎉 Welcome to Pro! All features are now unlocked."
              : "Payment received — refreshing your account…"}
        </motion.div>
      )}

      {status === "cancelled" && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 p-4 rounded-2xl bg-muted text-sm text-muted-foreground text-center"
        >
          Payment cancelled — you can try again any time.
        </motion.div>
      )}

      <div className="mt-6 text-center">
        <div className="mx-auto h-14 w-14 rounded-2xl bg-gradient-primary grid place-items-center shadow-glow">
          <Crown className="h-7 w-7 text-white" />
        </div>
        <h1 className="mt-5 font-display text-3xl font-semibold tracking-tight">
          Go <span className="text-gradient">Pro</span>
        </h1>
        <p className="mt-2 text-muted-foreground">
          Unlimited searches · All features · Nigerian pricing
        </p>
      </div>

      {/* Plan toggle */}
      <div className="mt-7 relative flex p-1 rounded-2xl glass-strong shadow-card">
        {(["monthly", "annual"] as const).map((p) => (
          <button
            key={p}
            onClick={() => setPlan(p)}
            className="relative flex-1 py-2.5 text-sm font-medium"
          >
            {plan === p && (
              <motion.div
                layoutId="plan-pill"
                className="absolute inset-0 bg-gradient-primary rounded-xl shadow-glow"
                transition={{ type: "spring", stiffness: 340, damping: 30 }}
              />
            )}
            <span className={`relative capitalize ${plan === p ? "text-white" : "text-muted-foreground"}`}>
              {p === "monthly" ? "Monthly" : `Annual · ${savings}`}
            </span>
          </button>
        ))}
      </div>

      {/* Price card */}
      <motion.div
        key={plan}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-5 p-6 rounded-3xl glass-strong shadow-card"
      >
        <div className="flex items-end justify-between">
          <div>
            <div className="text-xs uppercase tracking-[0.16em] text-primary font-medium">Pro</div>
            {pricingLoading ? (
              <div className="mt-1 h-10 w-32 rounded-xl glass animate-pulse" />
            ) : (
              <div className="mt-1 font-display text-4xl font-semibold">
                ₦{plan === "monthly" ? monthlyNaira.toLocaleString("en-NG") : annualMonthly.toLocaleString("en-NG")}
                <span className="text-base text-muted-foreground font-normal">/mo</span>
              </div>
            )}
            {plan === "annual" && !pricingLoading && (
              <div className="text-xs text-muted-foreground mt-0.5">
                Billed as ₦{annualNaira.toLocaleString("en-NG")}/year
              </div>
            )}
          </div>
          <Sparkles className="h-5 w-5 text-primary" />
        </div>
        <ul className="mt-5 space-y-2.5">
          {FEATURES.map((f) => (
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
        <span className="text-foreground font-medium">
          {pricing?.freeLimit ?? 20} searches
        </span>{" "}
        per day.
      </div>

      {isPro ? (
        <>
          <div className="mt-6 p-4 rounded-2xl bg-primary/10 border border-primary/20 text-center">
            <Crown className="h-5 w-5 text-primary mx-auto mb-1" />
            <p className="text-sm font-medium text-primary">You're on Pro</p>
            {user?.planExpiresAt && (
              <p className="text-xs text-muted-foreground mt-1">
                Renews {new Date(user.planExpiresAt).toLocaleDateString("en-NG", { day: "numeric", month: "long", year: "numeric" })}
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
                  <div className="font-display text-lg font-semibold">Cancel Pro?</div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    You'll keep Pro features until the end of your billing period, then revert to 20 searches/day.
                  </p>
                </div>
                <button onClick={() => setCancelConfirm(false)} className="h-8 w-8 rounded-full grid place-items-center hover:bg-muted">
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-5 grid grid-cols-2 gap-2">
                <button onClick={() => setCancelConfirm(false)} className="h-12 rounded-2xl glass-strong font-medium text-sm">
                  Keep Pro
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
