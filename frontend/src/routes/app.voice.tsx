import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { ArrowLeft, Mic, Keyboard } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useVoiceRecognition } from "@/hooks/useVoiceRecognition";
import { useIdentifyVerse } from "@/hooks/queries/useSearch";

export const Route = createFileRoute("/app/voice")({
  head: () => ({ meta: [{ title: "Listening — VerseID" }] }),
  component: VoiceSearch,
});

function VoiceSearch() {
  const [phase, setPhase] = useState<"listening" | "processing">("listening");
  const navigate = useNavigate();
  const identify = useIdentifyVerse();
  const handledRef = useRef(false);

  const { status, transcript } = useVoiceRecognition({
    onFinalResult: (finalTranscript) => {
      if (handledRef.current) return;
      handledRef.current = true;
      if (!finalTranscript) {
        navigate({ to: "/app/text" });
        return;
      }
      setPhase("processing");
      identify.mutate(
        { query: finalTranscript },
        {
          onSettled: () => {
            navigate({ to: "/app/results", search: { q: finalTranscript } });
          },
        },
      );
    },
  });

  // If the browser doesn't support speech recognition at all, fall back to
  // the existing text-search screen rather than leaving this screen stuck
  // on "Listening…" forever.
  useEffect(() => {
    if (status === "unsupported" || status === "error") {
      navigate({ to: "/app/text" });
    }
  }, [status, navigate]);

  return (
    <div>
      <div className="flex items-center justify-between">
        <Link to="/app/home" className="h-10 w-10 rounded-full glass grid place-items-center">
          <ArrowLeft className="h-4.5 w-4.5" />
        </Link>
        <Link
          to="/app/text"
          className="h-10 px-4 rounded-full glass text-sm font-medium inline-flex items-center gap-2"
        >
          <Keyboard className="h-4 w-4" /> Type instead
        </Link>
      </div>

      <div className="mt-16 flex flex-col items-center text-center">
        <div className="relative h-56 w-56 grid place-items-center">
          <div className="absolute inset-0 rounded-full bg-primary/15 animate-pulse-ring" />
          <div className="absolute inset-6 rounded-full bg-primary/25 animate-pulse-ring [animation-delay:-0.6s]" />
          <motion.div
            animate={{ scale: [1, 1.06, 1] }}
            transition={{ repeat: Infinity, duration: 1.4, ease: "easeInOut" }}
            className="h-32 w-32 rounded-full bg-gradient-primary shadow-glow grid place-items-center"
          >
            <Mic className="h-12 w-12 text-white" strokeWidth={2.2} />
          </motion.div>
        </div>

        <h2 className="mt-10 font-display text-2xl font-semibold">
          {phase === "listening" ? "Listening…" : "Identifying verse…"}
        </h2>
        <p className="mt-3 text-muted-foreground min-h-[1.5em] px-6">
          {transcript ? (
            <span className="italic">"{transcript}"</span>
          ) : (
            "Speak any verse you remember"
          )}
        </p>

        {/* Equalizer */}
        <div className="mt-10 flex items-end gap-1.5 h-12">
          {Array.from({ length: 24 }).map((_, i) => (
            <motion.span
              key={i}
              animate={{ scaleY: [0.3, 1, 0.4, 0.9, 0.3] }}
              transition={{
                repeat: Infinity,
                duration: 1.2 + (i % 5) * 0.1,
                delay: i * 0.04,
                ease: "easeInOut",
              }}
              className="w-1 h-full origin-bottom rounded-full bg-gradient-primary"
            />
          ))}
        </div>
      </div>
    </div>
  );
}
