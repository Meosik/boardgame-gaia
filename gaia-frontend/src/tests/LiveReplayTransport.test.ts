import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { useLiveReplays } from '../replay/useLiveReplays';
import { loadReplay, parseReplay } from '../replay/records';
import fixture from './fixtures/replay.json';

vi.mock('../replay/records', async original => ({
  ...await original<typeof import('../replay/records')>(), loadReplay: vi.fn(),
}));
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.resetAllMocks(); });

function sample(steps: number, revision: number) {
  const id = 'live-0123456789abcdef';
  const game = { id, file: `${id}-${revision}.json.gz`, policy: fixture.metadata.policy,
    faction: fixture.metadata.faction, seed: fixture.metadata.seed, vp: 0, steps,
    revision, status: 'running', updated_at: 1 };
  const frames = fixture.frames.slice(0, steps + 1);
  const raw = { ...fixture, metadata: { ...fixture.metadata, steps, live_revision: revision, live_status: 'running' },
    frames, events: fixture.events.slice(0, frames[frames.length - 1].event_end) };
  Reflect.deleteProperty(raw.metadata, 'scores');
  return { game, raw };
}

it('downloads only new revisions, preserves paused frame identity, and rejects rewritten history', async () => {
  let current = sample(1, 0);
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({ schema_version: 1, games: [current.game] }) })));
  vi.mocked(loadReplay).mockImplementation(async () => parseReplay(current.raw));
  const { result, unmount } = renderHook(() => useLiveReplays(current.game.id));
  await waitFor(() => expect(result.current.record?.frames).toHaveLength(2));
  const firstFrame = result.current.record!.frames[0];
  // Re-mount under fake timers to own every poll timer.
  unmount(); vi.useFakeTimers();
  const next = renderHook(() => useLiveReplays(current.game.id));
  await act(async () => {});
  const stableFrame = next.result.current.record!.frames[0];
  const calls = vi.mocked(loadReplay).mock.calls.length;
  await act(async () => { await vi.advanceTimersByTimeAsync(6000); });
  expect(loadReplay).toHaveBeenCalledTimes(calls);
  current = sample(2, 1);
  await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
  expect(next.result.current.record!.frames).toHaveLength(3);
  expect(next.result.current.record!.frames[0]).toBe(stableFrame);
  expect(next.result.current.record!.frames[0]).toEqual(firstFrame);
  current = structuredClone(sample(2, 2)); current.raw.frames[0].state.players[0].vp += 99;
  await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
  expect(next.result.current.error).toContain('이전 행동');
  expect(next.result.current.record!.metadata.live_revision).toBe(1);
  current = sample(1, 0);
  await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
  expect(next.result.current.record!.frames).toHaveLength(3);
  next.unmount();
  expect(vi.getTimerCount()).toBe(0);
});

it('keeps the last valid data/catalog on network failure or disappearance', async () => {
  const current = sample(1, 0);
  let mode = 'ok';
  vi.stubGlobal('fetch', vi.fn(async () => {
    if (mode === 'network') throw new Error('network unavailable');
    return { ok: true, json: async () => ({ schema_version: 1, games: mode === 'missing' ? [] : [current.game] }) };
  }));
  vi.mocked(loadReplay).mockResolvedValue(parseReplay(current.raw));
  vi.useFakeTimers();
  const { result, unmount } = renderHook(() => useLiveReplays(current.game.id));
  await act(async () => {});
  const before = result.current.record;
  for (const failure of ['network', 'missing']) {
    mode = failure;
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(result.current.error).toBeTruthy();
    expect(result.current.record).toBe(before);
    expect(result.current.games).toHaveLength(1);
  }
  unmount();
});
