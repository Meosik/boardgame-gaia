import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { FactionBoard } from '../components/PlayerDashboard/FactionBoard';
import type { Structure } from '../types/game';

function structure(kind: Structure['kind']): Structure {
  return { hex: { q: 0, r: 0 }, kind };
}

describe('FactionBoard', () => {
  it('renders the faction-specific board image and no filled slots when nothing is built', () => {
    render(<FactionBoard faction="Terrans" structures={[]} />);

    expect(screen.getByRole('img', { name: 'Terrans 종족 보드' })).toBeInTheDocument();
    expect(screen.queryByLabelText(/확보됨/)).not.toBeInTheDocument();
  });

  it('fills trading-station and research-lab income slots left to right as they are built', () => {
    const structures = [
      structure('TradingStation'),
      structure('TradingStation'),
      structure('ResearchLab'),
    ];
    render(<FactionBoard faction="Ivits" structures={structures} />);

    expect(screen.getByLabelText('교역소 수입 1 확보됨')).toBeInTheDocument();
    expect(screen.getByLabelText('교역소 수입 2 확보됨')).toBeInTheDocument();
    expect(screen.queryByLabelText('교역소 수입 3 확보됨')).not.toBeInTheDocument();
    expect(screen.getByLabelText('연구소 수입 1 확보됨')).toBeInTheDocument();
    expect(screen.queryByLabelText('연구소 수입 2 확보됨')).not.toBeInTheDocument();
  });

  it('marks the planetary institute once built', () => {
    render(<FactionBoard faction="Xenos" structures={[structure('PlanetaryInstitute')]} />);

    expect(screen.getByLabelText('행성 의회 건설됨')).toBeInTheDocument();
  });
});
