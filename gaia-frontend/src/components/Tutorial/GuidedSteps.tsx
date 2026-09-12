import { TUTORIAL_STEPS, tutorialProgress } from '../../tutorial/steps';
import type { GameEvent, PlayerId } from '../../types/game';

interface Props {
  events: GameEvent[] | undefined;
  myPlayerId: PlayerId | null;
}

/** Checklist for a first game: the real log decides what is done, so nothing to press here. */
export function GuidedSteps({ events, myPlayerId }: Props) {
  const { doneIds, current, completed } = tutorialProgress(events, myPlayerId);

  return (
    <section className="guided-steps" aria-label="따라 하기">
      <p className="guided-steps-progress">
        {doneIds.length} / {TUTORIAL_STEPS.length} 완료
        {completed && ' · 첫 게임에서 할 일을 모두 해봤습니다'}
      </p>

      {current && (
        <div className="guided-steps-current">
          <h3>지금 할 것 · {current.title}</h3>
          <p className="guided-steps-instruction">{current.instruction}</p>
          <p className="guided-steps-hint">{current.hint}</p>
        </div>
      )}

      <ol className="guided-steps-list">
        {TUTORIAL_STEPS.map((step) => {
          const done = doneIds.includes(step.id);
          return (
            <li key={step.id} className={done ? 'is-done' : undefined}>
              <span className="guided-steps-mark" aria-hidden>{done ? '✓' : '○'}</span>
              <span>{step.title}</span>
              <span className="guided-steps-state">{done ? '완료' : step === current ? '진행 중' : '대기'}</span>
            </li>
          );
        })}
      </ol>

      <p className="guided-steps-note">
        순서대로 하지 않아도 됩니다. 게임에서 실제로 해내면 자동으로 체크됩니다.
      </p>
    </section>
  );
}
