import terraformingSelectionBoard from './boards/normalized/terraforming_selection_board.webp';
import type { PlanetType } from '../types/game';
import type { StructureAssetColor } from './structureImages';

export const terraformingSelectionBoardImageSrc = terraformingSelectionBoard;

export const TERRAFORMING_SATELLITE_COLOR: Partial<
  Record<PlanetType, StructureAssetColor>
> = {
  Terra: 'blue',
  Swamp: 'brown',
  Desert: 'yellow',
  Oxide: 'red',
  Titanium: 'gray',
  Volcanic: 'orange',
  Ice: 'white',
};
