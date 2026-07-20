import { useCallback, useEffect, useState } from "react";
import { fetchCheatSheet } from "../services/api";
import type { CheatSheetResponse } from "../types/cheatSheet";

interface UseCheatSheetResult {
  data: CheatSheetResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

const POLL_INTERVAL_MS = 5000;

export function useCheatSheet(): UseCheatSheetResult {
  const [data, setData] = useState<CheatSheetResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const result = await fetchCheatSheet();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();

    const timer = setInterval(() => {
      load();
    }, POLL_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [load]);

  return {
    data,
    loading,
    error,
    refetch: load,
  };
}
