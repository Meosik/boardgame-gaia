import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PlayerActionShelf } from '../components/PlayerActionShelf';
import type { PlayerState } from '../types/game';

function player(overrides: Partial<PlayerState> = {}): PlayerState {
  return {
    player_id: 0,
    nickname: 'Me',
    faction: 'Terrans',
    resources: {
      ore: 4,
      credits: 15,
      knowledge: 3,
      qic: 2,
      power: { bowl1: 2, bowl2: 4, bowl3: 4, gaia_bowl: 0, gaia_forming: 0 },
      spent_gaia_formers: 0,
    },
    structures: [{ hex: { q: 0, r: 0 }, kind: { Academy: 'Qic' } }],
    research_tracks: { terraforming: 0, navigation: 0, ai: 0, gaia: 0, economy: 0, science: 0 },
    vp: 10,
    setup_bid_vp: 0,
    passed: false,
    federation_tokens: [],
    alliance_tiles: [],
    explored_ships: [],
    exploration_shuttles_available: 3,
    gaiaformers_total: 0,
    gaiaformers_deployed: 0,
    academy_qic_action_used_this_round: false,
    gleens_special_action_used_this_round: false,
    space_giants_special_action_used_this_round: false,
    tech_tiles: [10],
    advanced_tech_tiles: [20],
    ...overrides,
  };
}

describe('PlayerActionShelf', () => {
  it.each(['Firaks', 'Ivits'] as const)('opens the mapped %s PI action and respects locks', faction => {
    const onSelectFactionAction = vi.fn();
    const onAction = vi.fn();
    const ready = player({ faction, structures: [{ hex: { q: 0, r: 0 }, kind: 'PlanetaryInstitute' }] });
    const props = { player: ready, isMyTurn: true, onAction, onSelectFactionAction };
    const { rerender } = render(<PlayerActionShelf {...props} />);
    const label = faction === 'Firaks' ? '파이락 연구소 강등 + 무료 연구' : '하이브 우주정거장 배치';
    const button = screen.getByRole('button', { name: label });
    expect(button.querySelector('.action-crop')).not.toBeNull();
    fireEvent.click(button);
    expect(onSelectFactionAction).toHaveBeenCalledWith(faction === 'Firaks' ? 'FiraksDowngradeResearchLab' : 'IvitsPlaceSpaceStation');
    expect(onAction).not.toHaveBeenCalled();
    rerender(<PlayerActionShelf {...props} mainActionLocked />);
    expect(button).toBeDisabled();
    rerender(<PlayerActionShelf {...props} isMyTurn={false} />);
    expect(button).toBeDisabled();
    rerender(<PlayerActionShelf {...props} player={{ ...ready, faction_special_action_used_this_round: true }} />);
    expect(screen.getByRole('button', { name: label + ' · 이번 라운드 사용됨' })).toBeDisabled();
    rerender(<PlayerActionShelf {...props} player={{ ...ready, structures: [] }} />);
    expect(screen.queryByRole('button', { name: label })).toBeNull();
  });

  it('opens Bescods lowest research from the mapped image and respects turn locks and usage', () => {
    const onSelectBescodsResearch = vi.fn();
    const onAction = vi.fn();
    const ready = player({ faction: 'Bescods', structures: [] });
    const props = { player: ready, isMyTurn: true, onAction, onSelectBescodsResearch };
    const { rerender } = render(<PlayerActionShelf {...props} />);
    const button = screen.getByRole('button', { name: '매드 안드로이드 최저 연구 무료 상승' });
    expect(button.querySelector('.action-crop')).not.toBeNull();
    fireEvent.click(button);
    expect(onSelectBescodsResearch).toHaveBeenCalledOnce();
    expect(onAction).not.toHaveBeenCalled();
    rerender(<PlayerActionShelf {...props} mainActionLocked />);
    expect(button).toBeDisabled();
    rerender(<PlayerActionShelf {...props} isMyTurn={false} />);
    expect(button).toBeDisabled();
    rerender(<PlayerActionShelf {...props} player={{ ...ready, faction_special_action_used_this_round: true }} />);
    expect(screen.getByRole('button', { name: /매드 안드로이드.*이번 라운드 사용됨/ })).toBeDisabled();
    expect(button.querySelector('.game-piece-icon--action-used')).not.toBeNull();
  });

  it('shows the full tinkering tile until the server marks it used', () => {
    const onAction = vi.fn();
    const ready = player({ faction: 'Tinkeroids', tinkeroids_selected_tile: 2, tinkeroids_tiles_used: [] });
    const { rerender } = render(<PlayerActionShelf player={ready} isMyTurn onAction={onAction} />);
    const button = screen.getByRole('button', { name: '팅커로이드 타일 2 사용' });
    expect(button.querySelector('img')).not.toBeNull();
    expect(button.querySelector('.action-crop')).toBeNull();
    fireEvent.click(button);
    expect(onAction).toHaveBeenCalledWith({ type: 'TinkeroidsUseTile', tile: 2, coord: null });
    expect(button).toBeInTheDocument();
    rerender(<PlayerActionShelf player={{ ...ready, tinkeroids_tiles_used: [2] }} isMyTurn onAction={onAction} />);
    expect(screen.queryByRole('button', { name: '팅커로이드 타일 2 사용' })).not.toBeInTheDocument();
  });

  it.each([5, 8] as const)('includes cropped booster %i and closes it after use', (booster) => {
    const onAction = vi.fn();
    const onSelectBoosterAction = vi.fn();
    const ready = player({ booster });
    const { rerender } = render(<PlayerActionShelf player={ready} isMyTurn onAction={onAction} onSelectBoosterAction={onSelectBoosterAction} />);
    const button = screen.getByRole('button', { name: /부스터 ·/ });
    expect(button.querySelector('.action-crop')).not.toBeNull();
    fireEvent.click(button);
    expect(onSelectBoosterAction).toHaveBeenCalledWith(booster);
    expect(onAction).not.toHaveBeenCalled();
    rerender(<PlayerActionShelf player={{ ...ready, round_booster_special_action_used_this_round: true }} isMyTurn onAction={onAction} onSelectBoosterAction={onSelectBoosterAction} />);
    const closed = screen.getByRole('button', { name: /부스터 ·.*이번 라운드 사용됨/ });
    expect(closed).toBeDisabled();
    expect(closed.querySelector('.game-piece-icon--action-used')).not.toBeNull();
  });

  it('runs image-backed technology and Academy actions', () => {
    const onAction = vi.fn();
    render(<PlayerActionShelf player={player()} isMyTurn onAction={onAction} />);

    fireEvent.click(screen.getByRole('button', { name: '기술 타일 · 파워 4 충전' }));
    fireEvent.click(screen.getByRole('button', { name: '정보 큐브 아카데미 행동' }));

    expect(onAction.mock.calls).toEqual([
      [{ type: 'TechTileSpecialAction', tile: { pool: 'Standard', tile: 10 } }],
      [{ type: 'AcademyQicAction' }],
    ]);
    expect(screen.getAllByRole('img', { hidden: true })).toHaveLength(3);
  });

  it('keeps used and covered action sources visible or excluded consistently', () => {
    render(
      <PlayerActionShelf
        player={player({
          covered_tech_tiles: [10],
          academy_qic_action_used_this_round: true,
          advanced_tech_tile_special_actions_used_this_round: [20],
        })}
        isMyTurn
        onAction={vi.fn()}
      />,
    );

    expect(screen.queryByRole('button', { name: '기술 타일 · 파워 4 충전' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /고급 기술 타일 20 행동.*사용됨/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /정보 큐브 아카데미 행동.*사용됨/ })).toBeDisabled();
  });

  it('locks other main-action tiles while another action is being selected', () => {
    const onAction = vi.fn();
    render(
      <PlayerActionShelf player={player()} isMyTurn mainActionLocked onAction={onAction} />,
    );

    const techAction = screen.getByRole('button', { name: '기술 타일 · 파워 4 충전' });
    const academyAction = screen.getByRole('button', { name: '정보 큐브 아카데미 행동' });
    expect(techAction).toBeDisabled();
    expect(academyAction).toBeDisabled();
    fireEvent.click(techAction);
    expect(onAction).not.toHaveBeenCalled();
  });

  it('shows owned Federation tokens and selects their images during Twilight replay', () => {
    const onSelectFederationKind = vi.fn();
    const { rerender } = render(
      <PlayerActionShelf
        player={player({ federation_tokens: [5], gray_federation_tokens: [6] })}
        isMyTurn
        onAction={vi.fn()}
      />,
    );

    expect(screen.getByRole('region', { name: '내 연방' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '연방 토큰 5' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '연방 토큰 6 회색면' })).toBeDisabled();

    rerender(
      <PlayerActionShelf
        player={player({ federation_tokens: [5], gray_federation_tokens: [6] })}
        isMyTurn
        mainActionLocked
        federationSelectionMode
        selectedFederationKind={6}
        onSelectFederationKind={onSelectFederationKind}
        onAction={vi.fn()}
      />,
    );

    const greenToken = screen.getByRole('button', { name: '연방 토큰 5 · 효과 복사 선택' });
    const grayToken = screen.getByRole('button', { name: '연방 토큰 6 회색면 · 효과 복사 선택' });
    expect(greenToken).toBeEnabled();
    expect(grayToken).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(greenToken);
    expect(onSelectFederationKind).toHaveBeenCalledWith(5);
  });
});

