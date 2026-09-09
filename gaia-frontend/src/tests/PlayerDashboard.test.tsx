import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ResourcePanel } from '../components/PlayerDashboard/ResourcePanel';
import { PowerCycle } from '../components/PlayerDashboard/PowerCycle';
import { PlayerDashboard } from '../components/PlayerDashboard';
import type { PlayerState, PowerCycle as PowerCycleData, Resources } from '../types/game';

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
    expect(screen.getByText('정보 큐브')).toBeInTheDocument();
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

  it('renders the Taklons Brainstone in its current bowl', () => {
    render(
      <PowerCycle
        power={{ ...mockPower, brainstone: 'Area2' }}
        faction="Taklons"
      />,
    );
    expect(screen.getByTitle('Taklons Brainstone')).toBeInTheDocument();
  });
});

describe('PlayerDashboard', () => {
  it('keeps the faction board, resources, technology and federation holdings together', () => {
    const player: PlayerState = {
      player_id: 0,
      nickname: 'Me',
      faction: 'Taklons',
      resources: mockResources,
      structures: [],
      research_tracks: { terraforming: 0, navigation: 0, ai: 0, gaia: 0, economy: 0, science: 0 },
      vp: 14,
      setup_bid_vp: 0,
      passed: false,
      federation_tokens: [2],
      alliance_tiles: [],
      explored_ships: [],
      exploration_shuttles_available: 3,
      gaiaformers_total: 3,
      gaiaformers_deployed: 0,
      academy_qic_action_used_this_round: false,
      gleens_special_action_used_this_round: false,
      space_giants_special_action_used_this_round: false,
      tech_tiles: [4],
      advanced_tech_tiles: [7],
    };

    render(<PlayerDashboard player={player} />);

    expect(screen.queryByText('Me')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('승점 14점')).not.toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Taklons 종족 보드' })).toBeInTheDocument();
    expect(screen.getByAltText('일반 기술 타일 4')).toBeInTheDocument();
    expect(screen.getByAltText('고급 기술 타일 7')).toBeInTheDocument();
    expect(screen.getByAltText('연방 토큰 2')).toBeInTheDocument();
  });

  it('shows only Gaiaformers that are currently available to deploy', () => {
    const player: PlayerState = {
      player_id: 0,
      nickname: 'Me',
      faction: 'Terrans',
      resources: mockResources,
      structures: [],
      research_tracks: { terraforming: 0, navigation: 0, ai: 0, gaia: 1, economy: 0, science: 0 },
      vp: 10,
      setup_bid_vp: 0,
      passed: false,
      federation_tokens: [],
      alliance_tiles: [],
      explored_ships: [],
      exploration_shuttles_available: 3,
      gaiaformers_total: 3,
      gaiaformers_deployed: 0,
      academy_qic_action_used_this_round: false,
      gleens_special_action_used_this_round: false,
      space_giants_special_action_used_this_round: false,
    };
    const { rerender } = render(<PlayerDashboard player={player} />);
    expect(screen.getAllByLabelText(/사용 가능한 가이아포머/)).toHaveLength(3);

    rerender(
      <PlayerDashboard
        player={{
          ...player,
          resources: { ...player.resources, spent_gaia_formers: 1 },
          gaiaformers_deployed: 1,
          gaiaformers_in_gaia_area: 1,
        }}
      />,
    );
    expect(screen.queryByLabelText(/사용 가능한 가이아포머/)).not.toBeInTheDocument();
  });
});
