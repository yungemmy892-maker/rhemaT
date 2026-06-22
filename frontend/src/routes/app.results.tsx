import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Bookmark,
  Share2,
  Copy,
  Volume2,
  VolumeX,
  BookOpen,
  Check,
  Sparkles,
  ChevronUp,
  ChevronDown,
} from "lucide-react";
import { useEffect, useRef, useState, useCallback } from "react";
import { z } from "zod";
import { useIdentifyVerse } from "@/hooks/queries/useSearch";
import { useSavedVerses, useToggleSaved } from "@/hooks/queries/usePreferences";
import { bibleApi, type Verse } from "@/services/api";

const searchSchema = z.object({ q: z.string().default("") });

export const Route = createFileRoute("/app/results")({
  validateSearch: searchSchema,
  head: () => ({ meta: [{ title: "Result — VerseID" }] }),
  component: Results,
});

/* ── speech synthesis helper ─────────────────────────────────────────────── */
function useSpeech() {
  const [speaking, setSpeaking] = useState(false);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const speak = useCallback((text: string) => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.92;
    u.pitch = 1;
    u.onstart = () => setSpeaking(true);
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    utteranceRef.current = u;
    window.speechSynthesis.speak(u);
  }, []);

  const stop = useCallback(() => {
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, []);

  useEffect(() => () => window.speechSynthesis.cancel(), []);

  return { speaking, speak, stop };
}

