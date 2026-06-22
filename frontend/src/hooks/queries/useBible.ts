import { useQuery } from "@tanstack/react-query";
import { bibleApi, type BibleVersion } from "@/services/api";
import { queryKeys } from "./keys";

export function useVerseOfDay(version: BibleVersion = "KJV") {
  return useQuery({
    queryKey: queryKeys.verseOfDay(version),
    queryFn: () => bibleApi.verseOfDay(version),
    staleTime: 1000 * 60 * 60, // an hour — it only changes once a day server-side
  });
}

export function usePopularVerses(version: BibleVersion = "KJV") {
  return useQuery({
    queryKey: queryKeys.popular(version),
    queryFn: () => bibleApi.popular(version),
    staleTime: 1000 * 60 * 30,
  });
}
