import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { App } from '../App';
import { useGameStore } from '../store/gameStore';
import { useRoomStore } from '../store/roomStore';
import type { GameAction, GameState, Hex, PlayerState, ResearchTrack } from '../types/game';

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
      <button type="button" onClick={() => onActionSelect?.('TwilightRangeBuild', [
        'TwilightRangeBuild', 'TwilightRangeGaiaFormation', 'TwilightRangeExploreSpaceship',
      ])}>
        테스트 사거리 행동
      </button>
    </div>
  ),
}));

vi.mock('../components/ActionPanel', () => ({
  ActionPanel: ({ initialArtifactId }: { initialArtifactId?: number | null }) => (
    <div>함선 행동 상세 {initialArtifactId === null || initialArtifactId === undefined ? '' : initialArtifactId}</div>
  ),
}));

vi.mock('../components/GameBoard', () => ({
  GameBoard: ({
    onOwnedStructureClick,
  }: {
    onOwnedStructureClick?: (hex: Hex, anchor: { x: number; y: number }) => void;
  }) => (
    <button
      type="button"
      onClick={() => onOwnedStructureClick?.({
        coord: { q: 0, r: 0 },
        planet: null,
        space_tile_kind: null,
        structures: [{ owner: 0, kind: 'TradingStation' }],
        satellites: [],
      }, { x: 0, y: 0 })}
    >
      테스트 내 구조물
    </button>
  ),
}));
vi.mock('../components/PlayerDashboard/ResearchBoard', () => ({
  ResearchBoard: ({
    isMyTurn,
    mainActionLocked,
    onPowerAction,
    techSelectionMode,
    selectableResearchTracks,
    onResearchTrack,
    onStandardTechTile,
  }: {
    isMyTurn?: boolean;
    mainActionLocked?: boolean;
    onPowerAction?: (id: number) => void;
    techSelectionMode?: string | null;
    selectableResearchTracks?: ResearchTrack[];
    onResearchTrack?: (track: ResearchTrack) => void;
    onStandardTechTile?: (tile: number) => void;
  }) => (
    <>
    {techSelectionMode === 'tile' && <button onClick={() => onStandardTechTile?.(2)}>기술 2 보드 선택</button>}
    {techSelectionMode === 'track' && (['Terraforming', 'Navigation'] as ResearchTrack[]).map(track => (
      <button key={track} disabled={!selectableResearchTracks?.includes(track)} onClick={() => onResearchTrack?.(track)}>{track} 보드 선택</button>
    ))}
    <button
      type="button"
      disabled={!isMyTurn || mainActionLocked}
      onClick={() => onPowerAction?.(3)}
    >
      테스트 파워 행동
    </button>
    </>
  ),
  RESEARCH_TRACK_ORDER: [
    'Terraforming',
    'Navigation',
    'ArtificialIntelligence',
    'GaiaProject',
    'Economy',
    'Science',
  ],
}));
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
  it('chooses Space Giants institute technology before sending the single upgrade action', () => {
    const state = gameState();
    state.players[0].faction = 'SpaceGiants';
    state.players[0].structures = [{ hex: { q: 0, r: 0 }, kind: 'TradingStation' }];
    state.research_board.tech_tiles = [2];
    state.research_board.tech_tile_slots = [null, null, null, null, null, null, 2, null, null];
    useGameStore.setState({ gameState: state });
    const sendAction = vi.spyOn(useGameStore.getState().actions, 'sendAction').mockReturnValue(null);
    render(<App />);
    fireEvent.click(screen.getByText('테스트 게임 입장'));
    fireEvent.click(screen.getByText('테스트 내 구조물'));
    fireEvent.click(screen.getByRole('button', { name: /행성의회/ }));
    expect(sendAction).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText('기술 2 보드 선택'));
    fireEvent.click(screen.getByText('Navigation 보드 선택'));
    expect(sendAction).toHaveBeenCalledWith({ type: 'Upgrade', coord: { q: 0, r: 0 }, to: 'PlanetaryInstitute',
      tech_tile_choice: { kind: 'Standard', tile: 2, advance_track: 'Navigation', bonus_build_coord: null } });
    sendAction.mockRestore();
  });

  it.each(['Firaks', 'Ivits'] as const)('routes %s mapped PI image into the existing target-selection flow', faction => {
    const state = gameState();
    state.players[0].faction = faction;
    state.players[0].structures = [{ hex: { q: 0, r: 0 }, kind: 'PlanetaryInstitute' }];
    useGameStore.setState({ gameState: state });
    render(<App />);
    fireEvent.click(screen.getByText('테스트 게임 입장'));
    fireEvent.click(screen.getByRole('button', { name: faction === 'Firaks' ? '파이락 연구소 강등 + 무료 연구' : '하이브 우주정거장 배치' }));
    expect(useGameStore.getState().selectedAction).toBe(faction === 'Firaks' ? 'FiraksDowngradeResearchLab' : 'IvitsPlaceSpaceStation');
  });

  it('selects Bescods lowest research directly on the board without a popup', () => {
    const state = gameState();
    state.players[0].faction = 'Bescods';
    state.players[0].research_tracks.terraforming = 2;
    useGameStore.setState({ gameState: state });
    const sendAction = vi.spyOn(useGameStore.getState().actions, 'sendAction');
    render(<App />);
    fireEvent.click(screen.getByText('테스트 게임 입장'));
    fireEvent.click(screen.getByRole('button', { name: '매드 안드로이드 최저 연구 무료 상승' }));
    expect(screen.queryByRole('dialog', { name: '매드 안드로이드 최저 연구 무료 상승' })).not.toBeInTheDocument();
    expect(screen.getByText('Terraforming 보드 선택')).toBeDisabled();
    fireEvent.click(screen.getByText('Navigation 보드 선택'));
    expect(sendAction).toHaveBeenCalledWith({ type: 'BescodsLowestResearchAdvance', track: 'Navigation' });
    sendAction.mockRestore();
  });

  it('selects Twilight range without a details popup and cancels through the shared button', () => {
    render(<App />);
    fireEvent.click(screen.getByText('테스트 게임 입장'));
    fireEvent.click(screen.getByText('테스트 사거리 행동'));

    expect(useGameStore.getState().selectedAction).toBe('TwilightRangeBuild');
    expect(screen.queryByRole('dialog', { name: '함선 행동' })).not.toBeInTheDocument();
    expect(screen.queryByText(/함선 행동 상세/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '행동 취소' }));
    expect(useGameStore.getState().selectedAction).toBeNull();
    expect(screen.queryByRole('button', { name: '행동 취소' })).not.toBeInTheDocument();
  });

  it('executes simple ship actions and artifacts without a popup', () => {
    render(<App />);
    fireEvent.click(screen.getByText('테스트 게임 입장'));

    expect(document.querySelector('.app--game-table')).toBeInTheDocument();
    expect(document.querySelector('#game-overview')).toBeInTheDocument();
    expect(document.querySelector('#game-map')).toBeInTheDocument();
    expect(document.querySelector('#game-research')).toBeInTheDocument();
    expect(document.querySelector('#game-factions')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: '보드 바로가기' }))
      .toHaveClass('game-table-top-nav');
    expect(document.querySelector('.game-sidebar .game-section-nav')).not.toBeInTheDocument();

    const overviewClasses = [...document.querySelector('#game-overview')!.children]
      .map((element) => element.className);
    expect(overviewClasses).toEqual([
      expect.stringContaining('game-table-scoring-card'),
      expect.stringContaining('game-table-boosters-card'),
      expect.stringContaining('game-table-federation-card'),
      expect.stringContaining('game-table-terraforming-card'),
    ]);

    const researchClasses = [...document.querySelector('#game-research-section')!.children]
      .map((element) => element.className);
    expect(researchClasses).toEqual([
      expect.stringContaining('game-table-tech-requirement-card'),
      expect.stringContaining('game-table-research-card'),
      expect.stringContaining('player-action-shelf'),
      expect.stringContaining('game-table-ships-card'),
    ]);

    fireEvent.click(screen.getByText('테스트 함선 행동'));
    expect(screen.queryByRole('dialog', { name: '함선 행동' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '행동 취소' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '행동 취소' }));
    fireEvent.click(screen.getByText('테스트 아티팩트'));
    expect(screen.queryByRole('dialog', { name: '함선 행동' })).not.toBeInTheDocument();
    expect(useGameStore.getState().selectedAction).toBe('ExamineArtifact');
  });

  it('locks power actions while a structure action is open', () => {
    render(<App />);
    fireEvent.click(screen.getByText('테스트 게임 입장'));

    const powerAction = screen.getByRole('button', { name: '테스트 파워 행동' });
    expect(powerAction).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: '테스트 내 구조물' }));
    expect(powerAction).toBeDisabled();
  });
});
