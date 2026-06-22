import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Bell,
  BellOff,
  Palette,
  Globe,
  BookOpen,
  Mic,
  Moon,
  Trash2,
  LogOut,
  ShieldAlert,
  X,
  Sparkles,
  Heart,
  Calendar,
  MessageSquare,
  Volume2,
} from "lucide-react";
import { usePushNotifications } from "@/hooks/usePushNotifications";
import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useSettings, useUpdateSettings } from "@/hooks/queries/usePreferences";
import type { BibleVersion } from "@/services/api";

export const Route = createFileRoute("/app/settings")({
  head: () => ({ meta: [{ title: "Settings — VerseID" }] }),
  component: Settings,
});

function Settings() {
  const navigate = useNavigate();
  const { deleteAccount, signOut } = useAuth();
  const push = usePushNotifications();
  const { data: settings, isLoading } = useSettings();
  const updateSettings = useUpdateSettings();
  const [confirm, setConfirm] = useState(false);

  const onDelete = async () => {
    await deleteAccount();
    setConfirm(false);
    navigate({ to: "/" });
  };
  const onLogout = async () => {
    await signOut();
    navigate({ to: "/" });
  };

  if (isLoading || !settings) {
    return (
      <div>
        <div className="flex items-center gap-3">
          <Link to="/app/profile" className="h-10 w-10 rounded-full glass grid place-items-center">
            <ArrowLeft className="h-4.5 w-4.5" />
          </Link>
          <h1 className="font-display text-2xl font-semibold">Settings</h1>
        </div>
        <div className="mt-6 space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-40 rounded-3xl glass-strong shadow-card animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3">
        <Link to="/app/profile" className="h-10 w-10 rounded-full glass grid place-items-center">
          <ArrowLeft className="h-4.5 w-4.5" />
        </Link>
        <h1 className="font-display text-2xl font-semibold">Settings</h1>
      </div>

      <Group title="Preferences">
        <ToggleRow
          Icon={Bell}
          label="Notifications"
          value={settings.notifications}
          onChange={(v) => updateSettings.mutate({ notifications: v })}
        />
        <ToggleRow
          Icon={Moon}
          label="Dark mode"
          value={settings.darkMode}
          onChange={(v) => updateSettings.mutate({ darkMode: v })}
        />
        <ToggleRow
          Icon={Bell}
          label="Quiet hours (10pm–7am)"
          value={settings.quietHours}
          onChange={(v) => updateSettings.mutate({ quietHours: v })}
        />
      </Group>

      <Group title="Notification preferences">
        <ToggleRow
          Icon={Sparkles}
          label="Daily verse"
          value={settings.dailyVerse && settings.notifications}
          onChange={(v) => updateSettings.mutate({ dailyVerse: v })}
        />
        <ToggleRow
          Icon={Calendar}
          label="Verse reminders"
          value={settings.verseReminders && settings.notifications}
          onChange={(v) => updateSettings.mutate({ verseReminders: v })}
        />
        <ToggleRow
          Icon={Heart}
          label="Saved verse activity"
          value={settings.savedActivity && settings.notifications}
          onChange={(v) => updateSettings.mutate({ savedActivity: v })}
        />
        <ToggleRow
          Icon={MessageSquare}
          label="Community & devotionals"
          value={settings.community && settings.notifications}
          onChange={(v) => updateSettings.mutate({ community: v })}
        />
        <ToggleRow
          Icon={Sparkles}
          label="Product updates"
          value={settings.productUpdates && settings.notifications}
          onChange={(v) => updateSettings.mutate({ productUpdates: v })}
        />
        <ToggleRow
          Icon={Volume2}
          label="In‑app sound"
          value={settings.sound && settings.notifications}
          onChange={(v) => updateSettings.mutate({ sound: v })}
        />
        <div className="px-4 py-3.5">
          <div className="flex items-center gap-3 mb-3">
            <div className="h-9 w-9 rounded-xl bg-primary-soft grid place-items-center">
              <Calendar className="h-4.5 w-4.5 text-primary" />
            </div>
            <span className="flex-1 text-sm font-medium">Daily verse time</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {(["Morning", "Midday", "Evening"] as const).map((f) => (
              <button
                key={f}
                onClick={() => updateSettings.mutate({ dailyVerseTime: f })}
                className={`h-10 rounded-2xl text-xs font-medium transition ${
                  settings.dailyVerseTime === f
                    ? "bg-gradient-primary text-white shadow-glow"
                    : "glass-strong text-foreground"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Push notification subscribe/unsubscribe */}
        {push.status !== 'unsupported' && (
          <div className="px-4 py-3.5 flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-primary-soft grid place-items-center">
              {push.status === 'subscribed' ? (
                <Bell className="h-4.5 w-4.5 text-primary" />
              ) : (
                <BellOff className="h-4.5 w-4.5 text-primary" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium">
                {push.status === 'subscribed' ? 'Push notifications on' : 'Enable push notifications'}
              </div>
              {push.status === 'denied' && (
                <div className="text-xs text-muted-foreground">
                  Blocked in browser settings — tap ⓘ in the address bar to allow.
                </div>
              )}
              {push.error && (
                <div className="text-xs text-destructive">{push.error}</div>
              )}
            </div>
            {push.status === 'subscribed' ? (
              <button
                onClick={push.unsubscribe}
                className="text-xs text-destructive font-medium"
              >
                Turn off
              </button>
            ) : push.status === 'unsubscribed' ? (
              <button
                onClick={push.subscribe}
                className="text-xs text-primary font-medium"
              >
                Enable
              </button>
            ) : null}
          </div>
        )}
      </Group>

      <Group title="Reading">
        <div className="px-4 py-3.5">
          <div className="flex items-center gap-3 mb-3">
            <div className="h-9 w-9 rounded-xl bg-primary-soft grid place-items-center">
              <BookOpen className="h-4.5 w-4.5 text-primary" />
            </div>
            <span className="flex-1 text-sm font-medium">Bible version</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {(["KJV", "WEB"] as BibleVersion[]).map((v) => (
              <button
                key={v}
                onClick={() => updateSettings.mutate({ bibleVersion: v })}
                className={`h-10 rounded-2xl text-xs font-medium transition ${
                  settings.bibleVersion === v
                    ? "bg-gradient-primary text-white shadow-glow"
                    : "glass-strong text-foreground"
                }`}
              >
                {v === "KJV" ? "King James Version" : "World English Bible"}
              </button>
            ))}
          </div>
        </div>
        <SelectRow Icon={Globe} label="Language" value={settings.language} />
        <SelectRow Icon={Palette} label="Theme" value={settings.theme} />
      </Group>

      <Group title="Voice">
        <SelectRow Icon={Mic} label="AI voice" value={settings.aiVoice} />
        <SelectRow Icon={Mic} label="Tone" value={settings.voiceTone} />
      </Group>

      <Group title="Account">
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-3 px-4 py-3.5 hover:bg-primary-soft/60 transition"
        >
          <div className="h-9 w-9 rounded-xl bg-primary-soft grid place-items-center">
            <LogOut className="h-4.5 w-4.5 text-primary" />
          </div>
          <span className="flex-1 text-left text-sm font-medium">Log out</span>
        </button>
        <button
          onClick={() => setConfirm(true)}
          className="w-full flex items-center gap-3 px-4 py-3.5 hover:bg-destructive/5 transition"
        >
          <div className="h-9 w-9 rounded-xl bg-destructive/10 grid place-items-center">
            <Trash2 className="h-4.5 w-4.5 text-destructive" />
          </div>
          <span className="flex-1 text-left text-sm font-medium text-destructive">
            Delete account
          </span>
        </button>
      </Group>

      <p className="mt-8 text-center text-xs text-muted-foreground">VerseID · v1.0.0</p>

      <AnimatePresence>
        {confirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm grid place-items-end sm:place-items-center px-4 pb-6"
            onClick={() => setConfirm(false)}
          >
            <motion.div
              initial={{ y: 40, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 40, opacity: 0 }}
              transition={{ type: "spring", stiffness: 360, damping: 32 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-sm rounded-3xl bg-surface shadow-card p-6"
            >
              <div className="flex items-start gap-3">
                <div className="h-11 w-11 rounded-2xl bg-destructive/10 grid place-items-center">
                  <ShieldAlert className="h-5 w-5 text-destructive" />
                </div>
                <div className="flex-1">
                  <div className="font-display text-lg font-semibold">Delete your account?</div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    This permanently removes your saved verses, history and preferences. This action
                    cannot be undone.
                  </p>
                </div>
                <button
                  onClick={() => setConfirm(false)}
                  className="h-8 w-8 rounded-full grid place-items-center hover:bg-muted"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-5 grid grid-cols-2 gap-2">
                <button
                  onClick={() => setConfirm(false)}
                  className="h-12 rounded-2xl glass-strong font-medium text-sm"
                >
                  Cancel
                </button>
                <button
                  onClick={onDelete}
                  className="h-12 rounded-2xl bg-destructive text-white font-medium text-sm shadow-card"
                >
                  Delete
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-6">
      <div className="px-1 text-xs uppercase tracking-[0.16em] text-muted-foreground font-medium mb-2">
        {title}
      </div>
      <div className="rounded-3xl glass-strong shadow-card divide-y divide-border overflow-hidden">
        {children}
      </div>
    </div>
  );
}

function Row({
  Icon,
  label,
  right,
}: {
  Icon: React.ComponentType<{ className?: string }>;
  label: string;
  right: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-3.5">
      <div className="h-9 w-9 rounded-xl bg-primary-soft grid place-items-center">
        <Icon className="h-4.5 w-4.5 text-primary" />
      </div>
      <span className="flex-1 text-sm font-medium">{label}</span>
      {right}
    </div>
  );
}

function ToggleRow({
  Icon,
  label,
  value,
  onChange,
}: {
  Icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <Row
      Icon={Icon}
      label={label}
      right={
        <button
          onClick={() => onChange(!value)}
          className={`relative h-7 w-12 rounded-full transition ${value ? "bg-gradient-primary shadow-glow" : "bg-border"}`}
        >
          <motion.span
            layout
            transition={{ type: "spring", stiffness: 500, damping: 30 }}
            className={`absolute top-0.5 h-6 w-6 rounded-full bg-white shadow-card ${value ? "right-0.5" : "left-0.5"}`}
          />
        </button>
      }
    />
  );
}

function SelectRow({
  Icon,
  label,
  value,
}: {
  Icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <Row
      Icon={Icon}
      label={label}
      right={<span className="text-sm text-muted-foreground">{value} ›</span>}
    />
  );
}
