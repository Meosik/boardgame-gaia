import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render } from '@testing-library/react';
import { GameBoard } from '../components/GameBoard';
import { ReplayMarksContext } from '../replay/marks';
import { useGameStore } from '../store/gameStore';
import type { BoardState } from '../types/game';

const board = {
  sectors: [],
  hexes: {
    '0,0': { coord: { q: 0, r: 0 }, planet: null, space_tile_kind: null, structures: [], satellites: [] },
    '1,0': { coord: { q: 1, r: 0 }, planet: null, space_tile_kind: null, structures: [], satellites: [] },
  },
  lost_planet: null,
  spaceship_tiles: {},
} as unknown as BoardState;

beforeEach(() => {
  act(() => useGameStore.getState().actions.reset());
});

describe('replay hex marking', () => {
  it('routes a hex click to onHexMark and skips the normal handling', () => {
    const onHexMark = vi.fn();
    const onHexInspect = vi.fn();
    const { container } = render(
      <ReplayMarksContext.Provider value={{ marks: {}, onHexMark }}>
        <GameBoard board={board} onHexInspect={onHexInspect} />
      </ReplayMarksContext.Provider>,
    );
    const cells = container.querySelectorAll('polygon[points]');
    const clickable = Array.from(cells).map(p => p.closest('g')).filter((g): g is SVGGElement => !!g);
    clickable.forEach(g => fireEvent.click(g));
    expect(onHexMark).toHaveBeenCalledWith({ q: 0, r: 0 });
    expect(onHexMark).toHaveBeenCalledWith({ q: 1, r: 0 });
    expect(onHexInspect).not.toHaveBeenCalled();
  });

  it('renders the label of a mark', () => {
    const { getByTestId } = render(
      <ReplayMarksContext.Provider value={{ marks: { '1,0': '테란S' }, onHexMark: vi.fn() }}>
        <GameBoard board={board} />
      </ReplayMarksContext.Provider>,
    );
    expect(getByTestId('replay-mark-1,0').textContent).toBe('테란S');
  });

  it('changes nothing without the context', () => {
    const onHexInspect = vi.fn();
    const { container, queryByTestId } = render(<GameBoard board={board} onHexInspect={onHexInspect} />);
    expect(queryByTestId('replay-mark-1,0')).toBeNull();
    expect(container.querySelector('.replay-hex-mark')).toBeNull();
    const group = container.querySelector('polygon[points]')?.closest('g');
    fireEvent.click(group!);
    expect(onHexInspect).toHaveBeenCalledTimes(1);
  });
});
