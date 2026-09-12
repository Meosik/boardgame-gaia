import { useState } from 'react';
import { Tutorial } from './index';
import { GuidedSteps } from './GuidedSteps';
import type { GameEvent, PlayerId } from '../../types/game';

interface Props {
  events: GameEvent[] | undefined;
  myPlayerId: PlayerId | null;
}

/** In-game help: the guided checklist for a first game, and the same reference the lobby shows. */
export function TutorialPanel({ events, myPlayerId }: Props) {
  const [tab, setTab] = useState<'guided' | 'reference'>('guided');

  return (
    <div className="tutorial-panel">
      <div className="tutorial-panel-tabs" role="tablist" aria-label="도움말 보기 방식">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'guided'}
          className={tab === 'guided' ? 'is-active' : undefined}
          onClick={() => setTab('guided')}
        >
          따라 하기
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'reference'}
          className={tab === 'reference' ? 'is-active' : undefined}
          onClick={() => setTab('reference')}
        >
          행동 설명
        </button>
      </div>
      {tab === 'guided'
        ? <GuidedSteps events={events} myPlayerId={myPlayerId} />
        : <Tutorial compact />}
    </div>
  );
}
