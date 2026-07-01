import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { searchApi, type BibleVersion } from "@/services/api";
import { queryKeys } from "./keys";

export function useIdentifyVerse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ query, version }: { query: string; version?: BibleVersion }) =>
      searchApi.identify(query, version),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.recentSearches });
      queryClient.invalidateQueries({ queryKey: queryKeys.me });
    },
  });
}

/**
 * Query-based identify — uses the query string as the cache key so the
 * result survives remounts (e.g. navigating back then forward to the same
 * Results screen). This is what the Results screen uses instead of
 * useMutation, which loses state on every remount.
 */
export function useIdentifyQuery(q: string) {
  const queryClient = useQueryClient();
  const result = useQuery({
    queryKey: ["search", "identify", q],
    queryFn: () => searchApi.identify(q),
    enabled: Boolean(q),
    staleTime: 1000 * 60 * 10, // cache 10 mins — same query = same verse
    retry: false,
  });

  // Invalidate history/stats once a result arrives
  useEffect(() => {
    if (result.isSuccess) {
      queryClient.invalidateQueries({ queryKey: queryKeys.recentSearches });
      queryClient.invalidateQueries({ queryKey: queryKeys.me });
    }
  }, [result.isSuccess, queryClient]);

  return result;
}

export function useRecentSearches() {
  return useQuery({
    queryKey: queryKeys.recentSearches,
    queryFn: searchApi.recent,
    staleTime: 1000 * 30,
  });
}
