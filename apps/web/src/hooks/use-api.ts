"use client";

import useSWR from "swr";
import { apiRequest } from "@/lib/api/client";

export function useApi<T>(path: string | null, options?: { keepPreviousData?: boolean }) {
  return useSWR<T>(path, apiRequest, {
    keepPreviousData: options?.keepPreviousData ?? true,
    revalidateOnFocus: false,
    dedupingInterval: 30_000,
  });
}
