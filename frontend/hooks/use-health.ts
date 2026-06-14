"use client";

import { useQuery } from "@tanstack/react-query";

import { getHealth } from "@/lib/api";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => getHealth(signal),
    refetchInterval: 15_000,
    retry: false,
  });
}
