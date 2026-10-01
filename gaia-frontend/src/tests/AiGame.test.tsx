import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { CreateRoomView } from '../components/GameLobby/CreateRoomView';
import { api } from '../api/rest';
import { useRoomStore } from '../store/roomStore';

describe('AI game', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    useRoomStore.getState().actions.reset();
  });

  it('starts a game against three AI seats from the create-room view', async () => {
    const createAiGame = vi.spyOn(api, 'createAiGame').mockResolvedValue({
      room_code: 'AI1234',
      player_id: 5,
      session_token: 'token',
      game_setup: null as never,
      game_state: null as never,
      players: [{ player_id: 5, nickname: '나', ready: true }] as never,
      host_player_id: 5,
    });
    const onRoomCreated = vi.fn();
    render(<CreateRoomView onRoomCreated={onRoomCreated} onBack={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('닉네임'), { target: { value: '나' } });
    fireEvent.click(screen.getByRole('button', { name: 'AI 3명과 대전' }));
    await waitFor(() => expect(onRoomCreated).toHaveBeenCalled());
    expect(createAiGame).toHaveBeenCalledWith('나');
    const room = useRoomStore.getState();
    expect(room.roomCode).toBe('AI1234');
    expect(room.playerId).toBe(5);
    expect(room.manualControl).toBe(false);
    expect(room.roomState).toBe('faction_selection');
  });

  it('asks for a nickname before starting', () => {
    const createAiGame = vi.spyOn(api, 'createAiGame');
    render(<CreateRoomView onRoomCreated={vi.fn()} onBack={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'AI 3명과 대전' }));
    expect(createAiGame).not.toHaveBeenCalled();
    expect(screen.getByText('닉네임을 입력해주세요')).toBeInTheDocument();
  });

  it('is not offered in the manual DEV controller flow', () => {
    render(<CreateRoomView manualControl onRoomCreated={vi.fn()} onBack={vi.fn()} />);
    expect(screen.queryByRole('button', { name: 'AI 3명과 대전' })).not.toBeInTheDocument();
  });
});
