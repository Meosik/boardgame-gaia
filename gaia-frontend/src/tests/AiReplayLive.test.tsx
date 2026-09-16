import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AiReplay } from '../components/AiReplay';
import { useLiveReplays } from '../replay/useLiveReplays';
import { parseLiveReplay, type LiveGame, type LiveStatus } from '../replay/live';
import fixture from './fixtures/replay.json';
import { useGameStore } from '../store/gameStore';

vi.mock('../App', () => ({ App: () => <div>관전 보드</div> }));
vi.mock('../components/RewardMotion', () => ({ RewardMotion: () => null }));
vi.mock('../replay/useLiveReplays', () => ({ useLiveReplays: vi.fn() }));

function sample(steps: number, revision: number, status: LiveStatus = 'running', id = 'live-0123456789abcdef') {
  const game: LiveGame = { id, file: `${id}-${revision}.json.gz`, policy: fixture.metadata.policy,
    faction: fixture.metadata.faction, seed: fixture.metadata.seed, vp: 0, steps, revision, status, updated_at: 1 };
  const frames = fixture.frames.slice(0, steps + 1);
  const raw = { ...fixture, metadata: { ...fixture.metadata, steps, live_revision: revision, live_status: status },
    frames, events: fixture.events.slice(0, frames[frames.length - 1].event_end) };
  Reflect.deleteProperty(raw.metadata, 'scores');
  return { games: [game], record: parseLiveReplay(raw, game), error: null as string | null };
}

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); useGameStore.getState().actions.reset(); });

async function mount() {
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({ schema_version: 1, games: [] }) })));
  const initial = sample(1, 0);
  vi.mocked(useLiveReplays).mockImplementation(selected => ({ ...initial, record: selected ? initial.record : null }));
  const view = render(<AiReplay />);
  await screen.findByText('관전 보드');
  vi.useFakeTimers();
  return view;
}

