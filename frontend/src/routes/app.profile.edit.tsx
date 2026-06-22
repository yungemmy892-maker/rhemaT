import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Lock,
  User as UserIcon,
  Eye,
  EyeOff,
  Check,
  Camera,
  Image as ImageIcon,
  X,
  Loader2,
} from "lucide-react";
import { useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";

export const Route = createFileRoute("/app/profile/edit")({
  head: () => ({ meta: [{ title: "Edit profile — VerseID" }] }),
  component: EditProfile,
});

function EditProfile() {
  const { user, updateProfile, changePassword, uploadAvatar } = useAuth();

  const [name, setName] = useState(user?.name ?? "");
  const [nameSaving, setNameSaving] = useState(false);
  const [nameSaved, setNameSaved] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);

  const [avatarSheetOpen, setAvatarSheetOpen] = useState(false);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const galleryInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordSaved, setPasswordSaved] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const nameChanged = name.trim() && name.trim() !== user?.name;

  const handleAvatarFile = async (file: File | undefined) => {
    if (!file) return;
    setAvatarSheetOpen(false);
    setAvatarError(null);
    setAvatarUploading(true);
    try {
      await uploadAvatar(file);
    } catch (err) {
      setAvatarError((err as { message?: string })?.message || "Couldn't upload that photo.");
    } finally {
      setAvatarUploading(false);
    }
  };

  const handleSaveName = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nameChanged) return;
    setNameSaving(true);
    setNameError(null);
    try {
      await updateProfile(name.trim());
      setNameSaved(true);
      setTimeout(() => setNameSaved(false), 1800);
    } catch {
      setNameError("Couldn't update your name. Please try again.");
    } finally {
      setNameSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 6) {
      setPasswordError("New password must be at least 6 characters.");
      return;
    }
    setPasswordSaving(true);
    setPasswordError(null);
    try {
      await changePassword(user?.hasPassword ? currentPassword : undefined, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setPasswordSaved(true);
      setTimeout(() => setPasswordSaved(false), 1800);
    } catch (err) {
      setPasswordError((err as { message?: string })?.message || "Couldn't change your password.");
    } finally {
      setPasswordSaving(false);
    }
  };

  return (
    <div>
      <div className="flex items-center gap-3">
        <Link to="/app/profile" className="h-10 w-10 rounded-full glass grid place-items-center">
          <ArrowLeft className="h-4.5 w-4.5" />
        </Link>
        <h1 className="font-display text-2xl font-semibold">Edit profile</h1>
      </div>

      <div className="mt-6 flex items-center gap-4 p-4 rounded-3xl glass-strong shadow-card">
        <button
          type="button"
          onClick={() => setAvatarSheetOpen(true)}
          className="relative h-14 w-14 rounded-full ring-2 ring-primary-soft overflow-hidden shrink-0"
        >
          <img
            src={user?.avatar ?? "https://api.dicebear.com/9.x/notionists/svg?seed=guest"}
            alt="avatar"
            className="h-full w-full object-cover"
          />
          <div className="absolute inset-0 bg-black/0 hover:bg-black/30 transition grid place-items-center">
            {avatarUploading ? (
              <Loader2 className="h-4 w-4 text-white animate-spin" />
            ) : (
              <Camera className="h-4 w-4 text-white opacity-0 hover:opacity-100 transition" />
            )}
          </div>
        </button>
        <div className="min-w-0">
          <div className="font-medium truncate">{user?.name}</div>
          <div className="text-sm text-muted-foreground truncate">{user?.email}</div>
          {avatarError && <p className="text-xs text-destructive mt-1">{avatarError}</p>}
        </div>
      </div>

      {/* Hidden inputs: "gallery" picks any existing photo, "camera" hints
          the browser/OS to open the camera directly via the capture attr. */}
      <input
        ref={galleryInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => handleAvatarFile(e.target.files?.[0])}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={(e) => handleAvatarFile(e.target.files?.[0])}
      />

      <AnimatePresence>
        {avatarSheetOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm grid place-items-end sm:place-items-center px-4 pb-6"
            onClick={() => setAvatarSheetOpen(false)}
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
                <div className="flex-1">
                  <div className="font-display text-lg font-semibold">Update profile photo</div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Choose how you'd like to add a photo.
                  </p>
                </div>
                <button
                  onClick={() => setAvatarSheetOpen(false)}
                  className="h-8 w-8 rounded-full grid place-items-center hover:bg-muted"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="mt-5 space-y-2">
                <button
                  onClick={() => cameraInputRef.current?.click()}
                  className="w-full h-14 px-4 rounded-2xl glass-strong shadow-card flex items-center gap-3 text-sm font-medium"
                >
                  <div className="h-9 w-9 rounded-xl bg-primary-soft grid place-items-center">
                    <Camera className="h-4.5 w-4.5 text-primary" />
                  </div>
                  Take a photo
                </button>
                <button
                  onClick={() => galleryInputRef.current?.click()}
                  className="w-full h-14 px-4 rounded-2xl glass-strong shadow-card flex items-center gap-3 text-sm font-medium"
                >
                  <div className="h-9 w-9 rounded-xl bg-primary-soft grid place-items-center">
                    <ImageIcon className="h-4.5 w-4.5 text-primary" />
                  </div>
                  Choose from gallery
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <Group title="Name">
        <form onSubmit={handleSaveName} className="p-4 space-y-3">
          <Field Icon={UserIcon}>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Full name"
              className="w-full bg-transparent outline-none text-sm"
            />
          </Field>
          {nameError && <p className="text-xs text-destructive">{nameError}</p>}
          <button
            type="submit"
            disabled={!nameChanged || nameSaving}
            className="w-full h-12 rounded-2xl bg-gradient-primary text-white font-medium shadow-glow disabled:opacity-50 inline-flex items-center justify-center gap-2"
          >
            {nameSaved ? (
              <>
                <Check className="h-4 w-4" /> Saved
              </>
            ) : nameSaving ? (
              "Saving…"
            ) : (
              "Save name"
            )}
          </button>
        </form>
      </Group>

      <Group title={user?.hasPassword ? "Change password" : "Set a password"}>
        <form onSubmit={handleChangePassword} className="p-4 space-y-3">
          {user?.hasPassword && (
            <Field Icon={Lock}>
              <input
                type={showCurrent ? "text" : "password"}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Current password"
                className="w-full bg-transparent outline-none text-sm"
              />
              <button
                type="button"
                onClick={() => setShowCurrent(!showCurrent)}
                className="text-muted-foreground"
              >
                {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </Field>
          )}
          <Field Icon={Lock}>
            <input
              type={showNew ? "text" : "password"}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="New password"
              className="w-full bg-transparent outline-none text-sm"
              minLength={6}
            />
            <button
              type="button"
              onClick={() => setShowNew(!showNew)}
              className="text-muted-foreground"
            >
              {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </Field>
          {!user?.hasPassword && (
            <p className="text-xs text-muted-foreground">
              Your account currently signs in with Google only. Setting a password lets you also
              sign in with email.
            </p>
          )}
          {passwordError && <p className="text-xs text-destructive">{passwordError}</p>}
          <button
            type="submit"
            disabled={passwordSaving || newPassword.length < 6}
            className="w-full h-12 rounded-2xl glass-strong font-medium shadow-card disabled:opacity-50 inline-flex items-center justify-center gap-2"
          >
            {passwordSaved ? (
              <>
                <Check className="h-4 w-4" /> Updated
              </>
            ) : passwordSaving ? (
              "Saving…"
            ) : user?.hasPassword ? (
              "Update password"
            ) : (
              "Set password"
            )}
          </button>
        </form>
      </Group>
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-6">
      <div className="px-1 text-xs uppercase tracking-[0.16em] text-muted-foreground font-medium mb-2">
        {title}
      </div>
      <div className="rounded-3xl glass-strong shadow-card overflow-hidden">{children}</div>
    </div>
  );
}

function Field({
  Icon,
  children,
}: {
  Icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 h-14 px-4 rounded-2xl glass shadow-card">
      <Icon className="h-4.5 w-4.5 text-primary" />
      {children}
    </div>
  );
}
