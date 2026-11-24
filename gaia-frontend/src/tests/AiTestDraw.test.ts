import { describe, expect, it } from 'vitest';
import {
  AI_TEST_FACTIONS,
  AI_TEST_MAP_SEED,
  aiTestTurnOrder,
  drawAiTestFactions,
  otherBoardSide,
} from '../aiTestDraw';
import orderTable from '../aiTestOrder.json';

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

  it('draws four different boards every time and reaches every faction', () => {
    for (let seed = 1; seed <= 50; seed += 1) {
      const random = seeded(seed);
      const seen = new Set<string>();
      // 200 draws: a faction missing from all of them has a chance of about (14/18)^200.
      for (let game = 0; game < 200; game += 1) {
        const drawn = drawAiTestFactions(random);
        expect(drawn).toHaveLength(4);
        expect(new Set(drawn).size).toBe(4);
        for (const faction of drawn) {
          expect(drawn).not.toContain(otherBoardSide(faction));
          seen.add(faction);
        }
      }
      expect(seen.size, `seed ${seed}`).toBe(18);
    }
  });
});

describe('AI test turn order', () => {
  it('puts the weakest faction first whatever order the table is given in', () => {
    const expected = ['Taklons', 'Xenos', 'Terrans', 'HadschHallas'];
    expect(aiTestTurnOrder(['Terrans', 'Xenos', 'Taklons', 'HadschHallas'])).toEqual(expected);
    expect(aiTestTurnOrder(['HadschHallas', 'Taklons', 'Xenos', 'Terrans'])).toEqual(expected);
  });

  it('puts the strongest faction last', () => {
    expect(aiTestTurnOrder(['Terrans', 'Xenos', 'Darkanians', 'SpaceGiants'])).toEqual([
      'SpaceGiants',
      'Darkanians',
      'Xenos',
      'Terrans',
    ]);
  });

  it('orders every dealt table as a permutation of its four factions', () => {
    for (let seed = 1; seed <= 50; seed += 1) {
      const dealt = drawAiTestFactions(seeded(seed));
      const order = aiTestTurnOrder(dealt);
      expect(order, `seed ${seed}`).toHaveLength(4);
      expect([...order].sort(), `seed ${seed}`).toEqual([...dealt].sort());
    }
  });

  it('holds the order of the fixed map seed', () => {
    expect(orderTable.seed).toBe(AI_TEST_MAP_SEED);
  });
});
