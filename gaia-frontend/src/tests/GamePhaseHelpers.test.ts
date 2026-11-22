import { describe, expect, it } from 'vitest';
import type { GamePhase } from '../types/game';
import { pendingDecisionPlayerId } from '../types/game';

describe('pendingDecisionPlayerId', () => {
  it('surfaces the Tinkeroids round-start tile choice before action play', () => {
    const phase: GamePhase = {
      TinkeroidsTileSelectionPending: { player: 2, round: 4 },
    };

    expect(pendingDecisionPlayerId(phase)).toBe(2);
  });

  it('lets a queued viewer answer a charge offer or an income order behind the front seat', () => {
    const charge: GamePhase = {
      ChargePowerPending: {
        queue: [
          { player: 1, hex: { q: 0, r: 0 }, max_power: 2 },
          { player: 3, hex: { q: 0, r: 0 }, max_power: 1 },
        ],
        resume_active_player: 0,
      },
    };
    const income: GamePhase = {
      IncomeOrderPending: {
        queue: [
          { player: 1, charge_amount: 4, bonus_tokens: 1 },
          { player: 3, charge_amount: 4, bonus_tokens: 1 },
        ],
        round: 2,
      },
    };

    for (const phase of [charge, income]) {
      // A queued viewer is asked at once; anyone else waits for the front seat.
      expect(pendingDecisionPlayerId(phase, 3)).toBe(3);
      expect(pendingDecisionPlayerId(phase, 1)).toBe(1);
      expect(pendingDecisionPlayerId(phase, 2)).toBe(1);
      expect(pendingDecisionPlayerId(phase)).toBe(1);
    }
  });

  it('returns no pending player during the normal action phase', () => {
    expect(pendingDecisionPlayerId({ ActionPhase: { active_player: 0 } })).toBeNull();
  });
});
