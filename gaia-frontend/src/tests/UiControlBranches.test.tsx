import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { CreateRoomView } from '../components/GameLobby/CreateRoomView';
import { JoinRoomView } from '../components/GameLobby/JoinRoomView';
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

  it('creates with trimmed inputs, selected setup mode, regenerate, and back branches', async () => {
    const createRoom = vi.fn().mockResolvedValue(undefined);
    const regenerateSetup = vi.fn().mockResolvedValue(undefined);
    const onRoomCreated = vi.fn();
    const onBack = vi.fn();
    resetRoomStore({ gameSetup: setup });
    installRoomActions({ createRoom, regenerateSetup });

    render(<CreateRoomView onRoomCreated={onRoomCreated} onBack={onBack} />);

    fireEvent.change(screen.getByLabelText('닉네임'), { target: { value: '  Host  ' } });
    fireEvent.change(screen.getByLabelText('시드 (선택)'), { target: { value: '  seed-1  ' } });
    fireEvent.click(screen.getByRole('radio', { name: /순차 선택/ }));
    fireEvent.click(screen.getByRole('button', { name: '재생성' }));
    await waitFor(() => expect(regenerateSetup).toHaveBeenCalledWith('seed-1'));
    fireEvent.click(screen.getByRole('button', { name: '방 만들기' }));
    await waitFor(() => expect(onRoomCreated).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByRole('button', { name: '뒤로' }));

    expect(createRoom).toHaveBeenCalledWith('Host', 'seed-1', 'sequential');
    expect(onBack).toHaveBeenCalledOnce();
  });
});

describe('JoinRoomView control branches', () => {
  it('rejects empty code and empty nickname before joining', async () => {
    const joinRoom = vi.fn();
    installRoomActions({ joinRoom });

    render(<JoinRoomView onRoomJoined={vi.fn()} onBack={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: '참가하기' }));
    expect(await screen.findByText('룸 코드를 입력해주세요')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('룸 코드'), { target: { value: 'ab12' } });
    fireEvent.click(screen.getByRole('button', { name: '참가하기' }));
    expect(await screen.findByText('닉네임을 입력해주세요')).toBeInTheDocument();
    expect(joinRoom).not.toHaveBeenCalled();
  });

  it('joins with uppercase room code, disables buttons while loading, then supports back', async () => {
    const joinRoom = vi.fn(() => new Promise<void>((resolve) => setTimeout(resolve, 5)));
    const onRoomJoined = vi.fn();
    const onBack = vi.fn();
    installRoomActions({ joinRoom });

    render(<JoinRoomView onRoomJoined={onRoomJoined} onBack={onBack} />);
    fireEvent.change(screen.getByLabelText('룸 코드'), { target: { value: 'ab12' } });
    fireEvent.change(screen.getByLabelText('닉네임'), { target: { value: '  Guest  ' } });

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: '참가하기' }));
    });

    expect(screen.getByRole('button', { name: '참가 중...' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '뒤로' })).toBeDisabled();
    expect(joinRoom).toHaveBeenCalledWith('AB12', 'Guest');

    await waitFor(() => expect(onRoomJoined).toHaveBeenCalledOnce());
    fireEvent.click(screen.getByRole('button', { name: '뒤로' }));
    expect(onBack).toHaveBeenCalledOnce();
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

  it('covers host reroll blocked state and hides host-only reroll for non-hosts', () => {
    seedWaitingRoom({
      lobbyPlayers: [
        { player_id: 0, nickname: 'Host', ready: false },
        { player_id: 1, nickname: 'P1', ready: true },
      ],
    });
    const { rerender } = render(
      <WaitingRoomView onGameStart={vi.fn()} onFactionSelect={vi.fn()} />,
    );

    expect(screen.getByRole('button', { name: '랜더마이저 재설정' })).toBeDisabled();

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

  it('opens and closes scoring, booster, and spaceship panels from the top bar', async () => {
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

    fireEvent.click(screen.getByRole('button', { name: '함선 보드' }));
    expect(screen.getByRole('dialog', { name: '함선 보드' })).toHaveAttribute('aria-modal', 'false');
    expect(screen.getByText('Mock spaceship boards content')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '닫기' }));
    expect(screen.queryByText('Mock spaceship boards content')).not.toBeInTheDocument();
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
