import type { TurnStatus } from '../liveActivity';

/** One plain sentence saying whose turn it is and what this player has to do next.
 * Beginners could otherwise only infer it from which buttons happen to be enabled.
 * `warning` is a standing line about the game itself (`aiFallbackWarning`), shown even when
 * there is no turn sentence. */
export function TurnBanner({ status, warning = null }: { status: TurnStatus | null; warning?: string | null }) {
  if (!status && !warning) return null;

  return (
    <div
      className={`turn-banner${status?.mine ? ' turn-banner--mine' : ''}`}
      role="status"
      aria-live="polite"
    >
      {status && <strong className="turn-banner-text">{status.text}</strong>}
      {status?.hint && <small className="turn-banner-hint">{status.hint}</small>}
      {warning && <small className="turn-banner-warning">{warning}</small>}
    </div>
  );
}
