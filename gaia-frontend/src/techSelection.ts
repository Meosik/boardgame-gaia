/** What the research board lets the player pick while the technology of an upgrade is being
 * chosen (`TechUpgradeFlow` in App.tsx): first a tile, then a research track — for a standard
 * tile that leaves the track open, and for every advanced tile after the tile it covers is
 * chosen. `null` = the flow is not at a research-board choice. */
export function techSelectionModeForStage(stage: string | undefined): 'tile' | 'track' | null {
  if (stage === 'tile') return 'tile';
  if (stage === 'track' || stage === 'advanced-track') return 'track';
  return null;
}

/** Whether the Lost Fleet's extra Advanced Tech tile can be taken (expansion rulebook p.10):
 * the tile is still there, the condition of the board side in play is met (25 victory points,
 * or 3 different spaceships explored) and, as for every Advanced Tech tile, the player has a
 * green federation token to flip and an uncovered Standard Tech tile to cover. The server
 * also counts the points the same upgrade scores before the tile is taken; this check does
 * not, so below 25 points on the board it says no. */
export function canTakeLostFleetAdvancedTile(input: {
  tileId: number | null | undefined;
  side: 'exploration-shuttles' | '25-vp' | undefined;
  vp: number;
  exploredShips: number[] | undefined;
  greenFederationTokens: number;
  uncoveredStandardTiles: number;
}): boolean {
  if (input.tileId == null || input.greenFederationTokens < 1 || input.uncoveredStandardTiles < 1) {
    return false;
  }
  return input.side === '25-vp'
    ? input.vp >= 25
    : new Set(input.exploredShips ?? []).size >= 3;
}
