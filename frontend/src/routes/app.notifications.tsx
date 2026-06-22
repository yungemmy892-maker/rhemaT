import { createFileRoute, Link } from "@tanstack/react-router";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Bell,
  BookmarkCheck,
  Crown,
  Sparkles,
  Mic,
  Heart,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useNotifications, useMarkAllRead } from "@/hooks/queries/useNotificationsBilling";
import type { AppNotification } from "@/services/api";

export const Route = createFileRoute("/app/notifications")({
  head: () => ({ meta: [{ title: "Notifications — VerseID" }] }),
  component: Notifications,
});

// Map backend notification kinds to the existing visual design (icon + gradient)
// so the server sends only data and the frontend owns presentation.
const KIND_META: Record<
  AppNotification["kind"],
  { Icon: LucideIcon; tint: string }
> = {
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
  const { data: items = [], isLoading } = useNotifications();
  const markAll = useMarkAllRead();

  return (
    <div>
      <div className="flex items-center gap-3">
        <Link
          to="/app/profile"
          className="h-10 w-10 rounded-full glass grid place-items-center"
        >
          <ArrowLeft className="h-4.5 w-4.5" />
        </Link>
        <h1 className="font-display text-2xl font-semibold flex-1">Notifications</h1>
        <button
          className="text-xs font-medium text-primary"
          onClick={() => markAll.mutate()}
          disabled={markAll.isPending || !items.some((n) => n.unread)}
        >
          Mark all read
        </button>
      </div>

      <div className="mt-5 space-y-3">
        {isLoading
          ? [0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-[72px] rounded-2xl glass-strong shadow-card animate-pulse"
              />
            ))
          : items.length === 0
            ? (
              <div className="py-16 text-center text-sm text-muted-foreground">
                No notifications yet — check back after your first verse search.
              </div>
            )
            : items.map((n, i) => {
                const meta = KIND_META[n.kind] ?? KIND_META.verse_of_day;
                return (
                  <motion.div
                    key={n.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    className="relative flex gap-3 p-4 rounded-2xl glass-strong shadow-card"
                  >
                    <div
                      className={`h-11 w-11 shrink-0 rounded-2xl bg-gradient-to-br ${meta.tint} grid place-items-center shadow-glow`}
                    >
                      <meta.Icon className="h-5 w-5 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-sm font-semibold truncate">{n.title}</div>
                        <div className="text-[11px] text-muted-foreground shrink-0">
                          {formatTime(n.createdAt)}
                        </div>
                      </div>
                      <p className="text-sm text-muted-foreground mt-0.5 line-clamp-2">
                        {n.body}
                      </p>
                    </div>
                    {n.unread && (
                      <span className="absolute top-3 right-3 h-2 w-2 rounded-full bg-primary shadow-glow" />
                    )}
                  </motion.div>
                );
              })}
      </div>

      <div className="mt-8 p-5 rounded-3xl glass-strong shadow-card text-center">
        <Bell className="h-6 w-6 text-primary mx-auto" />
        <p className="mt-2 text-sm text-muted-foreground">
          Manage what you're notified about in Settings.
        </p>
        <Link
          to="/app/settings"
          className="mt-3 inline-block text-sm font-medium text-primary"
        >
          Open settings ›
        </Link>
      </div>
    </div>
  );
}
