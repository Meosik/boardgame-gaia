import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AiTurnReview, aiHoldOrigin, aiHoldSpares } from '../components/AiTurnReview';
import { api } from '../api/rest';
import { controlledPlayer } from '../devControl';
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
    expect(screen.queryByRole('button', { name: '계속' })).toBeNull();
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
    // Only the moves and the two buttons: nothing about where the move came from.
    expect(review).not.toHaveTextContent('교사의 첫 선택');
    fireEvent.click(proceed);
    await waitFor(() => expect(aiContinue).toHaveBeenCalledWith('ROOM', 'token'));
  });

  it('folds to one line that still says the AI seats wait, and unfolds again', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    show(state({ ai_review: true, ai_hold: hold() }));
    fireEvent.click(await screen.findByRole('button', { name: '접기' }));
    const review = screen.getByRole('region', { name: 'AI 차례 검토' });
    expect(review).toHaveTextContent('영희');
    expect(review).not.toHaveTextContent('자유 행동 A');
    expect(screen.queryByRole('button', { name: '계속' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: '펼치기' }));
    expect(screen.getByRole('button', { name: '계속' })).toBeInTheDocument();
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
    vi.spyOn(api, 'aiReject').mockRejectedValue(new Error('no finished AI turn waits at this position'));
    show(state({ ai_review: true, ai_hold: hold() }));
    fireEvent.click(await screen.findByRole('button', { name: '거절' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('no finished AI turn waits at this position');
  });

  it('says that a rejection without a spare move gives the turn to the player', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    const aiReject = vi.spyOn(api, 'aiReject').mockResolvedValue({ ok: true });
    show(state({ ai_review: true, ai_hold: hold({ rejections: 2, spares_left: 0 }) }));
    const reject = await screen.findByRole('button', { name: '거절하고 직접 두기' });
    expect(reject).not.toBeDisabled();
    expect(screen.getByRole('region', { name: 'AI 차례 검토' })).toHaveTextContent(
      '남은 예비 수 없음 — 다시 거절하면 이 차례를 직접 둡니다',
    );
    fireEvent.click(reject);
    await waitFor(() => expect(aiReject).toHaveBeenCalledWith('ROOM', 'token', 7));
  });

  it('asks the player to play the turn no move of the teacher is left for', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    const game = state({ ai_review: true, ai_takeover: { player: 1, rejections: 3 } });
    show(game);
    await screen.findByRole('checkbox');
    expect(screen.getByRole('region', { name: 'AI 차례 검토' })).toHaveTextContent(
      '영희의 차례를 직접 두세요 — 교사가 낼 다른 수가 없습니다 (거절 3회)',
    );
    expect(screen.queryByRole('button', { name: '계속' })).toBeNull();
    // Until that turn ends the player's commands act for the AI seat.
    expect(controlledPlayer(game, 0)).toBe(1);
    expect(controlledPlayer(state({ ai_review: true }), 0)).toBe(0);
  });

  it('lets the player take back a whole turn they played in the seat\'s place', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    const aiReject = vi.spyOn(api, 'aiReject').mockResolvedValue({ ok: true });
    show(state({ ai_review: true, ai_hold: hold({ revision: 21, rejections: 3, spares_left: 0, by_player: true }) }));
    const again = await screen.findByRole('button', { name: '다시 두기' });
    const review = screen.getByRole('region', { name: 'AI 차례 검토' });
    expect(review).toHaveTextContent('영희의 차례가 끝났습니다 — 내가 대신 둔 차례');
    // Not a move of the teacher: nothing about spares or where the move came from.
    expect(review).not.toHaveTextContent('예비 수');
    expect(screen.queryByRole('button', { name: '거절하고 직접 두기' })).toBeNull();
    expect(screen.getByRole('button', { name: '계속' })).toBeInTheDocument();
    fireEvent.click(again);
    await waitFor(() => expect(aiReject).toHaveBeenCalledWith('ROOM', 'token', 21));
  });

  it('rejects an earlier AI turn after asking once more', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    const turns = [
      { turn: { player: 1, start_revision: 5, revision: 7, decisions: ['오래된 수'] }, round: 1, by_player: false, rejections: 0 },
      { turn: { player: 1, start_revision: 30, revision: 31, decisions: ['최근 수'] }, round: 2, by_player: false, rejections: 0 },
    ];
    const aiTurns = vi.spyOn(api, 'aiTurns').mockResolvedValue({ revision: 40, turns });
    const aiReject = vi.spyOn(api, 'aiReject').mockResolvedValue({ ok: true });
    show(state({ ai_past_turns: 2 }));
    // Nothing is read until the list is opened.
    fireEvent.click(await screen.findByRole('button', { name: '지난 AI 차례 2개 보기' }));
    await waitFor(() => expect(aiTurns).toHaveBeenCalledWith('ROOM', 'token'));
    const review = screen.getByRole('region', { name: 'AI 차례 검토' });
    await waitFor(() => expect(review).toHaveTextContent('1R · 영희 — 오래된 수'));
    // Newest first: the second button belongs to the older turn.
    fireEvent.click(screen.getAllByRole('button', { name: '여기로 되돌리기' })[1]);
    expect(aiReject).not.toHaveBeenCalled();
    expect(review).toHaveTextContent('그 뒤에 둔 수는 내 수까지 모두 사라집니다');
    fireEvent.click(screen.getByRole('button', { name: '되돌려 거절' }));
    await waitFor(() => expect(aiReject).toHaveBeenCalledWith('ROOM', 'token', 40, 5));
  });

  it('says that a rejected turn is being played again', async () => {
    vi.spyOn(api, 'aiGame').mockResolvedValue(true);
    show(state({ ai_review: true, ai_replay: { player: 1, start_revision: 8, rejections: 1 } }));
    await screen.findByRole('checkbox');
    const review = screen.getByRole('region', { name: 'AI 차례 검토' });
    expect(review).toHaveTextContent('영희 — 거절된 차례를 다시 두는 중 (거절 1회)');
    expect(screen.queryByRole('button', { name: '계속' })).toBeNull();
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
    // No spare is left: the next rejection gives the turn to the player.
    expect(aiHoldSpares(hold({ rejections: 2, spares_left: 0 }))).toContain('이 차례를 직접 둡니다');
  });
});
