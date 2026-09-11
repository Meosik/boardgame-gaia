import { beforeEach, describe, expect, it } from 'vitest';
import { controlledPlayer } from '../devControl';
import { useGameStore } from '../store/gameStore';
import type { GamePhase, GameState } from '../types/game';

const stateWith = (phase: GamePhase, dev_controller: number | undefined = 7): GameState => ({
  dev_controller, phase, turn_order: [7, 8, 9, 10],
} as GameState);

const phases: [string, GamePhase, number][] = [
  ['faction', { Setup: { FactionSelection: { active_player: 8 } } }, 8],
  ['bid', { Setup: { Bidding: { active_player: 9 } } }, 9],
  ['bid winner', { Setup: { BiddingChoice: { winner: 10 } } }, 10],
  ['mine placement', { Setup: { StartingStructures: { active_player: 8, placement_index: 1, kind: 'Mine' } } }, 8],
  ['booster', { Setup: { StartingBoosters: { active_player: 10, selection_index: 0 } } }, 10],
  ['main action uses turn-order index, not ID', { ActionPhase: { active_player: 2 } }, 9],
  ['charge', { ChargePowerPending: { queue: [{ player: 8, hex: { q: 0, r: 0 }, max_power: 2 }], resume_active_player: 2 } }, 8],
  ['lost planet charge', { LostPlanetChargePowerPending: { queue: [{ player: 10, hex: { q: 0, r: 0 }, max_power: 2 }], resume_phase: { ActionPhase: { active_player: 2 } } } }, 10],
  ['lost planet', { LostPlanetPlacementPending: { player: 9, resume_phase: { ActionPhase: { active_player: 2 } } } }, 9],
  ['income', { IncomeOrderPending: { queue: [{ player: 8, charge_amount: 2, bonus_tokens: 1 }], round: 2 } }, 8],
  ['Gaia', { GaiaDecisionPending: { queue: [{ player: 10, kind: 'ItarsTechTile', remaining_power: 4 }], round: 2 } }, 10],
  ['tinkering', { TinkeroidsTileSelectionPending: { player: 9, round: 2 } }, 9],
];

describe('manual DEV seat control', () => {
  beforeEach(() => useGameStore.getState().actions.reset());
  it.each(phases)('switches to the player making the %s decision', (_name, phase, expected) => {
    expect(controlledPlayer(stateWith(phase), 7)).toBe(expected);
  });
  it.each(phases)('does not impersonate other seats in an ordinary game: %s', (_name, phase) => {
    const state = stateWith(phase);
    delete state.dev_controller;
    expect(controlledPlayer(state, 7)).toBe(7);
  });
  it('does not give a different authenticated player controller rights', () => {
    expect(controlledPlayer(stateWith({ ActionPhase: { active_player: 2 } }), 8)).toBe(8);
  });
  it('keeps session identity, clears old seat selections, and follows charge then the next turn', () => {
    const { actions } = useGameStore.getState();
    actions.setMyPlayerId(7);
    actions.setGameState(stateWith({ ActionPhase: { active_player: 0 } }));
    actions.selectAction('Build');
    actions.selectPlanet({ q: 1, r: 0 });
    actions.setGameState(stateWith(phases[6][1]));
    expect(useGameStore.getState()).toMatchObject({ sessionPlayerId: 7, myPlayerId: 8, selectedAction: null, activePlanet: null });
    actions.setMyPlayerId(7); // reconnect acknowledgement must not reset the acting seat
    expect(useGameStore.getState().myPlayerId).toBe(8);
    actions.setGameState(stateWith({ ActionPhase: { active_player: 2 } }));
    expect(useGameStore.getState().myPlayerId).toBe(9);
  });
});
