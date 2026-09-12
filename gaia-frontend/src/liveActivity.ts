import { activeActionPlayerId, pendingDecisionPlayerId } from './types/game';
import type {
  BoardState,
  GameEvent,
  GamePhase,
  GameState,
  PlayerId,
  PlayerState,
  ResearchTrack,
  SpaceshipId,
} from './types/game';
import type { ReplayHighlight } from './replay/highlight';
import { gameLogEntries, type GameLogEntry } from './components/GameLog';

/** Keys `ResearchBoard` marks tokens with (`ResearchTracks` fields), not the wire track names. */
const RESEARCH_HIGHLIGHT_KEY: Record<ResearchTrack, string> = {
  Terraforming: 'terraforming',
  Navigation: 'navigation',
  ArtificialIntelligence: 'ai',
  GaiaProject: 'gaia',
  Economy: 'economy',
  Science: 'science',
};

/** `ShipExplored` carries the ship's index; the boards are keyed by name. */
const SHIP_BY_INDEX: SpaceshipId[] = ['Twilight', 'Rebellion', 'TFMars', 'Eclipse'];

export interface TurnStatus {
  text: string;
  /** True when the viewing player is the one who has to act. */
  mine: boolean;
  hint?: string;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function payloadFor(event: GameEvent, tag: string): Record<string, unknown> | null {
  return asRecord(asRecord(event)?.[tag]);
}

/** Board highlight keys are `q,r`; events carry either that string or a `{ q, r }` coordinate. */
function hexKey(value: unknown): string | null {
  if (typeof value === 'string') return /^-?\d+,-?\d+$/.test(value) ? value : null;
  const hex = asRecord(value);
  return hex && typeof hex.q === 'number' && typeof hex.r === 'number' ? `${hex.q},${hex.r}` : null;
}

function tileId(value: unknown): number | null {
  if (typeof value === 'number') return value;
  const first = Object.values(asRecord(value) ?? {})[0];
  return typeof first === 'number' ? first : null;
}

export function liveActionEntries(
  events: GameEvent[] | undefined,
  players: PlayerState[],
  board?: BoardState | null,
): GameLogEntry[] {
  return gameLogEntries(events ?? [], players, board);
}

/**
 * Reuses the replay highlight contract for live play: the pieces one completed action touched,
 * so the same board/card markers light up after an opponent moves instead of only during replays.
 * `entry.index` is the first event of that action's group, which runs until its `ActionLog` marker.
 */
export function liveHighlight(
  events: GameEvent[] | undefined,
  entry: GameLogEntry | null,
): ReplayHighlight | null {
  if (!entry || !events) return null;

  const markerOffset = events
    .slice(entry.index)
    .findIndex((event) => payloadFor(event, 'ActionLog') !== null);
  const group = events.slice(entry.index, markerOffset === -1 ? undefined : entry.index + markerOffset);
  if (group.length === 0) return null;

  const hexes = new Set<string>();
  const research = new Set<string>();
  const standardTech = new Set<number>();
  const advancedTech = new Set<number>();
  let ship: string | null = null;
  let booster: number | null = null;
  // The event log records a power action's effects but not which board slot was taken, so that
  // marker stays off in live play; the replay feed sets it from the action itself.
  const powerAction = null;

  for (const event of group) {
    const tag = Object.keys(event)[0] ?? '';
    const payload = payloadFor(event, tag);
    if (!payload) continue;

    for (const key of ['hex', 'first', 'second', 'coord']) {
      const found = hexKey(payload[key]);
      if (found) hexes.add(found);
    }
    if (tag === 'ResearchAdvanced' && typeof payload.track === 'string') {
      const key = RESEARCH_HIGHLIGHT_KEY[payload.track as ResearchTrack];
      if (key) research.add(key);
    }
    if (tag === 'TechTileGained') {
      const id = tileId(payload.tile);
      if (id !== null) standardTech.add(id);
    }
    if (tag === 'AdvancedTechTileGained') {
      const id = tileId(payload.tile);
      if (id !== null) advancedTech.add(id);
    }
    if (tag === 'ShipExplored') {
      const index = payload.ship_id;
      ship = typeof index === 'number' ? SHIP_BY_INDEX[index] ?? null : null;
    }
    if (tag === 'PlayerPassed' || tag === 'BoosterSelected') {
      const id = tileId(payload.booster);
      booster = id;
    }
  }

  return {
    player: entry.player,
    faction: null,
    standardTech,
    advancedTech,
    actionType: '',
    label: entry.text,
    hexes,
    research,
    powerAction,
    ship,
    booster,
  };
}

interface PendingLabel {
  text: string;
  hint?: string;
}

function pendingLabel(phase: GamePhase): PendingLabel {
  if (typeof phase !== 'object' || phase === null) return { text: '결정' };
  if ('ChargePowerPending' in phase || 'LostPlanetChargePowerPending' in phase) {
    return { text: '파워 충전 여부 선택', hint: '충전을 받으면 충전량보다 1 적은 만큼 승점을 냅니다.' };
  }
  if ('IncomeOrderPending' in phase) {
    return { text: '수입 순서 선택', hint: '새 파워 토큰을 받기 전에 충전할지, 받은 뒤에 충전할지 고릅니다.' };
  }
  if ('GaiaDecisionPending' in phase) return { text: '가이아 단계 선택' };
  if ('TinkeroidsTileSelectionPending' in phase) return { text: '팅커링 타일 선택' };
  if ('LostPlanetPlacementPending' in phase) return { text: '검은 행성 배치' };
  return { text: '결정' };
}

function setupLabel(setup: Extract<GamePhase, { Setup: unknown }>['Setup']): {
  player: PlayerId | null;
  text: string;
} | null {
  if (setup === 'Complete') return null;
  if ('FactionSelection' in setup) {
    return { player: setup.FactionSelection.active_player, text: '종족 선택' };
  }
  if ('Bidding' in setup) return { player: setup.Bidding.active_player, text: '입찰' };
  if ('BiddingChoice' in setup) return { player: setup.BiddingChoice.winner, text: '종족·순서 선택' };
  if ('StartingStructures' in setup) {
    return { player: setup.StartingStructures.active_player, text: '시작 건물 배치' };
  }
  if ('StartingBoosters' in setup) {
    return { player: setup.StartingBoosters.active_player, text: '시작 부스터 선택' };
  }
  return null;
}

/** One sentence for the banner: who acts now, and what the viewing player must do. */
export function turnStatus(state: GameState, myPlayerId: PlayerId): TurnStatus | null {
  const nameOf = (id: PlayerId) =>
    state.players.find((player) => player.player_id === id)?.nickname ?? `플레이어 ${id}`;
  const phase = state.phase;

  if (phase === 'IncomePhase') return { text: '수입 단계 진행 중', mine: false };
  if (phase === 'GaiaPhase') return { text: '가이아 단계 진행 중', mine: false };
  if (phase === 'GaiaformingPhase') return { text: '가이아포밍 단계 진행 중', mine: false };
  if (phase === 'FinalScoring') return { text: '최종 점수 계산 중', mine: false };

  if (typeof phase === 'object' && phase !== null) {
    if ('Ended' in phase) return { text: '게임이 끝났습니다', mine: false };
    if ('RoundScoring' in phase) {
      return { text: `${phase.RoundScoring.round}라운드 정산 중`, mine: false };
    }
    if ('Setup' in phase) {
      const setup = setupLabel(phase.Setup);
      if (setup && setup.player !== null) {
        return setup.player === myPlayerId
          ? { text: `내 차례: ${setup.text}`, mine: true }
          : { text: `${nameOf(setup.player)}님 ${setup.text} 중 — 기다리는 중`, mine: false };
      }
    }
  }

  const pending = pendingDecisionPlayerId(phase);
  if (pending !== null) {
    const label = pendingLabel(phase);
    return pending === myPlayerId
      ? { text: `내 차례: ${label.text}`, mine: true, hint: label.hint }
      : { text: `${nameOf(pending)}님이 ${label.text} 중 — 기다리는 중`, mine: false };
  }

  const active = activeActionPlayerId(state);
  if (active === null) return null;
  return active === myPlayerId
    ? {
      text: '내 차례입니다',
      mine: true,
      hint: '주요 행동 1개를 고르면 차례가 넘어갑니다. 자유 행동(자원 교환)은 그 전에 여러 번 할 수 있어요.',
    }
    : { text: `${nameOf(active)}님 차례 — 기다리는 중`, mine: false };
}
