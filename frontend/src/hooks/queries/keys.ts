export const queryKeys = {
  me: ["auth", "me"] as const,
  verseOfDay: (version: string) => ["bible", "verse-of-day", version] as const,
  popular: (version: string) => ["bible", "popular", version] as const,
  recentSearches: ["search", "recent"] as const,
  saved: ["preferences", "saved"] as const,
  collections: ["preferences", "collections"] as const,
  settings: ["preferences", "settings"] as const,
  notifications: ["notifications"] as const,
  pricing: ["billing", "pricing"] as const,
};
