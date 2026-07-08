import { useQuery } from "@tanstack/react-query";
import { bibleApi, type BibleVersion, type Language } from "@/services/api";
import { queryKeys } from "./keys";

export function useVerseOfDay(version: BibleVersion = "KJV") {
  return useQuery({
    queryKey: queryKeys.verseOfDay(version),
    queryFn: () => bibleApi.verseOfDay(version),
    staleTime: 1000 * 60 * 60, // an hour — only changes once a day server-side
  });
}

export function usePopularVerses(version: BibleVersion = "KJV") {
  return useQuery({
    queryKey: queryKeys.popular(version),
    queryFn: () => bibleApi.popular(version),
    staleTime: 1000 * 60 * 30,
  });
}

export function useLanguages() {
  return useQuery<Language[]>({
    queryKey: ["bible", "languages"],
    queryFn: bibleApi.languages,
    staleTime: Infinity, // language list never changes between deploys
  });
}

/**
 * Translated UI chrome strings for the given interface-language code
 * ("en" or unset returns {} — nothing to override). Backs I18nContext's
 * t() helper. staleTime: Infinity because a language's cache on the
 * backend is itself permanent once warmed — no reason to ever refetch
 * within a session.
 */
export function useUITranslations(langCode: string | undefined) {
  return useQuery({
    queryKey: ["bible", "translations", langCode ?? "en"],
    queryFn: () => bibleApi.translations(langCode ?? "en"),
    enabled: Boolean(langCode) && langCode !== "en",
    staleTime: Infinity,
  });
}

/**
 * Fetches one verse directly by reference — used when opening a Saved or
 * History item whose exact verse is already known, so re-opening it neither
 * re-runs the fuzzy matcher nor spends one of the user's daily search quota
 * (unlike routing back through useIdentifyQuery with the original text).
 */
export function useVerseByRef(
  book: string | undefined,
  chapter: number | undefined,
  verseNum: number | undefined,
  version: BibleVersion | undefined,
  enabled = true,
) {
  return useQuery({
    queryKey: ["bible", "verse-by-ref", book, chapter, verseNum, version ?? "KJV"],
    queryFn: () => bibleApi.verse(book!, chapter!, verseNum!, version ?? "KJV"),
    enabled: enabled && Boolean(book && chapter && verseNum),
    staleTime: 1000 * 60 * 10,
    retry: false,
  });
}
