import type { FactionId } from '../types/game';

const EXPLORATION_BOARD_IMAGES = import.meta.glob('./exploration_boards/normalized/*.webp', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

/**
 * Maps each `FactionId` to its Lost Fleet Exploration Board image under
 * `exploration_boards/`.
 *
 * Runtime and archival files use stable `FactionId` snake-case names. The explicit map keeps
 * server identifiers decoupled from filenames without preserving scan-era aliases or typos.
 */
export const EXPLORATION_BOARD_IMAGE_FILE: Record<FactionId, string> = {
  Terrans: 'terrans',
  Lantids: 'lantids',
  Xenos: 'xenos',
  Gleens: 'gleens',
  Taklons: 'taklons',
  Ambas: 'ambas',
  HadschHallas: 'ivits',
  Ivits: 'hadsch_halla',
  Geodens: 'geodens',
  BalTaks: 'bal_taks',
  Firaks: 'firaks',
  Bescods: 'bescods',
  Nevlas: 'nevlas',
  Itars: 'itars',
  Tinkeroids: 'tinkeroids',
  Moweyds: 'moweyds',
  SpaceGiants: 'space_giants',
  Darkanians: 'darkanians',
};

export function explorationBoardImageSrc(faction: FactionId): string | null {
  const file = EXPLORATION_BOARD_IMAGE_FILE[faction];
  return EXPLORATION_BOARD_IMAGES[`./exploration_boards/normalized/${file}.webp`] ?? null;
}
