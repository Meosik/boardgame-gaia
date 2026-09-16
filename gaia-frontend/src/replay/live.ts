/** Live data boundary only. Playback/cursor behavior belongs to the viewer. */
import { parseCatalog, parseReplay } from './records';
import type { ReplayGame, ReplayRecord } from './records';

export type LiveStatus = 'running' | 'failed' | 'complete';
export interface LiveGame extends ReplayGame {
  status: LiveStatus;
  revision: number;
  updated_at: number;
}
export interface LiveRecord extends ReplayRecord {
  gameId: string;
  metadata: ReplayRecord['metadata'] & { live_status: LiveStatus; live_revision: number };
}

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function revision(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}

export function parseLiveCatalog(value: unknown): LiveGame[] {
  const games = parseCatalog(value);
  for (const game of games) {
    const entry: unknown = game;
    if (!object(entry) || !['running', 'failed', 'complete'].includes(String(entry.status))
      || !revision(entry.revision) || typeof entry.updated_at !== 'number'
      || !Number.isFinite(entry.updated_at) || entry.updated_at < 0
      || !/^live-[a-f0-9]{16}$/.test(game.id)
      || game.file !== `${game.id}-${entry.revision}.json.gz`) {
      throw new Error('실시간 리플레이 목록이 올바르지 않습니다.');
    }
  }
  return games as LiveGame[];
}

export function parseLiveReplay(value: unknown, game: LiveGame): LiveRecord {
  const replay = parseReplay(value);
  const meta: unknown = replay.metadata;
  if (!object(meta) || meta.seed !== game.seed || meta.policy !== game.policy
    || meta.faction !== game.faction || meta.steps !== game.steps
    || meta.live_status !== game.status || meta.live_revision !== game.revision) {
    throw new Error('실시간 리플레이와 목록 정보가 다릅니다.');
  }
  const phase: unknown = replay.frames[replay.frames.length - 1].state.phase;
  const ended = object(phase) && 'Ended' in phase;
  if ((game.status === 'complete' && (!ended || !object(meta.scores)))
    || (game.status === 'running' && ended)
    || (game.status !== 'complete' && 'scores' in meta)) {
    throw new Error('진행 중인 리플레이를 완료 결과로 표시할 수 없습니다.');
  }
  return { ...replay, gameId: game.id,
    metadata: { ...replay.metadata, live_status: game.status, live_revision: game.revision } };
}

/** Late responses cannot rewind a game; a new revision cannot rewrite its past. */
export function appendLiveReplay(previous: LiveRecord, incoming: LiveRecord): LiveRecord {
  const before = previous.metadata;
  const after = incoming.metadata;
  if (previous.gameId !== incoming.gameId || ['seed', 'policy', 'faction', 'focus_player', 'versions'].some(key =>
    JSON.stringify(before[key as keyof typeof before]) !== JSON.stringify(after[key as keyof typeof after]))) {
    throw new Error('다른 게임의 실시간 기록을 이어 붙일 수 없습니다.');
  }
  if (after.live_revision <= before.live_revision) return previous;
  if (before.live_status !== 'running' || incoming.frames.length < previous.frames.length
    || previous.frames.some((frame, index) => JSON.stringify(frame) !== JSON.stringify(incoming.frames[index]))
    || previous.events.some((event, index) => JSON.stringify(event) !== JSON.stringify(incoming.events[index]))) {
    throw new Error('실시간 리플레이의 이전 행동이 변경되었습니다.');
  }
  return incoming;
}
