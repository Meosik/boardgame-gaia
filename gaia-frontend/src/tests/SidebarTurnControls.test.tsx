import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SidebarTurnControls } from '../components/SidebarTurnControls';
import { TopPassControl } from '../components/TopPassControl';
import type { PlayerState, UndoState } from '../types/game';

function player(bowl3 = 4, overrides: Partial<PlayerState> = {}): PlayerState {
  return {
    player_id: 0,
    nickname: '나',
    faction: 'Terrans',
    resources: {
      ore: 4,
      credits: 15,
      knowledge: 3,
      qic: 1,
      power: { bowl1: 0, bowl2: 0, bowl3, gaia_bowl: 0, gaia_forming: 0 },
      spent_gaia_formers: 0,
    },
    structures: [],
    research_tracks: { terraforming: 0, navigation: 0, ai: 0, gaia: 0, economy: 0, science: 0 },
    vp: 10,
    setup_bid_vp: 0,
    passed: false,
    booster: 1,
    federation_tokens: [],
    alliance_tiles: [],
    explored_ships: [],
    exploration_shuttles_available: 3,
    gaiaformers_total: 3,
    gaiaformers_deployed: 0,
    academy_qic_action_used_this_round: false,
    gleens_special_action_used_this_round: false,
    space_giants_special_action_used_this_round: false,
    ...overrides,
  };
}

