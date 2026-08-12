import { Link } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { Cookie } from "lucide-react";

import { useConsent } from "@/context/ConsentContext";

/** Bottom-of-screen analytics consent prompt. Shows once, on first visit,
 * until the user accepts or declines — then never again (their choice is
 * remembered and can be changed later from Settings → Privacy). */
export function ConsentBanner() {
  const { consent, hydrated, grantConsent, declineConsent } = useConsent();

  const visible = hydrated && consent === "undecided";

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          initial={{ y: 80, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 80, opacity: 0 }}
          transition={{ type: "spring", stiffness: 360, damping: 32 }}
          className="fixed inset-x-0 bottom-0 z-50 px-4 pb-[max(env(safe-area-inset-bottom),16px)]"
          role="dialog"
          aria-live="polite"
          aria-label="Analytics consent"
        >
          <div className="mx-auto max-w-md rounded-3xl glass-strong shadow-card p-5">
            <div className="flex items-start gap-3">
              <div className="h-9 w-9 shrink-0 rounded-xl bg-primary-soft grid place-items-center">
                <Cookie className="h-4.5 w-4.5 text-primary" />
              </div>
              <div className="flex-1">
                <div className="font-display text-sm font-semibold">We use analytics</div>
                <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                  We'd like to use Google Analytics to understand how VerseID is used, so we can
                  improve it. It's optional see our{" "}
                  <Link to="/privacy" className="text-primary underline underline-offset-2">
                    Privacy Policy
                  </Link>{" "}
                  for details, and you can change your choice anytime in Settings.
                </p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2">
              <button
                onClick={declineConsent}
                className="h-11 rounded-2xl glass font-medium text-sm text-foreground"
              >
                Decline
              </button>
              <button
                onClick={grantConsent}
                className="h-11 rounded-2xl bg-gradient-primary text-white font-medium text-sm shadow-glow"
              >
                Accept
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}