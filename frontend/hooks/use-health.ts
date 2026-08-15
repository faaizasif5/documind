"use client";

import { useQuery } from "@tanstack/react-query";

import { getHealth } from "@/lib/api";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => getHealth(signal),
    refetchInterval: (query) => (query.state.data ? 30_000 : 5_000),
    retry: 6,
    retryDelay: (attempt) => Math.min(1_000 * 2 ** attempt, 10_000),
  });
}
