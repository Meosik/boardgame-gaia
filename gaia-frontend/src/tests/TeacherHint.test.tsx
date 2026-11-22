import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { TeacherHint, hintHexes } from '../components/TeacherHint';
import { api, type AiHintReply } from '../api/rest';
import { useRoomStore } from '../store/roomStore';
import type { GameState } from '../types/game';

// The label of a coordinate needs a board; these tests have none.
vi.mock('../hexLocation', () => ({ hexLocationLabel: () => '칸' }));

// A decision without coordinates, so its label does not need a board.
const decision = { phase: 'Game', action: { type: 'Pass', booster_id: 3 } };
const state = {} as GameState;

describe('hintHexes', () => {
  it('finds no hex in a move without coordinates', () => {
    expect(hintHexes(decision)).toEqual([]);
  });

  it('collects every hex of the move once, in the order found', () => {
    const federation = {
      phase: 'Game',
      action: {
        type: 'FormFederation',
        hexes: [{ q: 1, r: -1 }, { q: 2, r: 0 }],
        satellite_hexes: [{ q: 1, r: 0 }],
        bonus_build_coord: { q: 1, r: -1 },
        token: 3,
      },
    };
    expect(hintHexes(federation)).toEqual([{ q: 1, r: -1 }, { q: 2, r: 0 }, { q: 1, r: 0 }]);
  });
});

describe('teacher hint', () => {
  beforeEach(() => {
    useRoomStore.setState({ revision: 5 });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    useRoomStore.getState().actions.reset();
  });

  it('is not offered outside AI games', async () => {
    const aiGame = vi.spyOn(api, 'aiGame').mockResolvedValue(false);
    render(<TeacherHint roomCode="ROOM01" sessionToken="token" state={state} />);
    await waitFor(() => expect(aiGame).toHaveBeenCalledWith('ROOM01'));
    expect(screen.queryByRole('button', { name: '교사 수 보기' })).not.toBeInTheDocument();
  });

  it('asks for the revision on screen and shows the move until the position changes', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    const aiHint = vi.spyOn(api, 'aiHint').mockResolvedValue({ revision: 5, decision });
    render(<TeacherHint roomCode="ROOM01" sessionToken="token" state={state} />);
    fireEvent.click(await screen.findByRole('button', { name: '교사 수 보기' }));
    expect(await screen.findByText(/부스터: 3/)).toBeInTheDocument();
    expect(aiHint).toHaveBeenCalledWith('ROOM01', 'token', 5);

    act(() => {
      useRoomStore.setState({ revision: 6 });
    });
    expect(screen.queryByText(/부스터: 3/)).not.toBeInTheDocument();
  });

  it('reports the hexes of the shown move to the map and clears them when the position changes', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    vi.spyOn(api, 'aiHint').mockResolvedValue({
      revision: 5,
      decision: {
        phase: 'Game',
        action: { type: 'FreeAction', kind: 'PowerToOre', count: 1, target: { q: 3, r: -1 } },
      },
    });
    const onHexes = vi.fn();
    render(<TeacherHint roomCode="ROOM01" sessionToken="token" state={state} onHexes={onHexes} />);
    fireEvent.click(await screen.findByRole('button', { name: '교사 수 보기' }));
    expect(await screen.findByText(/지도에 초록 점선으로 표시/)).toBeInTheDocument();
    expect(onHexes).toHaveBeenLastCalledWith([{ q: 3, r: -1 }]);

    act(() => {
      useRoomStore.setState({ revision: 6 });
    });
    expect(onHexes).toHaveBeenLastCalledWith([]);
  });

  it('drops an answer that arrives after the position changed', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    let answer!: (reply: AiHintReply) => void;
    vi.spyOn(api, 'aiHint').mockReturnValue(
      new Promise<AiHintReply>((resolve) => {
        answer = resolve;
      }),
    );
    render(<TeacherHint roomCode="ROOM01" sessionToken="token" state={state} />);
    fireEvent.click(await screen.findByRole('button', { name: '교사 수 보기' }));
    expect(await screen.findByRole('button', { name: '교사가 생각 중…' })).toBeDisabled();

    act(() => {
      useRoomStore.setState({ revision: 6 });
    });
    // The new position can be asked about at once; the old request is still on its way.
    expect(screen.getByRole('button', { name: '교사 수 보기' })).toBeEnabled();
    await act(async () => {
      answer({ revision: 5, decision });
    });
    expect(screen.queryByText(/부스터: 3/)).not.toBeInTheDocument();
  });

  it('shows why no hint came', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    vi.spyOn(api, 'aiHint').mockRejectedValue(new Error('지금은 내 차례가 아닙니다.'));
    render(<TeacherHint roomCode="ROOM01" sessionToken="token" state={state} />);
    fireEvent.click(await screen.findByRole('button', { name: '교사 수 보기' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('지금은 내 차례가 아닙니다.');
  });
});
