import type { GameEvent, GameState } from '../../types/game';

export type RewardKind = 'ore' | 'credits' | 'knowledge' | 'qic' | 'vp';
export interface RewardGain { kind: RewardKind; amount: number }
export interface RewardBatch {
  id: number;
  player: number;
  gains: RewardGain[];
  costs?: RewardGain[];
  hex?: { q: number; r: number };
  origin?: { x: number; y: number };
}
function object(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

/** Fresh appended gains and costs only; never restored history or inferred power-bowl changes. */
export function resourceMotionBatch(before: GameState | null, after: GameState, player: number): Omit<RewardBatch, 'id' | 'origin'> | null {
  if (!before || before.round === 0 || after.round === 0) return null;
  const old = before.event_log ?? [];
  const next = after.event_log ?? [];
  if (next.length <= old.length || old.some((event, index) => JSON.stringify(event) !== JSON.stringify(next[index]))) return null;
  const gains: Record<RewardKind, number> = { ore: 0, credits: 0, knowledge: 0, qic: 0, vp: 0 };
  const spent = { ore: 0, credits: 0, knowledge: 0, qic: 0 };
  let hex: RewardBatch['hex'];
  function add(payload: Record<string, unknown>, keys: RewardKind[]) {
    for (const kind of keys) {
      const amount = payload[kind];
      if (typeof amount === 'number' && Number.isFinite(amount) && amount > 0) gains[kind] += amount;
    }
  }
  for (const event of next.slice(old.length) as GameEvent[]) {
    for (const [tag, raw] of Object.entries(event)) {
      const payload = object(raw);
      if (!payload || payload.player !== player) continue;
      if (tag === 'ResourceChanged') {
        const delta = object(payload.delta) ?? {};
        add(delta, ['ore', 'credits', 'knowledge', 'qic']);
        for (const kind of Object.keys(spent) as (keyof typeof spent)[]) {
          if (typeof delta[kind] === 'number' && Number.isFinite(delta[kind]) && Number(delta[kind]) < 0) spent[kind] -= Number(delta[kind]);
        }
      }
      if (tag === 'IncomeReceived') add(payload, ['ore', 'credits', 'knowledge', 'qic', 'vp']);
      if (tag === 'VpAwarded') add({ vp: payload.amount }, ['vp']);
      if (['StructureBuilt', 'StructureUpgraded', 'GaiaFormingStarted'].includes(tag)) {
        const coord = object(payload.hex);
        if (coord && Number.isInteger(coord.q) && Number.isInteger(coord.r)) hex = { q: Number(coord.q), r: Number(coord.r) };
      }
    }
  }
  const oldPlayer = before.players.find(p => p.player_id === player);
  const newPlayer = after.players.find(p => p.player_id === player);
  if (!oldPlayer || !newPlayer) return null;
  // Some engine receipts describe nominal rewards; only animate what fits after caps/costs.
  for (const kind of Object.keys(spent) as (keyof typeof spent)[]) {
    gains[kind] = Math.min(gains[kind], Math.max(0, newPlayer.resources[kind] - oldPlayer.resources[kind] + spent[kind]));
  }
  const result = (Object.keys(gains) as RewardKind[]).filter(kind => gains[kind] > 0).map(kind => ({ kind, amount: gains[kind] }));
  const costs: RewardGain[] = (Object.keys(spent) as (keyof typeof spent)[])
    .filter(kind => spent[kind] > 0).map(kind => ({ kind, amount: spent[kind] }));
  const vpPaid = Math.max(0, oldPlayer.vp + gains.vp - newPlayer.vp);
  if (vpPaid > 0) costs.push({ kind: 'vp', amount: vpPaid });
  return result.length || costs.length ? { player, gains: result, ...(costs.length ? { costs } : {}), hex } : null;
}
