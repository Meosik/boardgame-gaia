import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { CreateRoomView } from '../components/GameLobby/CreateRoomView';
import { FactionSelectView } from '../components/GameLobby/FactionSelectView';
import { useRoomStore } from '../store/roomStore';
import type {
  BiddingState,
  GameSetup,
  GameState,
  PlayerState,
  ServerMessage,
} from '../types/game';

const socket = vi.hoisted(() => ({
  isConnected: true,
  send: vi.fn(),
  sendCommand: vi.fn(),
  messages: [] as ServerMessage[],
}));

vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: () => socket,
}));

const biddingSetup: GameSetup = {
  setup_mode: 'bidding',
  factions: ['Terrans', 'Xenos', 'Taklons', 'HadschHallas'],
  round_tile_ids: [1, 2, 3, 4, 5, 6],
  boosters: [1, 2, 3, 4, 5, 6, 7],
  final_scoring: [],
  tech_tile_ids: [],
  sector_layout: [],
  deep_space_layout: [],
  seed: 'ui-bidding',
};

function biddingState(overrides: Partial<BiddingState> = {}): BiddingState {
  return {
    clockwise_order: [7, 3, 9, 1],
    remaining_players: [7, 3, 9, 1],
    available_factions: biddingSetup.factions,
    available_turn_positions: [1, 2, 3, 4],
    active_player: 7,
    highest_bid: 0,
    highest_bidder: null,
    passed_players: [],
    stage: 'Auction',
    assignments: [],
    ...overrides,
  };
}

function player(playerId: number): PlayerState {
  return {
    player_id: playerId,
    nickname: playerId === 7 ? 'Host' : `P${playerId}`,
    faction: null,
    resources: {
      ore: 0,
      credits: 0,
      knowledge: 0,
      qic: 0,
      power: { bowl1: 0, bowl2: 0, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 },
      spent_gaia_formers: 0,
    },
    structures: [],
    research_tracks: { terraforming: 0, navigation: 0, ai: 0, gaia: 0, economy: 0, science: 0 },
    vp: 10,
    setup_bid_vp: 0,
    passed: false,
    federation_tokens: [],
    alliance_tiles: [],
    explored_ships: [],
    exploration_shuttles_available: 3,
    gaiaformers_total: 0,
    gaiaformers_deployed: 0,
    academy_qic_action_used_this_round: false,
    gleens_special_action_used_this_round: false,
    space_giants_special_action_used_this_round: false,
  };
}

function setupGameState(bidding: BiddingState): GameState {
  return {
    players: [player(7), player(3), player(9), player(1)],
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
      advanced_tech_tiles: [],
      federation_tokens: [],
    },
    round: 0,
    phase: bidding.stage === 'Auction'
      ? { Setup: { Bidding: { active_player: bidding.active_player } } }
      : { Setup: { BiddingChoice: { winner: 7 } } },
    round_tiles: [],
    final_scoring_tiles: [],
    boosters: [],
    faction_selection: null,
    bidding,
    turn_order: [7, 3, 9, 1],
    current_player: 0,
    used_power_actions: [],
    spaceship_boards: [],
    used_spaceship_actions: [],
  };
}

function startingStructureGameState(): GameState {
  const state = setupGameState(biddingState({ stage: 'Complete' }));
  state.phase = {
    Setup: {
      StartingStructures: {
        active_player: 7,
        placement_index: 0,
        kind: 'Mine',
      },
    },
  };
  state.players[0].faction = 'Terrans';
  state.players[1].faction = 'Xenos';
  state.players[2].faction = 'Taklons';
  state.players[3].faction = 'Ivits';
  state.board.hexes = {
    '0,0': {
      coord: { q: 0, r: 0 },
      planet: { planet_type: 'Terra', is_gaia_formed: false, owner: null },
      space_tile_kind: null,
      structures: [],
      satellites: [],
    },
    '1,0': {
      coord: { q: 1, r: 0 },
      planet: { planet_type: 'Desert', is_gaia_formed: false, owner: null },
      space_tile_kind: null,
      structures: [],
      satellites: [],
    },
  };
  return state;
}

function startingBoosterGameState(): GameState {
  const state = startingStructureGameState();
  state.phase = {
    Setup: {
      StartingBoosters: {
        active_player: 1,
        selection_index: 0,
      },
    },
  };
  state.boosters = [1, 2, 3, 4, 5, 9, 13];
  return state;
}

beforeEach(() => {
  socket.send.mockReset();
  socket.sendCommand.mockReset();
  socket.messages = [];
  const actions = useRoomStore.getState().actions;
  useRoomStore.setState({
    roomCode: 'BID001',
    playerId: 7,
    sessionToken: 'session',
    playerCount: 4,
    roomState: 'faction_selection',
    gameSetup: biddingSetup,
    nickname: 'Host',
    lobbyPlayers: [
      { player_id: 7, nickname: 'Host', ready: true },
      { player_id: 3, nickname: 'P3', ready: true },
      { player_id: 9, nickname: 'P9', ready: true },
      { player_id: 1, nickname: 'P1', ready: true },
    ],
    hostPlayerId: 7,
    revision: 5,
    actions,
  });
});

