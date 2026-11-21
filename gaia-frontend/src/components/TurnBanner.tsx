import type { TurnStatus } from '../liveActivity';

interface Props {
  status: TurnStatus | null;
  /** A standing line about the game itself (`aiStallWarning`), shown even without a turn sentence. */
  warning?: string | null;
  /** What the player can do about the warning; the button sits beside it. */
  warningAction?: { label: string; busy?: boolean; onClick: () => void } | null;
}

/** One plain sentence saying whose turn it is and what this player has to do next.
 * Beginners could otherwise only infer it from which buttons happen to be enabled. */
export function TurnBanner({ status, warning = null, warningAction = null }: Props) {
  if (!status && !warning) return null;

  return (
    <div
      className={`turn-banner${status?.mine ? ' turn-banner--mine' : ''}`}
      role="status"
      aria-live="polite"
    >
      {status && <strong className="turn-banner-text">{status.text}</strong>}
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
