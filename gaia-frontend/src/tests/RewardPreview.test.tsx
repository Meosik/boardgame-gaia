import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { RewardPreview } from '../components/RewardPreview';
import { useGameStore } from '../store/gameStore';

beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });
const value = (label: string) => screen.getByLabelText(`${label} 수량`).textContent;
describe('isolated reward animation preview', () => {
  it('settles at 1000ms and supports rapid clicks without losing rewards', () => {
    const state = useGameStore.getState();
    const { container } = render(<RewardPreview />);
    fireEvent.click(screen.getByRole('button', { name: '광석 +2' }));
    fireEvent.click(screen.getByRole('button', { name: '광석 +2' }));
    expect(container.querySelectorAll('.reward-preview-flight')).toHaveLength(2);
    expect(container.querySelector('.reward-preview-flight .interaction-resource-token strong')).toHaveTextContent('2');
    expect(value('광석')).toBe('4');
    act(() => vi.advanceTimersByTime(999));
    expect(value('광석')).toBe('4');
    act(() => vi.advanceTimersByTime(1));
    expect(value('광석')).toBe('8');
    expect(container.querySelectorAll('.reward-preview-flight')).toHaveLength(0);
    expect(useGameStore.getState()).toBe(state);
  });
  it('moves mixed rewards together and separately supports VP', () => {
    render(<RewardPreview />);
    fireEvent.click(screen.getByRole('button', { name: '지식 +1 · 크레딧 +3' }));
    fireEvent.click(screen.getByRole('button', { name: '점수 +3' }));
    act(() => vi.advanceTimersByTime(1000));
    expect(value('지식')).toBe('4');
    expect(value('크레딧')).toBe('18');
    expect(value('점수')).toBe('13');
  });
  it('cancels pending rewards on reset and cleans up on unmount', () => {
    const { unmount } = render(<RewardPreview />);
    fireEvent.click(screen.getByRole('button', { name: '광석 +2' }));
    fireEvent.click(screen.getByRole('button', { name: '미리보기 초기화' }));
    act(() => vi.advanceTimersByTime(1000));
    expect(value('광석')).toBe('4');
    fireEvent.click(screen.getByRole('button', { name: '점수 +3' }));
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
  it('settles without a travel delay when reduced motion is requested', () => {
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: true })));
    render(<RewardPreview />);
    fireEvent.click(screen.getByRole('button', { name: '광석 +2' }));
    act(() => vi.advanceTimersByTime(0));
    expect(value('광석')).toBe('6');
  });
});
