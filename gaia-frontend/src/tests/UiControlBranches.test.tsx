import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { CreateRoomView } from '../components/GameLobby/CreateRoomView';
import { LobbyHomeView } from '../components/GameLobby/LobbyHomeView';
import { WaitingRoomView } from '../components/GameLobby/WaitingRoomView';
import { BoardOverlay } from '../components/BoardOverlay';
import { GameBoard } from '../components/GameBoard';
import { useRoomStore } from '../store/roomStore';
import type { GameSetup, Hex, PreviewBoard, ServerMessage } from '../types/game';

const socket = vi.hoisted(() => ({
  isConnected: true,
  send: vi.fn(),
  sendCommand: vi.fn(),
  messages: [] as ServerMessage[],
}));

vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: () => socket,
}));

// The lobby fetches the open-room list on mount, and picking a room from it is the only way in.
// One room is enough for these branches, which exercise the join controls rather than the list.
vi.mock('../api/rest', () => ({
  api: {
    listRooms: vi.fn().mockResolvedValue([{
      code: 'ABC123',
      name: '철수님의 방',
      host_nickname: '철수',
      player_count: 1,
      has_password: false,
      setup_mode: 'bidding',
    }]),
  },
}));

vi.mock('../components/ScoringBoard', () => ({
  ScoringBoard: () => <div>Mock scoring board content</div>,
}));

vi.mock('../components/RoundBoosters', () => ({
  RoundBoosters: () => <div>Mock round boosters content</div>,
}));

vi.mock('../components/SpaceshipBoards', () => ({
  SpaceshipBoards: () => <div>Mock spaceship boards content</div>,
}));

vi.mock('../components/PlayerDashboard/ResearchBoard', () => ({
  ResearchBoard: () => <div>Mock research board</div>,
}));

const setup: GameSetup = {
  setup_mode: 'bidding',
  factions: ['Terrans', 'Xenos', 'Taklons', 'HadschHallas'],
  round_tile_ids: [1, 2, 3, 4, 5, 6],
  boosters: [1, 2, 3, 4, 5, 6, 7],
  final_scoring: [],
  tech_tile_ids: [1, 2, 3, 4, 5, 6],
  sector_layout: [],
  deep_space_layout: [],
  seed: 'ui-control-seed',
};

const previewBoard: PreviewBoard = {
  seed: 'ui-seed',
  board: {
    sectors: [],
    hexes: {},
    lost_planet: null,
    spaceship_tiles: {},
  },
  round_tiles: [],
  final_scoring_tiles: [],
  spaceship_boards: [],
};

function resetRoomStore(overrides: Partial<ReturnType<typeof useRoomStore.getState>> = {}) {
  const currentActions = useRoomStore.getState().actions;
  useRoomStore.setState({
    roomCode: null,
    playerId: null,
    sessionToken: null,
    playerCount: 0,
    roomState: 'lobby',
    gameSetup: null,
    previewBoard: null,
    nickname: '',
    lobbyPlayers: [],
    hostPlayerId: null,
    revision: 0,
    paused: false,
    missingSeats: [],
    lastError: null,
    actions: currentActions,
    ...overrides,
  });
}

function installRoomActions(overrides: Partial<ReturnType<typeof useRoomStore.getState>['actions']>) {
  useRoomStore.setState({
    actions: {
      ...useRoomStore.getState().actions,
      ...overrides,
    },
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  socket.isConnected = true;
  socket.messages = [];
  resetRoomStore();
});

describe('CreateRoomView control branches', () => {
  it('rejects an empty nickname before calling createRoom', async () => {
    const createRoom = vi.fn();
    installRoomActions({ createRoom });

    render(<CreateRoomView onRoomCreated={vi.fn()} onBack={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: '방 만들기' }));

    expect(await screen.findByText('닉네임을 입력해주세요')).toBeInTheDocument();
    expect(createRoom).not.toHaveBeenCalled();
  });

  it('creates with a trimmed nickname and no seed input, selected setup mode, regenerate, and back branches', async () => {
    const createRoom = vi.fn().mockResolvedValue(undefined);
    const regenerateSetup = vi.fn().mockResolvedValue(undefined);
    const onRoomCreated = vi.fn();
    const onBack = vi.fn();
    resetRoomStore({ gameSetup: setup });
    installRoomActions({ createRoom, regenerateSetup });

    render(<CreateRoomView onRoomCreated={onRoomCreated} onBack={onBack} />);

    fireEvent.change(screen.getByLabelText('닉네임'), { target: { value: '  Host  ' } });
    expect(screen.queryByLabelText('시드 (선택)')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('radio', { name: /순차 선택/ }));
    fireEvent.click(screen.getByRole('button', { name: '재생성' }));
    await waitFor(() => expect(regenerateSetup).toHaveBeenCalledWith());
    fireEvent.click(screen.getByRole('button', { name: '방 만들기' }));
    await waitFor(() => expect(onRoomCreated).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByRole('button', { name: '뒤로' }));

    expect(createRoom).toHaveBeenCalledWith('Host', undefined, 'sequential', false, {
      name: undefined,
      password: undefined,
    });
    expect(onBack).toHaveBeenCalledOnce();
  });
});

