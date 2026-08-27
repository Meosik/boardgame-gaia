import type { FactionId } from '../types/game';

const FACTION_BOARD_IMAGES = import.meta.glob('./faction_boards/*.jpg', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

/**
 * Each physical `faction_board_0X{a,b}.jpg` scan is a double-sided sheet
 * shared by two factions (7 base-game boards + 2 Lost Fleet boards = 9
 * sheets x 2 sides = all 18 `FactionId`s) — confirmed by directly reading the
 * faction name printed on every one of the 18 faces (not inferred): 01a "DER
 * SCHWARM" (Ivits), 01b "HADSCH HALLA", 02a "GEODEN", 02b "BAL T'AK", 03a
 * "TAKLONS", 03b "AMBAS", 04a "TERRANER" (Terrans), 04b "LANTIDA" (Lantids),
 * 05a "NEVLA", 05b "ITAR" (Itars), 06a "GLEEN" (Gleens), 06b "XENOS", 07a
 * "FIRAKS", 07b "MAD ANDROIDS" (Bescods), 08a "SPACE GIANTS", 08b "MOWEYDS",
 * 09a "DARKANIANS", 09b "TINKEROIDS".
 */
const FACTION_BOARD_FILE: Record<FactionId, string> = {
  Ivits: 'faction_board_01a',
  HadschHallas: 'faction_board_01b',
  Geodens: 'faction_board_02a',
  BalTaks: 'faction_board_02b',
  Taklons: 'faction_board_03a',
  Ambas: 'faction_board_03b',
  Terrans: 'faction_board_04a',
  Lantids: 'faction_board_04b',
  Nevlas: 'faction_board_05a',
  Itars: 'faction_board_05b',
  Gleens: 'faction_board_06a',
  Xenos: 'faction_board_06b',
  Firaks: 'faction_board_07a',
  Bescods: 'faction_board_07b',
  SpaceGiants: 'faction_board_08a',
  Moweyds: 'faction_board_08b',
  Darkanians: 'faction_board_09a',
  Tinkeroids: 'faction_board_09b',
};

export function factionBoardImageSrc(faction: FactionId): string | null {
  const file = FACTION_BOARD_FILE[faction];
  return FACTION_BOARD_IMAGES[`./faction_boards/${file}.jpg`] ?? null;
}
