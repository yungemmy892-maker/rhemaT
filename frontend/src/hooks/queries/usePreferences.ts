import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { preferencesApi, type BibleVersion, type UserSettings } from "@/services/api";
import { queryKeys } from "./keys";

export function useSavedVerses() {
  return useQuery({
    queryKey: queryKeys.saved,
    queryFn: preferencesApi.getSaved,
  });
}

export function useToggleSaved() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ verseId, version }: { verseId: string; version?: BibleVersion }) =>
      preferencesApi.toggleSaved(verseId, version),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.saved });
      queryClient.invalidateQueries({ queryKey: queryKeys.me });
    },
  });
}

export function useCollections(version?: import("@/services/api").BibleVersion) {
  return useQuery({
    queryKey: [...queryKeys.collections, version ?? "KJV"],
    queryFn: () => preferencesApi.getCollections(version),
  });
}

export function useSettings() {
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: preferencesApi.getSettings,
  });
}

export function useUpdateSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (patch: Partial<UserSettings>) => preferencesApi.updateSettings(patch),
    onMutate: async (patch) => {
      // Optimistic update so toggles in Settings flip instantly, matching
      // how the existing local-state version felt (no spinner per toggle).
      await queryClient.cancelQueries({ queryKey: queryKeys.settings });
      const previous = queryClient.getQueryData<UserSettings>(queryKeys.settings);
      if (previous) {
        queryClient.setQueryData(queryKeys.settings, { ...previous, ...patch });
      }
      return { previous };
    },
    onError: (_err, _patch, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.settings, context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.settings });
    },
  });
}
