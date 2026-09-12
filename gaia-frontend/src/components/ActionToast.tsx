import type { GameLogEntry } from './GameLog';

/** The newest completed action, shown briefly over the table. Without it an opponent's whole turn
 * can pass with no visible trace except numbers changing somewhere on their board. */
export function ActionToast({ entry, myPlayerId }: { entry: GameLogEntry | null; myPlayerId: number }) {
  if (!entry) return null;

  const mine = entry.player === myPlayerId;
  return (
    <div
      className={`action-toast${mine ? ' action-toast--mine' : ''}`}
      role="status"
      aria-live="polite"
      aria-label={`방금 일어난 일: ${entry.text}`}
    >
      <span className="action-toast-eyebrow">{mine ? '내 행동' : '방금'}</span>
      <span className="action-toast-text">{entry.text}</span>
      {entry.details.length > 0 && (
        <span className="action-toast-details">{entry.details.join(' · ')}</span>
      )}
    </div>
  );
}
