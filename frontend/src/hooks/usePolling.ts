import { useEffect, useRef } from 'react';

/** Simplest reliable live-update mechanism available here: poll on an
 * interval while `enabled`. No SSE/WebSocket infra exists in this project
 * yet, so this is the honest choice rather than building new infrastructure
 * for it. Always calls the latest `callback` without resetting the interval. */
export function usePolling(callback: () => void, intervalMs: number, enabled: boolean = true) {
  const savedCallback = useRef(callback);
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(() => savedCallback.current(), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs, enabled]);
}