describe('CreateRoomView bidding mode', () => {
  it('creates a bidding room by default and allows sequential opt-out', async () => {
    const createRoom = vi.fn().mockResolvedValue(undefined);
    const actions = useRoomStore.getState().actions;
    useRoomStore.setState({
      gameSetup: null,
      actions: { ...actions, createRoom },
    });

    const { unmount } = render(<CreateRoomView onRoomCreated={vi.fn()} onBack={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('닉네임'), { target: { value: 'Host' } });
    fireEvent.click(screen.getByRole('button', { name: '방 만들기' }));
    await waitFor(() => {
      expect(createRoom).toHaveBeenCalledWith('Host', undefined, 'bidding');
    });
    unmount();

    createRoom.mockClear();
    render(<CreateRoomView onRoomCreated={vi.fn()} onBack={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('닉네임'), { target: { value: 'Host' } });
    fireEvent.click(screen.getByText('순차 선택'));
    fireEvent.click(screen.getByRole('button', { name: '방 만들기' }));
    await waitFor(() => {
      expect(createRoom).toHaveBeenCalledWith('Host', undefined, 'sequential');
    });
  });
});

describe('FactionSelectView bidding interactions', () => {
  it('lets the active host bid or pass using revisioned setup commands', () => {
    render(<FactionSelectView onGameStart={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: '1 VP 입찰' }));
    expect(socket.sendCommand).toHaveBeenCalledWith(
      { type: 'place_setup_action', action: { type: 'PlaceBid', amount: 1 } },
      5,
    );

    fireEvent.click(screen.getByRole('button', { name: '패스' }));
    expect(socket.sendCommand).toHaveBeenCalledWith(
      { type: 'place_setup_action', action: { type: 'PassBid' } },
      5,
    );
  });

  it('has no cap tied to current VP, but rejects a bid above the flat 100 sanity ceiling', () => {
    render(<FactionSelectView onGameStart={vi.fn()} />);

    const bidInput = screen.getByLabelText('입찰 VP');
    // Well above the fixture's 10 VP but still under the ceiling — no
    // rulebook rule caps a bid at the bidder's current VP.
    fireEvent.change(bidInput, { target: { value: '50' } });
    expect(screen.getByRole('button', { name: '50 VP 입찰' })).toBeEnabled();

    fireEvent.change(bidInput, { target: { value: '101' } });
    expect(screen.getByRole('button', { name: '101 VP 입찰' })).toBeDisabled();
  });

  it('renders the fully set-up board behind the bidding controls as a popup, not in place of it', async () => {
    // The auction is decided by looking at the actual board (sector layout,
    // home planets, round/final scoring tiles), not just the faction list —
    // so it must render underneath as soon as the real GameState arrives,
    // with the bidding panel as an overlay on top rather than replacing it.
    socket.messages = [{
      type: 'snapshot',
      protocol_version: 1,
      schema_hash: '0'.repeat(64),
      revision: 5,
      state: setupGameState(biddingState()),
    }];

    render(<FactionSelectView onGameStart={vi.fn()} />);

    await screen.findByRole('button', { name: '1 VP 입찰' });
    expect(document.querySelector('.bidding-modal-overlay')).not.toBeNull();
    expect(document.querySelector('.game-main')).not.toBeNull();
    expect(screen.queryByText('보드를 불러오는 중...')).not.toBeInTheDocument();
  });

  it('lets the auction winner choose a faction and final turn position', async () => {
    const choiceState = biddingState({
      active_player: 7,
      highest_bid: 4,
      highest_bidder: 7,
      passed_players: [3, 9, 1],
      stage: { WinnerChoice: { winner: 7, bid_vp: 4 } },
    });
    socket.messages = [{
      type: 'snapshot',
      protocol_version: 1,
      schema_hash: '0'.repeat(64),
      revision: 9,
      state: setupGameState(choiceState),
    }];

    render(<FactionSelectView onGameStart={vi.fn()} />);
    await screen.findByText('4 VP로 낙찰되었습니다. 종족과 최종 순서를 선택하세요.');
    fireEvent.click(screen.getByRole('button', { name: 'Terrans 선택' }));
    fireEvent.click(screen.getByRole('button', { name: '2번' }));
    fireEvent.click(screen.getByRole('button', { name: '종족과 순서 확정' }));

    expect(socket.sendCommand).toHaveBeenCalledWith(
      {
        type: 'place_setup_action',
        action: { type: 'ChooseBidReward', faction: 'Terrans', turn_position: 2 },
      },
      9,
    );
  });

  it('switches from completed bidding to interactive starting-structure placement', async () => {
    socket.messages = [{
      type: 'snapshot',
      protocol_version: 1,
      schema_hash: '0'.repeat(64),
      revision: 12,
      state: startingStructureGameState(),
    }];

    render(<FactionSelectView onGameStart={vi.fn()} />);
    await screen.findByRole('heading', { name: '시작 구조물 배치' });
    const confirm = screen.getByRole('button', { name: '광산 배치 확정' });
    expect(confirm).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'hex 1,0' }));
    expect(confirm).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: 'hex 0,0' }));
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);

    expect(socket.sendCommand).toHaveBeenCalledWith(
      {
        type: 'place_setup_action',
        action: { type: 'PlaceStartingStructure', coord: { q: 0, r: 0 } },
      },
      12,
    );
  });

  it('lets the last player choose an initial booster after structures are placed', async () => {
    useRoomStore.setState({ playerId: 1, revision: 14 });
    socket.messages = [{
      type: 'snapshot',
      protocol_version: 1,
      schema_hash: '0'.repeat(64),
      revision: 14,
      state: startingBoosterGameState(),
    }];

    render(<FactionSelectView onGameStart={vi.fn()} />);
    await screen.findByRole('heading', { name: '초기 부스터 선택' });
    const confirm = screen.getByRole('button', { name: '부스터 선택 확정' });
    expect(confirm).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: '부스터 #9 선택' }));
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);

    expect(socket.sendCommand).toHaveBeenCalledWith(
      {
        type: 'place_setup_action',
        action: { type: 'SelectStartingBooster', booster_id: 9 },
      },
      14,
    );
  });
});