describe('exploration board action crops', () => {
  it.each(['Gleens', 'SpaceGiants'] as const)('connects %s and closes the crop after use', (faction) => {
    const onSelectExplorationAction = vi.fn();
    const onAction = vi.fn();
    const ready = player({ faction });
    const label = faction === 'Gleens' ? '글린 · 사거리 +2 행동' : '스페이스자이언트 · 테라포밍 2단계 무료 광산 행동';
    const { rerender } = render(<PlayerActionShelf player={ready} isMyTurn onAction={onAction} onSelectExplorationAction={onSelectExplorationAction} />);
    const button = screen.getByRole('button', { name: label });
    expect(button.querySelector('.action-crop svg image')).not.toBeNull();
    fireEvent.click(button);
    expect(onSelectExplorationAction).toHaveBeenCalledWith(faction === 'Gleens' ? 'GleensBuildMine' : 'SpaceGiantsBuildMine');
    expect(onAction).not.toHaveBeenCalled();
    rerender(<PlayerActionShelf player={{ ...ready, gleens_special_action_used_this_round: true, space_giants_special_action_used_this_round: true }} isMyTurn onAction={onAction} onSelectExplorationAction={onSelectExplorationAction} />);
    const closed = screen.getByRole('button', { name: `${label} · 이번 라운드 사용됨` });
    expect(closed).toBeDisabled();
    expect(closed.querySelector('.action-crop-closed')).not.toBeNull();
  });
});
