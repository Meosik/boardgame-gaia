import type { FactionId } from './types/game';
import orderTable from './aiTestOrder.json';

/** The lab's fixed map (HANDOFF E178): every AI test game uses this seed's map and tiles. */
export const AI_TEST_MAP_SEED = 'quartet-e-88365';

/** The two sides of each faction board (gaia-engine `FactionId::other_board_side`). The server
 * refuses a game holding both sides of one board, so a draw never does. */
const FACTION_BOARDS: [FactionId, FactionId][] = [
  ['Terrans', 'Lantids'],
  ['Xenos', 'Gleens'],
  ['Taklons', 'Ambas'],
  ['HadschHallas', 'Ivits'],
  ['Geodens', 'BalTaks'],
  ['Firaks', 'Bescods'],
  ['Nevlas', 'Itars'],
  ['Tinkeroids', 'Darkanians'],
  ['Moweyds', 'SpaceGiants'],
];

export const AI_TEST_FACTIONS: FactionId[] = FACTION_BOARDS.reduce<FactionId[]>(
  (all, sides) => all.concat(sides),
  [],
);

/** How many AI test games each faction has been dealt into, on this browser. */
export type ShownCounts = Partial<Record<FactionId, number>>;

const STORAGE_KEY = 'gaia-ai-test-shown';

export function otherBoardSide(faction: FactionId): FactionId {
  const board = FACTION_BOARDS.find((sides) => sides[0] === faction || sides[1] === faction);
  if (!board) return faction;
  return board[0] === faction ? board[1] : board[0];
}

/** Four factions for one game: the least dealt first (ties in random order), never two sides of
 * one board. Dealing the least dealt first is what spreads the factions evenly over the games —
 * all eighteen come up within six games. */
export function drawAiTestFactions(
  counts: ShownCounts,
  random: () => number = Math.random,
): FactionId[] {
  const order = AI_TEST_FACTIONS
    .map((faction) => ({ faction, shown: counts[faction] ?? 0, tie: random() }))
    .sort((a, b) => a.shown - b.shown || a.tie - b.tie);
  const drawn: FactionId[] = [];
  for (const { faction } of order) {
    if (drawn.length === 4) break;
    if (!drawn.includes(otherBoardSide(faction))) drawn.push(faction);
  }
  return drawn;
}

export function readShownCounts(): ShownCounts {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
    if (!value || typeof value !== 'object') return {};
    const counts: ShownCounts = {};
    for (const faction of AI_TEST_FACTIONS) {
      const shown = (value as Record<string, unknown>)[faction];
      if (typeof shown === 'number' && Number.isInteger(shown) && shown > 0) counts[faction] = shown;
    }
    return counts;
  } catch {
    return {};
  }
}

/** Count a started game's four factions, so the next draw prefers the others. */
export function recordShown(factions: FactionId[]): void {
  try {
    const counts = readShownCounts();
    for (const faction of factions) counts[faction] = (counts[faction] ?? 0) + 1;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(counts));
  } catch {
    // Storage denied: the game still starts, the next draw is just less even.
  }
}

/** The turn order of an AI test table: the faction expected to do worst on the fixed map moves
 * first, the strongest last (the lab's strength order, `gaia-rl/tools/faction_strength.py`;
 * owner 2026-10-25 "잘 풀릴 것 같은 종족부터 4·3·2·1턴"). Read from `aiTestOrder.json`, which
 * holds the order of every table of four boards on `AI_TEST_MAP_SEED` — regenerate it with
 * `faction_strength.py <seed> --orders-table gaia-frontend/src/aiTestOrder.json` when the map
 * seed or the strength tool changes. A table it does not hold keeps the order it was given. */
export function aiTestTurnOrder(factions: FactionId[]): FactionId[] {
  const names = orderTable.factions as string[];
  const letter = (faction: FactionId) => String.fromCharCode(97 + names.indexOf(faction));
  if (factions.some((faction) => !names.includes(faction))) return factions;
  const key = factions.map(letter).sort().join('');
  const order = (orderTable.orders as Record<string, string>)[key];
  if (!order) return factions;
  return [...order].map((each) => names[each.charCodeAt(0) - 97] as FactionId);
}
