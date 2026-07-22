import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { Bookmark, Clock, Layers, X, ChevronRight, Trash2 } from "lucide-react";
import { useSavedVerses, useCollections } from "@/hooks/queries/usePreferences";
import {
  useRecentSearches,
  useClearHistory,
  useDeleteHistoryItem,
} from "@/hooks/queries/useSearch";
import { useSettings } from "@/hooks/queries/usePreferences";
import { useT } from "@/context/I18nContext";
import type { Collection, Verse } from "@/services/api";

export const Route = createFileRoute("/app/library")({
  head: () => ({ meta: [{ title: "Library - VerseID" }] }),
  component: Library,
});

const TABS = ["Saved", "Collections", "History"] as const;
type Tab = (typeof TABS)[number];

// Tab identity (state, `tab === t` comparisons) stays the fixed English
// value above; this maps each to its translation key/fallback for display
// only, so translating labels can't silently break tab switching.
const TAB_LABELS: Record<Tab, { key: string; fallback: string }> = {
  Saved: { key: "library.tab.saved", fallback: "Saved" },
  Collections: { key: "library.tab.collections", fallback: "Collections" },
  History: { key: "library.tab.history", fallback: "History" },
};

/* Gradient per collection name — stays consistent */
const COLLECTION_GRADIENTS: Record<string, string> = {
  Comfort: "from-violet-500 to-fuchsia-500",
  Strength: "from-purple-600 to-indigo-500",
  Gratitude: "from-pink-500 to-rose-400",
  Prayer: "from-sky-500 to-cyan-400",
};

function Library() {
  const t = useT();
  const [tab, setTab] = useState<Tab>("Saved");
  const [openCollection, setOpenCollection] = useState<Collection | null>(null);
  const [confirmClear, setConfirmClear] = useState(false);

  const { data: settings } = useSettings();
  const version = settings?.bibleVersion ?? "KJV";
  const { data: saved = [], isLoading: savedLoading } = useSavedVerses();
  const { data: collections = [], isLoading: collectionsLoading } = useCollections(version);
  const { data: recent = [], isLoading: recentLoading } = useRecentSearches();
  const clearHistory = useClearHistory();
  const deleteHistoryItem = useDeleteHistoryItem();

  return (
    <div>
      <h1 className="font-display text-3xl font-semibold">{t("library.title", "Library")}</h1>
      <p className="text-sm text-muted-foreground mt-1">
        {t("library.subtitle", "Your saved verses & history")}
      </p>

      {/* Tabs */}
      <div className="mt-6 relative flex p-1 rounded-2xl glass-strong shadow-card">
        {TABS.map((tabValue) => (
          <button
            key={tabValue}
            onClick={() => setTab(tabValue)}
            className="relative flex-1 py-2.5 text-sm font-medium z-10"
          >
            {tab === tabValue && (
              <motion.div
                layoutId="lib-tab"
                className="absolute inset-0 bg-gradient-primary rounded-xl shadow-glow"
                transition={{ type: "spring", stiffness: 340, damping: 30 }}
              />
            )}
            <span
              className={`relative ${tab === tabValue ? "text-white" : "text-muted-foreground"}`}
            >
              {t(TAB_LABELS[tabValue].key, TAB_LABELS[tabValue].fallback)}
            </span>
          </button>
        ))}
      </div>

      {tab === "History" && recent.length > 0 && (
        <div className="mt-4 flex items-center justify-end gap-3">
          {confirmClear ? (
            <>
              <span className="text-xs text-muted-foreground">
                {t("library.clearAllConfirm", "Clear all history?")}
              </span>
              <button
                className="text-xs font-medium text-muted-foreground"
                onClick={() => setConfirmClear(false)}
              >
                {t("action.cancel", "Cancel")}
              </button>
              <button
                className="text-xs font-medium text-destructive disabled:opacity-40"
                disabled={clearHistory.isPending}
                onClick={() => {
                  clearHistory.mutate();
                  setConfirmClear(false);
                }}
              >
                {t("action.confirm", "Confirm")}
              </button>
            </>
          ) : (
            <button
              className="text-xs font-medium text-muted-foreground hover:text-destructive transition"
              onClick={() => setConfirmClear(true)}
            >
              {t("library.clearAll", "Clear all")}
            </button>
          )}
        </div>
      )}

      <div className="mt-6 space-y-2.5">
        {/* ── Saved ──────────────────────────────────────────────── */}
        {tab === "Saved" &&
          (savedLoading ? (
            <LoadingRows />
          ) : saved.length ? (
            saved.map((v) => (
              <Link
                key={v.id}
                to="/app/results"
                search={{
                  q: "",
                  book: v.book,
                  chapter: v.chapter,
                  verse: v.verse,
                  version: v.version,
                }}
              >
                <VerseRow
                  title={`${v.book} ${v.chapter}:${v.verse}`}
                  text={v.text}
                  version={v.version}
                />
              </Link>
            ))
          ) : (
            <EmptyState
              Icon={Bookmark}
              text={t("library.emptySaved", "No saved verses yet. Tap save on any result.")}
            />
          ))}

        {/* ── Collections ────────────────────────────────────────── */}
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
                      <div className="text-xs text-white/80">
                        {c.count} verses · {version}
                      </div>
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
            recent.map((r, i) => (
              <motion.div
                key={r.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -12 }}
                transition={{ delay: i * 0.03 }}
                className="flex items-center gap-2 p-4 rounded-2xl glass-strong shadow-card hover:bg-primary-soft/40 transition"
              >
                <Link
                  to="/app/results"
                  search={
                    r.verse
                      ? {
                          q: "",
                          book: r.verse.book,
                          chapter: r.verse.chapter,
                          verse: r.verse.verse,
                          version: r.verse.version,
                        }
                      : { q: r.query }
                  }
                  className="flex-1 min-w-0 block"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-medium text-sm truncate">
                      {r.verse
                        ? `${r.verse.book} ${r.verse.chapter}:${r.verse.verse}`
                        : t("library.noMatchFound", "No match found")}
                    </div>
                    <span className="text-[10px] uppercase tracking-wider text-primary font-medium shrink-0">
                      {new Date(r.timestamp).toLocaleDateString("en-NG", {
                        day: "numeric",
                        month: "short",
                      })}
                    </span>
                  </div>
                  <p className="mt-1.5 text-sm text-muted-foreground line-clamp-2">"{r.query}"</p>
                </Link>
                <button
                  onClick={() => deleteHistoryItem.mutate(r.id)}
                  disabled={deleteHistoryItem.isPending}
                  aria-label="Delete from history"
                  className="h-8 w-8 shrink-0 rounded-full grid place-items-center text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition disabled:opacity-40"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </motion.div>
            ))
          ) : (
            <EmptyState
              Icon={Clock}
              text={t("library.emptyHistory", "Your search history will appear here.")}
            />
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
                  aria-label="Close"
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
                      search={{
                        q: "",
                        book: v.book,
                        chapter: v.chapter,
                        verse: v.verse,
                        version: v.version,
                      }}
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
