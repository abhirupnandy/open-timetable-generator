import { useQueries, useQuery } from "@tanstack/react-query";
import { useCallback, useState } from "react";

import { api } from "./api";
import { RESOURCES, type RefData, type ResourceKey } from "./resources";

export const resourceQuery = (key: ResourceKey) => ({
  queryKey: ["resource", key],
  queryFn: () => api.list(RESOURCES[key].path),
});

export function useResource(key: ResourceKey) {
  return useQuery(resourceQuery(key));
}

/** Load several resources (for labels and dropdowns) as one ``RefData`` map. */
export function useRefs(keys: ResourceKey[]): { refs: RefData; isLoading: boolean; error: Error | null } {
  const results = useQueries({ queries: keys.map(resourceQuery) });
  const refs: RefData = {};
  keys.forEach((key, index) => {
    const data = results[index].data;
    if (data) refs[key] = data;
  });
  return {
    refs,
    isLoading: results.some((result) => result.isLoading),
    error: results.find((result) => result.error)?.error ?? null,
  };
}

export function useConfig() {
  return useQuery({ queryKey: ["config"], queryFn: api.config, staleTime: 60_000 });
}

/** ``useState`` persisted to localStorage (ignored when storage is unavailable). */
export function useStoredState<T extends string = string>(
  key: string,
  initial: NoInfer<T>,
): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      return (localStorage.getItem(key) as T | null) ?? initial;
    } catch {
      return initial;
    }
  });

  const update = useCallback(
    (next: T) => {
      setValue(next);
      try {
        localStorage.setItem(key, next);
      } catch {
        /* storage unavailable */
      }
    },
    [key],
  );

  return [value, update];
}
