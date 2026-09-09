import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import {
  StructureActionPopup,
  upgradeOptionsFor,
} from '../components/StructureActionPopup';
import type { BoardState, PlayerState } from '../types/game';

describe('StructureActionPopup', () => {
  it('offers only Trading Station from a Mine and does not show Tech selection', () => {
    const onUpgrade = vi.fn();
    render(
      <StructureActionPopup
        anchor={{ x: 100, y: 100 }}
        coord={{ q: 2, r: -1 }}
        mode={{ kind: 'structure', structure: 'Mine', faction: 'Terrans' }}
        onUpgrade={onUpgrade}
        onStartFederation={() => undefined}
        onClose={() => undefined}
      />,
    );

    fireEvent.click(screen.getByText('교역소'));
    expect(onUpgrade).toHaveBeenCalledWith('TradingStation');
    expect(screen.queryByText(/기술 타일/)).not.toBeInTheDocument();
    expect(screen.queryByText('연구소')).not.toBeInTheDocument();
  });

  it('follows the faction-specific valid upgrade graph', () => {
    expect(upgradeOptionsFor('TradingStation', 'Terrans').map(({ label }) => label))
      .toEqual(['연구소', '행성의회']);
    expect(upgradeOptionsFor('TradingStation', 'Bescods').map(({ label }) => label))
      .toEqual(['과학 아카데미', '정보 큐브 아카데미']);
    expect(upgradeOptionsFor('PlanetaryInstitute', 'Terrans')).toEqual([]);
  });

  it('shows the physical owned tiles when an Advanced tile needs a cover choice', () => {
    const onCoverTile = vi.fn();
    render(
      <StructureActionPopup
        anchor={{ x: 100, y: 100 }}
        coord={{ q: 0, r: 0 }}
        mode={{ kind: 'choose-cover', tileIds: [2, 5] }}
        onCoverTile={onCoverTile}
        onClose={() => undefined}
      />,
    );

    fireEvent.click(screen.getByLabelText('표준 기술 타일 5 덮기'));
    expect(onCoverTile).toHaveBeenCalledWith(5);
  });

  it('shows upgrade costs and does not enter Tech selection when the upgrade is unaffordable', () => {
    const onUpgrade = vi.fn();
    const player = {
      player_id: 0,
      faction: 'Terrans',
      resources: { ore: 0, credits: 0 },
      structures: [{ hex: { q: 0, r: 0 }, kind: 'TradingStation' }],
    } as PlayerState;
    const board = {
      sectors: [],
      hexes: {},
      lost_planet: null,
      spaceship_tiles: {},
    } as BoardState;
    render(
      <StructureActionPopup
        anchor={{ x: 100, y: 100 }}
        coord={{ q: 0, r: 0 }}
        mode={{ kind: 'structure', structure: 'TradingStation', faction: 'Terrans' }}
        player={player}
        board={board}
        onUpgrade={onUpgrade}
        onStartFederation={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByLabelText('연구소 비용: 광석 3, 크레딧 5')).toBeInTheDocument();
    const researchLab = screen.getByText('연구소').closest('button');
    expect(researchLab).toBeDisabled();
    if (researchLab) fireEvent.click(researchLab);
    expect(onUpgrade).not.toHaveBeenCalled();
  });
});
