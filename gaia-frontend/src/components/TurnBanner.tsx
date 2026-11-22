import { useEffect, useState } from 'react';
import type { TurnStatus } from '../liveActivity';

interface Props {
  status: TurnStatus | null;
  /** A standing line about the game itself (`aiStallWarning`), shown even without a turn sentence. */
  warning?: string | null;
  /** What the player can do about the warning; the button sits beside it. */
  warningAction?: { label: string; busy?: boolean; onClick: () => void } | null;
  /** Changes whenever the game moves on. While the game waits on another player
   * (`status.waitingFor`) the banner counts the seconds since this last changed, so a seat that
   * is still thinking can be told from one that has stopped. Omit it to show no count. */
  waitKey?: string | null;
}

/** The count appears only once a wait is long enough to wonder about. */
const ELAPSED_FROM_SECONDS = 3;

function useElapsedSeconds(resetKey: string | null): number {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    setSeconds(0);
    if (resetKey === null) return undefined;
    const started = Date.now();
    const timer = window.setInterval(
      () => setSeconds(Math.floor((Date.now() - started) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [resetKey]);
  return seconds;
}

/** One plain sentence saying whose turn it is and what this player has to do next.
 * Beginners could otherwise only infer it from which buttons happen to be enabled. */
export function TurnBanner({ status, warning = null, warningAction = null, waitKey = null }: Props) {
  // A stalled seat has its own warning line; a count beside it would read as "still thinking".
  const counting = status?.waitingFor !== undefined && !warning && waitKey !== null;
  const elapsed = useElapsedSeconds(counting ? `${status?.waitingFor}:${waitKey}` : null);
  if (!status && !warning) return null;

  return (
    <div
      className={`turn-banner${status?.mine ? ' turn-banner--mine' : ''}`}
      role="status"
      aria-live="polite"
    >
      {status && <strong className="turn-banner-text">{status.text}</strong>}
      {counting && elapsed >= ELAPSED_FROM_SECONDS && (
        // Not announced every second: the sentence above already says who is awaited.
        <small className="turn-banner-elapsed" aria-hidden="true">{elapsed}초 경과</small>
      )}
      {status?.hint && <small className="turn-banner-hint">{status.hint}</small>}
      {warning && (
        <small className="turn-banner-warning">
          {warning}
          {warningAction && (
            <button
              type="button"
              className="btn btn-small btn-secondary turn-banner-warning-action"
              disabled={warningAction.busy}
              onClick={warningAction.onClick}
            >
              {warningAction.label}
            </button>
          )}
        </small>
      )}
    </div>
  );
}
