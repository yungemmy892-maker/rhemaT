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
  Wand2,
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
import { useVerseByRef } from "@/hooks/queries/useBible";
import { useSavedVerses, useToggleSaved, useSettings } from "@/hooks/queries/usePreferences";
import { bibleApi, type BibleVersion, type Verse } from "@/services/api";

const searchSchema = z.object({
  q: z.string().default(""),
  // Set instead of `q` when opening a verse whose exact reference is
  // already known (Saved / History / Recent / a just-completed Voice
  // match) — skips the fuzzy matcher entirely and doesn't spend any of the
  // user's daily search quota re-identifying something already found.
  book: z.string().optional(),
  chapter: z.coerce.number().optional(),
  verse: z.coerce.number().optional(),
  version: z.string().optional(),
  // Carried alongside book/chapter/verse when arriving from a real identify
  // pass (Voice) so the confidence bar still renders on a "direct" open.
  confidence: z.coerce.number().optional(),
  // Set by Voice when identify already ran and found no match — prevents
  // Results from silently re-running identify (and re-spending quota) for
  // the exact same query the Voice screen just checked.
  noMatch: z.coerce.boolean().optional(),
});

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

// Same palette as the daily-verse/welcome emails (notifications/email.py's
// BRAND dict) so a verse looks like it came from the same product whether
// it lands in an inbox or a share sheet.
const CARD_BRAND = {
  gradientStart: "#8B5CF6",
  gradientEnd: "#D946EF",
  card: "rgba(255,255,255,0.13)",
  cardBorder: "rgba(255,255,255,0.28)",
};

function drawRoundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function wrapLines(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const words = text.split(" ");
  const lines: string[] = [];
  let line = "";
  for (const word of words) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = word;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function loadImage(src: string): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

async function shareAsImage(verse: Verse) {
  // Canvas text only renders with a webfont once it's actually loaded —
  // without this, the very first share after page load would silently
  // fall back to the browser's default serif/sans instead of Fraunces /
  // Plus Jakarta Sans.
  await document.fonts.ready;
  const logo = await loadImage("/logo-glyph.png");

  const W = 1080;
  const H = 1080;
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d")!;

  /* Background — same 135° violet→fuchsia gradient as the rest of the app */
  const bg = ctx.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0, CARD_BRAND.gradientStart);
  bg.addColorStop(1, CARD_BRAND.gradientEnd);
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  // Two soft glows (not one) for a bit of depth instead of a flat fill.
  const glowA = ctx.createRadialGradient(W * 0.12, H * 0.08, 0, W * 0.12, H * 0.08, W * 0.55);
  glowA.addColorStop(0, "rgba(255,255,255,0.20)");
  glowA.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = glowA;
  ctx.fillRect(0, 0, W, H);

  const glowB = ctx.createRadialGradient(W * 0.92, H * 0.95, 0, W * 0.92, H * 0.95, W * 0.5);
  glowB.addColorStop(0, "rgba(0,0,0,0.14)");
  glowB.addColorStop(1, "rgba(0,0,0,0)");
  ctx.fillStyle = glowB;
  ctx.fillRect(0, 0, W, H);

  /* Header — logo mark + wordmark, centered as a group */
  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";
  ctx.font = "600 40px Fraunces, Georgia, serif";
  const wordmark = "VerseID";
  const wordmarkWidth = ctx.measureText(wordmark).width;
  const markSize = 52;
  const gap = 16;
  const groupWidth = markSize + gap + wordmarkWidth;
  const groupX = (W - groupWidth) / 2;
  const markY = 76;

  // Translucent circular backing so the white glyph reads clearly against
  // the busy gradient behind it, then the glyph itself on top.
  ctx.beginPath();
  ctx.arc(groupX + markSize / 2, markY + markSize / 2, markSize / 2, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(255,255,255,0.16)";
  ctx.fill();
  if (logo) {
    const pad = 13;
    ctx.drawImage(logo, groupX + pad, markY + pad, markSize - pad * 2, markSize - pad * 2);
  }
  ctx.fillStyle = "#ffffff";
  ctx.font = "600 40px Fraunces, Georgia, serif";
  ctx.fillText(wordmark, groupX + markSize + gap, markY + markSize / 2 + 14);

  /* Card geometry — sized around the wrapped verse text so short and long
     verses both look intentional rather than swimming in empty space or
     overflowing the canvas. */
  const cardX = 72;
  const cardWidth = W - cardX * 2;
  const cardPadX = 64;
  const textMaxWidth = cardWidth - cardPadX * 2;

  // Step down the font size for longer verses instead of using one size
  // that either wastes space on short verses or overflows on long ones.
  const sizes = [46, 42, 38, 34, 30];
  let fontSize = sizes[0];
  let lines: string[] = [];
  for (const size of sizes) {
    ctx.font = `500 ${size}px Fraunces, Georgia, serif`;
    const candidate = wrapLines(ctx, verse.text, textMaxWidth);
    fontSize = size;
    lines = candidate;
    // 8 lines at the largest readable size keeps the card comfortably
    // inside the canvas even for a long verse; stop shrinking once we fit.
    if (candidate.length <= 8) break;
  }
  const lineHeight = fontSize * 1.42; // serif-appropriate leading

  const quoteMarkHeight = 90;
  const refPillHeight = 56;
  const cardPadTop = 56;
  const cardPadBottom = 56;
  const gapAfterQuote = 12;
  const gapBeforeRef = 40;

  const textBlockHeight = lines.length * lineHeight;
  const cardHeight =
    cardPadTop +
    quoteMarkHeight +
    gapAfterQuote +
    textBlockHeight +
    gapBeforeRef +
    refPillHeight +
    cardPadBottom;

  const cardY = Math.max(200, (H - cardHeight) / 2 + 20);

  /* Glass card */
  drawRoundedRect(ctx, cardX, cardY, cardWidth, cardHeight, 40);
  ctx.fillStyle = CARD_BRAND.card;
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = CARD_BRAND.cardBorder;
  ctx.stroke();

  /* Oversized decorative quote glyph */
  ctx.textAlign = "left";
  ctx.font = "600 120px Fraunces, Georgia, serif";
  ctx.fillStyle = "rgba(255,255,255,0.35)";
  ctx.fillText("\u201C", cardX + cardPadX - 14, cardY + cardPadTop + quoteMarkHeight);

  /* Verse text, centered within the card */
  ctx.textAlign = "center";
  ctx.fillStyle = "rgba(255,255,255,0.97)";
  ctx.font = `500 ${fontSize}px Fraunces, Georgia, serif`;
  let ty = cardY + cardPadTop + quoteMarkHeight + gapAfterQuote + fontSize * 0.85;
  for (const line of lines) {
    ctx.fillText(line, W / 2, ty);
    ty += lineHeight;
  }

  /* Reference pill — same "ref · version" pattern as the daily-verse email */
  const refLabel = `${verse.ref}  ·  ${verse.version}`;
  ctx.font = "600 26px 'Plus Jakarta Sans', system-ui, sans-serif";
  const refWidth = ctx.measureText(refLabel).width;
  const pillPadX = 30;
  const pillWidth = refWidth + pillPadX * 2;
  const pillX = (W - pillWidth) / 2;
  const pillY = cardY + cardHeight - cardPadBottom - refPillHeight + 8;

  drawRoundedRect(ctx, pillX, pillY, pillWidth, refPillHeight, refPillHeight / 2);
  ctx.fillStyle = "rgba(255,255,255,0.16)";
  ctx.fill();
  ctx.lineWidth = 1;
  ctx.strokeStyle = "rgba(255,255,255,0.3)";
  ctx.stroke();
  ctx.fillStyle = "#ffffff";
  ctx.fillText(refLabel, W / 2, pillY + refPillHeight / 2 + 9);

  /* Footer caption */
  ctx.font = "500 24px 'Plus Jakarta Sans', system-ui, sans-serif";
  ctx.fillStyle = "rgba(255,255,255,0.65)";
  ctx.fillText("Find any verse, instantly — verseid.top", W / 2, H - 56);

  return new Promise<void>((resolve) => {
    canvas.toBlob(async (blob) => {
      if (!blob) return resolve();
      const file = new File([blob], `${verse.book}-${verse.chapter}-${verse.verse}.png`, {
        type: "image/png",
      });
      if (navigator.canShare?.({ files: [file] })) {
        try {
          await navigator.share({
            files: [file],
            title: verse.ref,
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
  const { q, book, chapter, verse: verseNum, version, confidence: confidenceParam, noMatch } =
    Route.useSearch();
  const navigate = useNavigate();
  const { data: settings } = useSettings();
  const isDirect = Boolean(book && chapter && verseNum);
  // Voice already ran identify and found nothing for this exact query —
  // re-running it here would silently spend a second quota unit for the
  // same search, so skip it and go straight to the "no match" screen.
  const skipIdentify = isDirect || noMatch;

  // Direct open (Saved / History / Recent / a completed Voice match) vs. a
  // real identify pass (Voice's own call already happened, or Text search
  // navigating straight here). useQuery (not useMutation) for identify —
  // result is cached by query string and survives component remounts, so
  // the screen never gets stuck.
  const preferredVersion = (version as BibleVersion | undefined) ?? settings?.bibleVersion;
  const identify = useIdentifyQuery(skipIdentify ? "" : q, isDirect ? undefined : preferredVersion);
  const direct = useVerseByRef(book, chapter, verseNum, version as BibleVersion | undefined, isDirect);

  const isPending = isDirect ? direct.isPending : noMatch ? false : identify.isPending;
  const response = identify.data;

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
          aria-label="Back to Home"
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
  if (!isDirect && response && "quotaExceeded" in response && response.quotaExceeded) {
    return (
      <div>
        <Link
          to="/app/home"
          aria-label="Back to Home"
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
  const result = isDirect
    ? direct.data
      ? { verse: direct.data, confidence: confidenceParam ?? null, semanticMatch: false }
      : null
    : response?.matched
      ? {
          verse: response.verse,
          confidence: response.confidence as number | null,
          semanticMatch: Boolean(response.semanticMatch),
        }
      : null;

  if (!result) {
    return (
      <div>
        <Link
          to="/app/home"
          aria-label="Back to Home"
          className="h-10 w-10 rounded-full glass grid place-items-center"
        >
          <ArrowLeft className="h-4.5 w-4.5" />
        </Link>
        <div className="mt-20 text-center">
          <h2 className="font-display text-2xl font-semibold">
            {isDirect ? "Verse unavailable" : "No match found"}
          </h2>
          <p className="mt-2 text-muted-foreground">
            {isDirect
              ? "This verse couldn't be loaded right now."
              : "Try a different phrase or speak again."}
          </p>
          <button
            onClick={() => navigate({ to: isDirect ? "/app/library" : "/app/text" })}
            className="mt-6 h-12 px-6 rounded-full bg-gradient-primary text-white font-medium shadow-glow"
          >
            {isDirect ? "Back to Library" : "Try again"}
          </button>
        </div>
      </div>
    );
  }

  /* ── result ─────────────────────────────────────────────────────────── */
  const { verse, confidence, semanticMatch } = result;
  const isSaved = savedVerses.some((v) => v.id === verse.id);
  const confPct = confidence !== null ? Math.round(confidence * 100) : null;

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
          aria-label="Back to Home"
          className="h-10 w-10 rounded-full glass grid place-items-center"
        >
          <ArrowLeft className="h-4.5 w-4.5" />
        </Link>
        <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary-soft text-primary text-xs font-medium">
          {confPct !== null ? (
            semanticMatch ? (
              <>
                <Wand2 className="h-3.5 w-3.5" /> Semantic match
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5" /> Match found
              </>
            )
          ) : (
            <>
              <BookOpen className="h-3.5 w-3.5" /> Opened from Library
            </>
          )}
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

          {/* Confidence — only shown for a real identify match, not a direct Library open */}
          {confPct !== null && (
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
          )}
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
          disabled={toggleSaved.isPending}
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

      {q && confPct !== null && (
        <div className="mt-8 text-center text-xs text-muted-foreground">
          Matched from: <span className="italic">"{q}"</span>
        </div>
      )}
    </div>
  );
}

function ActionBtn({
  Icon,
  label,
  active,
  onClick,
  disabled,
}: {
  Icon: React.ComponentType<{ className?: string }>;
  label: string;
  active?: boolean;
  onClick?: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-busy={disabled}
      className={`flex flex-col items-center gap-1.5 py-3.5 rounded-2xl glass-strong shadow-card transition ${
        active ? "bg-primary-soft" : "hover:bg-primary-soft"
      } disabled:opacity-60 disabled:pointer-events-none`}
    >
      <Icon className={`h-5 w-5 ${active ? "text-primary" : "text-foreground"}`} />
      <span className="text-[11px] font-medium leading-tight text-center">{label}</span>
    </button>
  );
}