import type { FactionId } from '../types/game';
import { FACTION_STRUCTURE_COLOR } from './structureImages';

const EXPLORATION_SHUTTLE_IMAGES = import.meta.glob(
  './structures/upscaled/*_exploration_shuttle.png',
  { eager: true, import: 'default' },
) as Record<string, string>;

export function explorationShuttleImageSrc(faction: FactionId | null): string {
  const color = faction ? FACTION_STRUCTURE_COLOR[faction] : 'gray';
  return EXPLORATION_SHUTTLE_IMAGES[
    `./structures/upscaled/${color}_exploration_shuttle.png`
  ];
}
