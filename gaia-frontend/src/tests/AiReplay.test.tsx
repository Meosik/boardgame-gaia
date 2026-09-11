import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AiReplay } from '../components/AiReplay';
import fixture from './fixtures/replay.json';
import { loadReplay, parseReplay } from '../replay/records';
import { useGameStore } from '../store/gameStore';

vi.mock('../App', () => ({ App: ({ replay }: { replay: { onEventSelect: (index: number) => void; eventStart: number } }) =>
  <button data-event-start={replay.eventStart} onClick={() => replay.onEventSelect(fixture.frames[1].event_end)}>기록 시점 이동</button> }));
vi.mock('../components/RewardMotion', () => ({ RewardMotion: ({ batch, duration }: { batch: { player: number }; duration: number }) =>
  <div data-testid="replay-motion" data-player={batch.player} data-duration={duration} /> }));
vi.mock('../replay/records', async importOriginal => {
  const original = await importOriginal<typeof import('../replay/records')>();
  return { ...original, loadReplay: vi.fn(async () => original.parseReplay(fixture)) };
});
const catalog = { schema_version: 1, games: [{ id: 'one', file: 'one.json.gz', policy: fixture.metadata.policy,
  faction: fixture.metadata.faction, seed: fixture.metadata.seed, vp: 56, steps: 2 }] };
beforeEach(() => {
  vi.mocked(loadReplay).mockReset().mockImplementation(async () => parseReplay(fixture));
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => catalog })));
});
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); useGameStore.getState().actions.reset(); });

