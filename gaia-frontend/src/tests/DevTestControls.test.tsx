import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DevTestControls } from '../components/DevTestControls';
import { api } from '../api/rest';
import { useRoomStore } from '../store/roomStore';
import { readRecentRoom, rememberRoom } from '../store/recentRoom';

vi.mock('../api/rest', () => ({ api: { devTool: vi.fn() } }));
describe('temporary DEV controls', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
    useRoomStore.getState().actions.reset();
    useRoomStore.setState({ manualControl: true, roomCode: 'TEST', sessionToken: 'test-token', revision: 7 });
  });
  it('refills through the authenticated revisioned endpoint', async () => {
    vi.mocked(api.devTool).mockResolvedValue({});
    render(<DevTestControls refillDisabled={false} />);
    fireEvent.click(screen.getByText('테스트 자원 보충'));
    await screen.findByRole('status');
    expect(api.devTool).toHaveBeenCalledWith('TEST', 'test-token', 7, 'refill');
    expect(screen.getByRole('status')).toHaveTextContent('파워 I/II/III 각 10개');
  });
  it('blocks refill during an action selection', () => {
    render(<DevTestControls refillDisabled />);
    expect(screen.getByText('테스트 자원 보충')).toBeDisabled();
    expect(screen.getByText('테스트 방 삭제')).toBeEnabled();
  });
  it('keeps the room and Continue record when deletion fails', async () => {
    rememberRoom({ roomCode: 'TEST', playerId: 1, sessionToken: 'test-token', nickname: 'DEV', manualControl: true });
    vi.mocked(api.devTool).mockRejectedValue(new Error('offline'));
    render(<DevTestControls refillDisabled={false} />);
    fireEvent.click(screen.getByText('테스트 방 삭제'));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('처리하지 못했습니다'));
    expect(useRoomStore.getState().roomCode).toBe('TEST');
    expect(readRecentRoom()?.roomCode).toBe('TEST');
  });
  it('does not send requests for ordinary rooms', () => {
    useRoomStore.setState({ manualControl: false });
    render(<DevTestControls refillDisabled={false} />);
    fireEvent.click(screen.getByText('테스트 방 삭제'));
    expect(api.devTool).not.toHaveBeenCalled();
  });
});
