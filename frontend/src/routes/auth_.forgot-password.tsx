import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Mail, KeyRound, Lock, Eye, EyeOff, CheckCircle2 } from "lucide-react";
import { useRef, useState } from "react";
import { z } from "zod";
import { authApi } from "@/services/api";

const searchSchema = z.object({
  // Pre-fills step 1 with whatever the person had already typed on /auth.
  email: z.string().default(""),
});

export const Route = createFileRoute("/auth_/forgot-password")({
  validateSearch: searchSchema,
  head: () => ({
    meta: [{ title: "Reset password — VerseID" }],
  }),
  component: ForgotPassword,
});

type Step = "email" | "code" | "password" | "done";

const STEP_ORDER: Step[] = ["email", "code", "password", "done"];

const RESEND_COOLDOWN_SECONDS = 30;

function ForgotPassword() {
  const { email: initialEmail } = Route.useSearch();
  const navigate = useNavigate();

  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState(["", "", "", "", "", ""]);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resendCooldown, setResendCooldown] = useState(0);

  const codeInputs = useRef<Array<HTMLInputElement | null>>([]);
  const codeValue = code.join("");

  const startResendCooldown = () => {
    setResendCooldown(RESEND_COOLDOWN_SECONDS);
    const interval = setInterval(() => {
      setResendCooldown((s) => {
        if (s <= 1) {
          clearInterval(interval);
          return 0;
        }
        return s - 1;
      });
    }, 1000);
  };

  /* ── Step 1: email ─────────────────────────────────────────────────── */
  const handleSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    setLoading(true);
    setError(null);
    try {
      await authApi.forgotPassword(email);
      setStep("code");
      startResendCooldown();
    } catch {
      setError("Couldn't send a reset code. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0) return;
    setError(null);
    try {
      await authApi.forgotPassword(email);
      setCode(["", "", "", "", "", ""]);
      codeInputs.current[0]?.focus();
      startResendCooldown();
    } catch {
      setError("Couldn't resend the code. Please try again.");
    }
  };

  /* ── Step 2: code ──────────────────────────────────────────────────── */
  const handleDigitChange = (index: number, raw: string) => {
    const digit = raw.replace(/\D/g, "").slice(-1);
    setCode((prev) => {
      const next = [...prev];
      next[index] = digit;
      return next;
    });
    if (digit && index < 5) codeInputs.current[index + 1]?.focus();
  };

  const handleDigitKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !code[index] && index > 0) {
      codeInputs.current[index - 1]?.focus();
    }
  };

  const handleDigitPaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (!pasted) return;
    e.preventDefault();
    setCode(pasted.padEnd(6, "").split("").slice(0, 6));
    codeInputs.current[Math.min(pasted.length, 5)]?.focus();
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (codeValue.length !== 6) return;
    setLoading(true);
    setError(null);
    try {
      await authApi.verifyResetCode({ email, code: codeValue });
      setStep("password");
    } catch (err) {
      setError((err as { message?: string })?.message || "That code is invalid or has expired.");
    } finally {
      setLoading(false);
    }
  };

  /* ── Step 3: new password ─────────────────────────────────────────── */
  const handleSetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await authApi.resetPassword({ email, code: codeValue, new_password: password });
      setStep("done");
    } catch (err) {
      setError(
        (err as { message?: string })?.message || "Couldn't reset your password. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  };

  const stepIndex = STEP_ORDER.indexOf(step);

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute -top-24 -left-24 h-80 w-80 rounded-full bg-primary/25 blur-3xl animate-float-slow" />
        <div className="absolute bottom-0 -right-24 h-80 w-80 rounded-full bg-accent/50 blur-3xl animate-float-slow [animation-delay:-6s]" />
      </div>

      <div className="mx-auto max-w-md min-h-screen flex flex-col px-6 pt-6 pb-10">
        {step === "done" ? (
          <div className="w-10" />
        ) : (
          <button
            onClick={() => {
              if (step === "email") navigate({ to: "/auth" });
              else if (step === "code") setStep("email");
              else setStep("code");
              setError(null);
            }}
            className="inline-flex items-center gap-2 text-sm text-muted-foreground w-fit"
          >
            <ArrowLeft className="h-4 w-4" /> Back
          </button>
        )}

        {/* Step progress */}
        {step !== "done" && (
          <div className="mt-6 flex items-center gap-2">
            {STEP_ORDER.slice(0, 3).map((s, i) => (
              <div
                key={s}
                className={`h-1.5 flex-1 rounded-full transition-colors ${
                  i <= stepIndex ? "bg-gradient-primary" : "bg-border"
                }`}
              />
            ))}
          </div>
        )}

        <div className="flex-1 flex flex-col justify-center">
          <AnimatePresence mode="wait">
            {step === "email" && (
              <motion.div
                key="email"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.25 }}
              >
                <Header
                  Icon={Mail}
                  title="Forgot your password?"
                  subtitle="Enter the email on your account and we'll send you a 6-digit reset code."
                />
                <form onSubmit={handleSendCode} className="mt-7 space-y-3">
                  <Field Icon={Mail}>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@example.com"
                      className="w-full bg-transparent outline-none text-sm"
                      autoFocus
                      required
                    />
                  </Field>
                  {error && <p className="text-xs text-destructive text-center">{error}</p>}
                  <SubmitButton loading={loading} label="Send code" />
                </form>
              </motion.div>
            )}

            {step === "code" && (
              <motion.div
                key="code"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.25 }}
              >
                <Header
                  Icon={KeyRound}
                  title="Enter your code"
                  subtitle={
                    <>
                      We sent a 6-digit code to{" "}
                      <span className="font-medium text-foreground">{email}</span>. It expires in 10
                      minutes.
                    </>
                  }
                />
                <form onSubmit={handleVerifyCode} className="mt-7 space-y-5">
                  <div className="flex justify-between gap-2">
                    {code.map((digit, i) => (
                      <input
                        key={i}
                        ref={(el) => {
                          codeInputs.current[i] = el;
                        }}
                        value={digit}
                        onChange={(e) => handleDigitChange(i, e.target.value)}
                        onKeyDown={(e) => handleDigitKeyDown(i, e)}
                        onPaste={handleDigitPaste}
                        inputMode="numeric"
                        maxLength={1}
                        autoFocus={i === 0}
                        className="h-14 w-12 rounded-2xl glass-strong shadow-card text-center text-lg font-display font-semibold outline-none focus:ring-2 focus:ring-primary"
                      />
                    ))}
                  </div>

                  {error && <p className="text-xs text-destructive text-center">{error}</p>}

                  <SubmitButton
                    loading={loading}
                    label="Verify code"
                    disabled={codeValue.length !== 6}
                  />

                  <div className="text-center">
                    <button
                      type="button"
                      onClick={handleResend}
                      disabled={resendCooldown > 0}
                      className="text-xs text-primary font-medium disabled:opacity-50 disabled:text-muted-foreground"
                    >
                      {resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : "Resend code"}
                    </button>
                  </div>
                </form>
              </motion.div>
            )}

            {step === "password" && (
              <motion.div
                key="password"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                transition={{ duration: 0.25 }}
              >
                <Header
                  Icon={Lock}
                  title="Set a new password"
                  subtitle="Choose a new password for your VerseID account."
                />
                <form onSubmit={handleSetPassword} className="mt-7 space-y-3">
                  <Field Icon={Lock}>
                    <input
                      type={showPw ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="New password"
                      className="w-full bg-transparent outline-none text-sm"
                      autoFocus
                      required
                      minLength={6}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw(!showPw)}
                      className="text-muted-foreground"
                    >
                      {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </Field>
                  <Field Icon={Lock}>
                    <input
                      type={showPw ? "text" : "password"}
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Confirm new password"
                      className="w-full bg-transparent outline-none text-sm"
                      required
                      minLength={6}
                    />
                  </Field>
                  {error && <p className="text-xs text-destructive text-center">{error}</p>}
                  <SubmitButton loading={loading} label="Reset password" />
                </form>
              </motion.div>
            )}

            {step === "done" && (
              <motion.div
                key="done"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="text-center"
              >
                <div className="mx-auto h-16 w-16 rounded-3xl bg-gradient-primary grid place-items-center shadow-glow">
                  <CheckCircle2 className="h-7 w-7 text-white" strokeWidth={2.4} />
                </div>
                <h1 className="mt-6 font-display text-2xl font-semibold tracking-tight">
                  Password reset
                </h1>
                <p className="mt-2 text-sm text-muted-foreground px-4">
                  Your password has been updated. You've been signed out of all devices for security
                  — sign in again with your new password.
                </p>
                <Link
                  to="/auth"
                  className="mt-7 inline-flex w-full h-14 rounded-2xl bg-gradient-primary text-white font-medium shadow-glow items-center justify-center"
                >
                  Back to sign in
                </Link>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

function Header({
  Icon,
  title,
  subtitle,
}: {
  Icon: React.ComponentType<{ className?: string; strokeWidth?: number }>;
  title: string;
  subtitle: React.ReactNode;
}) {
  return (
    <div className="text-center">
      <div className="mx-auto h-16 w-16 rounded-3xl bg-gradient-primary grid place-items-center shadow-glow">
        <Icon className="h-7 w-7 text-white" strokeWidth={2.4} />
      </div>
      <h1 className="mt-6 font-display text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground px-4">{subtitle}</p>
    </div>
  );
}

function Field({
  Icon,
  children,
}: {
  Icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 h-14 px-4 rounded-2xl glass-strong shadow-card">
      <Icon className="h-4.5 w-4.5 text-primary" />
      {children}
    </div>
  );
}

function SubmitButton({
  loading,
  label,
  disabled,
}: {
  loading: boolean;
  label: string;
  disabled?: boolean;
}) {
  return (
    <button
      type="submit"
      disabled={loading || disabled}
      className="w-full h-14 rounded-2xl bg-gradient-primary text-white font-medium shadow-glow disabled:opacity-50"
    >
      {loading ? "Please wait…" : label}
    </button>
  );
}