describe('AI replay controls', () => {
  it('animates forward steps only and omits motion for seeks, reverse, filters and high speed', async () => {
    const replay = parseReplay(fixture);
    for (const frame of replay.frames) frame.state.round = 1;
    replay.frames[1].state = structuredClone(replay.frames[0].state);
    replay.frames[1].state.players[0].resources.ore += 2;
    replay.frames[2].state = structuredClone(replay.frames[1].state);
    replay.frames[2].state.players[0].resources.ore += 1;
    vi.mocked(loadReplay).mockResolvedValueOnce(replay);
    render(<AiReplay />);
    await screen.findByRole('button', { name: '기록 시점 이동' });
    expect(screen.queryByTestId('replay-motion')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '다음 행동' }));
    expect(await screen.findByTestId('replay-motion')).toHaveAttribute('data-duration', '400');
    fireEvent.click(screen.getByRole('button', { name: '이전 행동' }));
    expect(screen.queryByTestId('replay-motion')).not.toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    await screen.findByTestId('replay-motion');
    fireEvent.change(screen.getByRole('slider'), { target: { value: '2' } });
    expect(screen.queryByTestId('replay-motion')).not.toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    fireEvent.change(screen.getByLabelText('재생 배속'), { target: { value: '2' } });
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 40)); });
    expect(screen.queryByTestId('replay-motion')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('재생 배속'), { target: { value: '1' } });
    expect(screen.queryByTestId('replay-motion')).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole('slider'), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: '다음 행동' }));
    await screen.findByTestId('replay-motion');
    fireEvent.change(screen.getByLabelText('행동 종족'), { target: { value: '0' } });
    expect(screen.queryByTestId('replay-motion')).not.toBeInTheDocument();
  });

  it('autoplay advances without waiting for motion and backward controls cancel it', async () => {
    const replay = parseReplay(fixture);
    for (const frame of replay.frames) frame.state.round = 1;
    replay.frames[1].state.players[0].resources.ore = replay.frames[0].state.players[0].resources.ore + 2;
    vi.mocked(loadReplay).mockResolvedValueOnce(replay);
    render(<AiReplay />);
    await screen.findByRole('button', { name: '기록 시점 이동' });
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole('button', { name: '재생' }));
    act(() => { vi.advanceTimersByTime(1000); });
    expect(screen.getByRole('slider')).toHaveValue('1');
    act(() => { vi.advanceTimersByTime(32); });
    expect(screen.getAllByTestId('replay-motion').length).toBeGreaterThan(0);
    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(screen.getByRole('slider')).toHaveValue('0');
    expect(screen.queryByTestId('replay-motion')).not.toBeInTheDocument();
    act(() => { vi.advanceTimersByTime(2000); });
    expect(screen.getByRole('slider')).toHaveValue('0');
  });

  async function loadMultiActorReplay() {
    const replay = parseReplay(fixture);
    replay.frames = [null, 0, 1, 0, 2].map((player, index) => ({
      ...structuredClone(replay.frames[index === 0 ? 0 : 1]),
      player,
      event_end: Math.min(index, 2),
    }));
    replay.frames[2].state.players[1].resources.credits = 23;
    replay.frames[3].state.players[1].resources.credits = 23;
    replay.metadata.steps = 4;
    const games = ['one', 'two'].map(id => ({ ...catalog.games[0], id, file: `${id}.json.gz`, steps: 4 }));
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({ schema_version: 1, games }) })));
    vi.mocked(loadReplay).mockResolvedValueOnce(replay).mockResolvedValueOnce(replay);
    render(<AiReplay />);
    await screen.findByRole('button', { name: '기록 시점 이동' });
    return replay;
  }

  it('filters buttons and keys without dropping intervening states or changing global seeks', async () => {
    const replay = await loadMultiActorReplay();
    fireEvent.change(screen.getByLabelText('행동 종족'), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: '다음 행동' }));
    expect(screen.getByRole('slider')).toHaveValue('1');
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(screen.getByRole('slider')).toHaveValue('3');
    expect(useGameStore.getState().gameState?.players).toEqual(replay.frames[3].state.players);
    expect(useGameStore.getState().myPlayerId).toBe(replay.metadata.focus_player);
    expect(screen.getByRole('button', { name: '기록 시점 이동' })).toHaveAttribute('data-event-start', '2');
    expect(screen.getByRole('button', { name: '다음 행동' })).toBeDisabled();
    expect(screen.getByText(/선택 종족의 남은 행동 없음/)).toBeInTheDocument();
    expect(screen.queryByText(/게임 종료/)).not.toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(screen.getByRole('slider')).toHaveValue('1');
    fireEvent.click(screen.getByRole('button', { name: '이전 행동' }));
    expect(screen.getByRole('slider')).toHaveValue('0');
    fireEvent.click(screen.getByRole('button', { name: '기록 시점 이동' }));
    expect(screen.getByRole('slider')).toHaveValue('2');
    fireEvent.change(screen.getByRole('slider'), { target: { value: '4' } });
    expect(screen.getByRole('slider')).toHaveValue('4');
  });

  it('autoplays only matching actions, pauses on filter changes and handles absent actions', async () => {
    await loadMultiActorReplay();
    vi.useFakeTimers();
    fireEvent.change(screen.getByLabelText('행동 종족'), { target: { value: '0' } });
    fireEvent.keyDown(window, { key: ' ' });
    act(() => { vi.advanceTimersByTime(1000); });
    expect(screen.getByRole('slider')).toHaveValue('1');
    act(() => { vi.advanceTimersByTime(1000); });
    expect(screen.getByRole('slider')).toHaveValue('3');
    expect(screen.getByRole('button', { name: '재생' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('행동 종족'), { target: { value: 'all' } });
    expect(screen.getByRole('slider')).toHaveValue('3');
    fireEvent.click(screen.getByRole('button', { name: '재생' }));
    fireEvent.change(screen.getByLabelText('행동 종족'), { target: { value: '3' } });
    act(() => { vi.advanceTimersByTime(2000); });
    expect(screen.getByRole('slider')).toHaveValue('3');
    expect(screen.getByRole('button', { name: '재생' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '재생' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('resets action filtering when switching games', async () => {
    await loadMultiActorReplay();
    fireEvent.change(screen.getByLabelText('행동 종족'), { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: '다음 행동' }));
    fireEvent.change(screen.getByLabelText('리플레이 게임'), { target: { value: 'two' } });
    await screen.findByRole('button', { name: '기록 시점 이동' });
    expect(screen.getByLabelText('행동 종족')).toHaveValue('all');
    expect(screen.getByRole('slider')).toHaveValue('0');
  });
  it('starts paused, moves back/forward and seeks via logs without live commands', async () => {
    render(<AiReplay />);
    await screen.findByRole('button', { name: '기록 시점 이동' });
    expect(useGameStore.getState().readOnly).toBe(true);
    expect(screen.getByRole('button', { name: '이전 행동' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '재생' })).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(screen.getByRole('button', { name: '다음 행동' }));
    expect(screen.getByRole('slider', { name: '행동 시점' })).toHaveValue('1');
    fireEvent.click(screen.getByRole('button', { name: '기록 시점 이동' }));
    expect(screen.getByRole('slider', { name: '행동 시점' })).toHaveValue('2');
    expect(screen.getByRole('button', { name: '다음 행동' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: '이전 행동' }));
    expect(screen.getByRole('slider', { name: '행동 시점' })).toHaveValue('1');
    expect(useGameStore.getState().gameState?.players).toEqual(parseReplay(fixture).frames[1].state.players);
  });
  it('respects speed, stops at the end and pauses on manual seek', async () => {
    render(<AiReplay />); await screen.findByRole('button', { name: '기록 시점 이동' });
    vi.useFakeTimers();
    fireEvent.change(screen.getByLabelText('재생 배속'), { target: { value: '4' } });
    fireEvent.click(screen.getByRole('button', { name: '재생' }));
    act(() => { vi.advanceTimersByTime(250); });
    expect(screen.getByRole('slider')).toHaveValue('1');
    act(() => { vi.advanceTimersByTime(250); });
    expect(screen.getByRole('slider')).toHaveValue('2');
    expect(screen.getByRole('button', { name: '재생' })).toBeDisabled();
    fireEvent.change(screen.getByRole('slider'), { target: { value: '0' } });
    expect(screen.getByRole('button', { name: '재생' })).toHaveAttribute('aria-pressed', 'false');
  });
  it('supports bounded keyboard seeking, speed and play/pause without stealing input keys', async () => {
    const { unmount } = render(<AiReplay />);
    await screen.findByRole('button', { name: '기록 시점 이동' });
    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(screen.getByRole('slider')).toHaveValue('0');
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(screen.getByRole('slider')).toHaveValue('1');
    fireEvent.keyDown(window, { key: ' ' });
    expect(screen.getByRole('button', { name: '정지' })).toHaveAttribute('aria-pressed', 'true');
    fireEvent.keyDown(window, { key: ' ', repeat: true });
    expect(screen.getByRole('button', { name: '정지' })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(screen.getByRole('slider')).toHaveValue('0');
    expect(screen.getByRole('button', { name: '재생' })).toHaveAttribute('aria-pressed', 'false');
    for (let i = 0; i < 5; i++) fireEvent.keyDown(window, { key: 'ArrowUp' });
    expect(screen.getByLabelText('재생 배속')).toHaveValue('4');
    for (let i = 0; i < 5; i++) fireEvent.keyDown(window, { key: 'ArrowDown' });
    expect(screen.getByLabelText('재생 배속')).toHaveValue('0.5');
    fireEvent.keyDown(screen.getByLabelText('재생 배속'), { key: 'ArrowRight' });
    fireEvent.keyDown(screen.getByRole('slider'), { key: 'ArrowRight' });
    fireEvent.keyDown(window, { key: 'ArrowRight', ctrlKey: true });
    expect(screen.getByRole('slider')).toHaveValue('0');
    for (let i = 0; i < 5; i++) fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(screen.getByRole('slider')).toHaveValue('2');
    fireEvent.keyDown(window, { key: ' ' });
    expect(screen.getByRole('button', { name: '재생' })).toBeDisabled();
    unmount();
    const event = new KeyboardEvent('keydown', { key: 'ArrowLeft', cancelable: true });
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(false);
  });
  it('shows catalog failures rather than entering a live game', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false })));
    render(<AiReplay />);
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('목록을 불러오지 못했습니다'));
    expect(screen.getByRole('button', { name: '재생' })).toBeDisabled();
  });

  it('narrows the game list to the selected faction and switches off a game that no longer matches', async () => {
    const otherFaction = fixture.metadata.faction === 'Terrans' ? 'Xenos' : 'Terrans';
    const twoFactionCatalog = { schema_version: 1, games: [
      { id: 'one', file: 'one.json.gz', policy: fixture.metadata.policy, faction: fixture.metadata.faction, seed: fixture.metadata.seed, vp: 56, steps: 2 },
      { id: 'two', file: 'two.json.gz', policy: fixture.metadata.policy, faction: otherFaction, seed: fixture.metadata.seed, vp: 12, steps: 2 },
    ] };
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => twoFactionCatalog })));
    render(<AiReplay />);
    await screen.findByRole('button', { name: '기록 시점 이동' });

    const gameSelect = screen.getByLabelText('리플레이 게임') as HTMLSelectElement;
    expect(gameSelect.options).toHaveLength(2);

    fireEvent.change(screen.getByLabelText('종족 필터'), { target: { value: otherFaction } });
    await waitFor(() => expect(gameSelect.options).toHaveLength(1));
    expect(gameSelect.value).toBe('two');
  });
});
