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

export function otherBoardSide(faction: FactionId): FactionId {
  const board = FACTION_BOARDS.find((sides) => sides[0] === faction || sides[1] === faction);
  if (!board) return faction;
  return board[0] === faction ? board[1] : board[0];
}

/** Four factions for one game, drawn at random every time (owner 2026-11-24 「완전 무작위」; before
 * that the least dealt came first), never two sides of one board. */
export function drawAiTestFactions(random: () => number = Math.random): FactionId[] {
  const shuffled = [...AI_TEST_FACTIONS];
  for (let i = shuffled.length - 1; i > 0; i -= 1) {
    const j = Math.floor(random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  const drawn: FactionId[] = [];
  for (const faction of shuffled) {
    if (drawn.length === 4) break;
    if (!drawn.includes(otherBoardSide(faction))) drawn.push(faction);
  }
  return drawn;
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
