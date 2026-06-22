import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { Mic, Search, Bookmark, History, Compass, ChevronRight, Bell, Sparkles } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useRecentSearches } from "@/hooks/queries/useSearch";

export const Route = createFileRoute("/app/home")({
  head: () => ({ meta: [{ title: "Home — VerseID" }] }),
  component: Home,
});

function Home() {
  const { user } = useAuth();
  const { data: recent = [], isLoading: recentLoading } = useRecentSearches();
  const navigate = useNavigate();
  const remaining = user?.dailySearchesRemaining;
  const isPro = user?.plan === "Pro";

  return (
    <div>
      {/* Greeting */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex items-center justify-between"
      >
        <div>
          <div className="text-xs text-muted-foreground">Good evening</div>
          <h1 className="font-display text-2xl font-semibold">
            {user?.name?.split(" ")[0] ?? "Friend"}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/app/notifications"
            className="relative h-11 w-11 rounded-full glass grid place-items-center"
          >
            <Bell className="h-4.5 w-4.5" />
            <span className="absolute top-2.5 right-2.5 h-2 w-2 rounded-full bg-primary shadow-glow" />
          </Link>
          <Link to="/app/profile">
            <img
              src={user?.avatar ?? "https://api.dicebear.com/9.x/notionists/svg?seed=guest"}
              className="h-11 w-11 rounded-full ring-2 ring-primary-soft"
              alt="profile"
            />
          </Link>
        </div>
      </motion.div>

      {/* Daily search quota pill — only shown to Free users */}
      {!isPro && remaining !== null && remaining !== undefined && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-3"
        >
          {remaining > 5 ? (
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl glass-strong text-xs text-muted-foreground">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              {remaining} free {remaining === 1 ? "search" : "searches"} left today
              <Link to="/app/subscription" className="ml-auto text-primary font-medium">
                Go Pro
              </Link>
            </div>
          ) : remaining === 0 ? (
            <Link
              to="/app/subscription"
              className="flex items-center gap-2 px-3 py-2 rounded-xl bg-primary/10 border border-primary/20 text-xs font-medium text-primary"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Daily limit reached — upgrade to Pro for unlimited searches
            </Link>
          ) : (
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-600">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
              Only {remaining} {remaining === 1 ? "search" : "searches"} left today
              <Link to="/app/subscription" className="ml-auto text-primary font-medium">
                Upgrade
              </Link>
            </div>
          )}
        </motion.div>
      )}

      {/* Mic CTA */}
      <motion.button
        onClick={() => navigate({ to: "/app/voice" })}
        initial={{ opacity: 0, scale: 0.94 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, delay: 0.1 }}
        whileTap={{ scale: 0.97 }}
        className="mt-8 w-full relative aspect-square max-h-80 rounded-[2rem] overflow-hidden bg-gradient-primary shadow-glow text-white grid place-items-center"
      >
        <div className="absolute inset-0 opacity-25 bg-[radial-gradient(circle_at_50%_30%,white,transparent_55%)]" />
        <div className="absolute inset-10 rounded-full border border-white/30 animate-pulse-ring" />
        <div className="relative flex flex-col items-center gap-4">
          <div className="h-24 w-24 rounded-full glass-strong grid place-items-center">
            <Mic className="h-10 w-10 text-white" strokeWidth={2.2} />
          </div>
          <div className="text-center">
            <div className="font-display text-xl font-semibold">Tap to identify a verse</div>
            <div className="text-sm text-white/80 mt-0.5">Listening starts instantly</div>
          </div>
        </div>
      </motion.button>

      {/* Text search shortcut */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <Link
          to="/app/text"
          className="mt-4 flex items-center gap-3 h-14 px-4 rounded-2xl glass-strong shadow-card"
        >
          <Search className="h-5 w-5 text-muted-foreground" />
          <span className="text-sm text-muted-foreground">Search by text…</span>
        </Link>
      </motion.div>

      {/* Quick actions */}
      <div className="mt-7 grid grid-cols-3 gap-3">
        {[
          { to: "/app/library", label: "Saved", Icon: Bookmark },
          { to: "/app/library", label: "History", Icon: History },
          { to: "/app/discover", label: "Discover", Icon: Compass },
        ].map((q, i) => (
          <motion.div
            key={q.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 + i * 0.05 }}
          >
            <Link
              to={q.to}
              className="flex flex-col items-center justify-center gap-2 py-4 rounded-2xl glass-strong shadow-card hover:bg-primary-soft transition"
            >
              <div className="h-10 w-10 rounded-xl bg-primary-soft grid place-items-center">
                <q.Icon className="h-5 w-5 text-primary" />
              </div>
              <span className="text-xs font-medium">{q.label}</span>
            </Link>
          </motion.div>
        ))}
      </div>

      {/* Recent */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-display text-lg font-semibold">Recent searches</h2>
          <Link to="/app/library" className="text-xs text-primary font-medium">
            See all
          </Link>
        </div>
        <div className="space-y-2.5">
          {recentLoading ? (
            [0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-[68px] rounded-2xl glass-strong shadow-card animate-pulse"
              />
            ))
          ) : recent.length === 0 ? (
            <div className="p-4 rounded-2xl glass-strong shadow-card text-center text-sm text-muted-foreground">
              No searches yet — tap the mic or search by text to identify your first verse.
            </div>
          ) : (
            recent.map((r) => {
              const v = r.verse;
              return (
                <Link
                  key={r.id}
                  to="/app/results"
                  search={{ q: r.query }}
                  className="flex items-center gap-3 p-3 rounded-2xl glass-strong shadow-card hover:bg-primary-soft transition"
                >
                  <div className="h-10 w-10 rounded-xl bg-gradient-primary grid place-items-center text-white text-xs font-semibold">
                    {(v?.book ?? "?").slice(0, 2)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">
                      {v ? `${v.book} ${v.chapter}:${v.verse}` : "No match found"}
                    </div>
                    <div className="text-xs text-muted-foreground truncate">"{r.query}"</div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </Link>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
