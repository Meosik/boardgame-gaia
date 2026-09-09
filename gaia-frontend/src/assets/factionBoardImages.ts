import type { FactionId } from '../types/game';

const FACTION_BOARD_IMAGES = import.meta.glob('./faction_boards/normalized/*.webp', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

/** Stable semantic filenames matching the engine's faction ids. */
const FACTION_BOARD_FILE: Record<FactionId, string> = {
  Ivits: 'ivits',
  HadschHallas: 'hadsch_hallas',
  Geodens: 'geodens',
  BalTaks: 'bal_taks',
  Taklons: 'taklons',
  Ambas: 'ambas',
  Terrans: 'terrans',
  Lantids: 'lantids',
  Nevlas: 'nevlas',
  Itars: 'itars',
  Gleens: 'gleens',
  Xenos: 'xenos',
  Firaks: 'firaks',
  Bescods: 'bescods',
  SpaceGiants: 'space_giants',
  Moweyds: 'moweyds',
  Darkanians: 'darkanians',
  Tinkeroids: 'tinkeroids',
};

export function factionBoardImageSrc(faction: FactionId): string | null {
  const file = FACTION_BOARD_FILE[faction];
  return FACTION_BOARD_IMAGES[`./faction_boards/normalized/${file}.webp`] ?? null;
}
