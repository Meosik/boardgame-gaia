import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ResourcePanel } from '../components/PlayerDashboard/ResourcePanel';
import { PowerCycle } from '../components/PlayerDashboard/PowerCycle';
import { ResearchTrack } from '../components/PlayerDashboard/ResearchTrack';
import type { PowerCycle as PowerCycleData, ResearchTracks, Resources } from '../types/game';

const mockPower: PowerCycleData = {
  bowl1: 3,
  bowl2: 4,
  bowl3: 2,
  gaia_bowl: 1,
  gaia_forming: 0,
};

const mockResources: Resources = {
  ore: 4,
  credits: 6,
  knowledge: 2,
  qic: 1,
  power: mockPower,
  spent_gaia_formers: 0,
};

const mockTracks: ResearchTracks = {
  terraforming: 2,
  navigation: 1,
  ai: 0,
  gaia: 3,
  economy: 1,
  science: 0,
};

describe('ResourcePanel', () => {
  it('displays all four resources', () => {
    render(<ResourcePanel resources={mockResources} />);
    expect(screen.getByText('4')).toBeInTheDocument(); // ore
    expect(screen.getByText('6')).toBeInTheDocument(); // credits
    expect(screen.getByText('2')).toBeInTheDocument(); // knowledge
    expect(screen.getByText('1')).toBeInTheDocument(); // qic
  });

  it('renders resource labels', () => {
    render(<ResourcePanel resources={mockResources} />);
    expect(screen.getByText('광석')).toBeInTheDocument();
    expect(screen.getByText('크레딧')).toBeInTheDocument();
    expect(screen.getByText('지식')).toBeInTheDocument();
    expect(screen.getByText('QIC')).toBeInTheDocument();
  });
});

describe('PowerCycle', () => {
  it('renders all bowl labels', () => {
    render(<PowerCycle power={mockPower} />);
    expect(screen.getByText('I')).toBeInTheDocument();
    expect(screen.getByText('II')).toBeInTheDocument();
    expect(screen.getByText('III')).toBeInTheDocument();
    expect(screen.getByText('G')).toBeInTheDocument();
  });

  it('does not render GF label when gaia_forming is 0', () => {
    render(<PowerCycle power={mockPower} />);
    expect(screen.queryByText('GF')).not.toBeInTheDocument();
  });

  it('renders GF label when gaia_forming > 0', () => {
    render(<PowerCycle power={{ ...mockPower, gaia_forming: 2 }} />);
    expect(screen.getByText('GF')).toBeInTheDocument();
  });
});

describe('ResearchTrack', () => {
  it('renders all 6 track labels', () => {
    render(<ResearchTrack tracks={mockTracks} />);
    expect(screen.getByText('TF')).toBeInTheDocument();
    expect(screen.getByText('NAV')).toBeInTheDocument();
    expect(screen.getByText('AI')).toBeInTheDocument();
    expect(screen.getByText('GP')).toBeInTheDocument();
    expect(screen.getByText('ECO')).toBeInTheDocument();
    expect(screen.getByText('SCI')).toBeInTheDocument();
  });

  it('renders level values', () => {
    render(<ResearchTrack tracks={mockTracks} />);
    expect(screen.getByText('3')).toBeInTheDocument(); // gaia level
  });
});
