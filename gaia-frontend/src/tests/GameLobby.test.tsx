import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { HomeView } from '../components/GameLobby/HomeView';
import { JoinRoomView } from '../components/GameLobby/JoinRoomView';
import { useRoomStore } from '../store/roomStore';

describe('HomeView', () => {
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
  });

  it('renders room code and nickname inputs', () => {
    render(<JoinRoomView onRoomJoined={vi.fn()} onBack={vi.fn()} />);
    expect(screen.getByLabelText('룸 코드')).toBeInTheDocument();
    expect(screen.getByLabelText('닉네임')).toBeInTheDocument();
  });

  it('shows error when join attempted with empty fields', async () => {
    render(<JoinRoomView onRoomJoined={vi.fn()} onBack={vi.fn()} />);
    fireEvent.click(screen.getByText('참가하기'));
    await waitFor(() => {
      expect(screen.getByText('룸 코드를 입력해주세요')).toBeInTheDocument();
    });
  });

  it('calls onBack when back button clicked', () => {
    const onBack = vi.fn();
    render(<JoinRoomView onRoomJoined={vi.fn()} onBack={onBack} />);
    fireEvent.click(screen.getByText('뒤로'));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('uppercases room code input', () => {
    render(<JoinRoomView onRoomJoined={vi.fn()} onBack={vi.fn()} />);
    const codeInput = screen.getByLabelText('룸 코드') as HTMLInputElement;
    fireEvent.change(codeInput, { target: { value: 'abcd12' } });
    expect(codeInput.value).toBe('ABCD12');
  });
});
