import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { useState } from "react";
import { Bookmark, Clock, Layers } from "lucide-react";
import { useSavedVerses } from "@/hooks/queries/usePreferences";
import { useCollections } from "@/hooks/queries/usePreferences";
import { useRecentSearches } from "@/hooks/queries/useSearch";

export const Route = createFileRoute("/app/library")({
  head: () => ({ meta: [{ title: "Library — VerseID" }] }),
  component: Library,
});

const TABS = ["Saved", "Collections", "History"] as const;
type Tab = (typeof TABS)[number];

function Library() {
  const [tab, setTab] = useState<Tab>("Saved");
  const { data: saved = [], isLoading: savedLoading } = useSavedVerses();
  const { data: collections = [], isLoading: collectionsLoading } = useCollections();
  const { data: recent = [], isLoading: recentLoading } = useRecentSearches();

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
        {tab === "Saved" &&
          (savedLoading ? (
            <LoadingRows />
          ) : saved.length ? (
            saved.map((v) => (
              <VerseRow
                key={v.id}
                title={`${v.book} ${v.chapter}:${v.verse}`}
                text={v.text}
                version={v.version}
              />
            ))
          ) : (
            <EmptyState Icon={Bookmark} text="No saved verses yet. Tap save on any result." />
          ))}

        {tab === "Collections" &&
          (collectionsLoading ? (
            <div className="grid grid-cols-2 gap-3">
              {[0, 1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="aspect-square rounded-3xl glass-strong shadow-card animate-pulse"
                />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3">
              {collections.map((c, i) => (
                <motion.div
                  key={c.name}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="aspect-square rounded-3xl bg-gradient-primary p-5 text-white shadow-card flex flex-col justify-between"
                >
                  <Layers className="h-5 w-5 opacity-80" />
                  <div>
                    <div className="font-display text-xl font-semibold">{c.name}</div>
                    <div className="text-xs text-white/80">{c.count} verses</div>
                  </div>
                </motion.div>
              ))}
            </div>
          ))}

        {tab === "History" &&
          (recentLoading ? (
            <LoadingRows />
          ) : recent.length ? (
            recent.map((r) =>
              r.verse ? (
                <Link key={r.id} to="/app/results" search={{ q: r.query }} className="block">
                  <VerseRow
                    title={`${r.verse.book} ${r.verse.chapter}:${r.verse.verse}`}
                    text={`"${r.query}"`}
                    version={new Date(r.timestamp).toLocaleDateString()}
                  />
                </Link>
              ) : (
                <Link key={r.id} to="/app/results" search={{ q: r.query }} className="block">
                  <VerseRow
                    title="No match found"
                    text={`"${r.query}"`}
                    version={new Date(r.timestamp).toLocaleDateString()}
                  />
                </Link>
              ),
            )
          ) : (
            <EmptyState Icon={Clock} text="Your search history will appear here." />
          ))}
      </div>
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
      className="p-4 rounded-2xl glass-strong shadow-card"
    >
      <div className="flex items-center justify-between">
        <div className="font-medium">{title}</div>
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
