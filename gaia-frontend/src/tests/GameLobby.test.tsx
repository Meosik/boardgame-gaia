import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { HomeView } from '../components/GameLobby/HomeView';
import { JoinRoomView } from '../components/GameLobby/JoinRoomView';
import { useRoomStore } from '../store/roomStore';

// `JoinRoomView` fetches the open-room list on mount and `useRoomStore.joinRoom`
// calls `api.joinRoom` under the hood — jsdom has no real server to hit, so both
// are mocked out the same way `WaitingRoomView.test.tsx` mocks its preview fetch.
const api = vi.hoisted(() => ({
  listRooms: vi.fn(),
  joinRoom: vi.fn(),
}));
vi.mock('../api/rest', () => ({ api }));

describe('HomeView', () => {
  it('links to AI replay in the same tab without carrying room parameters', () => {
    render(<HomeView onCreateRoom={vi.fn()} onJoinRoom={vi.fn()} />);
    const link = screen.getByRole('link', { name: 'AI 리플레이' });
    expect(link).toHaveAttribute('href', '?aiReplay=1');
    expect(link).not.toHaveAttribute('target');
  });

  it('renders create and join buttons', () => {
    const onCreate = vi.fn();
    const onJoin = vi.fn();
    render(<HomeView onCreateRoom={onCreate} onJoinRoom={onJoin} />);

    expect(screen.getByText('방 만들기')).toBeInTheDocument();
    expect(screen.getByText('방 참가하기')).toBeInTheDocument();
  });

  it('calls onCreateRoom when create button clicked', () => {
    const onCreate = vi.fn();
    render(<HomeView onCreateRoom={onCreate} onJoinRoom={vi.fn()} />);
    fireEvent.click(screen.getByText('방 만들기'));
    expect(onCreate).toHaveBeenCalledOnce();
  });

  it('calls onJoinRoom when join button clicked', () => {
    const onJoin = vi.fn();
    render(<HomeView onCreateRoom={vi.fn()} onJoinRoom={onJoin} />);
    fireEvent.click(screen.getByText('방 참가하기'));
    expect(onJoin).toHaveBeenCalledOnce();
  });
});

describe('JoinRoomView', () => {
  beforeEach(() => {
    useRoomStore.setState({
      roomCode: null,
      playerId: null,
      sessionToken: null,
      playerCount: 0,
      roomState: 'lobby',
      gameSetup: null,
      nickname: '',
    });
    api.listRooms.mockReset().mockResolvedValue([]);
    api.joinRoom.mockReset();
  });

  it('renders room code and nickname inputs', async () => {
    render(<JoinRoomView onRoomJoined={vi.fn()} onBack={vi.fn()} />);
    expect(screen.getByLabelText('룸 코드')).toBeInTheDocument();
    expect(screen.getByLabelText('닉네임')).toBeInTheDocument();
    await waitFor(() => expect(api.listRooms).toHaveBeenCalled());
  });

  it('shows error when join attempted with empty fields', async () => {
    render(<JoinRoomView onRoomJoined={vi.fn()} onBack={vi.fn()} />);
    fireEvent.click(screen.getByText('참가하기'));
    await waitFor(() => {
      expect(screen.getByText('룸 코드를 입력해주세요')).toBeInTheDocument();
    });
  });

  it('calls onBack when back button clicked', async () => {
    const onBack = vi.fn();
    render(<JoinRoomView onRoomJoined={vi.fn()} onBack={onBack} />);
    fireEvent.click(screen.getByText('뒤로'));
    expect(onBack).toHaveBeenCalledOnce();
    await waitFor(() => expect(api.listRooms).toHaveBeenCalled());
  });

  it('uppercases room code input', async () => {
    render(<JoinRoomView onRoomJoined={vi.fn()} onBack={vi.fn()} />);
    const codeInput = screen.getByLabelText('룸 코드') as HTMLInputElement;
    fireEvent.change(codeInput, { target: { value: 'abcd12' } });
    expect(codeInput.value).toBe('ABCD12');
    await waitFor(() => expect(api.listRooms).toHaveBeenCalled());
  });

  it('shows a message when no rooms are open', async () => {
    render(<JoinRoomView onRoomJoined={vi.fn()} onBack={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText('지금 대기 중인 방이 없습니다. 룸 코드로 직접 참가해보세요.')).toBeInTheDocument();
    });
  });

  it('lists open rooms and joins the clicked one using the entered nickname', async () => {
    api.listRooms.mockResolvedValue([
      { code: 'ABC123', host_nickname: '철수', player_count: 2 },
    ]);
    api.joinRoom.mockResolvedValue({
      player_id: 5,
      session_token: 'tok',
      room_code: 'ABC123',
      game_setup: null,
      players: [],
      host_player_id: 1,
      game_state: null,
    });
    const onRoomJoined = vi.fn();
    render(<JoinRoomView onRoomJoined={onRoomJoined} onBack={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText('ABC123')).toBeInTheDocument();
    });
    expect(screen.getByText('철수님의 방')).toBeInTheDocument();
    expect(screen.getByText('2/4')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('닉네임'), { target: { value: '영희' } });
    fireEvent.click(screen.getByText('참가'));

    await waitFor(() => {
      expect(api.joinRoom).toHaveBeenCalledWith('ABC123', '영희', undefined);
      expect(onRoomJoined).toHaveBeenCalledOnce();
    });
  });
});
