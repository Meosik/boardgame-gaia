import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ResearchBoard } from '../components/PlayerDashboard/ResearchBoard';
import { SpaceshipBoards } from '../components/SpaceshipBoards';
import type { SpaceshipBoard } from '../types/game';

function tfMarsBoard(explorers: SpaceshipBoard['explorers']): SpaceshipBoard {
  return {
    id: 'TFMars',
    explorers,
    artifact_pool: [],
    tech_tiles: [],
    federation_token: null,
  };
}

describe('physical board action spaces', () => {
  it('keeps lobby/reference boards noninteractive', () => {
    const { rerender } = render(<ResearchBoard players={[]} />);
    expect(screen.queryAllByRole('button')).toHaveLength(0);

    rerender(<SpaceshipBoards spaceshipBoards={[tfMarsBoard([null, null, null, null])]} players={[]} />);
    expect(screen.queryAllByRole('button')).toHaveLength(0);
  });

  it('distinguishes available and already-used research-board actions', () => {
    const onPowerAction = vi.fn();
    render(
      <ResearchBoard
        players={[]}
        usedPowerActions={[1]}
        isMyTurn
        onPowerAction={onPowerAction}
      />,
    );

    expect(screen.getByRole('button', { name: /파워 7 → 지식 3.*사용함/ })).toBeDisabled();
    const available = screen.getByRole('button', { name: /파워 4 → 광석 2.*사용 가능/ });
    expect(available).toBeEnabled();

    fireEvent.click(available);
    expect(onPowerAction).toHaveBeenCalledWith(3);
  });

  it('allows ship actions only to an entrant and locks a slot used by anyone', () => {
    const onActionSelect = vi.fn();
    const { rerender } = render(
      <SpaceshipBoards
        spaceshipBoards={[tfMarsBoard([1, null, null, null])]}
        players={[]}
        myPlayerId={0}
        isMyTurn
        onActionSelect={onActionSelect}
      />,
    );

    expect(screen.getByRole('button', { name: /크레딧 행동.*탐사 셔틀/ })).toBeDisabled();

    rerender(
      <SpaceshipBoards
        spaceshipBoards={[tfMarsBoard([0, null, null, null])]}
        players={[]}
        myPlayerId={0}
        isMyTurn
        usedActionIds={[5]}
        onActionSelect={onActionSelect}
      />,
    );

    const creditAction = screen.getByRole('button', { name: /크레딧 행동.*사용 가능/ });
    expect(creditAction).toBeEnabled();
    expect(screen.getByRole('button', { name: /기술 타일 수만큼.*사용함/ })).toBeDisabled();

    fireEvent.click(creditAction);
    expect(onActionSelect).toHaveBeenCalledWith('SpaceshipCreditTerraform');
  });
});