/* ── chapter panel ────────────────────────────────────────────────────────── */
function ChapterPanel({ book, chapter, version, highlightVerse }: {
  book: string; chapter: number; version: string; highlightVerse: number;
}) {
  const [verses, setVerses] = useState<Verse[]>([]);
  const [loading, setLoading] = useState(true);
  const highlightRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    bibleApi.chapter(book, chapter, version as "KJV" | "WEB")
      .then(setVerses)
      .finally(() => setLoading(false));
  }, [book, chapter, version]);

  useEffect(() => {
    if (!loading) highlightRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [loading]);

  if (loading) {
    return (
      <div className="mt-3 space-y-2">
        {[0,1,2,3,4].map(i => (
          <div key={i} className="h-10 rounded-xl glass animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="mt-3 max-h-96 overflow-y-auto space-y-2 pr-1">
      {verses.map((v) => {
        const isHighlight = v.verse === highlightVerse;
        return (
          <div
            key={v.verse}
            ref={isHighlight ? highlightRef : undefined}
            className={`p-3 rounded-xl text-sm leading-relaxed transition ${
              isHighlight
                ? "bg-primary/10 border border-primary/30 font-medium"
                : "glass"
            }`}
          >
            <span className="text-[11px] text-primary font-bold mr-2">{v.verse}</span>
            {v.text}
          </div>
        );
      })}
    </div>
  );
}

/* ── main component ───────────────────────────────────────────────────────── */
function Results() {
  const { q } = Route.useSearch();
  const navigate = useNavigate();
  const identify = useIdentifyVerse();
  const { data: savedVerses = [] } = useSavedVerses();
  const toggleSaved = useToggleSaved();
  const [copied, setCopied] = useState(false);
  const [chapterOpen, setChapterOpen] = useState(false);
  const ranForQuery = useRef<string | null>(null);
  const { speaking, speak, stop } = useSpeech();

  useEffect(() => {
    if (!q || ranForQuery.current === q) return;
    ranForQuery.current = q;
    identify.mutate({ query: q });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  /* ── loading skeleton ─────────────────────────────────────────────────── */
  if (identify.isPending || identify.isIdle) {
    return (
      <div>
        <Link to="/app/home" className="h-10 w-10 rounded-full glass grid place-items-center">
          <ArrowLeft className="h-4.5 w-4.5" />
        </Link>
        <div className="mt-6 h-64 rounded-[2rem] glass-strong shadow-card animate-pulse" />
        <div className="mt-5 grid grid-cols-4 gap-2.5">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="h-[72px] rounded-2xl glass-strong shadow-card animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const response = identify.data;

  /* ── quota exceeded ───────────────────────────────────────────────────── */
  if (response && "quotaExceeded" in response && response.quotaExceeded) {
    return (
      <div>
        <Link to="/app/home" className="h-10 w-10 rounded-full glass grid place-items-center">
          <ArrowLeft className="h-4.5 w-4.5" />
        </Link>
        <div className="mt-20 text-center px-4">
          <div className="mx-auto h-14 w-14 rounded-2xl bg-gradient-primary grid place-items-center shadow-glow">
            <Sparkles className="h-7 w-7 text-white" />
          </div>
          <h2 className="mt-5 font-display text-2xl font-semibold">Daily limit reached</h2>
          <p className="mt-2 text-muted-foreground text-sm">
            You've used all {response.dailySearchLimit} free searches today. Upgrade to Pro for
            unlimited searches.
          </p>
          <Link
            to="/app/subscription"
            className="mt-6 inline-flex h-12 px-8 items-center rounded-full bg-gradient-primary text-white font-medium shadow-glow"
          >
            Upgrade to Pro
          </Link>
          <p className="mt-3 text-xs text-muted-foreground">
            Or come back tomorrow for more free searches.
          </p>
        </div>
      </div>
    );
  }

  /* ── no match ─────────────────────────────────────────────────────────── */
  const result = response?.matched ? response : null;

  if (!result) {
    return (
      <div>
        <Link to="/app/home" className="h-10 w-10 rounded-full glass grid place-items-center">
          <ArrowLeft className="h-4.5 w-4.5" />
        </Link>
        <div className="mt-20 text-center">
          <h2 className="font-display text-2xl font-semibold">No match found</h2>
          <p className="mt-2 text-muted-foreground">Try a different phrase or speak again.</p>
          <button
            onClick={() => navigate({ to: "/app/text" })}
            className="mt-6 h-12 px-6 rounded-full bg-gradient-primary text-white font-medium shadow-glow"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  /* ── result ───────────────────────────────────────────────────────────── */
  const { verse, confidence } = result;
  const isSaved = savedVerses.some((v) => v.id === verse.id);
  const confPct = Math.round(confidence * 100);

  const copy = async () => {
    await navigator.clipboard.writeText(
      `"${verse.text}" — ${verse.book} ${verse.chapter}:${verse.verse} (${verse.version})`,
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  };

  const handleListen = () => {
    if (speaking) { stop(); return; }
    speak(`${verse.book}, chapter ${verse.chapter}, verse ${verse.verse}. ${verse.text}`);
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <Link to="/app/home" className="h-10 w-10 rounded-full glass grid place-items-center">
          <ArrowLeft className="h-4.5 w-4.5" />
        </Link>
        <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary-soft text-primary text-xs font-medium">
          <Sparkles className="h-3.5 w-3.5" /> Match found
        </div>
        <div className="w-10" />
      </div>

      {/* Verse card */}
      <motion.div
        initial={{ opacity: 0, y: 12, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="mt-6 relative overflow-hidden rounded-[2rem] p-7 bg-gradient-primary shadow-glow text-white"
      >
        <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_20%_10%,white,transparent_45%)]" />
        <div className="relative">
          <div className="text-xs uppercase tracking-[0.16em] text-white/80 font-medium">
            {verse.version}
          </div>
          <div className="mt-2 font-display text-3xl font-semibold">
            {verse.book} {verse.chapter}:{verse.verse}
          </div>
          <p className="mt-5 font-display text-xl leading-relaxed text-white/95">"{verse.text}"</p>

          {/* Confidence */}
          <div className="mt-7">
            <div className="flex items-center justify-between text-xs text-white/80 mb-1.5">
              <span>Confidence</span>
              <span className="font-medium">{confPct}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-white/20 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${confPct}%` }}
                transition={{ duration: 0.8, delay: 0.2 }}
                className="h-full bg-white rounded-full"
              />
            </div>
          </div>
        </div>
      </motion.div>

      {/* Actions */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mt-5 grid grid-cols-4 gap-2.5"
      >
        <ActionBtn
          Icon={isSaved ? Check : Bookmark}
          label={isSaved ? "Saved" : "Save"}
          active={isSaved}
          onClick={() => toggleSaved.mutate({ verseId: verse.id, version: verse.version })}
        />
        <ActionBtn
          Icon={Share2}
          label="Share"
          onClick={() =>
            navigator.share?.({
              title: `${verse.book} ${verse.chapter}:${verse.verse}`,
              text: `"${verse.text}" — ${verse.book} ${verse.chapter}:${verse.verse} (${verse.version})`,
            }).catch(() => {})
          }
        />
        <ActionBtn
          Icon={copied ? Check : Copy}
          label={copied ? "Copied" : "Copy"}
          onClick={copy}
        />
        <ActionBtn
          Icon={speaking ? VolumeX : Volume2}
          label={speaking ? "Stop" : "Listen"}
          active={speaking}
          onClick={handleListen}
        />
      </motion.div>

      {/* Read full chapter — expandable */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="mt-4 rounded-2xl glass-strong shadow-card overflow-hidden"
      >
        <button
          onClick={() => setChapterOpen((o) => !o)}
          className="w-full h-14 flex items-center justify-center gap-2 font-medium text-sm"
        >
          <BookOpen className="h-4.5 w-4.5 text-primary" />
          Read full chapter
          {chapterOpen ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </button>

        <AnimatePresence>
          {chapterOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden px-4 pb-4"
            >
              <div className="text-xs text-muted-foreground text-center mb-2">
                {verse.book} chapter {verse.chapter} · {verse.version}
              </div>
              <ChapterPanel
                book={verse.book}
                chapter={verse.chapter}
                version={verse.version}
                highlightVerse={verse.verse}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Searched query */}
      <div className="mt-8 text-center text-xs text-muted-foreground">
        Matched from: <span className="italic">"{q}"</span>
      </div>
    </div>
  );
}

function ActionBtn({
  Icon,
  label,
  active,
  onClick,
}: {
  Icon: React.ComponentType<{ className?: string }>;
  label: string;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-center gap-1.5 py-3.5 rounded-2xl glass-strong shadow-card transition ${
        active ? "bg-primary-soft" : "hover:bg-primary-soft"
      }`}
    >
      <Icon className={`h-5 w-5 ${active ? "text-primary" : "text-foreground"}`} />
      <span className="text-[11px] font-medium">{label}</span>
    </button>
  );
}