describe('SidebarTurnControls', () => {
  const undoState: UndoState = {
    open_turn: { player: 0, start_revision: 10, free_action_revisions: [10] },
    recent_turns: [{ player: 0, start_revision: 7, completed_revision: 8 }],
    pending_request: null,
  };

  it('sends one power free action directly from each resource icon', () => {
    const onFreeAction = vi.fn();
    render(
      <SidebarTurnControls
        player={player()}
        isMyTurn
        onFreeAction={onFreeAction}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '파워 4 → 정보 큐브 1' }));
    fireEvent.click(screen.getByRole('button', { name: '파워 3 → 광석 1' }));
    fireEvent.click(screen.getByRole('button', { name: '파워 4 → 지식 1' }));
    fireEvent.click(screen.getByRole('button', { name: '파워 1 → 크레딧 1' }));
    expect(onFreeAction.mock.calls).toEqual([
      ['PowerToQic'],
      ['PowerToOre'],
      ['PowerToKnowledge'],
      ['PowerToCredit'],
    ]);
    expect(screen.getByRole('button', {
      name: '정보 큐브 1개로 사거리 2 증가 추가',
    })).toBeEnabled();
  });

  it('adds multiple information cubes to the range preview instead of toggling it off', () => {
    const onRangePreviewAdd = vi.fn();
    const { rerender } = render(
      <SidebarTurnControls
        player={player(4, { resources: { ...player().resources, qic: 2 } })}
        isMyTurn
        onFreeAction={vi.fn()}
        onRangePreviewAdd={onRangePreviewAdd}
      />,
    );

    const addRange = screen.getByRole('button', {
      name: '정보 큐브 1개로 사거리 2 증가 추가',
    });
    fireEvent.click(addRange);
    fireEvent.click(addRange);
    expect(onRangePreviewAdd).toHaveBeenCalledTimes(2);

    rerender(
      <SidebarTurnControls
        player={player(4, { resources: { ...player().resources, qic: 2 } })}
        isMyTurn
        onFreeAction={vi.fn()}
        rangePreviewQic={2}
        onRangePreviewAdd={onRangePreviewAdd}
      />,
    );
    expect(screen.getByText('현재 +4 사거리 · 정보 큐브 2개 선택')).toBeInTheDocument();
    expect(screen.getByRole('button', {
      name: '정보 큐브 1개로 사거리 2 증가 추가',
    })).toBeDisabled();
  });

  it('disables conversions that exceed the available third-bowl power', () => {
    render(
      <SidebarTurnControls
        player={player(2)}
        isMyTurn
        onFreeAction={vi.fn()}
      />,
    );

    expect(screen.getByRole('button', { name: '파워 4 → 정보 큐브 1' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '파워 3 → 광석 1' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '파워 1 → 크레딧 1' })).toBeEnabled();
    expect(screen.getByRole('button', { name: '파워 희생: 2단계 2개 → 3단계 1개' })).toBeDisabled();
  });

  it('enables burning when two tokens are available in the second bowl', () => {
    const onFreeAction = vi.fn();
    render(
      <SidebarTurnControls
        player={player(0, {
          resources: {
            ...player().resources,
            power: { bowl1: 0, bowl2: 2, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 },
          },
        })}
        isMyTurn
        onFreeAction={onFreeAction}
      />,
    );

    const burnButton = screen.getByRole('button', { name: '파워 희생: 2단계 2개 → 3단계 1개' });
    expect(burnButton).toBeEnabled();
    fireEvent.click(burnButton);
    expect(onFreeAction).toHaveBeenCalledWith('BurnPower');
  });

  it('shows the receive-power test only when the DEV sandbox enables it', () => {
    const onToggle = vi.fn();
    const { rerender } = render(
      <SidebarTurnControls player={player()} isMyTurn onFreeAction={vi.fn()} />,
    );
    expect(screen.queryByRole('button', { name: '내 파워 충전 테스트' })).not.toBeInTheDocument();

    rerender(
      <SidebarTurnControls
        player={player()}
        isMyTurn
        onFreeAction={vi.fn()}
        showDevPowerChargeTest
        onDevPowerChargeToggle={onToggle}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: '내 파워 충전 테스트' }));
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it('undoes every free action from the current turn without consuming the action turn', () => {
    const onUndoFreeAction = vi.fn();
    const onRequestTurnUndo = vi.fn();
    render(
      <SidebarTurnControls
        player={player()}
        players={[player()]}
        isMyTurn
        onFreeAction={vi.fn()}
        undoState={undoState}
        onUndoFreeAction={onUndoFreeAction}
        onRequestTurnUndo={onRequestTurnUndo}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '이번 차례 자유행동 전부 되돌리기' }));
    fireEvent.click(screen.getByRole('button', { name: '직전 차례 되돌리기 요청' }));
    expect(onUndoFreeAction).toHaveBeenCalledOnce();
    expect(onRequestTurnUndo).toHaveBeenCalledOnce();
  });

  it('enables whole-turn free-action undo for a pending range extension alone', () => {
    const onUndoFreeAction = vi.fn();
    render(
      <SidebarTurnControls
        player={player()}
        isMyTurn
        onFreeAction={vi.fn()}
        rangePreviewQic={2}
        onUndoFreeAction={onUndoFreeAction}
      />,
    );

    const undo = screen.getByRole('button', { name: '이번 차례 자유행동 전부 되돌리기' });
    expect(undo).toBeEnabled();
    fireEvent.click(undo);
    expect(onUndoFreeAction).toHaveBeenCalledOnce();
  });

  it('pauses ordinary controls while another player asks for undo approval', () => {
    const onRespondTurnUndo = vi.fn();
    const requester = player(4, { player_id: 1, nickname: '요청자' });
    render(
      <SidebarTurnControls
        player={player()}
        players={[player(), requester]}
        isMyTurn={false}
        onFreeAction={vi.fn()}
        undoState={{
          ...undoState,
          pending_request: {
            requester: 1,
            target_revision: 7,
            required_approvals: [0, 2, 3],
            approvals: [],
          },
        }}
        onRespondTurnUndo={onRespondTurnUndo}
      />,
    );

    expect(screen.getByText('요청자님의 직전 차례를 되돌릴까요?')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '승인' }));
    expect(onRespondTurnUndo).toHaveBeenCalledWith(true);
    expect(screen.getByRole('button', { name: '파워 1 → 크레딧 1' })).toBeDisabled();
  });

});

describe('TopPassControl', () => {
  it('chooses a booster in a large popup before passing in rounds one through five', () => {
    const onPass = vi.fn();
    render(
      <TopPassControl
        player={player()}
        round={3}
        availableBoosters={[2, 3]}
        isMyTurn
        onPass={onPass}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '패스' }));
    expect(screen.getByRole('dialog', { name: '패스 후 받을 라운드 부스터 선택' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '라운드 부스터 3 미리 보기' }));
    expect(screen.getByRole('img', { name: '라운드 부스터 3' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '이 부스터로 패스' }));
    expect(onPass).toHaveBeenCalledWith(3);
  });

  it('closes a booster preview without selecting it', () => {
    render(
      <TopPassControl
        player={player()}
        round={3}
        availableBoosters={[2]}
        isMyTurn
        onPass={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '패스' }));
    fireEvent.click(screen.getByRole('button', { name: '닫기' }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('passes without a booster in the final round', () => {
    const onPass = vi.fn();
    render(
      <TopPassControl
        player={player()}
        round={6}
        availableBoosters={[2, 3]}
        isMyTurn
        onPass={onPass}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '패스' }));
    expect(onPass).toHaveBeenCalledWith(null);
  });
});
