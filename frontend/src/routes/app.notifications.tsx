import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Bell,
  BookmarkCheck,
  Crown,
  Sparkles,
  Mic,
  Heart,
  PartyPopper,
  X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  useNotifications,
  useMarkAllRead,
  useDeleteNotification,
  useClearNotifications,
} from "@/hooks/queries/useNotificationsBilling";
import { useT } from "@/context/I18nContext";
import type { AppNotification } from "@/services/api";

export const Route = createFileRoute("/app/notifications")({
  head: () => ({ meta: [{ title: "Notifications - VerseID" }] }),
  component: Notifications,
});

// Map backend notification kinds to the existing visual design (icon + gradient)
// so the server sends only data and the frontend owns presentation.
const KIND_META: Record<AppNotification["kind"], { Icon: LucideIcon; tint: string }> = {
  verse_of_day: {
    Icon: Sparkles,
    tint: "from-violet-500 to-fuchsia-500",
  },
  saved_to_library: {
    Icon: BookmarkCheck,
    tint: "from-purple-500 to-pink-500",
  },
  pro_upsell: {
    Icon: Crown,
    tint: "from-amber-400 to-orange-500",
  },
  new_voice: {
    Icon: Mic,
    tint: "from-sky-500 to-indigo-500",
  },
  streak: {
    Icon: Heart,
    tint: "from-rose-500 to-red-500",
  },
  welcome: {
    Icon: PartyPopper,
    tint: "from-violet-500 to-fuchsia-500",
  },
};

function formatTime(ts: number): string {
  const diff = Date.now() - ts;
  const m = Math.floor(diff / 60000);
  if (m < 1) return "Just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d === 1) return "Yesterday";
  if (d < 7) return `${d}d ago`;
  return new Date(ts).toLocaleDateString("en-NG", { day: "numeric", month: "short" });
}

function Notifications() {
  const t = useT();
  const { data: items = [], isLoading } = useNotifications();
  const markAll = useMarkAllRead();
  const deleteOne = useDeleteNotification();
  const clearAll = useClearNotifications();

  return (
    <div>
      <div className="flex items-center gap-3">
        <Link
          to="/app/profile"
          aria-label="Back to Profile"
          className="h-10 w-10 rounded-full glass grid place-items-center"
        >
          <ArrowLeft className="h-4.5 w-4.5" />
        </Link>
        <h1 className="font-display text-2xl font-semibold flex-1">
          {t("notifications.title", "Notifications")}
        </h1>
        <div className="flex items-center gap-2.5 text-xs font-medium">
          <button
            className="text-primary disabled:opacity-40"
            onClick={() => markAll.mutate()}
            disabled={markAll.isPending || !items.some((n) => n.unread)}
          >
            Mark all read
          </button>
          <span className="text-muted-foreground/40">·</span>
          <button
            className="text-muted-foreground disabled:opacity-40"
            onClick={() => {
              if (confirm("Clear all notifications? This can't be undone.")) {
                clearAll.mutate();
              }
            }}
            disabled={clearAll.isPending || items.length === 0}
          >
            Clear all
          </button>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {isLoading ? (
          [0, 1, 2].map((i) => (
            <div key={i} className="h-[72px] rounded-2xl glass-strong shadow-card animate-pulse" />
          ))
        ) : items.length === 0 ? (
          <div className="py-16 text-center text-sm text-muted-foreground">
            No notifications yet — check back after your first verse search.
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {items.map((n, i) => {
              const meta = KIND_META[n.kind] ?? KIND_META.verse_of_day;
              return (
                <motion.div
                  key={n.id}
                  layout
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, x: -24, transition: { duration: 0.15 } }}
                  transition={{ delay: i * 0.04 }}
                  className="relative flex gap-3 p-4 pr-11 rounded-2xl glass-strong shadow-card"
                >
                  <div
                    className={`h-11 w-11 shrink-0 rounded-2xl bg-gradient-to-br ${meta.tint} grid place-items-center shadow-glow`}
                  >
                    <meta.Icon className="h-5 w-5 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {n.unread && (
                        <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                      )}
                      <div className="text-sm font-semibold truncate">{n.title}</div>
                    </div>
                    <div className="flex items-center justify-between gap-2 mt-0.5">
                      <p className="text-sm text-muted-foreground line-clamp-2">{n.body}</p>
                    </div>
                    <div className="text-[11px] text-muted-foreground mt-1">
                      {formatTime(n.createdAt)}
                    </div>
                  </div>
                  <button
                    aria-label="Delete notification"
                    onClick={() => deleteOne.mutate(n.id)}
                    className="absolute top-3 right-3 h-6 w-6 rounded-full glass grid place-items-center text-muted-foreground opacity-70 active:opacity-100"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>

      <div className="mt-8 p-5 rounded-3xl glass-strong shadow-card text-center">
        <Bell className="h-6 w-6 text-primary mx-auto" />
        <p className="mt-2 text-sm text-muted-foreground">
          Manage what you're notified about in Settings.
        </p>
        <Link to="/app/settings" className="mt-3 inline-block text-sm font-medium text-primary">
          Open settings ›
        </Link>
      </div>
    </div>
  );
}