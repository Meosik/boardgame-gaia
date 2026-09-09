import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { ActionPanel } from '../components/ActionPanel';
import { useGameStore } from '../store/gameStore';
import type { GameState, PlayerState } from '../types/game';

function player(playerId: number, nickname: string): PlayerState {
  return {
    player_id: playerId,
    nickname,
    faction: 'Terrans',
    resources: {
      ore: 4,
      credits: 15,
      knowledge: 4,
      qic: 1,
      power: { bowl1: 4, bowl2: 4, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 },
      spent_gaia_formers: 0,
    },
    structures: [],
    research_tracks: { terraforming: 0, navigation: 5, ai: 0, gaia: 0, economy: 0, science: 0 },
    vp: 10,
    setup_bid_vp: 0,
    passed: false,
    federation_tokens: [],
    alliance_tiles: [],
    explored_ships: [],
    exploration_shuttles_available: 3,
    gaiaformers_total: 3,
    gaiaformers_deployed: 0,
    gaiaformers_in_gaia_area: 0,
    academy_qic_action_used_this_round: false,
    gleens_special_action_used_this_round: false,
    space_giants_special_action_used_this_round: false,
  };
}

function pendingState(pendingPlayer: number): GameState {
  return {
    players: [player(0, 'P0'), player(1, 'P1')],
    board: { sectors: [], hexes: {}, lost_planet: null, spaceship_tiles: {} },
    research_board: {
      tracks: {
        Terraforming: { player_levels: {}, alliance_taken: [] },
        Navigation: { player_levels: {}, alliance_taken: [] },
        ArtificialIntelligence: { player_levels: {}, alliance_taken: [] },
        GaiaProject: { player_levels: {}, alliance_taken: [] },
        Economy: { player_levels: {}, alliance_taken: [] },
        Science: { player_levels: {}, alliance_taken: [] },
      },
      tech_tiles: [],
      advanced_tech_tiles: [null, null, null, null, null, null],
      federation_tokens: [],
    },
    round: 2,
    phase: {
      LostPlanetPlacementPending: {
        player: pendingPlayer,
        resume_phase: { ActionPhase: { active_player: 1 } },
      },
    },
    round_tiles: [],
    final_scoring_tiles: [],
    boosters: [],
    faction_selection: null,
    bidding: null,
    turn_order: [0, 1],
    current_player: 1,
    used_power_actions: [],
    spaceship_boards: [],
    used_spaceship_actions: [],
  };
}

beforeEach(() => {
  useGameStore.setState({
    gameState: null,
    myPlayerId: null,
    activePlanet: null,
    selectedHexes: [],
    selectedAction: null,
    selectedPowerActionId: null,
    wsClient: null,
  });
});

describe('Lost Planet placement decision', () => {
  it('submits the selected map coordinate for the pending player', () => {
    const sendAction = vi.fn();
    useGameStore.setState((state) => ({
      activePlanet: { q: 3, r: -2 },
      actions: { ...state.actions, sendAction },
    }));

    render(<ActionPanel gameState={pendingState(0)} myPlayerId={0} />);
    fireEvent.click(screen.getByText('이 위치에 검은 행성 배치'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'PlaceLostPlanet',
      coord: { q: 3, r: -2 },
    });
  });

  it('blocks non-pending players with a waiting message', () => {
    render(<ActionPanel gameState={pendingState(1)} myPlayerId={0} />);
    expect(screen.getByText(/P1님이 검은 행성 위치를 선택 중/)).toBeInTheDocument();
  });
});
