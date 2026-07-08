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
 * Query-based identify — uses the query string AND the selected Bible
 * version as the cache key, so the result survives remounts (e.g.
 * navigating back then forward) but automatically re-searches if the user
 * switches their preferred Bible version in Settings.
 */
export function useIdentifyQuery(q: string, version?: BibleVersion) {
  const queryClient = useQueryClient();
  const result = useQuery({
    queryKey: ["search", "identify", q, version ?? "auto"],
    queryFn: () => searchApi.identify(q, version),
    enabled: Boolean(q),
    staleTime: 1000 * 60 * 10,
    retry: false,
  });

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

export function useClearHistory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: searchApi.clearHistory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.recentSearches });
    },
  });
}

export function useDeleteHistoryItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => searchApi.deleteHistoryItem(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.recentSearches });
      const prev = queryClient.getQueryData(queryKeys.recentSearches);
      queryClient.setQueryData(
        queryKeys.recentSearches,
        (old: { id: string }[] | undefined) => old?.filter((item) => item.id !== id) ?? []
      );
      return { prev };
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.prev) queryClient.setQueryData(queryKeys.recentSearches, ctx.prev);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.recentSearches });
    },
  });
}