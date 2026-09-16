import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AiReplay } from '../components/AiReplay';
import { GameLog } from '../components/GameLog';
import { useGameStore } from '../store/gameStore';
import { loadReplay, parseReplay } from '../replay/records';
import type { GameEvent } from '../types/game';
import fixture from './fixtures/replay.json';
import native from './fixtures/xenos140Settlement.json';

vi.mock('../App', () => ({ App: ({ replay }: { replay: { events: GameEvent[]; eventStart: number; eventEnd: number; onEventSelect: (index: number) => void } }) => {
  const state = useGameStore(s => s.gameState);
  return <><div id="game-round-boosters" /><div id="game-research" />{state && <GameLog
    events={replay.events} players={state.players} board={state.board} onEventSelect={replay.onEventSelect}
    activeEventRange={[replay.eventStart, replay.eventEnd]} />}</>;
} }));
vi.mock('../components/RewardMotion', () => ({ RewardMotion: ({ batch }: { batch: { player: number; gains: { amount: number }[] } }) =>
  <div data-testid="settlement-motion" data-player={batch.player} data-amount={batch.gains[0]?.amount ?? 0} /> }));
vi.mock('../replay/records', async original => ({ ...await original<typeof import('../replay/records')>(), loadReplay: vi.fn() }));

function completedRecord() {
  // Navigation fixture with an actual native terminal state, not a simulated game.
  const record = parseReplay(fixture);
  const end = parseReplay({ ...fixture, metadata: { ...fixture.metadata, steps: 0 }, events: [],
    frames: [{ ...fixture.frames[0], state: native.state, event_end: 0 }] }).frames[0].state;
  record.frames[2] = { ...record.frames[2], state: end, action: { type: 'Pass' }, player: 2 };
  return record;
}

beforeEach(() => {
  vi.mocked(loadReplay).mockReset().mockResolvedValue(completedRecord());
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({ schema_version: 1,
    games: [{ id: 'end', file: 'end.json.gz', policy: fixture.metadata.policy, faction: fixture.metadata.faction,
      seed: fixture.metadata.seed, vp: 140, steps: 2 }] }) })));
});
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); useGameStore.getState().actions.reset(); });

async function openFinalAction() {
  render(<AiReplay />);
  await waitFor(() => expect(screen.getByRole('slider')).toHaveAttribute('max', '7'));
  fireEvent.change(screen.getByRole('slider'), { target: { value: '2' } });
}

describe('final settlement through existing replay controls', () => {
  it('shows five stages and cumulative native-verified totals, then rewinds to the original action', async () => {
    const original = completedRecord();
    vi.mocked(loadReplay).mockResolvedValueOnce(original);
    const before = JSON.stringify(original);
    await openFinalAction();
    expect(useGameStore.getState().gameState?.players[2].vp).toBe(76);
    for (const [index, vp] of [94, 112, 140, 140, 140].entries()) {
      fireEvent.click(screen.getByRole('button', { name: '다음 행동' }));
      expect(screen.getByRole('slider')).toHaveValue(String(index + 3));
      expect(useGameStore.getState().gameState?.players[2].vp).toBe(vp);
      expect(screen.getByText(`2 / 2 행동 · 정산 ${index + 1}/5`)).toBeInTheDocument();
    }
    expect(within(screen.getByRole('status')).getByText('최종 순위')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '다음 행동' })).toBeDisabled();
    for (const vp of [140, 140, 112, 94, 76]) {
      fireEvent.click(screen.getByRole('button', { name: '이전 행동' }));
      expect(useGameStore.getState().gameState?.players[2].vp).toBe(vp);
    }
    expect(JSON.stringify(original)).toBe(before);
    expect(useGameStore.getState().readOnly).toBe(true);
  });

  it('keeps global awards reachable with a faction filter and seeks them from logs', async () => {
    await openFinalAction();
    fireEvent.change(screen.getByLabelText('행동 종족'), { target: { value: '0' } });
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(screen.getByRole('slider')).toHaveValue('3');
    const logs = screen.getAllByRole('button', { name: /종료 목표 2.*시점으로 이동/ });
    fireEvent.click(logs[0]);
    expect(screen.getByRole('slider')).toHaveValue('4');
    expect(useGameStore.getState().gameState?.players[2].vp).toBe(112);
    fireEvent.change(screen.getByLabelText('라운드 선택'), { target: { value: '6' } });
    expect(screen.getByRole('slider')).toHaveValue('2');
    expect(useGameStore.getState().gameState?.players[2].vp).toBe(76);
    expect(screen.getByLabelText('행동 종족')).toHaveValue('0');
  });

  it('autoplays through settlement, stops at the final rank, and preserves pause on seek', async () => {
    await openFinalAction();
    vi.useFakeTimers();
    fireEvent.click(screen.getByRole('button', { name: '재생' }));
    for (let cursor = 3; cursor <= 7; cursor++) {
      act(() => { vi.advanceTimersByTime(1000); });
      expect(screen.getByRole('slider')).toHaveValue(String(cursor));
    }
    expect(screen.getByRole('button', { name: '재생' })).toBeDisabled();
    fireEvent.change(screen.getByRole('slider'), { target: { value: '3' } });
    expect(screen.getByRole('button', { name: '재생' })).toHaveAttribute('aria-pressed', 'false');
    expect(screen.queryAllByTestId('settlement-motion')).toHaveLength(0);
  });

  it('animates the verified awards only when moving forward at normal speed', async () => {
    await openFinalAction();
    fireEvent.click(screen.getByRole('button', { name: '다음 행동' }));
    await waitFor(() => expect(screen.getAllByTestId('settlement-motion').find(e => e.dataset.player === '2'))
      .toHaveAttribute('data-amount', '18'));
    fireEvent.click(screen.getByRole('button', { name: '이전 행동' }));
    expect(screen.queryAllByTestId('settlement-motion')).toHaveLength(0);
    fireEvent.change(screen.getByLabelText('재생 배속'), { target: { value: '2' } });
    fireEvent.click(screen.getByRole('button', { name: '다음 행동' }));
    expect(screen.queryAllByTestId('settlement-motion')).toHaveLength(0);
  });

  it('keeps the original replay usable and labels an unmatched breakdown instead of awarding made-up points', async () => {
    const record = completedRecord();
    const phase = record.frames[2].state.phase;
    if (typeof phase === 'object' && 'Ended' in phase) phase.Ended.final_scores[2][1]++;
    vi.mocked(loadReplay).mockResolvedValueOnce(record);
    render(<AiReplay />);
    await screen.findByText(/정산 내역이 기록된 최종 점수와 일치하지 않아/);
    expect(screen.getByRole('slider')).toHaveAttribute('max', '2');
    fireEvent.change(screen.getByRole('slider'), { target: { value: '2' } });
    expect(useGameStore.getState().gameState?.players[2].vp).toBe(76);
  });
});
