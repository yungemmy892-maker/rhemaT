import { api } from "./client";

// ---------------------------------------------------------------------------
// Shared types — mirror the existing frontend's Verse/SearchResult/RecentSearch
// shapes (see src/lib/verse-data.ts) so swapping dummy data for real API data
// requires no changes to component prop types.
// ---------------------------------------------------------------------------

export type BibleVersion = "KJV" | "WEB" | "ASV" | "DRA";

export interface Verse {
  id: string;
  book: string;
  chapter: number;
  verse: number;
  text: string;
  version: BibleVersion;
  ref: string;
  testament: "OT" | "NT";
}

export interface MatchBreakdown {
  phraseMatch: number;
  partialMatch: number;
  tokenSetMatch: number;
  fuzzyTypoMatch: number;
  confidence: number;
  exactPhrase: boolean;
}

export interface IdentifyResult extends MatchBreakdown {
  matched: true;
  query: string;
  verse: Verse;
  dailySearchesRemaining: number | null;
}

export interface IdentifyNoMatch {
  matched: false;
  query: string;
  dailySearchesRemaining: number | null;
}

export interface IdentifyQuotaExceeded {
  matched: false;
  quotaExceeded: true;
  dailySearchesRemaining: 0;
  dailySearchLimit: number;
}

export type IdentifyResponse = IdentifyResult | IdentifyNoMatch;

export interface RecentSearch {
  id: string;
  query: string;
  verseId: string | null;
  matched: boolean;
  confidence: number;
  timestamp: number;
  verse: Verse | null;
}

export interface UserStats {
  identified: number;
  saved: number;
  streak: number;
}

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  avatar?: string | null;
  plan: "Free" | "Pro";
  planExpiresAt?: number | null;
  hasPassword: boolean;
  dailySearchesRemaining: number | null;
  dailySearchLimit: number;
  stats: UserStats;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse extends TokenPair {
  user: AuthUser;
}

export interface Collection {
  name: string;
  count: number;
  verseIds: string[];
  verses: Verse[];
}

export interface Language {
  code: string;
  name: string;
  native: string;
  region: string;
}

