import { FINAL_SCORING_LABELS, finalScoringMetric } from '../finalScoring';
import type { GameEvent, GameState, PlayerId } from '../types/game';
import type { RewardBatch } from '../components/RewardMotion/rewards';
import type { ReplayFrame, ReplayRecord } from './records';
import { adjacentReplayFrame } from './stepping';

interface RankedAward { player: PlayerId; metric: number; rank: number; tied: boolean; amount: number }
export interface SettlementAward { player: PlayerId; amount: number; total: number; detail: string }
export interface SettlementStep {
  kind: 'goal' | 'research' | 'resources' | 'ranking';
  title: string;
  awards: SettlementAward[];
  eventStart: number;
  eventEnd: number;
}
export interface ReplaySettlement { steps: SettlementStep[]; events: GameEvent[]; warning?: string }

/** Pool every occupied rank before dividing, including zero-valued ties. */
export function rankAwards(metrics: number[], points: number[]): RankedAward[] {
  const ranked = metrics.map((metric, player) => ({ player, metric, rank: 0, tied: false, amount: 0 }))
    .sort((a, b) => b.metric - a.metric || a.player - b.player);
  for (let i = 0; i < ranked.length;) {
    let end = i + 1;
    while (end < ranked.length && ranked[end].metric === ranked[i].metric) end++;
    const amount = Math.floor(points.slice(i, end).reduce((sum, value) => sum + value, 0) / (end - i));
    for (let k = i; k < end; k++) Object.assign(ranked[k], { rank: i + 1, tied: end - i > 1, amount });
    i = end;
  }
  return ranked;
}

const TRACKS = [
  ['terraforming', '테라포밍'], ['navigation', '항해'], ['ai', '인공지능'],
  ['gaia', '가이아'], ['economy', '경제'], ['science', '지식'],
] as const;

/** Presentation only: five positions after the native final action, never saved frames.
 * Existing metric fixtures mirror Rust; native terminal totals guard the whole calculation.
 * An unsupported scoring change leaves the original replay usable, without invented awards. */
export function buildReplaySettlement(record: ReplayRecord): ReplaySettlement {
  const last = record.frames[record.frames.length - 1];
  const phase = last?.state.phase;
  if (!phase || typeof phase !== 'object' || !('Ended' in phase)) return { steps: [], events: record.events };
  const unavailable = (): ReplaySettlement => ({ steps: [], events: record.events,
    warning: '정산 내역이 기록된 최종 점수와 일치하지 않아 항목별 표시를 생략합니다.' });
  // Formation decisions also cover older records without reconstructed event logs.
  const formations = record.frames.flatMap(frame => frame.action?.type === 'FormFederation'
    ? [{ ReplayDecision: { player: frame.player, action: frame.action } }] : []);
  const state = { ...last.state, event_log: [...record.events, ...formations] };
  if (state.round !== 6 || state.final_scoring_tiles.length !== 2
    || !Array.isArray(phase.Ended?.final_scores) || phase.Ended.final_scores.length !== 4
    || phase.Ended.final_scores.some(pair => !Array.isArray(pair) || pair.length !== 2
      || !Number.isSafeInteger(pair[0]) || !Number.isSafeInteger(pair[1]))) return unavailable();
  const finalScores = new Map(phase.Ended.final_scores);
  if (finalScores.size !== 4 || state.players.some(p => !Number.isSafeInteger(finalScores.get(p.player_id)))) return unavailable();
  const totals = state.players.map(p => p.vp);
  const steps: SettlementStep[] = [];
  const events = [...record.events];
  function append(kind: SettlementStep['kind'], title: string, awards: Omit<SettlementAward, 'total'>[]) {
    const eventStart = events.length;
    const rows = awards.map(award => {
      totals[award.player] += award.amount;
      return { ...award, total: totals[award.player] };
    });
    events.push(...rows.map(award => ({ ReplaySettlement: { title, ...award } })));
    steps.push({ kind, title, awards: rows, eventStart, eventEnd: events.length });
  }
  for (const [index, tile] of state.final_scoring_tiles.entries()) {
    const metrics = state.players.map(p => finalScoringMetric(state, p.player_id, tile.condition));
    if (metrics.some(value => !Number.isSafeInteger(value) || value < 0)) return unavailable();
    const ranked = rankAwards(metrics, [tile.vp_1st, tile.vp_2nd, tile.vp_3rd, 0]);
    append('goal', `종료 목표 ${index + 1} · ${FINAL_SCORING_LABELS[tile.condition]}`, ranked.map(a => ({
      player: a.player, amount: a.amount, detail: `${a.tied ? '공동 ' : ''}${a.rank}위 · 달성 ${a.metric}`,
    })));
  }
  append('research', '연구 정산', state.players.map(p => {
    const tracks = TRACKS.map(([key, label]) => ({ label, level: p.research_tracks[key],
      amount: Math.max(0, Math.min(3, p.research_tracks[key] - 2)) * 4 }));
    return { player: p.player_id, amount: tracks.reduce((sum, t) => sum + t.amount, 0),
      detail: tracks.filter(t => t.amount > 0).map(t => `${t.label} ${t.level}단계 ${t.amount}점`).join(' + ') || '3단계 이상 연구 없음' };
  }));
  append('resources', '잔여 자원 정산', state.players.map(p => {
    const { ore, credits, knowledge } = p.resources;
    const sum = ore + credits + knowledge;
    return { player: p.player_id, amount: Math.floor(sum / 3),
      detail: `광석 ${ore} + 크레딧 ${credits} + 지식 ${knowledge} = ${sum} · 3개당 1점` };
  }));
  // Current native faction hooks award zero here. Never hide a future hook or a
  // mismatched metric as an unexplained adjustment: reject the breakdown instead.
  if (state.players.some(p => totals[p.player_id] - (p.setup_bid_vp ?? 0) !== finalScores.get(p.player_id))) return unavailable();
  const ranking = rankAwards(state.players.map(p => finalScores.get(p.player_id)!), [0, 0, 0, 0]);
  append('ranking', '최종 순위', ranking.map(a => {
    const bid = state.players[a.player].setup_bid_vp ?? 0;
    return { player: a.player, amount: bid ? -bid : 0,
      detail: `${a.tied ? '공동 ' : ''}${a.rank}위${bid ? ` · 입찰 감점 −${bid}점` : ''}` };
  }));
  return { steps, events };
}

export function settlementState(state: GameState, step: SettlementStep): GameState {
  const totals = new Map(step.awards.map(a => [a.player, a.total]));
  return { ...state, players: state.players.map(p => ({ ...p, vp: totals.get(p.player_id) ?? p.vp })) };
}

export function settlementRewards(step: SettlementStep, id: number): RewardBatch[] {
  return step.awards.filter(a => a.amount !== 0).map(a => ({ id, player: a.player,
    gains: a.amount > 0 ? [{ kind: 'vp', amount: a.amount }] : [],
    costs: a.amount < 0 ? [{ kind: 'vp', amount: -a.amount }] : [],
  }));
}

/** The final pass and settlement belong to everyone, even with a faction filter. */
export function adjacentReplayPosition(frames: readonly ReplayFrame[], cursor: number,
  direction: -1 | 1, player: PlayerId | null, settlementCount: number): number | null {
  const last = frames.length - 1;
  if (cursor > last) {
    if (direction < 0) return cursor - 1;
    return cursor < last + settlementCount ? cursor + 1 : null;
  }
  const next = adjacentReplayFrame(frames, cursor, direction, player);
  if (next !== null || direction < 0 || !settlementCount) return next;
  return cursor < last ? last : last + 1;
}
