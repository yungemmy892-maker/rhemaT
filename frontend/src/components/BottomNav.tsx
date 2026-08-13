import { Link, useRouterState } from "@tanstack/react-router";
import { Home, BookmarkCheck, User, Compass } from "lucide-react";
import { motion } from "framer-motion";
import { useT } from "@/context/I18nContext";

const items = [
  { to: "/app/home", key: "nav.home", label: "Home", icon: Home },
  { to: "/app/library", key: "nav.library", label: "Library", icon: BookmarkCheck },
  { to: "/app/discover", key: "nav.discover", label: "Discover", icon: Compass },
  { to: "/app/profile", key: "nav.profile", label: "Profile", icon: User },
] as const;

function playNavChime() {
  if (typeof window === "undefined") return;

  const audio = new Audio("/sounds/chime.wav");
  audio.volume = 0.35;

  audio.play().catch(() => {
    // Ignore browsers that block audio playback.
  });
}

export function BottomNav() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const t = useT();

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 px-4 pb-[max(env(safe-area-inset-bottom),12px)]">
      <div className="mx-auto max-w-md glass-strong shadow-elevated rounded-3xl px-2 py-2 flex items-center justify-between">
        {items.map(({ to, key, label, icon: Icon }) => {
          const active = pathname === to || pathname.startsWith(to + "/");

          return (
            <Link
              key={to}
              to={to}
              onClick={() => {
                if (!active) {
                  playNavChime();
                }
              }}
              className="relative flex-1 flex flex-col items-center gap-0.5 py-2 rounded-2xl"
            >
              {active && (
                <motion.div
                  layoutId="nav-pill"
                  className="absolute inset-0 bg-primary-soft rounded-2xl"
                  transition={{ type: "spring", stiffness: 380, damping: 32 }}
                />
              )}

              <span className="relative z-10 flex flex-col items-center gap-0.5">
                <Icon
                  className={`h-5 w-5 transition-colors ${
                    active ? "text-primary" : "text-muted-foreground"
                  }`}
                  strokeWidth={active ? 2.4 : 2}
                />

                <span
                  className={`text-[10px] font-medium tracking-wide ${
                    active ? "text-primary" : "text-muted-foreground"
                  }`}
                >
                  {t(key, label)}
                </span>
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}