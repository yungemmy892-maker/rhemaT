import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Mic, Sparkles, Search, ShieldCheck, Wand2, ChevronRight, Quote } from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "VerseID — Find Any Bible Verse Instantly" },
      {
        name: "description",
        content: "Hear it. Speak it. Discover it. VerseID identifies any Bible verse from your voice or a few words.",
      },
      { property: "og:title", content: "VerseID — Find Any Bible Verse Instantly" },
      { property: "og:description", content: "Shazam for Bible verses. Speak or type — VerseID finds it." },
    ],
  }),
  component: Landing,
});

function Landing() {
  return (
    <div className="min-h-screen bg-background overflow-x-hidden">
      {/* Hero backdrop */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-[900px] bg-gradient-hero -z-10" />
      <div className="pointer-events-none fixed inset-0 -z-10">
        <div className="absolute top-20 -left-20 h-72 w-72 rounded-full bg-primary/20 blur-3xl animate-float-slow" />
        <div className="absolute top-96 -right-20 h-72 w-72 rounded-full bg-accent/50 blur-3xl animate-float-slow [animation-delay:-5s]" />
      </div>

      {/* Nav */}
      <header className="mx-auto max-w-6xl px-5 sm:px-8 pt-6 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="h-9 w-9 rounded-xl bg-gradient-primary grid place-items-center shadow-glow">
            <Sparkles className="h-4.5 w-4.5 text-white" strokeWidth={2.4} />
          </div>
          <span className="font-display text-xl font-semibold tracking-tight">VerseID</span>
        </Link>
        <Link
          to="/auth"
          className="hidden sm:inline-flex h-10 px-4 items-center rounded-full glass text-sm font-medium hover:bg-primary-soft transition"
        >
          Sign in
        </Link>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-3xl px-5 pt-16 sm:pt-24 pb-16 text-center">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass text-xs font-medium text-primary mb-6"
        >
          <Sparkles className="h-3.5 w-3.5" /> Shazam for Bible verses
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.05 }}
          className="font-display text-5xl sm:text-7xl font-semibold leading-[1.02] tracking-tight"
        >
          Find any Bible verse <span className="text-gradient">instantly.</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.15 }}
          className="mt-6 text-lg text-muted-foreground max-w-xl mx-auto"
        >
          Hear it. Speak it. Discover it. A calm, beautiful way to identify scripture in seconds.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.25 }}
          className="mt-10 flex flex-col sm:flex-row gap-3 justify-center"
        >
          <Link
            to="/app/voice"
            className="inline-flex items-center justify-center gap-2 h-14 px-7 rounded-full bg-gradient-primary text-white font-medium shadow-glow hover:scale-[1.02] active:scale-[0.98] transition-transform"
          >
            <Mic className="h-5 w-5" /> Try Verse Search
          </Link>
          <Link
            to="/auth"
            className="inline-flex items-center justify-center gap-2 h-14 px-7 rounded-full glass-strong font-medium hover:bg-surface transition"
          >
            <GoogleIcon /> Continue with Google
          </Link>
        </motion.div>

        {/* Floating mic visual */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.9, delay: 0.35 }}
          className="mt-20 relative mx-auto w-56 h-56"
        >
          <div className="absolute inset-0 rounded-full bg-gradient-primary blur-2xl opacity-50" />
          <div className="absolute inset-4 rounded-full bg-gradient-primary animate-pulse-ring" />
          <div className="absolute inset-0 grid place-items-center">
            <div className="h-32 w-32 rounded-full bg-gradient-primary shadow-glow grid place-items-center">
              <Mic className="h-12 w-12 text-white" strokeWidth={2.2} />
            </div>
          </div>
        </motion.div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-5xl px-5 py-20">
        <SectionHeader eyebrow="How it works" title="Three taps to scripture" />
        <div className="mt-12 grid sm:grid-cols-3 gap-4">
          {[
            { n: "01", t: "Tap the mic", d: "Speak the verse you remember — even just a fragment." },
            { n: "02", t: "We listen", d: "Smart matching finds the verse across translations." },
            { n: "03", t: "Discover", d: "Get book, chapter, verse, version and confidence score." },
          ].map((s, i) => (
            <RevealCard key={s.n} delay={i * 0.1}>
              <div className="text-xs font-mono text-primary">{s.n}</div>
              <div className="mt-3 font-display text-2xl font-semibold">{s.t}</div>
              <p className="mt-2 text-sm text-muted-foreground">{s.d}</p>
            </RevealCard>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-5xl px-5 py-20">
        <SectionHeader eyebrow="Features" title="Built for quiet moments of clarity" />
        <div className="mt-12 grid sm:grid-cols-2 gap-4">
          {[
            { Icon: Mic, t: "Voice identification", d: "Recite scripture aloud — we match it instantly." },
            { Icon: Search, t: "Fuzzy text search", d: "Type a few words; we find the right verse and version." },
            { Icon: Wand2, t: "Semantic AI", d: "Understand meaning, not just words." },
            { Icon: ShieldCheck, t: "Private & secure", d: "Your library stays yours, always." },
          ].map((f, i) => (
            <RevealCard key={f.t} delay={i * 0.08}>
              <div className="h-11 w-11 rounded-2xl bg-primary-soft grid place-items-center">
                <f.Icon className="h-5 w-5 text-primary" />
              </div>
              <div className="mt-4 font-display text-xl font-semibold">{f.t}</div>
              <p className="mt-1.5 text-sm text-muted-foreground">{f.d}</p>
            </RevealCard>
          ))}
        </div>
      </section>

      {/* Testimonials */}
      <section className="mx-auto max-w-5xl px-5 py-20">
        <SectionHeader eyebrow="Loved by readers" title="A daily companion" />
        <div className="mt-12 grid sm:grid-cols-3 gap-4">
          {[
            { q: "I heard a verse on the radio and had it identified before the song ended.", a: "Marcus T." },
            { q: "Beautiful, calming, and genuinely useful. My favorite app this year.", a: "Hannah L." },
            { q: "Like having a concordance in my pocket — but kinder.", a: "Pastor David K." },
          ].map((t, i) => (
            <RevealCard key={t.a} delay={i * 0.08}>
              <Quote className="h-5 w-5 text-primary" />
              <p className="mt-3 text-[15px] leading-relaxed">{t.q}</p>
              <div className="mt-4 text-xs text-muted-foreground">— {t.a}</div>
            </RevealCard>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="mx-auto max-w-3xl px-5 py-20">
        <SectionHeader eyebrow="FAQ" title="Good to know" />
        <div className="mt-10 space-y-3">
          {[
            {
              q: "Which translations are supported?",
              a: "KJV (King James Version) and WEB (World English Bible) — both public domain. Choose a default in Settings.",
            },
            {
              q: "Does it work offline?",
              a: "Not yet — VerseID needs a connection to search the full Bible text and identify a verse.",
            },
            {
              q: "Is my voice data stored?",
              a: "Speech is transcribed locally in your browser and never uploaded as audio — only the resulting text is sent to find a match.",
            },
            {
              q: "How accurate is the matching?",
              a: "Fuzzy text matching checks for exact phrases, partial matches, reordered words, and minor misquotes, with a confidence score on every result. Well-known verses paraphrased in modern wording match best when searched against WEB.",
            },
          ].map((f, i) => (
            <RevealCard key={i}>
              <div className="flex items-start gap-3">
                <div className="mt-0.5 h-6 w-6 rounded-full bg-primary-soft grid place-items-center shrink-0">
                  <ChevronRight className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="min-w-0">
                  <div className="font-medium">{f.q}</div>
                  <p className="mt-1 text-sm text-muted-foreground">{f.a}</p>
                </div>
              </div>
            </RevealCard>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-3xl px-5 pb-24">
        <div className="relative overflow-hidden rounded-[2rem] p-10 sm:p-14 text-center bg-gradient-primary shadow-glow">
          <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_30%_20%,white,transparent_40%)]" />
          <h3 className="relative font-display text-3xl sm:text-4xl font-semibold text-white">
            Start your library of verses today.
          </h3>
          <p className="relative mt-3 text-white/85">20 free identifications every day.</p>
          <Link
            to="/auth"
            className="relative inline-flex mt-7 items-center justify-center gap-2 h-12 px-7 rounded-full bg-white text-primary font-medium hover:scale-[1.02] transition-transform"
          >
            <GoogleIcon /> Continue with Google
          </Link>
        </div>
      </section>

      <footer className="mx-auto max-w-5xl px-5 pb-10 text-center text-xs text-muted-foreground">
        <div className="flex items-center justify-center gap-4 mb-3">
          <Link to="/privacy" className="hover:text-foreground transition">
            Privacy
          </Link>
          <Link to="/terms" className="hover:text-foreground transition">
            Terms
          </Link>
          <Link to="/help" className="hover:text-foreground transition">
            Help
          </Link>
        </div>
        © {new Date().getFullYear()} VerseID. Made with care.
      </footer>
    </div>
  );
}

function SectionHeader({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="text-center">
      <div className="text-xs uppercase tracking-[0.18em] text-primary font-medium">{eyebrow}</div>
      <h2 className="mt-3 font-display text-3xl sm:text-5xl font-semibold tracking-tight">{title}</h2>
    </div>
  );
}

function RevealCard({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ y: -3 }}
      className="rounded-3xl glass-strong shadow-card p-6 transition-shadow hover:shadow-elevated"
    >
      {children}
    </motion.div>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
      <path fill="#EA4335" d="M12 10.2v3.9h5.5c-.24 1.46-1.7 4.28-5.5 4.28-3.31 0-6.01-2.74-6.01-6.13S8.69 6.12 12 6.12c1.88 0 3.14.8 3.86 1.49l2.63-2.54C16.95 3.6 14.68 2.6 12 2.6 6.86 2.6 2.7 6.76 2.7 12s4.16 9.4 9.3 9.4c5.37 0 8.92-3.77 8.92-9.07 0-.61-.07-1.08-.16-1.55H12z"/>
      <path fill="#34A853" d="M3.88 7.34l3.2 2.35C7.99 7.66 9.83 6.12 12 6.12c1.88 0 3.14.8 3.86 1.49l2.63-2.54C16.95 3.6 14.68 2.6 12 2.6 8.3 2.6 5.12 4.71 3.88 7.34z" opacity="0"/>
      <path fill="#FBBC05" d="M12 21.4c2.62 0 4.82-.86 6.43-2.34l-3.06-2.5c-.83.58-1.94.98-3.37.98-2.6 0-4.8-1.74-5.59-4.11l-3.15 2.43C4.5 19.04 7.94 21.4 12 21.4z" opacity="0"/>
      <path fill="#4285F4" d="M20.92 10.78H12v3.92h5.5c-.24 1.46-1.7 4.28-5.5 4.28v.02c3.27 0 6.02-1.16 8.02-3.16 1.43-1.43 2.06-3.5 2.06-5.6 0-.61-.07-1.08-.16-1.46z"/>
    </svg>
  );
}
