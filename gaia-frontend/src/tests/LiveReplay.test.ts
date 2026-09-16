import { describe, expect, it } from 'vitest';
import fixture from './fixtures/replay.json';
import { appendLiveReplay, parseLiveCatalog, parseLiveReplay } from '../replay/live';
import type { LiveGame, LiveStatus } from '../replay/live';

function sample(steps = 1, revision = 0, status: LiveStatus = 'running') {
  const id = 'live-0123456789abcdef';
  const game: LiveGame = { id, file: `${id}-${revision}.json.gz`, policy: fixture.metadata.policy,
    faction: fixture.metadata.faction, seed: fixture.metadata.seed, vp: 0, steps,
    revision, status, updated_at: 1 };
  const frames = fixture.frames.slice(0, steps + 1);
  const raw = { ...fixture, metadata: { ...fixture.metadata, steps, live_revision: revision, live_status: status },
    frames, events: fixture.events.slice(0, frames[frames.length - 1].event_end) };
  Reflect.deleteProperty(raw.metadata, 'scores');
  return { game, raw };
}

describe('live replay data boundary (no automatic playback policy)', () => {
  it('requires a revision-specific local file and an explicit live status', () => {
    const { game } = sample();
    expect(parseLiveCatalog({ schema_version: 1, games: [game] })).toEqual([game]);
    for (const invalid of [{ ...game, status: undefined }, { ...game, revision: -1 },
      { ...game, updated_at: Infinity }, { ...game, file: '../private.json.gz' },
      { ...game, file: `${game.id}-99.json.gz` }]) {
      expect(() => parseLiveCatalog({ schema_version: 1, games: [invalid] })).toThrow();
    }
  });

  it('accepts a partial record only with matching catalog identity and revision', () => {
    const { raw, game } = sample();
    expect(parseLiveReplay(raw, game).frames).toHaveLength(2);
    for (const changed of [{ ...game, revision: 1 }, { ...game, policy: 'other' },
      { ...game, steps: 3 }, { ...game, faction: 'other' }]) {
      expect(() => parseLiveReplay(raw, changed)).toThrow();
    }
  });

  it('does not present a partial or failed record as completed scoring', () => {
    const { raw, game } = sample(1, 0, 'complete');
    expect(() => parseLiveReplay(raw, game)).toThrow();
    const failed = sample(1, 1, 'failed');
    expect(parseLiveReplay(failed.raw, failed.game).metadata.live_status).toBe('failed');
    expect(() => parseLiveReplay({ ...failed.raw,
      metadata: { ...failed.raw.metadata, scores: { 0: 999 } } }, failed.game)).toThrow();
  });

  it('appends actual actions, ignores delayed older responses and rejects changed history', () => {
    const first = sample(1, 0);
    const next = sample(2, 1);
    const a = parseLiveReplay(first.raw, first.game);
    const b = parseLiveReplay(next.raw, next.game);
    expect(appendLiveReplay(a, b)).toBe(b);
    expect(appendLiveReplay(b, a)).toBe(b);
    const broken = structuredClone(b);
    broken.frames[0].state.players[0].vp += 10;
    expect(() => appendLiveReplay(a, broken)).toThrow();
    const stranger = structuredClone(b);
    stranger.metadata.seed = 'another-game';
    expect(() => appendLiveReplay(a, stranger)).toThrow();
    expect(() => appendLiveReplay(a, { ...b, gameId: 'live-fedcba9876543210' })).toThrow();
  });
});
