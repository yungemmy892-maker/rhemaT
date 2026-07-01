import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import {
  ChevronRight,
  Settings,
  Bell,
  Mic,
  Shield,
  Crown,
  LogOut,
  BookmarkCheck,
  HelpCircle,
  UserCog,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export const Route = createFileRoute("/app/profile/")({
  head: () => ({ meta: [{ title: "Profile — VerseID" }] }),
  component: Profile,
});

function Profile() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const handleSignOut = async () => {
    await signOut();
    navigate({ to: "/" });
  };

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="font-display text-3xl font-semibold">Profile</h1>
        <Link
          to="/app/settings"
          className="h-10 w-10 rounded-full glass grid place-items-center"
        >
          <Settings className="h-4.5 w-4.5" />
        </Link>
      </div>

      {/* Profile card */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mt-6 p-6 rounded-3xl glass-strong shadow-card text-center"
      >
        <div className="relative inline-block">
          <img
            src={
              user?.avatar ??
              "https://api.dicebear.com/9.x/notionists/svg?seed=guest"
            }
            alt="avatar"
            className="h-24 w-24 rounded-full ring-4 ring-primary-soft"
          />
          {user?.plan === "Pro" && (
            <div className="absolute -bottom-1 -right-1 h-7 w-7 rounded-full bg-gradient-primary grid place-items-center shadow-glow">
              <Crown className="h-3.5 w-3.5 text-white" />
            </div>
          )}
        </div>
        <div className="mt-4 font-display text-xl font-semibold">
          {user?.name ?? "Guest"}
        </div>
        <div className="text-sm text-muted-foreground">
          {user?.email ?? "Not signed in"}
        </div>

        <Link
          to="/app/subscription"
          className="mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-soft text-primary text-sm font-medium"
        >
          <Crown className="h-4 w-4" />
          {user?.plan === "Pro" ? "Pro plan · Manage" : "Free plan · Upgrade to Pro"}
        </Link>
      </motion.div>

      {/* Stats */}
      <div className="mt-4 grid grid-cols-3 gap-3">
        {[
          { v: String(user?.stats.identified ?? 0), l: "Identified" },
          { v: String(user?.stats.saved ?? 0), l: "Saved" },
          { v: String(user?.stats.streak ?? 0), l: "Streak" },
        ].map((s) => (
          <div
            key={s.l}
            className="p-4 rounded-2xl glass-strong shadow-card text-center"
          >
            <div className="font-display text-2xl font-semibold text-gradient">
              {s.v}
            </div>
            <div className="text-[11px] text-muted-foreground mt-0.5">{s.l}</div>
          </div>
        ))}
      </div>

      {/* Menu */}
      <div className="mt-6 rounded-3xl glass-strong shadow-card divide-y divide-border overflow-hidden">
        <MenuRow Icon={UserCog} label="Edit profile" to="/app/profile/edit" />
        <MenuRow Icon={BookmarkCheck} label="Saved verses" to="/app/library" />
        <MenuRow Icon={Bell} label="Notifications" to="/app/notifications" />
        <MenuRow Icon={Mic} label="Voice preferences" to="/app/settings" />
        <MenuRow Icon={Shield} label="Privacy" to="/privacy" />
        <MenuRow Icon={Crown} label="Upgrade to Pro" to="/app/subscription" />
        <MenuRow Icon={HelpCircle} label="Help & support" to="/help" />
      </div>

      <button
        onClick={handleSignOut}
        className="mt-4 w-full h-14 rounded-2xl glass-strong shadow-card flex items-center justify-center gap-2 text-destructive font-medium"
      >
        <LogOut className="h-4.5 w-4.5" /> Log out
      </button>
    </div>
  );
}

function MenuRow({
  Icon,
  label,
  to,
}: {
  Icon: React.ComponentType<{ className?: string }>;
  label: string;
  to: string;
}) {
  return (
    <Link
      to={to}
      className="flex items-center gap-3 px-4 py-3.5 hover:bg-primary-soft/60 transition"
    >
      <div className="h-9 w-9 rounded-xl bg-primary-soft grid place-items-center">
        <Icon className="h-4.5 w-4.5 text-primary" />
      </div>
      <span className="flex-1 text-sm font-medium">{label}</span>
      <ChevronRight className="h-4 w-4 text-muted-foreground" />
    </Link>
  );
}
