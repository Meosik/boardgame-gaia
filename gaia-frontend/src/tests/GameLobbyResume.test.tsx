import { beforeEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { GameLobby } from '../components/GameLobby';
import { rememberRoom } from '../store/recentRoom';
import { useRoomStore } from '../store/roomStore';

vi.mock('../components/GameLobby/WaitingRoomView', () => ({ WaitingRoomView: () => <div>기존 방 연결</div> }));
vi.mock('../components/GameLobby/CreateRoomView', () => ({ CreateRoomView: () => <div>새 방 만들기</div> }));

beforeEach(() => {
  useRoomStore.getState().actions.reset();
  localStorage.clear();
});

it('resumes a saved DEV room instead of starting creation after rehydration', async () => {
  useRoomStore.setState({ roomCode: 'DEV001', sessionToken: 'test-session', playerId: 0 });
  useRoomStore.setState({ roomCode: null }, false);
  sessionStorage.setItem('gaia-room-session', JSON.stringify({ state: {
    roomCode: 'DEV001', sessionToken: 'test-session', playerId: 0, nickname: 'DEV',
  }, version: 0 }));
  await useRoomStore.persist.rehydrate();
  render(<GameLobby manualControl onGameStart={vi.fn()} />);
  expect(screen.getByText('기존 방 연결')).toBeInTheDocument();
  expect(screen.queryByText('새 방 만들기')).not.toBeInTheDocument();
});

it('still opens creation for DEV without a saved room', () => {
  render(<GameLobby manualControl onGameStart={vi.fn()} />);
  expect(screen.getByText('새 방 만들기')).toBeInTheDocument();
});

it('offers resume after closing the tab and restores the saved seat only when clicked', () => {
  rememberRoom({ roomCode: 'DEV002', playerId: 4, sessionToken: 'saved-session', nickname: 'Tester', manualControl: true });
  sessionStorage.clear();
  render(<GameLobby manualControl onGameStart={vi.fn()} />);
  expect(useRoomStore.getState().roomCode).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '이어하기 · DEV002' }));
  expect(screen.getByText('기존 방 연결')).toBeInTheDocument();
  expect(useRoomStore.getState()).toMatchObject({ roomCode: 'DEV002', playerId: 4, sessionToken: 'saved-session', manualControl: true });
});

it('keeps the active tab seat even when another room is saved as recent', () => {
  useRoomStore.setState({ roomCode: 'ACTIVE', playerId: 1, sessionToken: 'active-session' });
  rememberRoom({ roomCode: 'OTHER', playerId: 2, sessionToken: 'other-session', nickname: 'Other', manualControl: false });
  render(<GameLobby onGameStart={vi.fn()} />);
  expect(screen.getByText('기존 방 연결')).toBeInTheDocument();
  expect(useRoomStore.getState()).toMatchObject({ roomCode: 'ACTIVE', playerId: 1, sessionToken: 'active-session' });
});