export interface UserSettings {
  notifications: boolean;
  darkMode: boolean;
  quietHours: boolean;
  dailyVerse: boolean;
  verseReminders: boolean;
  savedActivity: boolean;
  community: boolean;
  productUpdates: boolean;
  sound: boolean;
  dailyVerseTime: "Morning" | "Midday" | "Evening";
  bibleVersion: BibleVersion;
  language: string;
  theme: string;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const authApi = {
  google: (idToken: string) =>
    api.post<AuthResponse>("/auth/google/", { id_token: idToken }).then((r) => r.data),

  register: (payload: { name?: string; email: string; password: string }) =>
    api.post<AuthResponse>("/auth/register/", payload).then((r) => r.data),

  login: (payload: { email: string; password: string }) =>
    api.post<AuthResponse>("/auth/login/", payload).then((r) => r.data),

  forgotPassword: (email: string) =>
    api.post<void>("/auth/forgot-password/", { email }).then((r) => r.data),

  resetPassword: (payload: { token: string; new_password: string }) =>
    api.post<void>("/auth/reset-password/", payload).then((r) => r.data),

  refresh: (refreshToken: string) =>
    api.post<TokenPair>("/auth/refresh/", { refresh_token: refreshToken }).then((r) => r.data),

  logout: (refreshToken: string) =>
    api.post<void>("/auth/logout/", { refresh_token: refreshToken }).then((r) => r.data),

  me: () => api.get<AuthUser>("/auth/me/").then((r) => r.data),

  updateProfile: (payload: { name: string }) =>
    api.patch<AuthUser>("/auth/me/", payload).then((r) => r.data),

  uploadAvatar: (file: File) => {
    const formData = new FormData();
    formData.append("avatar", file);
    return api
      .post<AuthUser>("/auth/avatar/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  changePassword: (payload: { current_password?: string; new_password: string }) =>
    api.post<void>("/auth/change-password/", payload).then((r) => r.data),

  deleteAccount: () => api.delete<void>("/auth/me/").then((r) => r.data),
};

// ---------------------------------------------------------------------------
// Bible
// ---------------------------------------------------------------------------

export const bibleApi = {
  verseOfDay: (version: BibleVersion = "KJV") =>
    api.get<Verse>("/bible/verse-of-day/", { params: { version } }).then((r) => r.data),

  popular: (version: BibleVersion = "KJV") =>
    api.get<Verse[]>("/bible/popular/", { params: { version } }).then((r) => r.data),

  verse: (book: string, chapter: number, verse: number, version: BibleVersion = "KJV") =>
    api
      .get<Verse>("/bible/verse/", { params: { book, chapter, verse, version } })
      .then((r) => r.data),

  chapter: (book: string, chapterNum: number, version: BibleVersion = "KJV") =>
    api
      .get<Verse[]>("/bible/chapter/", { params: { book, chapter: chapterNum, version } })
      .then((r) => r.data),

  books: () =>
    api
      .get<
        { book: string; display: string; testament: "OT" | "NT"; order: number }[]
      >("/bible/books/")
      .then((r) => r.data),

  languages: () =>
    api.get<Language[]>("/bible/languages/").then((r) => r.data),
};

// ---------------------------------------------------------------------------
// Search / identification
// ---------------------------------------------------------------------------

export const searchApi = {
  identify: (query: string, version?: BibleVersion) =>
    api
      .post<IdentifyResponse>("/search/identify/", { query, version })
      .then((r) => r.data)
      .catch((err: { status?: number; message?: string }) => {
        if (err?.status === 429) {
          return {
            matched: false as const,
            quotaExceeded: true as const,
            dailySearchesRemaining: 0 as const,
            dailySearchLimit: 20,
          } as IdentifyQuotaExceeded;
        }
        throw err;
      }),

  recent: () => api.get<RecentSearch[]>("/search/recent/").then((r) => r.data),
};

// ---------------------------------------------------------------------------
// Billing (Paystack / NGN subscriptions)
// ---------------------------------------------------------------------------

export interface NGNPricing {
  currency: "NGN";
  symbol: "₦";
  freeLimit: number;
  plans: {
    monthly: { kobo: number; label: string; naira: number };
    annual: { kobo: number; label: string; naira: number; savings: string };
  };
}

export interface PaymentInit {
  authorization_url: string;
  reference: string;
  amount_naira: number;
  interval: "monthly" | "annual";
}

export const billingApi = {
  pricing: () => api.get<NGNPricing>("/billing/pricing/").then((r) => r.data),

  initiate: (interval: "monthly" | "annual", callbackUrl?: string) =>
    api
      .post<PaymentInit>("/billing/initiate/", {
        interval,
        callback_url:
          callbackUrl ?? `${window.location.origin}/app/subscription?status=success`,
      })
      .then((r) => r.data),

  verify: (reference: string) =>
    api.post<{ user: AuthUser; status: string }>("/billing/verify/", { reference }).then((r) => r.data),

  cancel: () => api.post<AuthUser>("/billing/cancel/").then((r) => r.data),
};

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export interface AppNotification {
  id: string;
  kind:
    | "verse_of_day"
    | "saved_to_library"
    | "pro_upsell"
    | "new_voice"
    | "streak";
  title: string;
  body: string;
  unread: boolean;
  createdAt: number;
}

export const notificationsApi = {
  list: () => api.get<AppNotification[]>("/notifications/").then((r) => r.data),

  markAllRead: () => api.post<void>("/notifications/mark-all-read/").then((r) => r.data),

  subscribe: (sub: PushSubscriptionJSON) =>
    api.post<void>("/notifications/push/subscribe/", {
      endpoint: sub.endpoint,
      keys: sub.keys,
    }),

  unsubscribe: (endpoint: string) =>
    api.post<void>("/notifications/push/unsubscribe/", { endpoint }),

  vapidPublicKey: () =>
    api
      .get<{ publicKey: string }>("/notifications/push/vapid-public-key/", {
        baseURL: api.defaults.baseURL,
      })
      .then((r) => r.data.publicKey),
};

// ---------------------------------------------------------------------------
// Preferences (saved verses, collections, settings)
// ---------------------------------------------------------------------------

export const preferencesApi = {
  getSaved: () => api.get<Verse[]>("/preferences/saved/").then((r) => r.data),

  toggleSaved: (verseId: string, version?: BibleVersion) =>
    api
      .post<{ verseId: string; saved: boolean }>("/preferences/saved/", {
        verse_id: verseId,
        version,
      })
      .then((r) => r.data),

  getCollections: (version?: BibleVersion) =>
    api.get<Collection[]>("/preferences/collections/", { params: { version } }).then((r) => r.data),

  getSettings: () => api.get<UserSettings>("/preferences/settings/").then((r) => r.data),

  updateSettings: (patch: Partial<UserSettings>) =>
    api.patch<UserSettings>("/preferences/settings/", patch).then((r) => r.data),
};
