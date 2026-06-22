import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { ArrowLeft, Search, Mic, X } from "lucide-react";
import { useState } from "react";

export const Route = createFileRoute("/app/text")({
  head: () => ({ meta: [{ title: "Text search — VerseID" }] }),
  component: TextSearch,
});

const SUGGESTIONS = [
  "For God so loved the world",
  "The Lord is my shepherd",
  "I can do all things",
  "Be still and know",
  "Trust in the Lord",
  "Love is patient",
];

function TextSearch() {
  const [q, setQ] = useState("");
  const navigate = useNavigate();
  const submit = (val: string) => {
    if (!val.trim()) return;
    navigate({ to: "/app/results", search: { q: val.trim() } });
  };

  return (
    <div>
      <div className="flex items-center gap-2">
        <Link to="/app/home" className="h-10 w-10 rounded-full glass grid place-items-center shrink-0">
          <ArrowLeft className="h-4.5 w-4.5" />
        </Link>
        <div className="flex-1 min-w-0 flex items-center gap-2 h-12 px-4 rounded-full glass-strong shadow-card">
          <Search className="h-4.5 w-4.5 text-muted-foreground shrink-0" />
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit(q)}
            placeholder="Type a few words…"
            className="flex-1 min-w-0 bg-transparent outline-none text-sm"
          />
          {q && (
            <button onClick={() => setQ("")} className="text-muted-foreground">
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <Link to="/app/voice" className="h-10 w-10 rounded-full bg-gradient-primary grid place-items-center shrink-0 shadow-glow">
          <Mic className="h-4.5 w-4.5 text-white" />
        </Link>
      </div>

      <div className="mt-8">
        <h3 className="text-xs uppercase tracking-[0.16em] text-muted-foreground font-medium">
          Try searching
        </h3>
        <div className="mt-4 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s, i) => (
            <motion.button
              key={s}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              onClick={() => submit(s)}
              className="px-3.5 py-2 rounded-full glass-strong text-sm hover:bg-primary-soft transition"
            >
              {s}
            </motion.button>
          ))}
        </div>
      </div>

      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: q ? 1 : 0.4 }}
        disabled={!q}
        onClick={() => submit(q)}
        className="mt-10 w-full h-14 rounded-2xl bg-gradient-primary text-white font-medium shadow-glow disabled:cursor-not-allowed"
      >
        Identify verse
      </motion.button>
    </div>
  );
}
