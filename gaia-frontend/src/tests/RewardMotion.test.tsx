import { act, render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { RewardMotion } from '../components/RewardMotion';
import { resourceMotionBatch } from '../components/RewardMotion/rewards';
import { parseReplay } from '../replay/records';
import fixture from './fixtures/replay.json';
const state = () => ({ ...structuredClone(parseReplay(fixture).frames[0].state), round: 1, event_log: [] });
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); });

it('uses the replay duration for both the CSS flight and cost-then-gain timers', () => {
  vi.useFakeTimers();
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({ top: 100, bottom: 140, left: 700, right: 740, width: 40, height: 40 } as DOMRect);
  const { container, unmount } = render(<>
    <div data-reward-player="0"><span data-reward-kind="ore" /><span data-reward-kind="vp" /></div>
    <RewardMotion duration={400} batch={{ id: 1, player: 0,
      costs: [{ kind: 'ore', amount: 2 }], gains: [{ kind: 'vp', amount: 3 }] }} />
  </>);
  expect(container.querySelector('[data-motion-phase="cost"]')).toHaveStyle({ animationDuration: '400ms' });
  expect(container.querySelector('[data-motion-phase="gain"]')).toHaveStyle({ animationDelay: '400ms' });
  act(() => { vi.advanceTimersByTime(400); });
  expect(container.querySelector('[data-motion-phase="cost"]')).toBeNull();
  expect(container.querySelector('[data-motion-phase="gain"]')).not.toBeNull();
  act(() => { vi.advanceTimersByTime(400); });
  expect(container.querySelector('.reward-motion-flight')).toBeNull();
  unmount();
  expect(vi.getTimerCount()).toBe(0);
});

describe('live reward receipts', () => {
  it('separates my costs and gains without semantic free-action duplicates', () => {
    const before = state();
    const after = { ...before, event_log: [
      { ResourceChanged: { player: 0, delta: { ore: -2, credits: 3 } } },
      { FreeActionTaken: { player: 0, kind: 'PowerToCredit', count: 3 } },
      { ResourceChanged: { player: 1, delta: { ore: 9 } } },
      { VpAwarded: { player: 0, amount: 3 } },
      { VpAwarded: { player: 0, amount: -1 } },
      { StructureBuilt: { player: 0, hex: { q: -1, r: 2 } } },
    ] };
    after.players = structuredClone(before.players);
    after.players[0].resources.credits += 3;
    after.players[0].resources.ore -= 2;
    after.players[0].vp += 2;
    expect(resourceMotionBatch(before, after, 0)).toEqual({ player: 0, hex: { q: -1, r: 2 }, gains: [
      { kind: 'credits', amount: 3 }, { kind: 'vp', amount: 3 },
    ], costs: [{ kind: 'ore', amount: 2 }, { kind: 'vp', amount: 1 }] });
  });
  it('does not replay initial/reconnect baselines, duplicates, undo or changed history', () => {
    const before = { ...state(), event_log: [{ VpAwarded: { player: 0, amount: 2 } }] };
    expect(resourceMotionBatch(null, before, 0)).toBeNull();
    expect(resourceMotionBatch(before, structuredClone(before), 0)).toBeNull();
    expect(resourceMotionBatch(before, state(), 0)).toBeNull();
    expect(resourceMotionBatch(before, { ...state(), event_log: [{ VpAwarded: { player: 0, amount: 3 } }, { VpAwarded: { player: 0, amount: 4 } }] }, 0)).toBeNull();
    expect(resourceMotionBatch({ ...state(), round: 0 }, before, 0)).toBeNull();
  });
  it('includes actual income summaries without treating power bowls as spendable gains', () => {
    const before = state();
    const after = { ...before, event_log: [{ IncomeReceived: { player: 0, ore: 2, knowledge: 1, qic: 1, vp: 4, power_charge: 5 } }] };
    after.players = structuredClone(before.players);
    after.players[0].resources.ore += 2;
    after.players[0].resources.knowledge += 1;
    after.players[0].resources.qic += 1;
    after.players[0].vp += 4;
    expect(resourceMotionBatch(before, after, 0)?.gains).toEqual([
      { kind: 'ore', amount: 2 }, { kind: 'knowledge', amount: 1 }, { kind: 'qic', amount: 1 }, { kind: 'vp', amount: 4 },
    ]);
  });
});

it('flies to the specified right-panel player, stays noninteractive and cleans up', () => {
  vi.useFakeTimers();
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({ top: 100, bottom: 140, left: 700, right: 740, width: 40, height: 40 } as DOMRect);
  const { container, rerender, unmount } = render(<><div data-reward-player="0"><span data-reward-kind="ore" /></div><RewardMotion batch={null} /></>);
  const batch = { id: 1, player: 0, gains: [{ kind: 'ore' as const, amount: 2 }], origin: { x: 100, y: 200 } };
  rerender(<><div data-reward-player="0"><span data-reward-kind="ore" /></div><RewardMotion batch={batch} /></>);
  expect(container.querySelector('.reward-motion-layer')).toHaveAttribute('aria-hidden', 'true');
  const flight = container.querySelector('.reward-motion-flight') as HTMLElement;
  expect(flight.style.getPropertyValue('--reward-dx')).toBe('620px');
  expect(flight.querySelector('strong')).toHaveTextContent('2');
  act(() => vi.advanceTimersByTime(999));
  expect(container.querySelector('.reward-motion-flight')).not.toBeNull();
  act(() => vi.advanceTimersByTime(1));
  expect(container.querySelector('.reward-motion-flight')).toBeNull();
  unmount(); expect(vi.getTimerCount()).toBe(0);
});

