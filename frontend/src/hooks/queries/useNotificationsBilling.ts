import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { billingApi, notificationsApi } from "@/services/api";
import { queryKeys } from "./keys";

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export function useNotifications() {
  return useQuery({
    queryKey: queryKeys.notifications,
    queryFn: notificationsApi.list,
    refetchInterval: 60_000, // poll every minute for fresh feed items
  });
}

export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: notificationsApi.markAllRead,
    // Optimistic: immediately zero out the unread dots without waiting for
    // the round-trip, matching the expected tap-and-see-it-update feel.
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: queryKeys.notifications });
      const prev = qc.getQueryData(queryKeys.notifications);
      qc.setQueryData(
        queryKeys.notifications,
        (old: { unread: boolean }[] | undefined) =>
          old?.map((n) => ({ ...n, unread: false })) ?? []
      );
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(queryKeys.notifications, ctx.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: queryKeys.notifications }),
  });
}

// ---------------------------------------------------------------------------
// Billing / pricing
// ---------------------------------------------------------------------------

export function usePricing() {
  return useQuery({
    queryKey: queryKeys.pricing,
    queryFn: billingApi.pricing,
    staleTime: Infinity, // prices don't change between deployments
  });
}

export function useInitiatePayment() {
  return useMutation({
    mutationFn: ({
      interval,
      callbackUrl,
    }: {
      interval: "monthly" | "annual";
      callbackUrl?: string;
    }) => billingApi.initiate(interval, callbackUrl),
    onSuccess: (data) => {
      // Open Paystack's hosted checkout in the same tab.
      window.location.href = data.authorization_url;
    },
  });
}

export function useVerifyPayment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reference: string) => billingApi.verify(reference),
    onSuccess: (data) => {
      // Refresh auth user so plan/quota reflect the upgrade immediately
      qc.setQueryData(queryKeys.me, data.user);
    },
  });
}

export function useCancelSubscription() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: billingApi.cancel,
    onSuccess: (updated) => {
      qc.setQueryData(queryKeys.me, updated);
    },
  });
}
