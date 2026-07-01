import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { Bookmark, Clock, Layers, X, ChevronRight } from "lucide-react";
import { useSavedVerses, useCollections } from "@/hooks/queries/usePreferences";
import { useRecentSearches } from "@/hooks/queries/useSearch";
import { useSettings } from "@/hooks/queries/usePreferences";
import type { Collection, Verse } from "@/services/api";

export const Route = createFileRoute("/app/library")({
  head: () => ({ meta: [{ title: "Library — VerseID" }] }),
  component: Library,
});

const TABS = ["Saved", "Collections", "History"] as const;
type Tab = (typeof TABS)[number];

/* Gradient per collection name — stays consistent */
const COLLECTION_GRADIENTS: Record<string, string> = {
  Comfort:   "from-violet-500 to-fuchsia-500",
  Strength:  "from-purple-600 to-indigo-500",
  Gratitude: "from-pink-500 to-rose-400",
  Prayer:    "from-sky-500 to-cyan-400",
};

function Library() {
  const [tab, setTab]                         = useState<Tab>("Saved");
  const [openCollection, setOpenCollection]   = useState<Collection | null>(null);

  const { data: settings }                              = useSettings();
  const version                                         = settings?.bibleVersion ?? "KJV";
  const { data: saved = [],       isLoading: savedLoading }       = useSavedVerses();
  const { data: collections = [], isLoading: collectionsLoading } = useCollections(version);
  const { data: recent = [],      isLoading: recentLoading }      = useRecentSearches();

  return (
    <div>
      <h1 className="font-display text-3xl font-semibold">Library</h1>
      <p className="text-sm text-muted-foreground mt-1">Your saved verses & history</p>

      {/* Tabs */}
      <div className="mt-6 relative flex p-1 rounded-2xl glass-strong shadow-card">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className="relative flex-1 py-2.5 text-sm font-medium z-10"
          >
            {tab === t && (
              <motion.div
                layoutId="lib-tab"
                className="absolute inset-0 bg-gradient-primary rounded-xl shadow-glow"
                transition={{ type: "spring", stiffness: 340, damping: 30 }}
              />
            )}
            <span className={`relative ${tab === t ? "text-white" : "text-muted-foreground"}`}>
              {t}
            </span>
          </button>
        ))}
      </div>

      <div className="mt-6 space-y-2.5">
        {/* ── Saved ──────────────────────────────────────────────── */}
        {tab === "Saved" &&
          (savedLoading ? (
            <LoadingRows />
          ) : saved.length ? (
            saved.map((v) => (
              <Link key={v.id} to="/app/results" search={{ q: v.text.slice(0, 40) }}>
                <VerseRow
                  title={`${v.book} ${v.chapter}:${v.verse}`}
                  text={v.text}
                  version={v.version}
                />
              </Link>
            ))
          ) : (
            <EmptyState Icon={Bookmark} text="No saved verses yet. Tap save on any result." />
          ))}

        {/* ── Collections ────────────────────────────────────────── */}
        {tab === "Collections" &&
          (collectionsLoading ? (
            <div className="grid grid-cols-2 gap-3">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="aspect-square rounded-3xl glass-strong shadow-card animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {collections.map((c, i) => {
                const gradient = COLLECTION_GRADIENTS[c.name] ?? "from-violet-500 to-fuchsia-500";
                return (
                  <motion.button
                    key={c.name}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    onClick={() => setOpenCollection(c)}
                    className={`aspect-square rounded-3xl bg-gradient-to-br ${gradient} p-5 text-white shadow-card flex flex-col justify-between hover:scale-[1.02] transition-transform`}
                  >
                    <Layers className="h-5 w-5 opacity-80" />
                    <div className="text-left">
                      <div className="font-display text-xl font-semibold">{c.name}</div>
                      <div className="text-xs text-white/80">{c.count} verses · {version}</div>
                    </div>
                  </motion.button>
                );
              })}
            </div>
          ))}

        {/* ── History ────────────────────────────────────────────── */}
        {tab === "History" &&
          (recentLoading ? (
            <LoadingRows />
          ) : recent.length ? (
            recent.map((r) => (
              <Link key={r.id} to="/app/results" search={{ q: r.query }} className="block">
                <VerseRow
                  title={
                    r.verse
                      ? `${r.verse.book} ${r.verse.chapter}:${r.verse.verse}`
                      : "No match found"
                  }
                  text={`"${r.query}"`}
                  version={new Date(r.timestamp).toLocaleDateString("en-NG", {
                    day: "numeric",
                    month: "short",
                  })}
                />
              </Link>
            ))
          ) : (
            <EmptyState Icon={Clock} text="Your search history will appear here." />
          ))}
      </div>

      {/* ── Collection verse sheet ──────────────────────────────── */}
      <AnimatePresence>
        {openCollection && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
            onClick={() => setOpenCollection(null)}
          >
            <motion.div
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", stiffness: 340, damping: 35 }}
              onClick={(e) => e.stopPropagation()}
              className="absolute bottom-0 left-0 right-0 bg-surface rounded-t-[2rem] max-h-[85vh] overflow-hidden flex flex-col"
            >
              {/* Sheet header */}
              <div className="flex items-center gap-3 px-5 pt-5 pb-4 border-b border-border/40">
                <div
                  className={`h-11 w-11 rounded-2xl bg-gradient-to-br ${
                    COLLECTION_GRADIENTS[openCollection.name] ?? "from-violet-500 to-fuchsia-500"
                  } grid place-items-center`}
                >
                  <Layers className="h-5 w-5 text-white" />
                </div>
                <div className="flex-1">
                  <h2 className="font-display text-lg font-semibold">{openCollection.name}</h2>
                  <p className="text-xs text-muted-foreground">
                    {openCollection.count} verses · {version}
                  </p>
                </div>
                <button
                  onClick={() => setOpenCollection(null)}
                  className="h-9 w-9 rounded-full grid place-items-center hover:bg-muted"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Verse list */}
              <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
                {openCollection.verses.length === 0 ? (
                  <div className="py-10 text-center text-sm text-muted-foreground">
                    No verses loaded — make sure you've run{" "}
                    <code className="text-xs bg-muted px-1 rounded">
                      python manage.py load_bible
                    </code>
                  </div>
                ) : (
                  openCollection.verses.map((v: Verse) => (
                    <Link
                      key={v.id}
                      to="/app/results"
                      search={{ q: v.text.slice(0, 40) }}
                      onClick={() => setOpenCollection(null)}
                    >
                      <motion.div
                        initial={{ opacity: 0, x: -6 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="p-4 rounded-2xl glass-strong shadow-card flex items-start gap-3 hover:bg-primary-soft/60 transition"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-semibold">
                              {v.book} {v.chapter}:{v.verse}
                            </span>
                            <span className="text-[10px] uppercase tracking-wider text-primary font-medium shrink-0">
                              {v.version}
                            </span>
                          </div>
                          <p className="mt-1.5 text-sm text-muted-foreground line-clamp-3">
                            {v.text}
                          </p>
                        </div>
                        <ChevronRight className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                      </motion.div>
                    </Link>
                  ))
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function LoadingRows() {
  return (
    <>
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-[72px] rounded-2xl glass-strong shadow-card animate-pulse" />
      ))}
    </>
  );
}

function VerseRow({ title, text, version }: { title: string; text: string; version: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-4 rounded-2xl glass-strong shadow-card hover:bg-primary-soft/40 transition"
    >
      <div className="flex items-center justify-between">
        <div className="font-medium text-sm">{title}</div>
        <span className="text-[10px] uppercase tracking-wider text-primary font-medium">
          {version}
        </span>
      </div>
      <p className="mt-1.5 text-sm text-muted-foreground line-clamp-2">{text}</p>
    </motion.div>
  );
}

function EmptyState({
  Icon,
  text,
}: {
  Icon: React.ComponentType<{ className?: string }>;
  text: string;
}) {
  return (
    <div className="text-center py-16">
      <div className="mx-auto h-14 w-14 rounded-2xl bg-primary-soft grid place-items-center">
        <Icon className="h-6 w-6 text-primary" />
      </div>
      <p className="mt-4 text-sm text-muted-foreground">{text}</p>
    </div>
  );
}
