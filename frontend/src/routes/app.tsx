import { createFileRoute, Outlet, useNavigate } from "@tanstack/react-router";
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

  useEffect(() => {
    // Only redirect once the session check is fully resolved. If isReady is
    // false we're still verifying a stored token — wait for the result
    // before deciding where to send the user.
    if (isReady && !user) {
      navigate({ to: "/auth", replace: true });
    }
  }, [isReady, user, navigate]);

  // While verifying a stored access token, show a minimal inline spinner
  // inside the mobile frame. This only shows for users who have a stored
  // token (i.e. they were previously logged in) — new visitors are
  // redirected immediately after the no-token fast path in AuthContext.
  if (!isReady) {
    return (
      <MobileFrame>
        <div className="flex h-full min-h-screen items-center justify-center">
          <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
        </div>
      </MobileFrame>
    );
  }

  // isReady && !user → redirect in progress (handled by useEffect above)
  if (!user) return null;

  return (
    <MobileFrame>
      <Outlet />
      <BottomNav />
    </MobileFrame>
  );
}
