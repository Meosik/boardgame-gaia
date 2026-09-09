import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { App } from '../App';
import { useGameStore } from '../store/gameStore';
import { useRoomStore } from '../store/roomStore';
import type { GameAction, GameState, PlayerState } from '../types/game';

vi.mock('../components/GameLobby', () => ({
  GameLobby: ({ onGameStart }: { onGameStart: () => void }) => (
    <button type="button" onClick={onGameStart}>테스트 게임 입장</button>
  ),
}));

vi.mock('../components/SpaceshipBoards', () => ({
  SpaceshipBoards: ({
    onActionSelect,
    onArtifactSelect,
  }: {
    onActionSelect?: (action: GameAction['type'], actions: GameAction['type'][]) => void;
    onArtifactSelect?: (artifactId: number) => void;
  }) => (
    <div>
      <button
        type="button"
        onClick={() => onActionSelect?.('RebellionCreditsAndQic', ['RebellionCreditsAndQic'])}
      >
        테스트 함선 행동
      </button>
      <button type="button" onClick={() => onArtifactSelect?.(8)}>
        테스트 아티팩트
      </button>
    </div>
  ),
}));

vi.mock('../components/ActionPanel', () => ({
  ActionPanel: ({ initialArtifactId }: { initialArtifactId?: number | null }) => (
    <div>함선 행동 상세 {initialArtifactId === null || initialArtifactId === undefined ? '' : initialArtifactId}</div>
  ),
}));

vi.mock('../components/GameBoard', () => ({ GameBoard: () => <div /> }));
vi.mock('../components/PlayerDashboard/ResearchBoard', () => ({ ResearchBoard: () => <div /> }));
vi.mock('../components/OpponentPanels', () => ({ OpponentPanels: () => <div /> }));
vi.mock('../components/SidebarTurnControls', () => ({ SidebarTurnControls: () => <div /> }));
vi.mock('../components/TopPassControl', () => ({ TopPassControl: () => <div /> }));
vi.mock('../components/LostFleetTechRequirementBoard', () => ({
  LostFleetTechRequirementBoard: () => <div />,
}));

function player(): PlayerState {
  return {
    player_id: 0,
    nickname: 'P0',
    faction: 'Terrans',
    resources: {
      ore: 10,
      credits: 20,
      knowledge: 10,
      qic: 10,
      power: { bowl1: 0, bowl2: 0, bowl3: 10, gaia_bowl: 0, gaia_forming: 0 },
      spent_gaia_formers: 0,
    },
    structures: [],
    research_tracks: { terraforming: 0, navigation: 0, ai: 0, gaia: 0, economy: 0, science: 0 },
    vp: 10,
    setup_bid_vp: 0,
    passed: false,
    federation_tokens: [],
    alliance_tiles: [],
    explored_ships: [0, 1, 2, 3],
    exploration_shuttles_available: 0,
    gaiaformers_total: 3,
    gaiaformers_deployed: 0,
    gaiaformers_in_gaia_area: 0,
    academy_qic_action_used_this_round: false,
    gleens_special_action_used_this_round: false,
    space_giants_special_action_used_this_round: false,
  };
}

function gameState(): GameState {
  return {
    players: [player()],
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
    round: 1,
    phase: { ActionPhase: { active_player: 0 } },
    round_tiles: [],
    final_scoring_tiles: [],
    boosters: [],
    faction_selection: null,
    bidding: null,
    turn_order: [0],
    current_player: 0,
    used_power_actions: [],
    spaceship_boards: [],
    used_spaceship_actions: [],
  };
}

beforeEach(() => {
  window.history.replaceState({}, '', '/');
  const gameActions = useGameStore.getState().actions;
  useGameStore.setState({
    gameState: gameState(),
    myPlayerId: 0,
    activePlanet: null,
    selectedHexes: [],
    selectedAction: null,
    selectedPowerActionId: null,
    wsClient: null,
    finalResult: null,
    actions: gameActions,
  });
  useRoomStore.setState({
    roomCode: null,
    playerId: null,
    sessionToken: null,
    nickname: '',
    lastError: null,
  });
});

describe('App spaceship-board action flow', () => {
  it('opens the focused action popup for a printed ship action and an artifact', () => {
    render(<App />);
    fireEvent.click(screen.getByText('테스트 게임 입장'));

    fireEvent.click(screen.getByText('테스트 함선 행동'));
    expect(screen.getByRole('dialog', { name: '함선 행동' })).toBeInTheDocument();

    act(() => useGameStore.getState().actions.selectAction(null));
    fireEvent.click(screen.getByText('테스트 아티팩트'));
    expect(screen.getByRole('dialog', { name: '함선 행동' })).toHaveTextContent('함선 행동 상세 8');
  });
});
