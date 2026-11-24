import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AiTurnReview, aiHoldOrigin, aiHoldSpares } from '../components/AiTurnReview';
import { api } from '../api/rest';
import type { AiHold, GameState, PlayerState } from '../types/game';

const players = [
  { player_id: 0, nickname: '나' },
  { player_id: 1, nickname: '영희' },
] as PlayerState[];

/** The moves are plain strings here: a decision without an action is shown as it came. */
function hold(overrides: Partial<AiHold> = {}): AiHold {
  return {
    revision: 7,
    turn: { player: 1, start_revision: 5, revision: 7, decisions: ['자유 행동 A', '본 행동 B'] },
    rejections: 0,
    spares_left: null,
    can_reject: true,
    ...overrides,
  };
}

function state(overrides: Partial<GameState> = {}): GameState {
  return { players, ...overrides } as unknown as GameState;
}

function show(game: GameState) {
  return render(<AiTurnReview roomCode="ROOM" sessionToken="token" state={game} />);
}

describe('AiTurnReview', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows nothing in a game without AI seats', async () => {
    const aiGame = vi.spyOn(api, 'aiGame').mockResolvedValue(false);
    const { container } = show(state({ ai_hold: hold() }));
    await waitFor(() => expect(aiGame).toHaveBeenCalledWith('ROOM'));
    expect(container).toBeEmptyDOMElement();
  });

  it('switches the wait after every AI turn on and off', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    const aiReview = vi.spyOn(api, 'aiReview').mockResolvedValue({ ok: true });
    const { unmount } = show(state());
    const off = await screen.findByRole('checkbox', { name: /AI 차례마다 멈춤/ });
    expect(off).not.toBeChecked();
    expect(screen.queryByRole('button')).toBeNull();
    fireEvent.click(off);
    await waitFor(() => expect(aiReview).toHaveBeenCalledWith('ROOM', 'token', true));
    unmount();

    show(state({ ai_review: true }));
    const on = await screen.findByRole('checkbox', { name: /AI 차례마다 멈춤/ });
    expect(on).toBeChecked();
    fireEvent.click(on);
    await waitFor(() => expect(aiReview).toHaveBeenCalledWith('ROOM', 'token', false));
  });

  it('shows the finished AI turn and lets the AI seats play on', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    const aiContinue = vi.spyOn(api, 'aiContinue').mockResolvedValue({ ok: true });
    show(state({ ai_review: true, ai_hold: hold() }));
    const proceed = await screen.findByRole('button', { name: '계속' });
    const review = screen.getByRole('region', { name: 'AI 차례 검토' });
    expect(review).toHaveTextContent('영희');
    expect(review).toHaveTextContent('자유 행동 A');
    expect(review).toHaveTextContent('본 행동 B');
    expect(review).toHaveTextContent('교사의 첫 선택');
    fireEvent.click(proceed);
    await waitFor(() => expect(aiContinue).toHaveBeenCalledWith('ROOM', 'token'));
  });

  it('rejects the turn at the revision the AI seats wait at', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    const aiReject = vi.spyOn(api, 'aiReject').mockResolvedValue({ ok: true });
    show(state({ ai_review: true, ai_hold: hold({ revision: 12 }) }));
    fireEvent.click(await screen.findByRole('button', { name: '거절' }));
    await waitFor(() => expect(aiReject).toHaveBeenCalledWith('ROOM', 'token', 12));
  });

  it('shows why a rejection failed', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    vi.spyOn(api, 'aiReject').mockRejectedValue(new Error('no other move is left for this AI turn'));
    show(state({ ai_review: true, ai_hold: hold() }));
    fireEvent.click(await screen.findByRole('button', { name: '거절' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('no other move is left for this AI turn');
  });

  it('offers no rejection when no other move is left', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    show(state({ ai_review: true, ai_hold: hold({ rejections: 2, spares_left: 0, can_reject: false }) }));
    expect(await screen.findByRole('button', { name: '거절' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '계속' })).not.toBeDisabled();
    expect(screen.getByRole('region', { name: 'AI 차례 검토' })).toHaveTextContent('남은 예비 수 없음');
  });

  it('says that a rejected turn is being played again', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    show(state({ ai_review: true, ai_replay: { player: 1, start_revision: 8, rejections: 1 } }));
    await screen.findByRole('checkbox');
    const review = screen.getByRole('region', { name: 'AI 차례 검토' });
    expect(review).toHaveTextContent('영희 — 거절된 차례를 다시 두는 중 (거절 1회)');
    expect(screen.queryByRole('button')).toBeNull();
  });
});

describe('aiHoldOrigin and aiHoldSpares', () => {
  it('say where the turn came from and what another rejection would use', () => {
    expect(aiHoldOrigin(hold())).toBe('교사의 첫 선택');
    expect(aiHoldSpares(hold())).toContain('다시 탐색');
    const once = hold({ rejections: 1, spares_left: 2 });
    expect(aiHoldOrigin(once)).toBe('거절한 수를 빼고 다시 탐색한 수');
    expect(aiHoldSpares(once)).toBe('남은 예비 수 2개');
    const twice = hold({ rejections: 2, spares_left: 1 });
    expect(aiHoldOrigin(twice)).toContain('보관해 둔 예비 수(새 탐색 없음) — 첫 수만 예비');
    const single = hold({
      rejections: 2,
      spares_left: 1,
      turn: { player: 1, start_revision: 5, revision: 6, decisions: ['본 행동 B'] },
    });
    expect(aiHoldOrigin(single)).toBe('보관해 둔 예비 수(새 탐색 없음)');
    // The teacher had nothing but the rejected move: its own choice again, no further rejection.
    const none = hold({ rejections: 1, spares_left: null, can_reject: false });
    expect(aiHoldOrigin(none)).toContain('원래 판단대로');
    expect(aiHoldSpares(none)).toBe('다시 거절할 수 없습니다');
  });
});
