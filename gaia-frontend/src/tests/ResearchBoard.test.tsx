import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ResearchBoard } from '../components/PlayerDashboard/ResearchBoard';
import type { PlayerState, ResearchBoard as ResearchBoardState } from '../types/game';

function mockPlayer(overrides: Partial<PlayerState> = {}): PlayerState {
  return {
    player_id: 0,
    nickname: 'P0',
    faction: 'Terrans',
    resources: {
      ore: 4,
      credits: 15,
      knowledge: 3,
      qic: 1,
      power: { bowl1: 4, bowl2: 4, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 },
      spent_gaia_formers: 0,
    },
    structures: [],
    research_tracks: { terraforming: 0, navigation: 0, ai: 0, gaia: 0, economy: 0, science: 0 },
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

describe('ResearchBoard', () => {
  const board: ResearchBoardState = {
    tracks: {} as ResearchBoardState['tracks'],
    tech_tiles: [],
    tech_tile_slots: [2, 3, 4, 5, 6, 7, 8, 9, 10],
    advanced_tech_tiles: [1, 2, 3, 4, 5, 6],
    terraforming_level_5_token: 4,
    federation_tokens: [],
  };

  it('lays out all starting Tech tiles and covers the three obsolete 정보 큐브 actions', () => {
    render(<ResearchBoard players={[]} board={board} />);

    expect(screen.getAllByAltText(/표준 기술 타일/)).toHaveLength(9);
    for (const standardTile of screen.getAllByAltText(/표준 기술 타일/)) {
      expect(parseFloat(standardTile.style.top)).toBeLessThan(83.4);
    }
    const advancedTiles = screen.getAllByAltText(/고급 기술 타일/);
    expect(advancedTiles).toHaveLength(6);
    // Each socket's own measured center (see `ADVANCED_TECH_SLOTS`'s comment) — no longer a
    // shared xPct plus a small per-column pixel nudge.
    const expectedAdvancedLeft = [10.53, 27.81, 44.5, 60.48, 76.72, 92.58];
    const expectedAdvancedTop = [13.92, 13.92, 14.15, 13.96, 14.04, 14.0];
    advancedTiles.forEach((tile, index) => {
      expect(parseFloat(tile.style.left)).toBeCloseTo(expectedAdvancedLeft[index], 4);
      expect(parseFloat(tile.style.top)).toBeCloseTo(expectedAdvancedTop[index], 4);
    });
    expect(screen.getByAltText(/기존 정보 큐브 액션 3개 폐쇄/)).toBeInTheDocument();
    expect(screen.getByAltText('테라포밍 5레벨 연방 토큰 4')).toBeInTheDocument();
    expect(screen.getByAltText('항법 5레벨 검은 행성 토큰')).toBeInTheDocument();
  });

  it('removes the reserved Terraforming reward after it has been claimed', () => {
    render(
      <ResearchBoard
        players={[]}
        board={{ ...board, terraforming_level_5_token: null }}
      />,
    );

    expect(screen.queryByAltText(/테라포밍 5레벨 연방 토큰/)).not.toBeInTheDocument();
  });

  it('removes the Lost Planet token after a player reaches Navigation level 5', () => {
    const players = [mockPlayer({
      research_tracks: { terraforming: 0, navigation: 5, ai: 0, gaia: 0, economy: 0, science: 0 },
    })];

    render(<ResearchBoard players={players} board={board} />);

    expect(screen.queryByAltText('항법 5레벨 검은 행성 토큰')).not.toBeInTheDocument();
  });

  it('renders the shared board image and one token per player per track', () => {
    const players = [
      mockPlayer({ player_id: 0, nickname: 'P0', faction: 'Terrans' }),
      mockPlayer({
        player_id: 1,
        nickname: 'P1',
        faction: 'Xenos',
        research_tracks: { terraforming: 3, navigation: 0, ai: 0, gaia: 0, economy: 0, science: 5 },
      }),
    ];
    render(<ResearchBoard players={players} />);

    expect(screen.getByRole('img', { name: '연구판' })).toBeInTheDocument();
    // 6 tracks x 2 players = 12 tokens
    expect(screen.getAllByLabelText(/레벨/)).toHaveLength(12);
    expect(screen.getByLabelText('P1 · Xenos · 테라포밍 3레벨')).toHaveAttribute(
      'title',
      'P1 · Xenos · 테라포밍 3레벨',
    );
    expect(screen.getByLabelText('P1 · Xenos · 과학 5레벨')).toBeInTheDocument();
  });

  it('skips players who have not picked a faction yet', () => {
    const players = [
      mockPlayer({ player_id: 0, faction: 'Terrans' }),
      mockPlayer({ player_id: 1, faction: null }),
    ];
    render(<ResearchBoard players={players} />);

    expect(screen.getAllByLabelText(/레벨/)).toHaveLength(6);
  });

  it('clamps out-of-range levels into the drawn track', () => {
    const players = [
      mockPlayer({
        research_tracks: { terraforming: 9, navigation: -2, ai: 0, gaia: 0, economy: 0, science: 0 },
      }),
    ];
    render(<ResearchBoard players={players} />);

    expect(screen.getByLabelText('P0 · Terrans · 테라포밍 5레벨')).toBeInTheDocument();
    expect(screen.getByLabelText('P0 · Terrans · 항법 0레벨')).toBeInTheDocument();
  });

  it('uses the physical tile artwork as the Tech tile picker', () => {
    const onStandardTechTile = vi.fn();
    const onAdvancedTechTile = vi.fn();
    render(
      <ResearchBoard
        players={[mockPlayer()]}
        board={board}
        techSelectionMode="tile"
        selectableStandardTiles={[2]}
        selectableAdvancedTracks={['Terraforming']}
        onStandardTechTile={onStandardTechTile}
        onAdvancedTechTile={onAdvancedTechTile}
      />,
    );

    fireEvent.click(screen.getByLabelText('표준 기술 타일 2 선택'));
    expect(onStandardTechTile).toHaveBeenCalledWith(2, 0);
    expect(screen.getByLabelText('표준 기술 타일 3 선택')).toBeDisabled();

    fireEvent.click(screen.getByLabelText('고급 기술 타일 1 선택'));
    expect(onAdvancedTechTile).toHaveBeenCalledWith(1, 'Terraforming');
    expect(screen.getByLabelText('고급 기술 타일 2 선택')).toBeDisabled();
  });

  it('lets a free-position standard tile choose its research track on the board', () => {
    const onResearchTrack = vi.fn();
    render(
      <ResearchBoard
        players={[mockPlayer()]}
        board={board}
        techSelectionMode="track"
        onResearchTrack={onResearchTrack}
      />,
    );

    fireEvent.click(screen.getByLabelText('과학 트랙 선택'));
    expect(onResearchTrack).toHaveBeenCalledWith('Science');
  });

  it('uses the same track columns for the normal four-knowledge research action', () => {
    const onPaidResearchTrack = vi.fn();
    render(
      <ResearchBoard
        players={[mockPlayer()]}
        board={board}
        onPaidResearchTrack={onPaidResearchTrack}
      />,
    );

    fireEvent.click(screen.getByLabelText('경제 트랙 연구 (지식 4)'));
    expect(onPaidResearchTrack).toHaveBeenCalledWith('Economy');
    expect(screen.queryByLabelText('경제 트랙 선택')).not.toBeInTheDocument();
  });
});