it('does not animate to a hidden panel or another player', () => {
  const { container } = render(<><div data-reward-player="1"><span data-reward-kind="ore" /></div><RewardMotion batch={{ id: 1, player: 0, gains: [{ kind: 'ore', amount: 2 }] }} /></>);
  expect(container.querySelector('.reward-motion-flight')).toBeNull();
});

it('does not show rewards lost to resource caps', () => {
  const before = state(); before.players[0].resources.knowledge = 15;
  const after = { ...before, event_log: [{ ResourceChanged: { player: 0, delta: { knowledge: 3 } } }] };
  expect(resourceMotionBatch(before, after, 0)).toBeNull();
});

it('keeps actual rewards visible even when a same-action cost makes the net change negative', () => {
  const before = state(); before.players[0].resources.ore = 8;
  const after = { ...before, players: structuredClone(before.players), event_log: [
    { ResourceChanged: { player: 0, delta: { ore: -5 } } },
    { ResourceChanged: { player: 0, delta: { ore: 2 } } },
  ] };
  after.players[0].resources.ore = 5;
  expect(resourceMotionBatch(before, after, 0)?.gains).toEqual([{ kind: 'ore', amount: 2 }]);
});

it('clears in-flight receipts when history is reset, without replaying a duplicate batch', () => {
  vi.useFakeTimers();
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({ top: 100, bottom: 140, left: 700, right: 740, width: 40, height: 40 } as DOMRect);
  const batch = { id: 9, player: 0, gains: [{ kind: 'ore' as const, amount: 1 }] };
  const view = (value: typeof batch | null) => <><div data-reward-player="0"><span data-reward-kind="ore" /></div><RewardMotion batch={value} /></>;
  const { container, rerender } = render(view(batch));
  rerender(view({ ...batch }));
  expect(container.querySelectorAll('.reward-motion-flight')).toHaveLength(1);
  rerender(view(null));
  expect(container.querySelectorAll('.reward-motion-flight')).toHaveLength(0);
  expect(vi.getTimerCount()).toBe(0);
});


it('returns cost-only research and no motion for unchanged snapshots', () => {
  const before = state(); before.players[0].resources.knowledge = 8;
  const after = { ...before, players: structuredClone(before.players), event_log: [
    { ResourceChanged: { player: 0, delta: { knowledge: -4 } } },
    { ResearchAdvanced: { player: 0, track: 'Economy', level: 1 } },
  ] };
  after.players[0].resources.knowledge = 4;
  expect(resourceMotionBatch(before, after, 0)).toMatchObject({ gains: [], costs: [{kind: 'knowledge', amount: 4}] });
  expect(resourceMotionBatch(after, after, 0)).toBeNull();
});

it('plays negative cost tokens panel-to-board before rewards return to the panel', () => {
  vi.useFakeTimers();
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({ top: 100, bottom: 140, left: 700, right: 740, width: 40, height: 40 } as DOMRect);
  const { container, unmount } = render(<><div data-reward-player="0"><span data-reward-kind="ore" /></div>
    <RewardMotion batch={{ id: 1, player: 0, costs: [{ kind: 'ore', amount: 5 }], gains: [{ kind: 'ore', amount: 2 }], origin: { x: 100, y: 200 } }} /></>);
  const cost = container.querySelector('[data-motion-phase="cost"]') as HTMLElement;
  const gain = container.querySelector('[data-motion-phase="gain"]') as HTMLElement;
  expect(cost.style.left).toBe('720px');
  expect(cost.style.getPropertyValue('--reward-dx')).toBe('-620px');
  expect(cost.querySelector('strong')).toHaveTextContent('-5');
  expect(gain.style.animationDelay).toBe('1000ms');
  expect(gain.style.getPropertyValue('--reward-dx')).toBe('620px');
  act(() => vi.advanceTimersByTime(1000));
  expect(container.querySelector('[data-motion-phase="cost"]')).toBeNull();
  expect(container.querySelector('[data-motion-phase="gain"]')).not.toBeNull();
  act(() => vi.advanceTimersByTime(1000));
  expect(container.querySelector('.reward-motion-flight')).toBeNull();
  unmount(); expect(vi.getTimerCount()).toBe(0);
});

it('cancels both expense and delayed reward stages on undo/reset', () => {
  vi.useFakeTimers();
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({ top: 100, bottom: 140, left: 700, right: 740, width: 40, height: 40 } as DOMRect);
  const { container, rerender } = render(<><div data-reward-player="0"><span data-reward-kind="ore" /></div>
    <RewardMotion batch={{ id: 1, player: 0, costs: [{ kind: 'ore', amount: 5 }], gains: [{ kind: 'ore', amount: 2 }] }} /></>);
  act(() => vi.advanceTimersByTime(500));
  rerender(<RewardMotion batch={null} />);
  expect(container.querySelector('.reward-motion-flight')).toBeNull();
  expect(vi.getTimerCount()).toBe(0);
});
