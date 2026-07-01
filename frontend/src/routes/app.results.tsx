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
  Image as ImageIcon,
} from "lucide-react";
import {
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
import { z } from "zod";
import { useIdentifyQuery } from "@/hooks/queries/useSearch";
import { useSavedVerses, useToggleSaved } from "@/hooks/queries/usePreferences";
import { bibleApi, type Verse } from "@/services/api";

const searchSchema = z.object({ q: z.string().default("") });

export const Route = createFileRoute("/app/results")({
  validateSearch: searchSchema,
  head: () => ({ meta: [{ title: "Result — VerseID" }] }),
  component: Results,
});

/* ── speech synthesis ──────────────────────────────────────────────────────── */
function useSpeech() {
  const [speaking, setSpeaking] = useState(false);
  const utterRef = useRef<SpeechSynthesisUtterance | null>(null);

  const speak = useCallback((text: string) => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.92;
    u.onstart = () => setSpeaking(true);
    u.onend = () => setSpeaking(false);
    u.onerror = () => setSpeaking(false);
    utterRef.current = u;
    window.speechSynthesis.speak(u);
  }, []);

  const stop = useCallback(() => {
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, []);

  useEffect(() => () => window.speechSynthesis.cancel(), []);
  return { speaking, speak, stop };
}

/* ── share as image ────────────────────────────────────────────────────────── */
async function shareAsImage(verse: Verse) {
  const canvas = document.createElement("canvas");
  const W = 1080;
  const H = 1080;
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d")!;

  // Purple gradient background
  const grad = ctx.createLinearGradient(0, 0, W, H);
  grad.addColorStop(0, "#7C3AED");
  grad.addColorStop(1, "#C084FC");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, W, H);

  // Subtle radial glow
  const glow = ctx.createRadialGradient(W * 0.2, H * 0.1, 0, W * 0.2, H * 0.1, W * 0.6);
  glow.addColorStop(0, "rgba(255,255,255,0.18)");
  glow.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, W, H);

  ctx.fillStyle = "rgba(255,255,255,0.95)";
  ctx.textAlign = "center";

  // Version badge
  ctx.font = "bold 32px system-ui, sans-serif";
  ctx.fillStyle = "rgba(255,255,255,0.7)";
  ctx.fillText(verse.version, W / 2, 120);

  // Reference
  ctx.font = "bold 64px system-ui, sans-serif";
  ctx.fillStyle = "#ffffff";
  ctx.fillText(`${verse.book} ${verse.chapter}:${verse.verse}`, W / 2, 210);

  // Verse text — word-wrapped
  ctx.font = "44px Georgia, serif";
  ctx.fillStyle = "rgba(255,255,255,0.92)";
  const words = `"${verse.text}"`.split(" ");
  let line = "";
  let y = 340;
  const maxW = W - 160;
  for (const word of words) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > maxW && line) {
      ctx.fillText(line, W / 2, y);
      line = word;
      y += 64;
    } else {
      line = test;
    }
  }
  if (line) ctx.fillText(line, W / 2, y);

  // VerseID watermark
  ctx.font = "bold 30px system-ui, sans-serif";
  ctx.fillStyle = "rgba(255,255,255,0.5)";
  ctx.fillText("VerseID", W / 2, H - 80);

  return new Promise<void>((resolve) => {
    canvas.toBlob(async (blob) => {
      if (!blob) return resolve();
      const file = new File([blob], "verse.png", { type: "image/png" });
      if (navigator.canShare?.({ files: [file] })) {
        try {
          await navigator.share({
            files: [file],
            title: `${verse.book} ${verse.chapter}:${verse.verse}`,
          });
        } catch {}
      } else {
        // Fallback: download the image
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${verse.book}-${verse.chapter}-${verse.verse}.png`;
        a.click();
        URL.revokeObjectURL(url);
      }
      resolve();
    }, "image/png");
  });
}

/* ── chapter panel ─────────────────────────────────────────────────────────── */
function ChapterPanel({
  book,
  chapter,
  version,
  highlightVerse,
}: {
  book: string;
  chapter: number;
  version: string;
  highlightVerse: number;
}) {
  const [verses, setVerses] = useState<Verse[]>([]);
  const [loading, setLoading] = useState(true);
  const highlightRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    bibleApi
      .chapter(book, chapter, version as "KJV" | "WEB")
      .then(setVerses)
      .finally(() => setLoading(false));
  }, [book, chapter, version]);

  useEffect(() => {
    if (!loading)
      highlightRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [loading]);

  if (loading)
    return (
      <div className="mt-3 space-y-2">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="h-10 rounded-xl glass animate-pulse" />
        ))}
      </div>
    );

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

/* ── main component ─────────────────────────────────────────────────────────── */
function Results() {
  const { q } = Route.useSearch();
  const navigate = useNavigate();

  // useQuery (not useMutation) — result is cached by query string and
  // survives component remounts, so the screen never gets stuck.
  const { data: response, isPending } = useIdentifyQuery(q);

  const { data: savedVerses = [] } = useSavedVerses();
  const toggleSaved = useToggleSaved();
  const [copied, setCopied] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [chapterOpen, setChapterOpen] = useState(false);
  const { speaking, speak, stop } = useSpeech();

  /* ── loading skeleton ─────────────────────────────────────────────── */
  if (isPending) {
    return (
      <div>
        <Link
          to="/app/home"
          className="h-10 w-10 rounded-full glass grid place-items-center"
        >
          <ArrowLeft className="h-4.5 w-4.5" />
        </Link>
        <div className="mt-6 h-64 rounded-[2rem] glass-strong shadow-card animate-pulse" />
        <div className="mt-5 grid grid-cols-4 gap-2.5">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-[72px] rounded-2xl glass-strong shadow-card animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  /* ── quota exceeded ─────────────────────────────────────────────────── */
  if (response && "quotaExceeded" in response && response.quotaExceeded) {
    return (
      <div>
        <Link
          to="/app/home"
          className="h-10 w-10 rounded-full glass grid place-items-center"
        >
          <ArrowLeft className="h-4.5 w-4.5" />
        </Link>
        <div className="mt-20 text-center px-4">
          <div className="mx-auto h-14 w-14 rounded-2xl bg-gradient-primary grid place-items-center shadow-glow">
            <Sparkles className="h-7 w-7 text-white" />
          </div>
          <h2 className="mt-5 font-display text-2xl font-semibold">Daily limit reached</h2>
          <p className="mt-2 text-muted-foreground text-sm">
            You've used all {response.dailySearchLimit} free searches today. Upgrade to
            Pro for unlimited searches.
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

  /* ── no match ───────────────────────────────────────────────────────── */
  const result = response?.matched ? response : null;

  if (!result) {
    return (
      <div>
        <Link
          to="/app/home"
          className="h-10 w-10 rounded-full glass grid place-items-center"
        >
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

  /* ── result ─────────────────────────────────────────────────────────── */
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
    if (speaking) {
      stop();
      return;
    }
    speak(
      `${verse.book}, chapter ${verse.chapter}, verse ${verse.verse}. ${verse.text}`,
    );
  };

  const handleShareText = async () => {
    const text = `"${verse.text}" — ${verse.book} ${verse.chapter}:${verse.verse} (${verse.version})`;
    if (navigator.share) {
      try {
        await navigator.share({ title: `${verse.book} ${verse.chapter}:${verse.verse}`, text });
      } catch {}
    } else {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    }
  };

  const handleShareImage = async () => {
    setSharing(true);
    try {
      await shareAsImage(verse);
    } finally {
      setSharing(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <Link
          to="/app/home"
          className="h-10 w-10 rounded-full glass grid place-items-center"
        >
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
          <p className="mt-5 font-display text-xl leading-relaxed text-white/95">
            "{verse.text}"
          </p>

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

      {/* Primary actions */}
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
          onClick={() =>
            toggleSaved.mutate({ verseId: verse.id, version: verse.version })
          }
        />
        <ActionBtn
          Icon={speaking ? VolumeX : Volume2}
          label={speaking ? "Stop" : "Listen"}
          active={speaking}
          onClick={handleListen}
        />
        <ActionBtn
          Icon={copied ? Check : Copy}
          label={copied ? "Copied" : "Share text"}
          onClick={handleShareText}
        />
        <ActionBtn
          Icon={sharing ? Sparkles : ImageIcon}
          label={sharing ? "Creating…" : "Share image"}
          onClick={handleShareImage}
        />
      </motion.div>

      {/* Read full chapter */}
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
      <span className="text-[11px] font-medium leading-tight text-center">{label}</span>
    </button>
  );
}