describe('LobbyHomeView control branches', () => {
  it('rejects an empty nickname before joining', async () => {
    const joinRoom = vi.fn();
    installRoomActions({ joinRoom });

    render(<LobbyHomeView onRoomJoined={vi.fn()} onCreateRoom={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: '참가' }));

    expect(await screen.findByText('닉네임을 입력해주세요')).toBeInTheDocument();
    expect(joinRoom).not.toHaveBeenCalled();
  });

  it('trims the nickname and locks the join button while the join is in flight', async () => {
    let resolveJoin!: () => void;
    const pendingJoin = new Promise<void>((resolve) => { resolveJoin = resolve; });
    const joinRoom = vi.fn(() => pendingJoin);
    const onRoomJoined = vi.fn();
    installRoomActions({ joinRoom });

    render(<LobbyHomeView onRoomJoined={onRoomJoined} onCreateRoom={vi.fn()} />);
    const join = await screen.findByRole('button', { name: '참가' });
    fireEvent.change(screen.getByLabelText('닉네임'), { target: { value: '  Guest  ' } });

    await act(async () => { fireEvent.click(join); });

    expect(join).toBeDisabled();
    expect(joinRoom).toHaveBeenCalledWith('ABC123', 'Guest', undefined, undefined);
    expect(onRoomJoined).not.toHaveBeenCalled();

    await act(async () => { resolveJoin(); });
    expect(onRoomJoined).toHaveBeenCalledOnce();
    expect(join).toBeEnabled();
  });
});

