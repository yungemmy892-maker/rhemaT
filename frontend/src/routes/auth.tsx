import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, ArrowLeft, Mail, Lock, User as UserIcon, Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useGoogleSignIn } from "@/hooks/useGoogleSignIn";
import { authApi } from "@/services/api";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Sign in — VerseID" },
      {
        name: "description",
        content: "Sign in or create a VerseID account to save and revisit your verses.",
      },
    ],
  }),
  component: Auth,
});

type Mode = "login" | "register";

function Auth() {
  const navigate = useNavigate();
  const { signInGoogle, signInEmail, registerEmail } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [forgotSent, setForgotSent] = useState(false);
  const [forgotLoading, setForgotLoading] = useState(false);

  const goApp = () => navigate({ to: "/app/home" });

  const handleForgotPassword = async () => {
    if (!email) {
      setError("Enter your email address above, then tap 'Forgot password?'.");
      return;
    }
    setForgotLoading(true);
    setError(null);
    try {
      await authApi.forgotPassword(email);
      setForgotSent(true);
    } catch {
      setError("Couldn't send a reset email. Please try again.");
    } finally {
      setForgotLoading(false);
    }
  };

  const { trigger: triggerGoogleSignIn } = useGoogleSignIn({
    onSuccess: async (idToken) => {
      setLoading(true);
      setError(null);
      try {
        await signInGoogle(idToken);
        goApp();
      } catch {
        setError("Couldn't sign in with Google. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    onError: (err) => setError(err.message),
  });

  const handleGoogle = () => {
    setError(null);
    triggerGoogleSignIn();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    setLoading(true);
    setError(null);
    try {
      if (mode === "login") await signInEmail(email, password);
      else await registerEmail(name, email, password);
      goApp();
    } catch (err) {
      const message =
        (err as { message?: string })?.message ||
        (mode === "login" ? "Incorrect email or password." : "Couldn't create your account.");
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute -top-24 -left-24 h-80 w-80 rounded-full bg-primary/25 blur-3xl animate-float-slow" />
        <div className="absolute bottom-0 -right-24 h-80 w-80 rounded-full bg-accent/50 blur-3xl animate-float-slow [animation-delay:-6s]" />
      </div>
      <div className="mx-auto max-w-md min-h-screen flex flex-col px-6 pt-6 pb-10">
        <Link to="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground">
          <ArrowLeft className="h-4 w-4" /> Back
        </Link>

        <div className="flex-1 flex flex-col justify-center">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-center"
          >
            <div className="mx-auto h-16 w-16 rounded-3xl bg-gradient-primary grid place-items-center shadow-glow">
              <Sparkles className="h-7 w-7 text-white" strokeWidth={2.4} />
            </div>
            <h1 className="mt-6 font-display text-3xl font-semibold tracking-tight">
              {mode === "login" ? "Welcome back" : "Create your account"}
            </h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {mode === "login"
                ? "Sign in to continue your journey through scripture."
                : "Join VerseID and start identifying verses instantly."}
            </p>
          </motion.div>

          {/* Tabs */}
          <div className="mt-7 relative grid grid-cols-2 p-1 rounded-2xl glass-strong shadow-card">
            <motion.div
              layout
              transition={{ type: "spring", stiffness: 500, damping: 35 }}
              className="absolute top-1 bottom-1 w-[calc(50%-4px)] rounded-xl bg-gradient-primary shadow-glow"
              style={{ left: mode === "login" ? 4 : "calc(50% + 0px)" }}
            />
            {(["login", "register"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`relative z-10 h-10 rounded-xl text-sm font-medium transition ${mode === m ? "text-white" : "text-muted-foreground"}`}
              >
                {m === "login" ? "Sign in" : "Register"}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="mt-5 space-y-3">
            <AnimatePresence mode="popLayout">
              {mode === "register" && (
                <motion.div
                  key="name"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <Field Icon={UserIcon}>
                    <input
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Full name"
                      className="w-full bg-transparent outline-none text-sm"
                    />
                  </Field>
                </motion.div>
              )}
            </AnimatePresence>

            <Field Icon={Mail}>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full bg-transparent outline-none text-sm"
                required
              />
            </Field>

            <Field Icon={Lock}>
              <input
                type={showPw ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Password"
                className="w-full bg-transparent outline-none text-sm"
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

            {mode === "login" && (
              <div className="text-right">
                {forgotSent ? (
                  <span className="text-xs text-primary font-medium">
                    Reset link sent — check your inbox.
                  </span>
                ) : (
                  <button
                    type="button"
                    disabled={forgotLoading}
                    onClick={handleForgotPassword}
                    className="text-xs text-primary font-medium disabled:opacity-60"
                  >
                    {forgotLoading ? 'Sending…' : 'Forgot password?'}
                  </button>
                )}
              </div>
            )}

            {error && <p className="text-xs text-destructive text-center">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full h-14 rounded-2xl bg-gradient-primary text-white font-medium shadow-glow disabled:opacity-70"
            >
              {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>

          <div className="my-5 flex items-center gap-3 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            <div className="h-px flex-1 bg-border" /> or <div className="h-px flex-1 bg-border" />
          </div>

          <button
            onClick={handleGoogle}
            className="w-full h-14 rounded-2xl glass-strong shadow-card font-medium flex items-center justify-center gap-3 hover:bg-surface transition"
          >
            <GoogleIcon /> Continue with Google
          </button>

          <p className="mt-5 text-xs text-center text-muted-foreground px-6">
            By continuing you agree to our{" "}
            <Link to="/terms" className="text-primary font-medium">
              Terms
            </Link>{" "}
            and{" "}
            <Link to="/privacy" className="text-primary font-medium">
              Privacy Policy
            </Link>
            .
          </p>
        </div>
      </div>
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

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
      <path
        fill="#EA4335"
        d="M12 10.2v3.9h5.5c-.24 1.46-1.7 4.28-5.5 4.28-3.31 0-6.01-2.74-6.01-6.13S8.69 6.12 12 6.12c1.88 0 3.14.8 3.86 1.49l2.63-2.54C16.95 3.6 14.68 2.6 12 2.6 6.86 2.6 2.7 6.76 2.7 12s4.16 9.4 9.3 9.4c5.37 0 8.92-3.77 8.92-9.07 0-.61-.07-1.08-.16-1.55H12z"
      />
      <path
        fill="#4285F4"
        d="M20.92 10.78H12v3.92h5.5c-.24 1.46-1.7 4.28-5.5 4.28v.02c3.27 0 6.02-1.16 8.02-3.16 1.43-1.43 2.06-3.5 2.06-5.6 0-.61-.07-1.08-.16-1.46z"
      />
    </svg>
  );
}
