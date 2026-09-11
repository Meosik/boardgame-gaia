import type { RewardBatch, RewardGain, RewardKind } from '../components/RewardMotion/rewards';
import type { ReplayRecord } from './records';

const KINDS: RewardKind[] = ['ore', 'credits', 'knowledge', 'qic', 'vp'];

/** Historical records contain net changes, not complete cost/reward receipts. Animate only
 * observed deltas, splitting out verified income when available; never infer power charges. */
export function replayRewardBatches(record: ReplayRecord, cursor: number, id: number): RewardBatch[] {
  const before = record.frames[cursor - 1];
  const after = record.frames[cursor];
  if (!before || !after || after.state.round === 0) return [];
  const events = record.events.slice(before.event_end, after.event_end);
  return after.state.players.flatMap(player => {
    const old = before.state.players.find(p => p.player_id === player.player_id);
    if (!old) return [];
    const income: Partial<Record<RewardKind, number>> = {};
    for (const event of events) {
      if (!('IncomeReceived' in event)) continue;
      const receipt = event.IncomeReceived as { player?: number } & Partial<Record<RewardKind, number>> | undefined;
      if (receipt?.player !== player.player_id) continue;
      for (const kind of KINDS) {
        const value = receipt[kind];
        if (typeof value === 'number' && Number.isFinite(value) && value > 0) income[kind] = (income[kind] ?? 0) + value;
      }
    }
    const gains: RewardGain[] = [];
    const costs: RewardGain[] = [];
    for (const kind of KINDS) {
      const delta = kind === 'vp' ? player.vp - old.vp : player.resources[kind] - old.resources[kind];
      const received = income[kind] ?? 0;
      const actionNet = delta - received;
      if (actionNet < 0) costs.push({ kind, amount: -actionNet });
      if (received + Math.max(0, actionNet) > 0) gains.push({ kind, amount: received + Math.max(0, actionNet) });
    }
    if (!gains.length && !costs.length) return [];
    const coord = after.player === player.player_id ? after.action?.coord : undefined;
    const hex = coord && typeof coord === 'object' && 'q' in coord && 'r' in coord
      && typeof coord.q === 'number' && typeof coord.r === 'number' ? { q: coord.q, r: coord.r } : undefined;
    return [{ id, player: player.player_id, gains, costs, hex }];
  });
}
