interface Props {
  /** 1-based number of the position on screen among the kept ones. */
  position: number;
  total: number;
  /** An older position is on screen (the live game continues behind it). */
  reviewing: boolean;
  onStep: (to: 'back' | 'forward' | 'live' | 'mine') => void;
}

/** Steps back and forth through the positions received while watching, so the moves the other
 * seats just made can be looked at one by one. The board, boards and markers all show the chosen
 * position; nothing can be played until 「지금으로」 returns to the live game. */
export function ActionReview({ position, total, reviewing, onStep }: Props) {
  const canGoBack = total > 1 && position > 1;
  return (
    <section className="action-review" aria-label="방금 수 다시 보기">
      <div className="action-review-buttons">
        <button
          type="button"
          className="btn btn-small btn-secondary"
          disabled={total < 2}
          title="내가 마지막으로 수를 둔 직후의 판부터 봅니다."
          onClick={() => onStep('mine')}
        >
          내 수 직후
        </button>
        <button
          type="button"
          className="btn btn-small btn-secondary"
          disabled={!canGoBack}
          aria-label="한 수 전으로"
          onClick={() => onStep('back')}
        >
          ◀
        </button>
        <span className="action-review-position" aria-live="polite">
          {reviewing ? `${position}/${total}` : '지금'}
        </span>
        <button
          type="button"
          className="btn btn-small btn-secondary"
          disabled={!reviewing}
          aria-label="한 수 뒤로"
          onClick={() => onStep('forward')}
        >
          ▶
        </button>
        <button
          type="button"
          className="btn btn-small btn-secondary"
          disabled={!reviewing}
          onClick={() => onStep('live')}
        >
          지금으로
        </button>
      </div>
      {reviewing && (
        <p className="action-review-note">지난 판을 보는 중입니다. 수를 두려면 「지금으로」를 누르세요.</p>
      )}
    </section>
  );
}
