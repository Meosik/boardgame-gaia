import { decodeHexCoordinates } from '../../api/websocket';
import { hexLocationLabel } from '../../hexLocation';
import { ACTION_NAMES } from '../../replay/records';
import type { GameState } from '../../types/game';

export interface Candidate { phase: string; action: { type: string; [key: string]: unknown } }
export interface CoachState {
  schema: 1;
  token: string;
  session_id: string;
  status: 'waiting' | 'thinking' | 'ready' | 'error' | 'complete';
  snapshot: { decision_id: number; steps: number; player: number | null; state: GameState; candidates: Candidate[] };
  recommendation: { index: number; scores: { value: number; reason: string; excluded: boolean }[];
    audit: { ranking_mode?: string; value_model?: string; selected?: string; timing?: { seconds?: number } } } | null;
  error: string | null;
  config: { seed: string; delta_factions: string[];
    clock?: { target_seconds: number; long_seconds: number; uses_per_seat: number } };
  recorded: number;
  corrections: number;
  last_feedback: { controller: string; reason: string; plan: string; player: number; decision_id: number } | null;
}

export function parseCoach(value: unknown): CoachState {
  const data = value as CoachState;
  if (!data || data.schema !== 1 || typeof data.token !== 'string' || typeof data.session_id !== 'string'
    || !['waiting', 'thinking', 'ready', 'error', 'complete'].includes(data.status)
    || !data.snapshot || !Number.isSafeInteger(data.snapshot.decision_id)
    || !Array.isArray(data.snapshot.candidates) || data.snapshot.state?.players?.length !== 4
    || !data.snapshot.candidates.every(c => c?.action && typeof c.action.type === 'string')) {
    throw new Error('교정 대국 응답을 확인할 수 없습니다.');
  }
  const rec = data.recommendation;
  if ((data.status === 'ready' && !rec) || (rec && (!Number.isInteger(rec.index) || rec.index < 0
    || rec.index >= data.snapshot.candidates.length || rec.scores.length !== data.snapshot.candidates.length
    || rec.scores.some(s => !Number.isFinite(s.value) || typeof s.reason !== 'string')))) {
    throw new Error('현재 결정과 AI 평가가 일치하지 않습니다.');
  }
  // Decode only game coordinates, never the human's explanation text.
  return { ...data, snapshot: decodeHexCoordinates(data.snapshot) as CoachState['snapshot'] };
}

const VALUES: Record<string, string> = {
  Mine: '광산', TradingStation: '교역소', ResearchLab: '연구소', PlanetaryInstitute: '행성의회',
  Academy: '아카데미', GaiaFormer: '가이아포머', Terraforming: '테라포밍', Navigation: '항해',
  ArtificialIntelligence: '인공지능', GaiaProject: '가이아포밍', Gaiaforming: '가이아포밍', Economy: '경제', Science: '과학',
  Rebellion: '리벨리온', TFMars: 'TF마스', Twilight: '트와일라잇', Eclipse: '이클립스',
  Standard: '일반 기술', Advanced: '고급 기술', LostFleetAdvanced: '함대 고급 기술',
  OreToCredit: '광석→돈', KnowledgeToCredit: '지식→돈', QicToOre: 'QIC→광석',
  PowerToCredit: '파워→돈', PowerToOre: '파워→광석', PowerToKnowledge: '파워→지식',
  PowerToQic: '파워→QIC', BurnPower: '파워 소각', OreToPowerBowl3: '광석→3구역 토큰',
  TaklonsChargePower: '타클론 파워 충전',
};
const KEYS: Record<string, string> = {
  coord: '위치', to: '건물', kind: '종류', track: '트랙', advance_track: '연구', count: '횟수',
  booster_id: '부스터', tech_tile_choice: '기술 선택', tile: '타일', choice: '선택', pool: '종류',
  covered_tile: '덮을 기술', ship: '함선', power_amount: '충전량', amount: '양', accept: '수락',
  id: '번호', bonus_build_coord: '추가 광산', bonus_tech_tile: '추가 기술',
  satellite_hexes: '위성', building_hexes: '건물', token: '연방 토큰', token_id: '연방 토큰',
};

export function candidateLabel(candidate: Candidate, state: GameState): string {
  const tile = candidate.action.tile;
  if (candidate.action.type === 'TechTileSpecialAction' && tile && typeof tile === 'object'
    && 'pool' in tile && tile.pool === 'Standard' && 'tile' in tile && tile.tile === 10) {
    return '파워 4 충전 · 일반 10번 기술 행동';
  }
  function format(value: unknown): string {
    if (value === null) return '없음';
    if (typeof value === 'boolean') return value ? '예' : '아니오';
    if (typeof value === 'string') return VALUES[value] ?? value;
    if (typeof value !== 'object') return String(value);
    if (Array.isArray(value)) return value.map(format).join(', ');
    const object = value as Record<string, unknown>;
    if (typeof object.q === 'number' && typeof object.r === 'number') {
      return `${hexLocationLabel({ q: object.q, r: object.r }, state.board)} (${object.q},${object.r})`;
    }
    return Object.entries(object).filter(([, v]) => v !== null).map(([k, v]) =>
      `${KEYS[k] ?? VALUES[k] ?? k}: ${format(v)}`).join(' / ');
  }
  const { type, ...detail } = candidate.action;
  const text = format(detail);
  return `${ACTION_NAMES[type] ?? VALUES[type] ?? type}${text ? ` · ${text}` : ''}`;
}
