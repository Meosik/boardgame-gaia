import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { SetupRedo } from '../components/SetupRedo';
import { api } from '../api/rest';
import { useRoomStore } from '../store/roomStore';
import type { GameState } from '../types/game';

function state(overrides: Partial<GameState> = {}): GameState {
  return { players: [], ...overrides } as unknown as GameState;
}

describe('SetupRedo', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    useRoomStore.getState().actions.reset();
  });

  it('shows nothing while no setup choice can be taken back', () => {
    const { container } = render(<SetupRedo roomCode="ROOM" sessionToken="token" state={state()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('takes back the latest setup choice at the revision on screen', async () => {
    const setupRedo = vi.spyOn(api, 'setupRedo').mockResolvedValue({ ok: true });
    useRoomStore.getState().actions.setRevision(9);
    render(<SetupRedo roomCode="ROOM" sessionToken="token" state={state({ setup_redo: 2 })} />);
    fireEvent.click(screen.getByRole('button', { name: '내 직전 셋업 선택 되돌리기 (2)' }));
    await waitFor(() => expect(setupRedo).toHaveBeenCalledWith('ROOM', 'token', 9));
  });

  it('shows why a choice was not taken back', async () => {
    vi.spyOn(api, 'setupRedo').mockRejectedValue(new Error('no setup choice can be taken back at this position'));
    render(<SetupRedo roomCode="ROOM" sessionToken="token" state={state({ setup_redo: 1 })} />);
    fireEvent.click(screen.getByRole('button', { name: '내 직전 셋업 선택 되돌리기 (1)' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('no setup choice can be taken back at this position');
  });
});
