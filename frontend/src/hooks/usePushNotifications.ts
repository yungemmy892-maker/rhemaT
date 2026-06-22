import { useCallback, useEffect, useState } from "react";
import { notificationsApi } from "@/services/api";

export type PushStatus = "unsupported" | "denied" | "subscribed" | "unsubscribed" | "loading";

function urlBase64ToUint8Array(base64: string): ArrayBuffer {
  const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
  const raw = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0)).buffer;
}

export function usePushNotifications() {
  const [status, setStatus] = useState<PushStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      setStatus("unsupported");
      return;
    }
    if (Notification.permission === "denied") {
      setStatus("denied");
      return;
    }
    navigator.serviceWorker.ready.then((reg) =>
      reg.pushManager.getSubscription().then((sub) => {
        setStatus(sub ? "subscribed" : "unsubscribed");
      })
    );
  }, []);

  const subscribe = useCallback(async () => {
    setError(null);
    if (!("serviceWorker" in navigator)) return;

    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setStatus("denied");
        return;
      }

      const vapidKey = await notificationsApi.vapidPublicKey();
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidKey),
      });

      await notificationsApi.subscribe(sub.toJSON() as PushSubscriptionJSON);
      setStatus("subscribed");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Push subscription failed.");
    }
  }, []);

  const unsubscribe = useCallback(async () => {
    try {
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (sub) {
        await notificationsApi.unsubscribe(sub.endpoint);
        await sub.unsubscribe();
      }
      setStatus("unsubscribed");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unsubscribe failed.");
    }
  }, []);

  return { status, error, subscribe, unsubscribe };
}
