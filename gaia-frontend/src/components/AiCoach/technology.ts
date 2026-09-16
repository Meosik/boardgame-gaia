import type { GameState } from '../../types/game';
import { candidateLabel, type Candidate } from './protocol';
import { ADVANCED_TECH_TILE_LABELS } from '../advancedTechDescriptions';

export const TRACKS = ['Terraforming', 'Navigation', 'ArtificialIntelligence', 'GaiaProject', 'Economy', 'Science'];
export const TRACK_NAMES: Record<string, string> = {
  Terraforming: '테라포밍', Navigation: '항해', ArtificialIntelligence: '인공지능',
  GaiaProject: '가이아포밍', Economy: '경제', Science: '과학', none: '연구 진행 안 함',
};
const TECH_NAMES: Record<number, string> = {
  2: '수입 광석 1·파워 충전 1', 3: '수입 크레딧 4', 4: '즉시 광석 1·QIC 1',
  5: '수입 지식 1·크레딧 1', 6: '의회·아카데미 파워 가치 증가', 7: '즉시 7점',
  8: '가이아 광산 건설 시 3점', 9: '즉시 행성 종류당 지식 1', 10: '행동 파워 충전 4',
  11: '무료 광산·테라포밍 최대 2단계', 12: '기본 사거리 1 증가', 13: '즉시 광석 1·지식 3',
};
type Choice = { kind: string; tile?: number; track?: string; covered_tile?: number;
  advance_track?: string | null; bonus_build_coord?: unknown };

function choice(candidate: Candidate): Choice | null | undefined {
  const a = candidate.action;
  if (['RebellionGainTechTile', 'ItarsGaiaTechTile'].includes(a.type)) return { kind: 'Standard', tile: a.tile as number,
    advance_track: a.track as string, bonus_build_coord: a.bonus_build_coord };
  if (a.bonus_tech_tile != null) return { kind: 'Standard', tile: a.bonus_tech_tile as number,
    advance_track: a.bonus_research_track as string | null, bonus_build_coord: a.bonus_build_coord };
  if ('tech_tile_choice' in a) return a.tech_tile_choice as Choice | null;
  if (a.choice && typeof a.choice === 'object' && 'kind' in a.choice
    && ['Standard', 'Advanced', 'LostFleetAdvanced'].includes(String(a.choice.kind))) return a.choice as Choice;
  return undefined;
}

export function baseCandidate(candidate: Candidate): Candidate {
  const action = { ...candidate.action };
  if (['RebellionGainTechTile', 'ItarsGaiaTechTile'].includes(action.type)) {
    delete action.tile; delete action.track; delete action.bonus_build_coord;
  } else if (action.bonus_tech_tile != null) {
    delete action.bonus_tech_tile; delete action.bonus_research_track; delete action.bonus_build_coord;
  } else if ('tech_tile_choice' in action) delete action.tech_tile_choice;
  else if (choice(candidate) !== undefined) delete action.choice;
  return { ...candidate, action };
}

function canonical(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  return `{${Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${JSON.stringify(k)}:${canonical(v)}`).join(',')}}`;
}

export interface TechVariant {
  index: number; tileKey: string; tileLabel: string; tileId: number | null;
  advanced: boolean; fixedTrack: boolean; track: string; candidate: Candidate;
}
export function technologyVariants(candidates: Candidate[], index: number, state: GameState): TechVariant[] {
  const selected = candidates[index];
  if (!selected || choice(selected) === undefined) return [];
  const key = canonical(baseCandidate(selected));
  const same = candidates.map((candidate, index) => ({ candidate, index }))
    .filter(v => canonical(baseCandidate(v.candidate)) === key);
  if (!same.some(v => choice(v.candidate))) return [];
  return same.map(({ candidate, index }) => {
    const c = choice(candidate);
    if (!c) return { index, candidate, tileKey: 'none', tileLabel: '기술 획득 안 함', tileId: null,
      advanced: false, fixedTrack: true, track: 'none' };
    const advanced = c.kind !== 'Standard';
    const tileId = (c.kind === 'Standard' ? c.tile : c.kind === 'Advanced'
      ? state.research_board.advanced_tech_tiles[TRACKS.indexOf(c.track!)]
      : state.research_board.lost_fleet_advanced_tech_tile) ?? null;
    const slot = advanced ? -1 : (state.research_board.tech_tile_slots ?? []).indexOf(tileId);
    const fixedTrack = slot >= 0 && slot < 6;
    const track = fixedTrack ? TRACKS[slot] : c.advance_track ?? 'none';
    const tileKey = canonical({ kind: c.kind, tile: tileId, covered: c.covered_tile ?? null });
    const description = tileId === null ? '' : advanced ? ADVANCED_TECH_TILE_LABELS[tileId] : TECH_NAMES[tileId];
    const tileLabel = `${advanced ? '고급' : '일반'} ${tileId}번 · ${description ?? ''}`
      + (c.covered_tile != null ? ` · ${c.covered_tile}번 덮기` : '');
    return { index, candidate, tileKey, tileLabel, tileId, advanced, fixedTrack, track };
  });
}

export interface TechnologySelection { tileKey: string; track: string; detail: number | null }
export const EMPTY_TECHNOLOGY: TechnologySelection = { tileKey: '', track: '', detail: null };
export function resolveTechnology(variants: TechVariant[], selected: TechnologySelection): number | null {
  const tiles = variants.filter(v => v.tileKey === selected.tileKey);
  if (!tiles.length) return null;
  const tracks = tiles.filter(v => v.fixedTrack || v.track === selected.track);
  if (tracks.length === 1) return tracks[0].index;
  return tracks.find(v => v.index === selected.detail)?.index ?? null;
}

export function groupedChoices(candidates: Candidate[], state: GameState, scores: number[], recommendation: number) {
  const result: { index: number; indices: number[]; label: string; technology: boolean }[] = [];
  const seen = new Map<string, number>();
  for (let i = 0; i < candidates.length; i++) {
    const key = canonical(baseCandidate(candidates[i]));
    const old = seen.get(key);
    if (old !== undefined) { result[old].indices.push(i); continue; }
    seen.set(key, result.length);
    result.push({ index: i, indices: [i], label: '', technology: false });
  }
  for (const group of result) {
    group.index = group.indices.includes(recommendation) ? recommendation
      : group.indices.reduce((a, b) => scores[b] > scores[a] ? b : a);
    group.technology = technologyVariants(candidates, group.index, state).length > 0;
    group.label = candidateLabel(group.technology ? baseCandidate(candidates[group.index]) : candidates[group.index], state)
      + (group.technology ? ' · 기술 직접 선택' : '');
  }
  return result;
}

export function technologySummary(candidate: Candidate, state: GameState): string {
  const c = choice(candidate);
  if (!c) return '';
  const variant = technologyVariants([candidate], 0, state)[0];
  return variant ? `${variant.tileLabel} → ${TRACK_NAMES[variant.track] ?? variant.track}${variant.fixedTrack ? ' (연결 트랙 고정)' : ' (직접 선택)'}` : '';
}
