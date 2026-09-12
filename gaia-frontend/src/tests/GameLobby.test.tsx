import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LobbyHomeView } from '../components/GameLobby/LobbyHomeView';
import { useRoomStore } from '../store/roomStore';
import type { RoomSummary } from '../types/game';

// `LobbyHomeView` fetches the open-room list on mount and `useRoomStore.joinRoom` calls
// `api.joinRoom` under the hood — jsdom has no real server to hit, so both are mocked out the
// same way `WaitingRoomView.test.tsx` mocks its preview fetch.
const api = vi.hoisted(() => ({
  listRooms: vi.fn(),
  joinRoom: vi.fn(),
}));
vi.mock('../api/rest', () => ({ api }));

function room(overrides: Partial<RoomSummary> = {}): RoomSummary {
  return {
    code: 'ABC123',
    name: '철수님의 방',
    host_nickname: '철수',
    player_count: 2,
    has_password: false,
    setup_mode: 'bidding',
    ...overrides,
  };
}

const joined = {
  player_id: 5,
  session_token: 'tok',
  room_code: 'ABC123',
  game_setup: null,
  players: [],
  host_player_id: 1,
  game_state: null,
};

describe('LobbyHomeView', () => {
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
    api.joinRoom.mockReset().mockResolvedValue(joined);
  });

  it('opens on the room list with create and AI replay as its two actions', async () => {
    const onCreateRoom = vi.fn();
    render(<LobbyHomeView onRoomJoined={vi.fn()} onCreateRoom={onCreateRoom} />);

    // The AI replay is a full-width entry card now, so its link carries a description too.
    expect(screen.getByRole('link', { name: /AI 보기/ })).toHaveAttribute('href', '?aiReplay=1');
    fireEvent.click(screen.getByText('방 만들기'));
    expect(onCreateRoom).toHaveBeenCalledOnce();
    await waitFor(() => expect(api.listRooms).toHaveBeenCalled());
  });

  it('shows a message when no rooms are open', async () => {
    render(<LobbyHomeView onRoomJoined={vi.fn()} onCreateRoom={vi.fn()} />);
    await waitFor(() => {
      expect(screen.getByText('지금 대기 중인 방이 없습니다. 위의 방 만들기로 첫 방을 열어보세요.')).toBeInTheDocument();
    });
  });

  it('lists a room by title, host, seats and setup mode, and joins it', async () => {
    api.listRooms.mockResolvedValue([room()]);
    const onRoomJoined = vi.fn();
    render(<LobbyHomeView onRoomJoined={onRoomJoined} onCreateRoom={vi.fn()} />);

    await waitFor(() => expect(screen.getByText('철수님의 방')).toBeInTheDocument());
    expect(screen.getByText('철수')).toBeInTheDocument();
    expect(screen.getByText('ABC123')).toBeInTheDocument();
    expect(screen.getByText('2/4')).toBeInTheDocument();
    expect(screen.getByText('승점 비딩')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('닉네임'), { target: { value: '영희' } });
    fireEvent.click(screen.getByText('참가'));

    await waitFor(() => {
      expect(api.joinRoom).toHaveBeenCalledWith('ABC123', '영희', undefined, undefined);
      expect(onRoomJoined).toHaveBeenCalledOnce();
    });
  });

  it('asks for the password before joining a locked room', async () => {
    api.listRooms.mockResolvedValue([room({ name: '우리끼리', has_password: true })]);
    render(<LobbyHomeView onRoomJoined={vi.fn()} onCreateRoom={vi.fn()} />);

    await waitFor(() => expect(screen.getByText('우리끼리')).toBeInTheDocument());
    expect(screen.getByLabelText('비밀번호가 있는 방')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('닉네임'), { target: { value: '영희' } });
    fireEvent.click(screen.getByText('참가'));

    // Clicking a locked room prompts instead of joining.
    expect(api.joinRoom).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText('우리끼리 · 비밀번호'), { target: { value: 'hunter2' } });
    fireEvent.click(screen.getByText('비밀번호 확인'));

    await waitFor(() => {
      expect(api.joinRoom).toHaveBeenCalledWith('ABC123', '영희', undefined, 'hunter2');
    });
  });

  it('surfaces a rejected password without losing the prompt', async () => {
    api.listRooms.mockResolvedValue([room({ name: '우리끼리', has_password: true })]);
    api.joinRoom.mockRejectedValue(new Error('room password does not match'));
    render(<LobbyHomeView onRoomJoined={vi.fn()} onCreateRoom={vi.fn()} />);

    await waitFor(() => expect(screen.getByText('우리끼리')).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText('닉네임'), { target: { value: '영희' } });
    fireEvent.click(screen.getByText('참가'));
    fireEvent.change(screen.getByLabelText('우리끼리 · 비밀번호'), { target: { value: 'nope' } });
    fireEvent.click(screen.getByText('비밀번호 확인'));

    await waitFor(() => expect(screen.getByText('room password does not match')).toBeInTheDocument());
    expect(screen.getByLabelText('우리끼리 · 비밀번호')).toBeInTheDocument();
  });

  it('asks for a nickname before joining a room from the list', async () => {
    api.listRooms.mockResolvedValue([room()]);
    render(<LobbyHomeView onRoomJoined={vi.fn()} onCreateRoom={vi.fn()} />);

    await waitFor(() => expect(screen.getByText('철수님의 방')).toBeInTheDocument());
    fireEvent.click(screen.getByText('참가'));

    await waitFor(() => expect(screen.getByText('닉네임을 입력해주세요')).toBeInTheDocument());
    expect(api.joinRoom).not.toHaveBeenCalled();
  });

  it('offers the most recent room as a resume shortcut', () => {
    const onResumeRoom = vi.fn();
    render(
      <LobbyHomeView
        onRoomJoined={vi.fn()}
        onCreateRoom={vi.fn()}
        recentRoomCode="ZZ9999"
        onResumeRoom={onResumeRoom}
      />,
    );

    fireEvent.click(screen.getByText('이어하기 · ZZ9999'));
    expect(onResumeRoom).toHaveBeenCalledOnce();
  });
});
