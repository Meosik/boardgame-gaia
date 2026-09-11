import { decodeHexCoordinates } from '../api/websocket';
import type { GameEvent, GameState, PlayerId } from '../types/game';

export interface ReplayGame {
  id: string;
  file: string;
  policy: string;
  faction: string;
  seed: string;
  vp: number;
  steps: number;
}
export interface ReplayFrame {
  decision_id: number;
  player: PlayerId | null;
  action: { type: string; [key: string]: unknown } | null;
  legal_action_count: number;
  legal_federation_count: number;
  event_end: number;
  state: GameState;
}
export interface ReplayRecord {
  schema_version: 1;
  metadata: { focus_player: PlayerId; seed: string; policy: string; faction: string; steps: number; versions: Record<string, unknown> };
  events: GameEvent[];
  frames: ReplayFrame[];
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function integer(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0;
}

export function parseCatalog(value: unknown): ReplayGame[] {
  if (!record(value) || value.schema_version !== 1 || !Array.isArray(value.games)) throw new Error('지원하지 않는 리플레이 목록입니다.');
  const ids = new Set<string>();
  for (const game of value.games) {
    if (!record(game) || typeof game.id !== 'string' || ids.has(game.id) || typeof game.file !== 'string'
      || !/^[a-z0-9_-]+\.json\.gz$/.test(game.file) || typeof game.policy !== 'string'
      || typeof game.faction !== 'string' || typeof game.seed !== 'string' || !integer(game.steps)
      || typeof game.vp !== 'number' || !Number.isFinite(game.vp)) throw new Error('잘못된 리플레이 목록입니다.');
    ids.add(game.id);
  }
  return value.games as ReplayGame[];
}

function validState(value: unknown): boolean {
  if (!record(value) || !integer(value.round) || value.round > 6 || !Array.isArray(value.players) || value.players.length !== 4
    || !record(value.board) || !record(value.board.hexes) || !Array.isArray(value.board.sectors)
    || !record(value.board.spaceship_tiles) || !record(value.research_board) || !record(value.research_board.tracks)
    || !Array.isArray(value.spaceship_boards) || value.phase == null) return false;
  const arrays = ['round_tiles', 'final_scoring_tiles', 'boosters', 'turn_order', 'pass_order', 'used_power_actions', 'used_spaceship_actions'];
  if (arrays.some(key => !Array.isArray(value[key]))) return false;
  const players = value.players;
  return players.every((p: unknown, index: number) => record(p) && p.player_id === index
    && typeof p.nickname === 'string' && record(p.resources) && record(p.resources.power)
    && record(p.research_tracks) && ['structures', 'artifacts', 'federation_tokens', 'tech_tiles', 'advanced_tech_tiles',
      'covered_tech_tiles', 'explored_ships', 'federated_hexes'].every(key => Array.isArray(p[key])));
}

export function parseReplay(value: unknown): ReplayRecord {
  const decoded = decodeHexCoordinates(value);
  if (!record(decoded) || decoded.schema_version !== 1 || !record(decoded.metadata)
    || !integer(decoded.metadata.focus_player) || decoded.metadata.focus_player > 3
    || !integer(decoded.metadata.steps) || !record(decoded.metadata.versions)
    || !Array.isArray(decoded.events) || !Array.isArray(decoded.frames)
    || decoded.frames.length !== decoded.metadata.steps + 1 || decoded.frames.length === 0) throw new Error('지원하지 않거나 손상된 리플레이입니다.');
  let end = 0;
  for (const [index, frame] of decoded.frames.entries()) {
    if (!record(frame) || frame.decision_id !== index || !integer(frame.event_end)
      || frame.event_end < end || frame.event_end > decoded.events.length || !validState(frame.state)
      || !integer(frame.legal_action_count) || !integer(frame.legal_federation_count)
      || frame.legal_federation_count > frame.legal_action_count
      || (index === 0 ? frame.action !== null || frame.player !== null
        : !record(frame.action) || typeof frame.action.type !== 'string' || !integer(frame.player) || frame.player > 3)) {
      throw new Error(`리플레이 ${index}번째 기록이 올바르지 않습니다.`);
    }
    end = frame.event_end;
  }
  if (end !== decoded.events.length) throw new Error('리플레이 종료 로그가 일치하지 않습니다.');
  return decoded as unknown as ReplayRecord;
}

/** An event belongs to the earliest post-action frame that contains it. */
export function frameForEvent(frames: ReplayFrame[], eventIndex: number): number {
  const found = frames.findIndex(frame => frame.event_end > eventIndex);
  return found < 0 ? frames.length - 1 : found;
}

export async function loadReplay(file: string, signal: AbortSignal): Promise<ReplayRecord> {
  if (!/^[a-z0-9_-]+\.json\.gz$/.test(file)) throw new Error('잘못된 리플레이 파일 경로입니다.');
  const response = await fetch(`/ai-replays/${file}`, { signal });
  if (!response.ok || !response.body) throw new Error('리플레이 파일을 불러오지 못했습니다.');
  if (typeof DecompressionStream === 'undefined') throw new Error('이 브라우저는 압축 리플레이를 지원하지 않습니다. 최신 브라우저로 열어 주세요.');
  const raw: unknown = await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).json();
  return parseReplay(raw);
}

export const POLICY_NAMES: Record<string, string> = {
  baseline: '일반 PPO', imitation_plus_ppo: '시범학습 + PPO', teacher: '교사 전략',
  continued_ppo: 'PPO 추가 학습', bc_only: '개선 시범학습만', economy_bc_ppo: '개선 시범학습 + PPO',
};
export const ACTION_NAMES: Record<string, string> = {
  PlaceStartingStructure: '초기 건물 배치', SelectStartingBooster: '초기 부스터 선택', Build: '광산 건설',
  Upgrade: '건물 업그레이드', ResearchAdvance: '연구 진전', FormFederation: '연방 형성', FreeAction: '자원 변환',
  ChargePower: '파워 충전 선택', Pass: '패스', ExploreSpaceship: '함선 탐사', PowerAction: '파워 행동',
  TechTileSpecialAction: '기술 타일 행동', AcademyQicAction: '아카데미 행동', ExamineArtifact: '아티팩트 획득',
  SpaceshipCreditTerraform: 'TF마스 테라포밍 건설', TwilightRangeBuild: '트와일라잇 사거리 건설',
  TwilightRangeExploreSpaceship: '트와일라잇 사거리 탐사', RebellionGainTechTile: '리벨리온 기술 획득',
  RebellionCreditsAndQic: '리벨리온 크레딧·정보 큐브', RebellionFreeTradingStation: '리벨리온 교역소 건설',
  TwilightFreeResearchLab: '트와일라잇 연구소 건설', TFMarsTechBonus: 'TF마스 기술 득점',
  EclipsePlanetTypeBonus: '이클립스 행성 종류 득점', ChooseIncomeOrder: '수입 순서 선택',
  GaiaFormation: '가이아포밍', PlaceLostPlanet: '검은 행성 배치',
  EclipseAsteroidMine: '이클립스 소행성 광산', EclipseResearchBoost: '이클립스 연구 진전',
  RoundBoosterImmediateGaiaFormation: '부스터 즉시 가이아포밍', RoundBoosterRangeBuild: '부스터 사거리 건설',
  RoundBoosterRangeExploreSpaceship: '부스터 사거리 탐사', RoundBoosterRangeGaiaFormation: '부스터 사거리 가이아포밍',
  TwilightRangeGaiaFormation: '트와일라잇 사거리 가이아포밍', TwilightReplayFederationToken: '트와일라잇 연방 효과 복사',
};
