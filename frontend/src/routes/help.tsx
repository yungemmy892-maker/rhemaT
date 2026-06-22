import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, HelpCircle, Mic, Search, Bookmark, Bell, Crown, User, Shield, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

export const Route = createFileRoute("/help")({
  head: () => ({ meta: [{ title: "Help & Support — VerseID" }] }),
  component: Help,
});

const FAQS = [
  {
    q: "How does voice search work?",
    a: "Tap the microphone on the Home screen and speak any verse you remember — even a partial phrase or a few words. Your browser's built-in speech recognition converts your speech to text (this happens entirely on your device, not our servers), then sends the text to our matching engine. You'll see a live transcript as you speak.",
  },
  {
    q: "Which Bible translations are supported?",
    a: "VerseID currently supports two public-domain translations: King James Version (KJV) and World English Bible (WEB). You can set your preferred version in Settings → Bible version. The search engine automatically checks both versions to give you the best match, which is especially helpful because some well-known verses use very different wording between KJV ('charity suffereth long') and modern translations ('love is patient').",
  },
  {
    q: "What are the free plan limits?",
    a: "Free accounts can identify up to 20 verses per day. The count resets at midnight UTC. Your search history, saved verses, and collections are unlimited on the free plan.",
  },
  {
    q: "What does Pro include?",
    a: "Pro removes the daily search limit entirely (unlimited identifications), and includes all current and future premium features. Pricing is ₦2,500/month or ₦20,000/year — processed securely by Paystack in Nigerian Naira.",
  },
  {
    q: "How do I upgrade to Pro?",
    a: "Go to Profile → Upgrade to Pro (or the Crown icon). Choose monthly or annual billing, then tap 'Subscribe with Paystack'. You'll be redirected to Paystack's secure checkout where you can pay with your Nigerian bank card, USSD, or bank transfer. You're returned to the app automatically after payment.",
  },
  {
    q: "Why didn't it find my verse?",
    a: "A few common reasons: (1) The verse uses very different wording in KJV/WEB than the version you learnt it from (e.g. NIV/ESV phrases can differ substantially from KJV). Try the WEB version in Settings for more modern phrasing. (2) The phrase is very short or contains only common words ('for God', 'in the beginning') — add a few more distinctive words for a better match. (3) Background noise affected the voice transcript — try the text search instead.",
  },
  {
    q: "How does the confidence score work?",
    a: "After each identification, VerseID shows a confidence percentage from 0–100%. It's calculated from four signals blended together: exact phrase match (did the query appear verbatim in the verse?), partial match (is the query a fragment of the verse?), token-set match (do most of the same words appear in any order?), and fuzzy-typo match (are the words similar even if slightly misspelled?). Higher confidence means a more reliable result.",
  },
  {
    q: "How do I enable daily verse notifications?",
    a: "Go to Settings and make sure 'Notifications' is on and 'Daily verse' is toggled on. Then choose your preferred time (Morning, Midday, or Evening). The first time you do this, your browser will ask for notification permission — tap Allow. If you've already denied permission, you'll need to re-enable it in your browser's site settings.",
  },
  {
    q: "How do I change my profile picture?",
    a: "Go to Profile → Edit profile, then tap your avatar photo. A sheet will appear with two options: 'Take a photo' (opens your camera) or 'Choose from gallery' (opens your photo library). Your photo is cropped to a square and saved to your account.",
  },
  {
    q: "How do I change my name or password?",
    a: "Go to Profile → Edit profile. The 'Name' section lets you update your display name. The 'Change password' section lets you set or update your password — if you signed up with Google and haven't set a password yet, you can set one here to enable email/password sign-in as an alternative.",
  },
  {
    q: "Can I use voice search offline?",
    a: "No. Voice transcription uses your browser's Web Speech API, which requires an internet connection on most browsers. Verse identification also requires a connection to our server. Offline mode is not currently available.",
  },
  {
    q: "How do I cancel my Pro subscription?",
    a: "Go to Profile → Upgrade to Pro (while subscribed this becomes 'Manage subscription'). Tap 'Cancel subscription' and confirm. Your Pro access continues until the end of your current billing period, then you'll revert to the free plan automatically.",
  },
  {
    q: "How do I delete my account?",
    a: "Go to Settings → Delete account. Confirm the dialog. Your account, search history, saved verses, and all associated data are permanently deleted within 24 hours. This action cannot be undone.",
  },
];

