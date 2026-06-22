import { Link, useRouterState } from "@tanstack/react-router";
import { Home, BookmarkCheck, User, Compass } from "lucide-react";
import { motion } from "framer-motion";

const items = [
  { to: "/app/home", label: "Home", icon: Home },
  { to: "/app/library", label: "Library", icon: BookmarkCheck },
  { to: "/app/discover", label: "Discover", icon: Compass },
  { to: "/app/profile", label: "Profile", icon: User },
] as const;

export function BottomNav() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 px-4 pb-[max(env(safe-area-inset-bottom),12px)]">
      <div className="mx-auto max-w-md glass-strong shadow-elevated rounded-3xl px-2 py-2 flex items-center justify-between">
        {items.map(({ to, label, icon: Icon }) => {
          const active = pathname === to || pathname.startsWith(to + "/");
          return (
            <Link
              key={to}
              to={to}
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
                  className={`h-5 w-5 transition-colors ${active ? "text-primary" : "text-muted-foreground"}`}
                  strokeWidth={active ? 2.4 : 2}
                />
                <span
                  className={`text-[10px] font-medium tracking-wide ${active ? "text-primary" : "text-muted-foreground"}`}
                >
                  {label}
                </span>
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
