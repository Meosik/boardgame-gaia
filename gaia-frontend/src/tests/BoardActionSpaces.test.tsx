import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ResearchBoard } from '../components/PlayerDashboard/ResearchBoard';
import { SpaceshipBoards } from '../components/SpaceshipBoards';
import {
  isSpaceshipBoardAction,
  SPACESHIP_ACTION_SPACES,
} from '../components/boardActionSpaces';
import type { SpaceshipBoard, SpaceshipId } from '../types/game';

function spaceshipBoard(
  id: SpaceshipId,
  explorers: SpaceshipBoard['explorers'],
  artifactPool: number[] = [],
): SpaceshipBoard {
  return {
    id,
    explorers,
    artifact_pool: artifactPool,
    tech_tiles: [],
    federation_token: null,
  };
}

describe('physical board action spaces', () => {
  it('keeps lobby/reference boards noninteractive', () => {
    const { rerender } = render(<ResearchBoard players={[]} />);
    expect(screen.queryAllByRole('button')).toHaveLength(0);

    rerender(<SpaceshipBoards spaceshipBoards={[spaceshipBoard('TFMars', [null, null, null, null])]} players={[]} />);
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
    const oreAction = screen.getByRole('button', { name: /파워 4 → 광석 2.*사용 가능/ });
    const creditAction = screen.getByRole('button', { name: /파워 4 → 크레딧 7.*사용 가능/ });
    expect(oreAction).toBeEnabled();
    expect(creditAction).toBeEnabled();

    fireEvent.click(oreAction);
    fireEvent.click(creditAction);
    expect(onPowerAction).toHaveBeenNthCalledWith(1, 3);
    expect(onPowerAction).toHaveBeenNthCalledWith(2, 4);
  });

  it('allows ship actions only to an entrant and locks a slot used by anyone', () => {
    const onActionSelect = vi.fn();
    const { rerender } = render(
      <SpaceshipBoards
        spaceshipBoards={[spaceshipBoard('TFMars', [1, null, null, null])]}
        players={[]}
        myPlayerId={0}
        isMyTurn
        onActionSelect={onActionSelect}
      />,
    );

    expect(screen.getByRole('button', { name: /크레딧 행동.*탐사 셔틀/ })).toBeDisabled();

    rerender(
      <SpaceshipBoards
        spaceshipBoards={[spaceshipBoard('TFMars', [0, null, null, null])]}
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
    expect(onActionSelect).toHaveBeenCalledWith(
      'SpaceshipCreditTerraform',
      ['SpaceshipCreditTerraform'],
    );
  });

  it('connects every printed spaceship action slot to its primary action flow', () => {
    const onActionSelect = vi.fn();
    const boards = (Object.keys(SPACESHIP_ACTION_SPACES) as SpaceshipId[]).map((id) =>
      spaceshipBoard(id, [0, null, null, null]),
    );
    render(
      <SpaceshipBoards
        spaceshipBoards={boards}
        players={[]}
        myPlayerId={0}
        isMyTurn
        onActionSelect={onActionSelect}
      />,
    );

    const spaces = Object.values(SPACESHIP_ACTION_SPACES).flat();
    for (const space of spaces) {
      expect(isSpaceshipBoardAction(space.primaryActionType)).toBe(true);
      fireEvent.click(screen.getByTitle(`${space.label} — 사용 가능`));
    }

    expect(onActionSelect.mock.calls.map(([actionType]) => actionType)).toEqual(
      spaces.map(({ primaryActionType }) => primaryActionType),
    );
  });

  it('opens artifact examination from an available Twilight artifact', () => {
    const onArtifactSelect = vi.fn();
    render(
      <SpaceshipBoards
        spaceshipBoards={[spaceshipBoard('Twilight', [0, null, null, null], [8])]}
        players={[]}
        myPlayerId={0}
        isMyTurn
        onArtifactSelect={onArtifactSelect}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '아티팩트 8 조사' }));
    expect(onArtifactSelect).toHaveBeenCalledWith(8);
  });
});
