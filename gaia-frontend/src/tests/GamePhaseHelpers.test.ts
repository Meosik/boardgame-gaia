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

  it('returns no pending player during the normal action phase', () => {
    expect(pendingDecisionPlayerId({ ActionPhase: { active_player: 0 } })).toBeNull();
  });
});
