/** What the research board lets the player pick while the technology of an upgrade is being
 * chosen (`TechUpgradeFlow` in App.tsx): first a tile, then a research track — for a standard
 * tile that leaves the track open, and for every advanced tile after the tile it covers is
 * chosen. `null` = the flow is not at a research-board choice. */
export function techSelectionModeForStage(stage: string | undefined): 'tile' | 'track' | null {
  if (stage === 'tile') return 'tile';
  if (stage === 'track' || stage === 'advanced-track') return 'track';
  return null;
}
