import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TUTORIAL_STEPS, tutorialProgress } from '../tutorial/steps';
import { GuidedSteps } from '../components/Tutorial/GuidedSteps';
import type { GameEvent } from '../types/game';

const ME = 0;
const built: GameEvent = { StructureBuilt: { player: ME, hex: '1,-1', kind: 'Mine' } };
const opponentBuilt: GameEvent = { StructureBuilt: { player: 1, hex: '2,0', kind: 'Mine' } };
const researched: GameEvent = { ResearchAdvanced: { player: ME, track: 'Navigation', level: 1 } };
const powerAction: GameEvent = { ActionLog: { player: ME, action: 'PowerAction', event_count: 2 } };

describe('tutorialProgress', () => {
  it('starts on the first step with nothing done', () => {
    const progress = tutorialProgress([], ME);
    expect(progress.doneIds).toEqual([]);
    expect(progress.current?.id).toBe('build');
    expect(progress.completed).toBe(false);
  });

  it('checks off a step from the real log and moves to the next outstanding one', () => {
    const progress = tutorialProgress([built], ME);
    expect(progress.doneIds).toContain('build');
    expect(progress.current?.id).toBe('free-action');
  });

  it("ignores another player's identical action", () => {
    expect(tutorialProgress([opponentBuilt], ME).doneIds).toEqual([]);
  });

  it('accepts steps done out of order', () => {
    const progress = tutorialProgress([researched, powerAction], ME);
    expect(progress.doneIds).toEqual(['research', 'power-action']);
    expect(progress.current?.id).toBe('build');
  });

  it('reads a power action from its action-log boundary, not a resource change', () => {
    expect(tutorialProgress([powerAction], ME).doneIds).toEqual(['power-action']);
    const otherAction: GameEvent = { ActionLog: { player: ME, action: 'Build', event_count: 1 } };
    expect(tutorialProgress([otherAction], ME).doneIds).toEqual([]);
  });

  it('reports completion once every step has happened', () => {
    const all: GameEvent[] = [
      built,
      { FreeActionTaken: { player: ME, kind: 'PowerToCredit', count: 1 } },
      researched,
      { StructureUpgraded: { player: ME, hex: '1,-1', from: 'Mine', to: 'TradingStation' } },
      powerAction,
      { GaiaFormingStarted: { player: ME, hex: '3,0' } },
      { FederationFormed: { player: ME, token: 2 } },
      { PlayerPassed: { player: ME, booster: 7 } },
    ];
    const progress = tutorialProgress(all, ME);
    expect(progress.doneIds).toHaveLength(TUTORIAL_STEPS.length);
    expect(progress.current).toBeNull();
    expect(progress.completed).toBe(true);
  });

  it('has nothing to check before a seat is known', () => {
    expect(tutorialProgress([built], null).doneIds).toEqual([]);
  });
});

describe('GuidedSteps', () => {
  it('shows the outstanding step with its hint and a progress count', () => {
    render(<GuidedSteps events={[built]} myPlayerId={ME} />);

    expect(screen.getByText(/1 \/ 8 완료/)).toBeInTheDocument();
    expect(screen.getByText('지금 할 것 · 자원 바꿔보기')).toBeInTheDocument();
    expect(screen.getByText(/자유 행동 목록에서/)).toBeInTheDocument();
  });

  it('marks finished steps and says so when everything is done', () => {
    const { rerender } = render(<GuidedSteps events={[built]} myPlayerId={ME} />);
    expect(screen.getAllByText('완료').length).toBeGreaterThan(0);

    const all = TUTORIAL_STEPS.map((step) => ({ Done: { step: step.id } }) as GameEvent);
    rerender(<GuidedSteps events={all} myPlayerId={ME} />);
    // Unrecognised events must not count as progress.
    expect(screen.getByText(/0 \/ 8 완료/)).toBeInTheDocument();
  });
});
