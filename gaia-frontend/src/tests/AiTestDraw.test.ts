import { describe, expect, it } from 'vitest';
import {
  AI_TEST_FACTIONS,
  drawAiTestFactions,
  otherBoardSide,
  type ShownCounts,
} from '../aiTestDraw';

/** A small deterministic generator, so a failing seed can be replayed. */
function seeded(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0;
    return state / 4294967296;
  };
}

describe('AI test faction draw', () => {
  it('covers eighteen factions on nine boards', () => {
    expect(AI_TEST_FACTIONS).toHaveLength(18);
    expect(new Set(AI_TEST_FACTIONS).size).toBe(18);
    for (const faction of AI_TEST_FACTIONS) {
      expect(otherBoardSide(faction)).not.toBe(faction);
      expect(otherBoardSide(otherBoardSide(faction))).toBe(faction);
    }
  });

  it('deals four different boards every time and every faction within six games', () => {
    for (let seed = 1; seed <= 50; seed += 1) {
      const random = seeded(seed);
      const counts: ShownCounts = {};
      for (let game = 0; game < 6; game += 1) {
        const dealt = drawAiTestFactions(counts, random);
        expect(dealt).toHaveLength(4);
        expect(new Set(dealt).size).toBe(4);
        for (const faction of dealt) {
          expect(dealt).not.toContain(otherBoardSide(faction));
          counts[faction] = (counts[faction] ?? 0) + 1;
        }
      }
      for (const faction of AI_TEST_FACTIONS) {
        expect(counts[faction] ?? 0, `seed ${seed}: ${faction}`).toBeGreaterThanOrEqual(1);
      }
    }
  });

  it('deals the least dealt factions first', () => {
    const counts: ShownCounts = {};
    for (const faction of AI_TEST_FACTIONS) counts[faction] = 2;
    const fresh = ['Terrans', 'Xenos', 'Ivits', 'Moweyds'] as const;
    for (const faction of fresh) counts[faction] = 1;
    expect([...drawAiTestFactions(counts, seeded(7))].sort()).toEqual([...fresh].sort());
  });
});
