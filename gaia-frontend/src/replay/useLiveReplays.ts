import { useEffect, useRef, useState } from 'react';
import { appendLiveReplay, parseLiveCatalog, parseLiveReplay, type LiveGame, type LiveRecord } from './live';
import { loadReplay } from './records';

/** One request chain at a time; unchanged immutable revisions are never downloaded again. */
export function useLiveReplays(selected: string) {
  const [games, setGames] = useState<LiveGame[]>([]);
  const [record, setRecord] = useState<LiveRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const latest = useRef<LiveRecord | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    latest.current = null;
    setRecord(null);
    setError(null);
    async function poll() {
      try {
        const response = await fetch('/ai-live/index.json', { signal: controller.signal, cache: 'no-store' });
        if (response.status === 404 && !selected.startsWith('live-')) {
          if (!controller.signal.aborted) setGames([]);
          return;
        }
        if (!response.ok) throw new Error('실시간 연결 확인 중 · 마지막 수를 유지합니다.');
        const catalog = parseLiveCatalog(await response.json());
        if (controller.signal.aborted) return;
        const game = catalog.find(g => g.id === selected);
        if (!game && selected.startsWith('live-')) throw new Error('실시간 기록을 찾지 못했습니다. 마지막 수를 유지합니다.');
        setGames(previous => catalog.map(game => {
          const known = previous.find(item => item.id === game.id);
          return known && known.revision > game.revision ? known : game;
        }));
        const previous = latest.current;
        if (game && (!previous || game.revision > previous.metadata.live_revision)) {
          const incoming = parseLiveReplay(await loadReplay(game.file, controller.signal, '/ai-live'), game);
          if (controller.signal.aborted) return;
          const validated = previous ? appendLiveReplay(previous, incoming) : incoming;
          // Keep paused frame identities stable: receiving data must not scroll the old view.
          const next = previous ? { ...validated,
            frames: [...previous.frames, ...validated.frames.slice(previous.frames.length)],
            events: [...previous.events, ...validated.events.slice(previous.events.length)] } : validated;
          latest.current = next;
          setRecord(next);
        }
        setError(null);
      } catch (cause: unknown) {
        if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : '실시간 연결 확인 중');
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(poll, 2000);
      }
    }
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [selected]);
  return { games, record: record?.gameId === selected ? record : null, error };
}