function Help() {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-2xl px-5 py-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Link to="/" className="h-10 w-10 rounded-full glass grid place-items-center">
            <ArrowLeft className="h-4.5 w-4.5" />
          </Link>
          <div className="h-10 w-10 rounded-full bg-gradient-primary grid place-items-center">
            <HelpCircle className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="font-display text-xl font-semibold">Help & Support</h1>
            <p className="text-xs text-muted-foreground">Everything you need to know</p>
          </div>
        </div>

        {/* Quick feature tiles */}
        <div className="grid grid-cols-2 gap-3 mb-8">
          {[
            { Icon: Mic, label: "Voice search", desc: "Speak any verse to find it", to: "/app/voice" },
            { Icon: Search, label: "Text search", desc: "Type a phrase to identify", to: "/app/text" },
            { Icon: Bookmark, label: "Library", desc: "Saved verses & history", to: "/app/library" },
            { Icon: Bell, label: "Notifications", desc: "Daily verse & alerts", to: "/app/settings" },
            { Icon: Crown, label: "Pro plan", desc: "Unlimited searches (₦2,500/mo)", to: "/app/subscription" },
            { Icon: User, label: "Profile", desc: "Edit name, photo & password", to: "/app/profile/edit" },
          ].map(({ Icon, label, desc, to }) => (
            <Link
              key={label}
              to={to}
              className="p-4 rounded-2xl glass-strong shadow-card hover:bg-primary-soft/60 transition"
            >
              <div className="h-9 w-9 rounded-xl bg-primary-soft grid place-items-center mb-2">
                <Icon className="h-4.5 w-4.5 text-primary" />
              </div>
              <div className="text-sm font-medium">{label}</div>
              <div className="text-xs text-muted-foreground mt-0.5">{desc}</div>
            </Link>
          ))}
        </div>

        {/* How it works */}
        <h2 className="font-display text-lg font-semibold mb-4">How VerseID works</h2>
        <div className="space-y-3 mb-8">
          {[
            {
              step: "1",
              title: "You speak or type a verse",
              body: "Tap the mic and recite any fragment — a few words, a phrase, even a rough paraphrase. Or use the text search to type it out.",
            },
            {
              step: "2",
              title: "We search KJV + WEB",
              body: "Our fuzzy matching engine checks your query against all 31,100+ verses in both the King James Version and the World English Bible, scoring each candidate on phrase similarity, word overlap, and tolerance for misspellings.",
            },
            {
              step: "3",
              title: "You get the verse + confidence score",
              body: "The best match is shown with the exact verse text, reference (book, chapter, verse), translation, and a confidence score so you can judge how certain the result is.",
            },
            {
              step: "4",
              title: "Save, share, or read the chapter",
              body: "Bookmark the verse to your library, copy it, share it, listen to it via text-to-speech, or expand the 'Read full chapter' panel to read the surrounding context.",
            },
          ].map((s) => (
            <div key={s.step} className="flex gap-4 p-4 rounded-2xl glass-strong shadow-card">
              <div className="h-8 w-8 rounded-full bg-gradient-primary grid place-items-center text-white text-sm font-bold shrink-0">
                {s.step}
              </div>
              <div>
                <div className="text-sm font-semibold">{s.title}</div>
                <div className="text-sm text-muted-foreground mt-0.5">{s.body}</div>
              </div>
            </div>
          ))}
        </div>

        {/* FAQ accordion */}
        <h2 className="font-display text-lg font-semibold mb-4">Frequently asked questions</h2>
        <div className="space-y-2 mb-10">
          {FAQS.map((faq, i) => (
            <div key={i} className="rounded-2xl glass-strong shadow-card overflow-hidden">
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="w-full flex items-center justify-between gap-3 px-4 py-4 text-left"
              >
                <span className="text-sm font-medium">{faq.q}</span>
                {open === i ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground shrink-0" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                )}
              </button>
              {open === i && (
                <div className="px-4 pb-4 text-sm text-muted-foreground leading-relaxed border-t border-border/50 pt-3">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Contact */}
        <div className="p-5 rounded-3xl glass-strong shadow-card text-center">
          <Shield className="h-6 w-6 text-primary mx-auto mb-2" />
          <h3 className="font-display font-semibold">Still need help?</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Send us an email and we'll get back to you within 24 hours.
          </p>
          <a
            href="mailto:support@verseid.app"
            className="mt-4 inline-flex h-11 px-6 items-center rounded-full bg-gradient-primary text-white text-sm font-medium shadow-glow"
          >
            Email support@verseid.app
          </a>
        </div>

        <div className="mt-8 flex gap-4 text-xs text-muted-foreground">
          <Link to="/privacy" className="hover:text-foreground transition">Privacy</Link>
          <Link to="/terms" className="hover:text-foreground transition">Terms</Link>
          <Link to="/" className="hover:text-foreground transition">Home</Link>
        </div>
      </div>
    </div>
  );
}
