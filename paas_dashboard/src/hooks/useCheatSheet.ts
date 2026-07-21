import { useCallback, useEffect, useRef, useState } from "react";
import { fetchCheatSheet } from "../services/api";
import type { CheatSheetResponse } from "../types/cheatSheet";

interface UseCheatSheetResult {
  data: CheatSheetResponse | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

const POLL_INTERVAL_MS = 5000;
const BACKOFF_INTERVAL_MS = 30000;
const MAX_FAILURES_BEFORE_PAUSE = 10;
const MAX_FAILURES_BEFORE_BACKOFF = 3;

/**
 * 计算当前轮询间隔。
 *
 * - 正常情况：5 秒。
 * - 连续失败 3 次后：30 秒（指数退避的简化实现）。
 * - 连续失败 10 次后：暂停轮询，避免后端宕机时持续消耗资源。
 */
function getPollInterval(failureCount: number): number | null {
  if (failureCount >= MAX_FAILURES_BEFORE_PAUSE) {
    return null;
  }
  if (failureCount >= MAX_FAILURES_BEFORE_BACKOFF) {
    return BACKOFF_INTERVAL_MS;
  }
  return POLL_INTERVAL_MS;
}

export function useCheatSheet(): UseCheatSheetResult {
  const [data, setData] = useState<CheatSheetResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const failureCountRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scheduleNext = useCallback((callback: () => void, delay: number) => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    timerRef.current = setTimeout(callback, delay);
  }, []);

  const load = useCallback(async () => {
    try {
      const result = await fetchCheatSheet();
      setData((prev) => {
        if (prev && JSON.stringify(prev) === JSON.stringify(result)) {
          return prev;
        }
        return result;
      });
      setError(null);
      failureCountRef.current = 0;
    } catch (err) {
      const nextCount = failureCountRef.current + 1;
      failureCountRef.current = nextCount;

      // 静默处理：只在开发环境以 debug 级别输出，避免污染用户控制台。
      if (import.meta.env.DEV) {
        // eslint-disable-next-line no-console
        console.debug(
          `[useCheatSheet] 轮询失败（后端可能未启动），累计 ${nextCount} 次`,
          err
        );
      }

      // 保持上一次数据，仅在首次失败时给用户一个简短提示。
      if (nextCount === 1) {
        setError("后端连接失败，正在重试...");
      } else if (nextCount >= MAX_FAILURES_BEFORE_PAUSE) {
        setError("后端长时间不可用，已暂停自动刷新。可点击右上角手动刷新。");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const refetch = useCallback(() => {
    failureCountRef.current = 0;
    setError(null);
    setLoading(true);
    load();
  }, [load]);

  useEffect(() => {
    let cancelled = false;

    const tick = async () => {
      if (cancelled) return;
      await load();
      if (cancelled) return;

      const interval = getPollInterval(failureCountRef.current);
      if (interval !== null) {
        scheduleNext(tick, interval);
      }
    };

    tick();

    return () => {
      cancelled = true;
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [load, scheduleNext]);

  return {
    data,
    loading,
    error,
    refetch,
  };
}
