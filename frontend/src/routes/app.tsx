import { createFileRoute, Outlet, useNavigate, useRouter } from "@tanstack/react-router";
import { useEffect } from "react";
import { BottomNav } from "@/components/BottomNav";
import { MobileFrame } from "@/components/MobileFrame";
import { useAuth } from "@/context/AuthContext";

export const Route = createFileRoute("/app")({
  component: AppLayout,
});

function AppLayout() {
  const { user, isReady } = useAuth();
  const navigate = useNavigate();
  const router = useRouter();

  /* ── Auth guard ────────────────────────────────────────────────── */
  useEffect(() => {
    if (isReady && !user) {
      navigate({ to: "/auth", replace: true });
    }
  }, [isReady, user, navigate]);

  /* ── Back-navigation guard ─────────────────────────────────────── */
  // Prevents the hardware/browser back button from leaving the app and
  // landing on the landing page while the user is signed in.
  // Works by pushing a dummy history state on mount so that pressing
  // back just pops that state back to the current app page, and the
  // popstate handler immediately re-pushes it so it never escapes.
  useEffect(() => {
    if (!user) return;

    // Push a sentinel entry so there is always something behind us.
    window.history.pushState({ verseid: true }, "");

    const handlePopState = (e: PopStateEvent) => {
      // If the popped state is NOT one of ours the user is trying to
      // navigate away (e.g. to the landing page). Block it by pushing
      // the sentinel back.
      if (!e.state?.verseid) {
        window.history.pushState({ verseid: true }, "");
      } else {
        // Normal in-app back — let TanStack Router handle it.
        router.history.back();
        // Re-push the sentinel after the router has navigated.
        setTimeout(() => window.history.pushState({ verseid: true }, ""), 0);
      }
    };

    window.addEventListener("popstate", handlePopState);

    // Also intercept the browser's beforeunload (tab close / refresh)
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      window.removeEventListener("popstate", handlePopState);
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [user, router]);

  /* ── Loading state ─────────────────────────────────────────────── */
  if (!isReady) {
    return (
      <MobileFrame>
        <div className="flex h-full min-h-screen items-center justify-center">
          <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
        </div>
      </MobileFrame>
    );
  }

  // isReady && !user → redirect in progress, render nothing
  if (!user) return null;

  return (
    <MobileFrame>
      <Outlet />
      <BottomNav />
    </MobileFrame>
  );
}
