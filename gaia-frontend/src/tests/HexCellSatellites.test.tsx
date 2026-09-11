import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { HexCell } from '../components/GameBoard/HexCell';
import { structureImageSrc } from '../assets/structureImages';
import type { Hex, PlayerId } from '../types/game';

function renderSatellites(owners: PlayerId[], onClick = vi.fn()) {
  const hex: Hex = { coord: { q: -1, r: -2 }, planet: null, space_tile_kind: null,
    structures: [], satellites: owners };
  return render(<svg><HexCell hex={hex} cx={50} cy={50} size={36}
    playerFactions={{ 0: 'Ambas', 1: 'Xenos', 2: 'HadschHallas', 3: 'Terrans' }}
    isHighlighted={false} isSelected={false} isPrintedOnSectorArt isStandardSectorArt
    mutePrintedBackground={false} showPlanetOverlay={false} hasPowerRing={false}
    isDeepSpaceOutline={false} onClick={onClick} /></svg>);
}

describe('shared satellite spaces', () => {
  it('renders no satellite for empty space', () => {
    renderSatellites([]);
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });
  it('preserves the existing single satellite position and size', () => {
    renderSatellites([1]);
    const marker = screen.getByRole('img', { name: '플레이어 2 위성' });
    expect(marker).toHaveAttribute('x', String(50 - 36 * .233));
    expect(marker).toHaveAttribute('y', String(50 - 36 * .57));
    expect(marker).toHaveAttribute('width', String(36 * .475));
  });
  it('renders both red and yellow markers for the reported Xenos replay overlap', () => {
    const onClick = vi.fn();
    renderSatellites([2, 1], onClick);
    const markers = screen.getAllByRole('img');
    expect(markers).toHaveLength(2);
    expect(markers[0]).toHaveAttribute('href', structureImageSrc('red', 'marker'));
    expect(markers[1]).toHaveAttribute('href', structureImageSrc('yellow', 'marker'));
    expect(Number(markers[0].getAttribute('x')) + Number(markers[0].getAttribute('width')))
      .toBeLessThan(Number(markers[1].getAttribute('x')));
    expect(markers[0]).toHaveStyle({ pointerEvents: 'none' });
    fireEvent.click(markers[0].parentElement!);
    expect(onClick).toHaveBeenCalledOnce();
  });
  it.each([3, 4])('keeps %i owners side by side within the hex', count => {
    renderSatellites(([0, 1, 2, 3] as PlayerId[]).slice(0, count));
    const markers = screen.getAllByRole('img');
    expect(markers).toHaveLength(count);
    for (let i = 0; i < markers.length; i++) {
      const x = Number(markers[i].getAttribute('x'));
      const width = Number(markers[i].getAttribute('width'));
      expect(x).toBeGreaterThanOrEqual(50 - 36 * .7);
      expect(x + width).toBeLessThanOrEqual(50 + 36 * .7);
      if (i > 0) expect(x).toBeGreaterThan(Number(markers[i-1].getAttribute('x')) + Number(markers[i-1].getAttribute('width')));
    }
  });
});
