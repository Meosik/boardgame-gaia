import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { OpponentPanels } from '../components/OpponentPanels';
import type { PlayerState } from '../types/game';

function mockPlayer(overrides: Partial<PlayerState> = {}): PlayerState {
  return {
    player_id: 1,
    nickname: 'P1',
    faction: 'Xenos',
    resources: {
      ore: 4,
      credits: 15,
      knowledge: 3,
      qic: 1,
      power: { bowl1: 4, bowl2: 4, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 },
      spent_gaia_formers: 0,
    },
    structures: [],
    research_tracks: {
      terraforming: 0,
      navigation: 0,
      ai: 0,
      gaia: 0,
      economy: 0,
      science: 0,
    },
    vp: 10,
    setup_bid_vp: 0,
    passed: false,
    federation_tokens: [],
    alliance_tiles: [],
    explored_ships: [],
    exploration_shuttles_available: 3,
    gaiaformers_total: 3,
    gaiaformers_deployed: 0,
    gaiaformers_in_gaia_area: 0,
    academy_qic_action_used_this_round: false,
    gleens_special_action_used_this_round: false,
    space_giants_special_action_used_this_round: false,
    ...overrides,
  };
}

describe('OpponentPanels', () => {
  it('shows icon resources and opens a full personal board from a player card', () => {
    const players = [
      mockPlayer({ player_id: 1, nickname: 'P1', faction: 'Xenos' }),
      mockPlayer({ player_id: 2, nickname: 'P2', faction: 'Ivits', setup_bid_vp: 7 }),
    ];
    const onPlayerSelect = vi.fn();
    const { container } = render(
      <OpponentPanels players={players} myPlayerId={1} onPlayerSelect={onPlayerSelect} />,
    );

    expect(screen.getByText('P1')).toBeInTheDocument();
    expect(screen.getByText('P2')).toBeInTheDocument();
    expect(screen.getAllByLabelText('광석 4')).toHaveLength(2);
    expect(screen.getAllByLabelText('이번 수입 광석 0')).toHaveLength(2);
    expect(screen.getByLabelText('1번째 행동 순서')).toHaveTextContent('1');
    expect(screen.getByLabelText('2번째 행동 순서')).toHaveTextContent('2');
    expect(screen.getByText('나')).toBeInTheDocument();
    expect(screen.getByLabelText('비딩 감점 7점')).toHaveTextContent('-7점');
    expect(screen.getAllByLabelText('승점 10점')).toHaveLength(2);
    expect(screen.queryByText('비딩 0점')).not.toBeInTheDocument();
    expect(screen.queryByRole('img', { name: 'Xenos 종족 보드' })).not.toBeInTheDocument();
    expect(container.querySelectorAll('.opponent-panel')[0]).toHaveStyle('--player-color: #facc15');
    expect(container.querySelectorAll('.opponent-panel')[1]).toHaveStyle('--player-color: #ef4444');

    screen.getByRole('button', { name: 'P2 개인 보드 보기' }).click();
    expect(onPlayerSelect).toHaveBeenCalledWith(players[1]);
  });

  it('renders nothing when there are no opponents', () => {
    const { container } = render(<OpponentPanels players={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('updates the shown next income after advancing an income research track', () => {
    const player = mockPlayer({
      research_tracks: {
        terraforming: 0,
        navigation: 0,
        ai: 0,
        gaia: 0,
        economy: 1,
        science: 1,
      },
    });
    render(
      <OpponentPanels
        players={[player]}
        round={1}
        events={[
          {
            IncomeReceived: {
              player: 1,
              round: 1,
              ore: 1,
              credits: 3,
              knowledge: 1,
              qic: 0,
              power_charge: 2,
              power_tokens: 0,
              vp: 0,
            },
          },
          { ResearchAdvanced: { player: 1, track: 'Economy', level: 1 } },
          { ResearchAdvanced: { player: 1, track: 'Science', level: 1 } },
        ]}
      />,
    );

    expect(screen.getByLabelText('이번 수입 크레딧 5')).toBeInTheDocument();
    expect(screen.getByLabelText('이번 수입 지식 2')).toBeInTheDocument();
    expect(screen.getByText('이번 수입 충전 3')).toBeInTheDocument();
  });
});
