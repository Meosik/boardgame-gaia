import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { HexCell } from '../components/GameBoard/HexCell';
import { ReplayHighlightContext, type ReplayHighlight } from '../replay/highlight';

describe('Ivits station planet-scale placement', () => {
  it.each([false, true])('centers the enlarged station without moving shared satellites (replay=%s)', replay => {
    const highlight: ReplayHighlight = { player: 0, faction: 'Ivits', actionType: 'IvitsPlaceSpaceStation',
      label: '', standardTech: new Set(), advancedTech: new Set(), hexes: new Set(), research: new Set(),
      powerAction: null, ship: null, booster: null };
    render(<ReplayHighlightContext.Provider value={replay ? highlight : null}><svg>
      <HexCell hex={{ coord: { q: 0, r: 0 }, planet: null, space_tile_kind: null,
        structures: [{ owner: 0, kind: 'SpaceStation' }], satellites: [1, 2, 3] }}
        cx={100} cy={100} size={50} playerFactions={{ 0: 'Ivits', 1: 'Xenos', 2: 'Terrans', 3: 'Itars' }}
        isHighlighted={false} isSelected={false} isPrintedOnSectorArt={false} isStandardSectorArt={false}
        mutePrintedBackground={false} showPlanetOverlay={false} hasPowerRing={false}
        emphasizeStructure isDeepSpaceOutline={false} onClick={vi.fn()} />
    </svg></ReplayHighlightContext.Provider>);
    const station = screen.getByRole('img', { name: '이비츠 우주 정거장' });
    expect(station).toHaveAttribute('x', '70');
    expect(station).toHaveAttribute('y', '70');
    expect(station).toHaveAttribute('width', '60');
    expect(station).toHaveAttribute('height', '60');
    const satellites = screen.getAllByRole('img', { name: /플레이어 .* 위성/ });
    expect(satellites).toHaveLength(3);
    satellites.forEach(satellite => expect(satellite).toHaveAttribute('y', '71.5'));
  });
});
