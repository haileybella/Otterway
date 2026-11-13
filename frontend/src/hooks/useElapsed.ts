import { useEffect, useState } from 'react';

/** "02:14"-style call timer that ticks every second from `startedAt` (ms). */
export function useElapsed(startedAt: number | null): string {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (startedAt == null) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  if (startedAt == null) return '00:00';
  const total = Math.max(0, Math.floor((now - startedAt) / 1000));
  const m = String(Math.floor(total / 60)).padStart(2, '0');
  const s = String(total % 60).padStart(2, '0');
  return `${m}:${s}`;
}
