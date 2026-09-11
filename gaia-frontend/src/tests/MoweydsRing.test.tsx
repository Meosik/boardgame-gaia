import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { HexCell } from '../components/GameBoard/HexCell';
import { ReplayHighlightContext, type ReplayHighlight } from '../replay/highlight';
import type { Hex, StructureType } from '../types/game';

const highlight: ReplayHighlight = { player: 0, faction: 'Moweyds', actionType: 'Build', label: '',
  standardTech: new Set(), advancedTech: new Set(), hexes: new Set(['0,0']),
  research: new Set(), powerAction: null, ship: null, booster: null };
function setup(kind: StructureType, ring: boolean, replay: boolean) {
  const hex: Hex = { coord: { q: 0, r: 0 }, planet: null, space_tile_kind: null,
    structures: [{ owner: 0, kind }], satellites: [] };
  return render(<ReplayHighlightContext.Provider value={replay ? highlight : null}><svg>
    <HexCell hex={hex} cx={100} cy={100} size={50} playerFactions={{ 0: 'Moweyds' }}
      isHighlighted={false} isSelected={false} isPrintedOnSectorArt={false} isStandardSectorArt={false}
      mutePrintedBackground={false} showPlanetOverlay={false} hasPowerRing={ring}
      isDeepSpaceOutline={false} onClick={vi.fn()} />
  </svg></ReplayHighlightContext.Provider>);
}
describe('Moweyds ring placement', () => {
  const kinds: StructureType[] = ['Mine', 'TradingStation', 'ResearchLab', 'PlanetaryInstitute', { Academy: 'Qic' }];
  it.each(kinds.flatMap(kind => [false, true].map(replay => ({ kind, replay }))))(
    'keeps $kind inside its ring (replay=$replay)', ({ kind, replay }) => {
      const { container } = setup(kind, true, replay);
      const ring = screen.getByLabelText('모웨이드 파워 링 · 건물 파워값 +2');
      expect(ring.getAttribute('href')).toContain('moweyds-power-ring');
      expect(ring).toHaveStyle({ pointerEvents: 'none' });
      expect(Number(ring.getAttribute('width'))).toBe(78);
      const building = screen.getByLabelText('구조물');
      expect(building).toHaveAttribute('width', '37');
      expect(building).toHaveAttribute('x', '81.5');
      expect(building).toHaveAttribute('y', '81.5');
      const images: Element[] = [...container.querySelectorAll('image')];
      expect(images.indexOf(ring)).toBeLessThan(images.indexOf(building));
    },
  );
  it('does not change buildings without rings', () => {
    setup('Mine', false, false);
    expect(screen.queryByLabelText('모웨이드 파워 링 · 건물 파워값 +2')).toBeNull();
    expect(screen.getByLabelText('구조물')).toHaveAttribute('width', '39.6');
  });
});