describe('WaitingRoomView lobby controls and overlays', () => {
  function seedWaitingRoom(overrides: Partial<ReturnType<typeof useRoomStore.getState>> = {}) {
    const fetchPreviewBoard = vi.fn().mockResolvedValue(undefined);
    const regenerateSetup = vi.fn().mockResolvedValue(undefined);
    resetRoomStore({
      roomCode: 'ABCD12',
      playerId: 0,
      sessionToken: 'token-0',
      playerCount: 4,
      roomState: 'lobby',
      gameSetup: setup,
      previewBoard,
      nickname: 'Host',
      lobbyPlayers: [
        { player_id: 0, nickname: 'Host', ready: false },
        { player_id: 1, nickname: 'P1', ready: false },
        { player_id: 2, nickname: 'P2', ready: false },
        { player_id: 3, nickname: 'P3', ready: false },
      ],
      hostPlayerId: 0,
      revision: 7,
      ...overrides,
    });
    installRoomActions({ fetchPreviewBoard, regenerateSetup });
    return { fetchPreviewBoard, regenerateSetup };
  }

  it('sends ready toggle commands and host reroll succeeds when nobody is ready', async () => {
    const { regenerateSetup } = seedWaitingRoom();

    render(<WaitingRoomView onGameStart={vi.fn()} onFactionSelect={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: '준비 완료' }));
    expect(socket.sendCommand).toHaveBeenCalledWith({ type: 'player_ready', ready: true }, 7);

    fireEvent.click(screen.getByRole('button', { name: '랜더마이저 재설정' }));
    await waitFor(() => expect(regenerateSetup).toHaveBeenCalledOnce());
  });

  it('allows host reroll with ready players and hides host-only reroll for non-hosts', async () => {
    const { regenerateSetup } = seedWaitingRoom({
      lobbyPlayers: [
        { player_id: 0, nickname: 'Host', ready: false },
        { player_id: 1, nickname: 'P1', ready: true },
      ],
    });
    const { rerender } = render(
      <WaitingRoomView onGameStart={vi.fn()} onFactionSelect={vi.fn()} />,
    );

    fireEvent.click(screen.getByRole('button', { name: '랜더마이저 재설정' }));
    await waitFor(() => expect(regenerateSetup).toHaveBeenCalledOnce());
    expect(screen.getByRole('button', { name: '랜더마이저 재설정' })).toBeEnabled();

    act(() => {
      seedWaitingRoom({ playerId: 1, nickname: 'P1', hostPlayerId: 0 });
    });
    rerender(<WaitingRoomView onGameStart={vi.fn()} onFactionSelect={vi.fn()} />);

    expect(screen.queryByRole('button', { name: '랜더마이저 재설정' })).not.toBeInTheDocument();
  });

  it('shows command rejection errors and resyncs revision', async () => {
    seedWaitingRoom();
    socket.messages = [
      {
        type: 'command_rejected',
        protocol_version: 1,
        schema_hash: '0'.repeat(64),
        command_id: 'cmd-1',
        revision: 11,
        rejection: { code: 'stale_revision', message_key: 'stale revision' },
      },
    ];

    await act(async () => {
      render(<WaitingRoomView onGameStart={vi.fn()} onFactionSelect={vi.fn()} />);
    });

    expect(await screen.findByText('stale revision')).toBeInTheDocument();
    expect(useRoomStore.getState().revision).toBe(11);
  });

  it('opens and closes scoring, booster, and personal-board panels from the top bar', async () => {
    seedWaitingRoom();
    render(<WaitingRoomView onGameStart={vi.fn()} onFactionSelect={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: '라운드·게임 종료 목표' }));
    expect(screen.getByText('Mock scoring board content')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '닫기' }));
    expect(screen.queryByText('Mock scoring board content')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '라운드 부스터' }));
    expect(screen.getByText('Mock round boosters content')).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByText('Mock round boosters content')).not.toBeInTheDocument();

    expect(screen.getByText('Mock spaceship boards content')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '개인 보드' }));
    expect(screen.getByRole('dialog', { name: '개인 보드' })).toHaveAttribute('aria-modal', 'false');
    fireEvent.click(screen.getByRole('button', { name: '개인 보드' }));
    expect(screen.queryByRole('dialog', { name: '개인 보드' })).not.toBeInTheDocument();
  });
});

describe('BoardOverlay close branches', () => {
  it('closes from backdrop and close button but not from panel body clicks', () => {
    const onClose = vi.fn();
    const { container } = render(
      <BoardOverlay title="테스트 보드" onClose={onClose}>
        <button type="button">내부 버튼</button>
      </BoardOverlay>,
    );

    fireEvent.click(screen.getByText('내부 버튼'));
    expect(onClose).not.toHaveBeenCalled();

    fireEvent.click(container.querySelector('.board-overlay-backdrop')!);
    expect(onClose).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: '닫기' }));
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});

describe('GameBoard hex click branches', () => {
  const hex: Hex = {
    coord: { q: 0, r: 0 },
    planet: null,
    space_tile_kind: null,
    structures: [],
    satellites: [],
  };
  const board = {
    sectors: [],
    hexes: { '0,0': hex },
    lost_planet: null,
    spaceship_tiles: {},
  };

  it('fires the supplied callback for valid targets and ignores invalid target clicks', () => {
    const onHexClick = vi.fn();
    const { rerender } = render(
      <GameBoard board={board} validTargets={[{ q: 0, r: 0 }]} onHexClick={onHexClick} />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'hex 0,0' }));
    expect(onHexClick).toHaveBeenCalledWith({ q: 0, r: 0 });

    onHexClick.mockClear();
    rerender(<GameBoard board={board} validTargets={[]} onHexClick={onHexClick} />);
    fireEvent.click(screen.getByRole('button', { name: 'hex 0,0' }));
    expect(onHexClick).not.toHaveBeenCalled();
  });
});
