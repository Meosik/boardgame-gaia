import type { GameState, PlayerId } from './types/game';

/** Keep the authenticated session separate from the seat currently making a test decision. */
export function controlledPlayer(state: GameState | null, sessionPlayer: PlayerId | null): PlayerId | null {
  if (!state || sessionPlayer === null || state.dev_controller !== sessionPlayer) return sessionPlayer;
  const phase = state.phase;
  if (typeof phase === 'string') return sessionPlayer;
  if ('Setup' in phase) {
    const setup = phase.Setup;
    if (typeof setup === 'string') return sessionPlayer;
    if ('BiddingChoice' in setup) return setup.BiddingChoice.winner;
    if ('FactionSelection' in setup) return setup.FactionSelection.active_player;
    if ('Bidding' in setup) return setup.Bidding.active_player;
    if ('StartingStructures' in setup) return setup.StartingStructures.active_player;
    return setup.StartingBoosters.active_player;
  }
  if ('ActionPhase' in phase) return state.turn_order[phase.ActionPhase.active_player] ?? sessionPlayer;
  if ('ChargePowerPending' in phase) return phase.ChargePowerPending.queue[0]?.player ?? sessionPlayer;
  if ('LostPlanetChargePowerPending' in phase) return phase.LostPlanetChargePowerPending.queue[0]?.player ?? sessionPlayer;
  if ('IncomeOrderPending' in phase) return phase.IncomeOrderPending.queue[0]?.player ?? sessionPlayer;
  if ('GaiaDecisionPending' in phase) return phase.GaiaDecisionPending.queue[0]?.player ?? sessionPlayer;
  if ('LostPlanetPlacementPending' in phase) return phase.LostPlanetPlacementPending.player;
  if ('TinkeroidsTileSelectionPending' in phase) return phase.TinkeroidsTileSelectionPending.player;
  return sessionPlayer;
}
