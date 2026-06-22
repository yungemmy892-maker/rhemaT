import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { searchApi, type BibleVersion } from "@/services/api";
import { queryKeys } from "./keys";

export function useIdentifyVerse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ query, version }: { query: string; version?: BibleVersion }) =>
      searchApi.identify(query, version),
    onSuccess: () => {
      // A successful identification can change recent history, the
      // identified counter (Profile), and streak — invalidate everything
      // that surfaces those rather than trying to patch them by hand.
      queryClient.invalidateQueries({ queryKey: queryKeys.recentSearches });
      queryClient.invalidateQueries({ queryKey: queryKeys.me });
    },
  });
}

export function useRecentSearches() {
  return useQuery({
    queryKey: queryKeys.recentSearches,
    queryFn: searchApi.recent,
    staleTime: 1000 * 30,
  });
}