describe('approved LIVE/latest-move playback', () => {
  it('automatically selects the next live game while following', async () => {
    const view = await mount();
    const next = sample(2, 0, 'running', 'live-fedcba9876543210');
    const old = sample(1, 0);
    vi.mocked(useLiveReplays).mockImplementation(selected => ({
      ...next, games: [...next.games, ...old.games],
      record: selected === next.games[0].id ? next.record : old.record,
    }));
    view.rerender(<AiReplay />);
    expect(screen.getByLabelText('리플레이 게임')).toHaveValue(next.games[0].id);
    expect(screen.getByRole('slider')).toHaveValue('2');
    expect(screen.getByRole('button', { name: '정지' })).toBeEnabled();
  });

  it('keeps automatic following armed after a game finishes playback', async () => {
    const view = await mount();
    const old = sample(1, 0);
    const game = { ...old.games[0], status: 'complete' as const, revision: 1 };
    const raw = { ...old.record, metadata: { ...old.record.metadata,
      live_status: 'complete', live_revision: 1, scores: fixture.metadata.scores },
      frames: old.record.frames.map((frame, index) => index === 1
        ? { ...frame, state: { ...frame.state, phase: { Ended: { final_scores: [] } } } } : frame) };
    const completed = { games: [game], record: parseLiveReplay(raw, game), error: null };
    vi.mocked(useLiveReplays).mockReturnValue(completed);
    view.rerender(<AiReplay />);
    expect(screen.getByRole('button', { name: '재생' })).toBeDisabled();
    const next = sample(2, 0, 'running', 'live-fedcba9876543210');
    vi.mocked(useLiveReplays).mockImplementation(selected => ({ ...next,
      games: [...next.games, ...completed.games],
      record: selected === next.games[0].id ? next.record : completed.record }));
    view.rerender(<AiReplay />);
    expect(screen.getByLabelText('리플레이 게임')).toHaveValue(next.games[0].id);
  });

  it('keeps a paused game across rollover and LIVE returns to the current game', async () => {
    const view = await mount();
    fireEvent.click(screen.getByRole('button', { name: '정지' }));
    const old = sample(1, 0);
    const next = sample(2, 0, 'running', 'live-fedcba9876543210');
    vi.mocked(useLiveReplays).mockImplementation(selected => ({
      ...next, games: [...next.games, ...old.games],
      record: selected === next.games[0].id ? next.record : old.record,
    }));
    view.rerender(<AiReplay />);
    expect(screen.getByLabelText('리플레이 게임')).toHaveValue(old.games[0].id);
    expect(screen.getByRole('slider')).toHaveValue('1');
    fireEvent.click(screen.getByRole('button', { name: 'LIVE · 최신 수' }));
    expect(screen.getByLabelText('리플레이 게임')).toHaveValue(next.games[0].id);
    expect(screen.getByRole('slider')).toHaveValue('2');
  });

  it('prefers a live game arriving after the saved catalog without overriding manual selection', async () => {
    const saved = { id: 'saved-game', file: 'saved-game.json.gz', policy: fixture.metadata.policy,
      faction: fixture.metadata.faction, seed: fixture.metadata.seed, vp: 0, steps: fixture.metadata.steps };
    vi.stubGlobal('fetch', vi.fn(async (url: string) => new Response(JSON.stringify(
      url.endsWith('/index.json') ? { schema_version: 1, games: [saved] }
        : url.endsWith('.json.gz') ? fixture : {}))));
    vi.mocked(useLiveReplays).mockReturnValue({ games: [], record: null, error: null });
    const view = render(<AiReplay />);
    await screen.findByText('관전 보드');
    expect(screen.getByLabelText('리플레이 게임')).toHaveValue(saved.id);
    const old = sample(1, 0);
    vi.mocked(useLiveReplays).mockImplementation(selected => ({ ...old, record: selected ? old.record : null }));
    view.rerender(<AiReplay />);
    await screen.findByText('관전 보드');
    const next = sample(2, 0, 'running', 'live-fedcba9876543210');
    vi.mocked(useLiveReplays).mockImplementation(selected => ({ ...next, games: [...next.games, ...old.games],
      record: selected === next.games[0].id ? next.record : old.record }));
    view.rerender(<AiReplay />);
    fireEvent.change(screen.getByLabelText('리플레이 게임'), { target: { value: old.games[0].id } });
    view.rerender(<AiReplay />);
    expect(screen.getByLabelText('리플레이 게임')).toHaveValue(old.games[0].id);
  });

  it('opens at the latest action, waits at the edge, then follows each new action', async () => {
    const view = await mount();
    expect(screen.getByRole('slider')).toHaveValue('1');
    expect(screen.getByRole('button', { name: '정지' })).toHaveAttribute('aria-pressed', 'true');
    act(() => { vi.advanceTimersByTime(2000); });
    expect(screen.getByRole('button', { name: '정지' })).toBeEnabled();
    vi.mocked(useLiveReplays).mockReturnValue(sample(2, 1));
    view.rerender(<AiReplay />);
    expect(screen.getByRole('slider')).toHaveValue('1');
    act(() => { vi.advanceTimersByTime(1000); });
    expect(screen.getByRole('slider')).toHaveValue('2');
    expect(useGameStore.getState().readOnly).toBe(true);
  });

  it('keeps a paused view fixed; Play catches up; LIVE clears the actor filter and jumps', async () => {
    const view = await mount();
    fireEvent.click(screen.getByRole('button', { name: '정지' }));
    vi.mocked(useLiveReplays).mockReturnValue(sample(2, 1));
    view.rerender(<AiReplay />);
    act(() => { vi.advanceTimersByTime(3000); });
    expect(screen.getByRole('slider')).toHaveValue('1');
    fireEvent.click(screen.getByRole('button', { name: '재생' }));
    act(() => { vi.advanceTimersByTime(1000); });
    expect(screen.getByRole('slider')).toHaveValue('2');
    fireEvent.click(screen.getByRole('button', { name: '이전 행동' }));
    fireEvent.change(screen.getByLabelText('행동 종족'), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: 'LIVE · 최신 수' }));
    expect(screen.getByRole('slider')).toHaveValue('2');
    expect(screen.getByLabelText('행동 종족')).toHaveValue('all');
    expect(screen.getByRole('button', { name: 'LIVE · 최신 수' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('retains the last valid board on connection trouble and stops a failed recording', async () => {
    const view = await mount();
    vi.mocked(useLiveReplays).mockReturnValue({ ...sample(1, 0), error: '연결 확인 중' });
    view.rerender(<AiReplay />);
    expect(screen.getByText('관전 보드')).toBeInTheDocument();
    expect(screen.getByRole('status', { name: '실시간 연결 상태' })).toHaveTextContent('연결 확인 중');
    vi.mocked(useLiveReplays).mockReturnValue(sample(1, 1, 'failed'));
    view.rerender(<AiReplay />);
    expect(screen.getByRole('button', { name: '재생' })).toBeDisabled();
    expect(screen.getByRole('status', { name: '실시간 연결 상태' })).toHaveTextContent('기록 중단');
  });
});
