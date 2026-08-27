import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { WaitingRoomView } from '../components/GameLobby/WaitingRoomView';
import { useRoomStore } from '../store/roomStore';
import type { GameSetup, GameState, ServerMessage } from '../types/game';

const socket = vi.hoisted(() => ({
  isConnected: true,
  send: vi.fn(),
  sendCommand: vi.fn(),
  messages: [] as ServerMessage[],
}));

vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: () => socket,
}));

// The preview-board fetch (triggered by a `gameSetup.seed` effect) isn't
// under test here and jsdom has no real server to hit — mock it out so it
// doesn't reject with an unhandled "Invalid URL" error for a relative path.
const emptyPreview = {
  seed: 'ui-waiting-room',
  board: { sectors: [], hexes: {}, lost_planet: null, spaceship_tiles: {} },
  round_tiles: [],
  final_scoring_tiles: [],
  spaceship_boards: [],
};
const api = vi.hoisted(() => ({
  getPreviewBoard: vi.fn(),
}));
vi.mock('../api/rest', () => ({ api }));

// Only `phase` matters for the code path under test — `WaitingRoomView`
// never reads any other `GameState` field before handing off to
// `onFactionSelect`.
const biddingGameState = {
  phase: { Setup: { Bidding: { active_player: 0 } } },
} as unknown as GameState;

const biddingGameSetup: GameSetup = {
  setup_mode: 'bidding',
  factions: ['Terrans', 'Xenos', 'Taklons', 'HadschHallas'],
  round_tile_ids: [1, 2, 3, 4, 5, 6],
  boosters: [1, 2, 3, 4, 5, 6, 7],
  final_scoring: [],
  tech_tile_ids: [],
  sector_layout: [],
  deep_space_layout: [],
  seed: 'ui-waiting-room',
};

beforeEach(() => {
  socket.send.mockReset();
  socket.sendCommand.mockReset();
  socket.messages = [];
  api.getPreviewBoard.mockReset().mockResolvedValue(emptyPreview);
  const actions = useRoomStore.getState().actions;
  useRoomStore.setState({
    roomCode: 'BID001',
    playerId: 0,
    sessionToken: 'session',
    playerCount: 4,
    roomState: 'lobby',
    gameSetup: biddingGameSetup,
    previewBoard: null,
    nickname: 'Host',
    lobbyPlayers: [
      { player_id: 0, nickname: 'Host', ready: true },
      { player_id: 1, nickname: 'P1', ready: true },
      { player_id: 2, nickname: 'P2', ready: true },
      { player_id: 3, nickname: 'P3', ready: true },
    ],
    hostPlayerId: 0,
    revision: 4,
    actions,
  });
});

describe('WaitingRoomView message-batch handling', () => {
  it('still detects a snapshot carrying a real GameState even when a lobby_state broadcast arrives alongside it in the same batch', async () => {
    // Reproduces the reported bug: `handle_player_ready` (gaia-server)
    // broadcasts a `snapshot` immediately followed by a `lobby_state` for
    // the same command. If both land in the same render (exactly what
    // `useWebSocket`'s `messages` array — populated before this component
    // ever mounts, i.e. the worst case for a single-slot "lastMessage"
    // design — represents here), the fix must still process the `snapshot`
    // and not let the trailing `lobby_state` silently win.
    socket.messages = [
      {
        type: 'snapshot',
        protocol_version: 1,
        schema_hash: '0'.repeat(64),
        revision: 5,
        state: biddingGameState,
      },
      {
        type: 'lobby_state',
        players: [
          { player_id: 0, nickname: 'Host', ready: true },
          { player_id: 1, nickname: 'P1', ready: true },
          { player_id: 2, nickname: 'P2', ready: true },
          { player_id: 3, nickname: 'P3', ready: true },
        ],
        host_player_id: 0,
      },
    ];

    const onFactionSelect = vi.fn();
    await act(async () => {
      render(<WaitingRoomView onGameStart={vi.fn()} onFactionSelect={onFactionSelect} />);
    });

    expect(onFactionSelect).toHaveBeenCalledOnce();
  });

  it('still shows the waiting hint (not "starting") when only the lobby_state half of the pair is queued', async () => {
    socket.messages = [
      {
        type: 'lobby_state',
        players: [
          { player_id: 0, nickname: 'Host', ready: true },
          { player_id: 1, nickname: 'P1', ready: true },
          { player_id: 2, nickname: 'P2', ready: true },
          { player_id: 3, nickname: 'P3', ready: true },
        ],
        host_player_id: 0,
      },
    ];

    const onFactionSelect = vi.fn();
    await act(async () => {
      render(<WaitingRoomView onGameStart={vi.fn()} onFactionSelect={onFactionSelect} />);
    });

    expect(onFactionSelect).not.toHaveBeenCalled();
    expect(screen.getByText('비딩을 시작하는 중...')).toBeInTheDocument();
  });
});

describe('WaitingRoomView board preview', () => {
  it('fetches the preview board for the current seed on mount', async () => {
    let container!: HTMLElement;
    await act(async () => {
      ({ container } = render(<WaitingRoomView onGameStart={vi.fn()} onFactionSelect={vi.fn()} />));
    });

    await waitFor(() => expect(api.getPreviewBoard).toHaveBeenCalledWith('BID001'));
    const topbar = container.querySelector('.waiting-room-topbar');
    const panel = container.querySelector('.waiting-room-panel');
    const boardRail = container.querySelector('.waiting-room-board-rail');

    expect(topbar).toHaveTextContent('라운드·게임 종료 목표');
    expect(topbar).toHaveTextContent('라운드 부스터');
    expect(topbar).toHaveTextContent('함선 보드');
    expect(topbar).not.toHaveTextContent('보드 보기');
    expect(panel).not.toHaveTextContent('라운드·게임 종료 목표');
    expect(panel).not.toHaveTextContent('라운드 부스터');
    expect(boardRail).toHaveTextContent('연구 트랙');
    expect(boardRail).not.toHaveTextContent('함선 보드');
    expect(screen.getByLabelText('개인 보드 영역')).toHaveTextContent('종족 확정 후');
    expect(boardRail?.querySelector('.waiting-room-personal-placeholder')).toBe(
      screen.getByLabelText('개인 보드 영역'),
    );
    expect(screen.queryByText('보드 보기')).not.toBeInTheDocument();
    expect(screen.queryByText('보드 미리보기 불러오는 중...')).not.toBeInTheDocument();
  });

  it('re-fetches when the seed changes (reroll)', async () => {
    await act(async () => {
      render(<WaitingRoomView onGameStart={vi.fn()} onFactionSelect={vi.fn()} />);
    });
    await waitFor(() => expect(api.getPreviewBoard).toHaveBeenCalledTimes(1));

    await act(async () => {
      useRoomStore.setState({ gameSetup: { ...biddingGameSetup, seed: 'rerolled-seed' } });
    });

    await waitFor(() => expect(api.getPreviewBoard).toHaveBeenCalledTimes(2));
  });

  it('opens ship boards in a non-modal panel so the map remains interactive', async () => {
    const { container } = render(
      <WaitingRoomView onGameStart={vi.fn()} onFactionSelect={vi.fn()} />,
    );
    await waitFor(() => expect(api.getPreviewBoard).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: '함선 보드' }));

    expect(screen.getByRole('dialog', { name: '함선 보드' })).toHaveAttribute('aria-modal', 'false');
    expect(container.querySelector('.board-overlay-backdrop')).not.toBeInTheDocument();
  });
});
