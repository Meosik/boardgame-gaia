import type { FactionId } from '../types/game';

const FACTION_BOARD_IMAGES = import.meta.glob('./faction_boards_individual/*.jpg', {
  eager: true,
  import: 'default',
}) as Record<string, string>;

/**
 * Maps each `FactionId` to its portrait filename under
 * `faction_boards_individual/`.
 *
 * Base-game factions map directly by name (German rulebook naming for a
 * couple of assets: `terraner` = Terrans). `Ivits` and `Bescods` map to
 * `der_schwarm` / `mad_androids` respectively — inferred by elimination
 * (these are the only unmatched base-faction image files) and lore fit
 * (Ivits' hive/swarm-like federation growth; Bescods' robotic theme) rather
 * than an explicit label in the source art; verify against the rulebook art
 * if this ever looks wrong. `Lantids` has two unused alternate-board variants
 * on disk (`lantida_b.jpg`, `lantida_c.jpg`) that are intentionally not
 * referenced here since `FactionId` has only one Lantids entry.
 *
 * The four Lost Fleet expansion factions map directly by (snake_cased) name,
 * same as the base-game factions.
 */
export const FACTION_BOARD_IMAGE_FILE: Record<FactionId, string> = {
  Terrans: 'terraner',
  Lantids: 'lantida',
  Xenos: 'xenos',
  Gleens: 'gleen',
  Taklons: 'taklons',
  Ambas: 'ambas',
  HadschHallas: 'hadsch_halla',
  Ivits: 'der_schwarm',
  Geodens: 'geoden',
  BalTaks: 'bal_t_ak',
  Firaks: 'firaks',
  Bescods: 'mad_androids',
  Nevlas: 'nevla',
  Itars: 'itar',
  Tinkeroids: 'tinkeroids',
  Moweyds: 'moweyds',
  SpaceGiants: 'space_giants',
  Darkanians: 'darkanians',
};

export function factionBoardImageSrc(faction: FactionId): string | null {
  const file = FACTION_BOARD_IMAGE_FILE[faction];
  return FACTION_BOARD_IMAGES[`./faction_boards_individual/${file}.jpg`] ?? null;
}
