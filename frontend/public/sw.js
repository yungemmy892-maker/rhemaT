/* eslint-disable no-restricted-globals */
/**
 * VerseID Push Notification Service Worker
 * Registered by usePushNotifications.ts via navigator.serviceWorker.register('/sw.js')
 *
 * Handles:
 *   - push: receives a background push event from the backend (daily verse, streak, etc.)
 *           and shows a native OS notification even when the app tab is closed.
 *   - notificationclick: taps on the native notification navigate the user to the app.
 */

self.addEventListener("push", (event) => {
  if (!event.data) return;

  let payload;
  try {
    payload = event.data.json();
  } catch {
    payload = { title: "VerseID", body: event.data.text(), url: "/app/home" };
  }

  const title = payload.title ?? "VerseID";
  const options = {
    body: payload.body ?? "",
    icon: "/icons/icon-192.png",
    badge: "/icons/badge-72.png",
    tag: payload.tag ?? "verseid-default",
    data: { url: payload.url ?? "/app/home" },
    vibrate: [100, 50, 100],
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url ?? "/app/home";

  event.waitUntil(
    clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        // If the app is already open in a tab, focus it and navigate.
        for (const client of clientList) {
          if ("focus" in client) {
            client.focus();
            if ("navigate" in client) client.navigate(targetUrl);
            return;
          }
        }
        // Otherwise open a new tab.
        if (clients.openWindow) return clients.openWindow(targetUrl);
      })
  );
});

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) =>
  event.waitUntil(clients.claim())
);
