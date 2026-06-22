import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { useVerseOfDay, usePopularVerses } from "@/hooks/queries/useBible";
import { useSettings } from "@/hooks/queries/usePreferences";

export const Route = createFileRoute("/app/discover")({
  head: () => ({ meta: [{ title: "Discover — VerseID" }] }),
  component: Discover,
});

const THEMES = [
  { name: "Peace", from: "#A855F7", to: "#C084FC", query: "peace that passes all understanding" },
  { name: "Hope", from: "#8B5CF6", to: "#A78BFA", query: "hope does not disappoint" },
  { name: "Love", from: "#D946EF", to: "#F0ABFC", query: "love is patient love is kind" },
  { name: "Strength", from: "#7C3AED", to: "#A855F7", query: "i can do all things through Christ" },
];

function Discover() {
  const { data: settings } = useSettings();
  const version = settings?.bibleVersion ?? "KJV";

  const { data: verseOfDay, isLoading: vodLoading } = useVerseOfDay(version);
  const { data: popular = [], isLoading: popularLoading } = usePopularVerses(version);

  return (
    <div>
      <h1 className="font-display text-3xl font-semibold">Discover</h1>
      <p className="text-sm text-muted-foreground mt-1">Curated verses & daily readings</p>

      {/* Verse of the day */}
      {vodLoading ? (
        <div className="mt-6 h-48 rounded-[2rem] glass-strong shadow-card animate-pulse" />
      ) : verseOfDay ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 relative overflow-hidden rounded-[2rem] p-6 bg-gradient-primary text-white shadow-glow"
        >
          <div className="absolute inset-0 opacity-25 bg-[radial-gradient(circle_at_80%_10%,white,transparent_45%)]" />
          <div className="relative">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/20 text-[11px] font-medium">
              <Sparkles className="h-3 w-3" /> Verse of the day
            </div>
            <p className="mt-4 font-display text-xl leading-relaxed">"{verseOfDay.text}"</p>
            <div className="mt-3 text-sm text-white/85">
              {verseOfDay.book} {verseOfDay.chapter}:{verseOfDay.verse} · {verseOfDay.version}
            </div>
          </div>
        </motion.div>
      ) : null}

      {/* Themes — tapping a theme runs a real search for that topic */}
      <h2 className="mt-8 font-display text-lg font-semibold">Browse by theme</h2>
      <div className="mt-3 grid grid-cols-2 gap-3">
        {THEMES.map((t, i) => (
          <Link
            key={t.name}
            to="/app/results"
            search={{ q: t.query }}
          >
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="aspect-[4/3] rounded-3xl p-5 text-white shadow-card flex items-end hover:scale-[1.02] transition-transform"
              style={{ background: `linear-gradient(135deg, ${t.from}, ${t.to})` }}
            >
              <div className="font-display text-2xl font-semibold">{t.name}</div>
            </motion.div>
          </Link>
        ))}
      </div>

      {/* Popular verses */}
      <h2 className="mt-8 font-display text-lg font-semibold">Popular verses</h2>
      <div className="mt-3 space-y-2.5">
        {popularLoading
          ? [0, 1, 2, 3, 4].map((i) => (
              <div key={i} className="h-[72px] rounded-2xl glass-strong shadow-card animate-pulse" />
            ))
          : popular.map((v) => (
              <Link
                key={v.id}
                to="/app/results"
                search={{ q: v.text.slice(0, 32) }}
                className="block p-4 rounded-2xl glass-strong shadow-card hover:bg-primary-soft transition"
              >
                <div className="font-medium text-sm">
                  {v.book} {v.chapter}:{v.verse}
                  <span className="ml-2 text-[10px] text-muted-foreground uppercase tracking-wide">
                    {v.version}
                  </span>
                </div>
                <p className="mt-1 text-sm text-muted-foreground line-clamp-2">"{v.text}"</p>
              </Link>
            ))}
      </div>
    </div>
  );
}
