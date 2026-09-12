import type { TurnStatus } from '../liveActivity';

/** One plain sentence saying whose turn it is and what this player has to do next.
 * Beginners could otherwise only infer it from which buttons happen to be enabled. */
export function TurnBanner({ status }: { status: TurnStatus | null }) {
  if (!status) return null;

  return (
    <div
      className={`turn-banner${status.mine ? ' turn-banner--mine' : ''}`}
      role="status"
      aria-live="polite"
    >
      <strong className="turn-banner-text">{status.text}</strong>
      {status.hint && <small className="turn-banner-hint">{status.hint}</small>}
    </div>
  );
}
