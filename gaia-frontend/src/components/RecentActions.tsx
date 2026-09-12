import type { GameLogEntry } from './GameLog';

/** Newest-first summary of the last few actions, kept on the always-visible info tab so the full
 * log behind the second tab is a detail view rather than the only place opponents' moves appear. */
export function RecentActions({
  entries,
  onOpenLog,
}: {
  entries: GameLogEntry[];
  onOpenLog: () => void;
}) {
  return (
    <section className="recent-actions" aria-label="최근 행동">
      <header className="recent-actions-header">
        <h3>최근 행동</h3>
        <button type="button" className="recent-actions-more" onClick={onOpenLog}>
          전체 기록
        </button>
      </header>
      {entries.length === 0 ? (
        <p className="recent-actions-empty">아직 기록된 행동이 없습니다.</p>
      ) : (
        <ol className="recent-actions-list">
          {entries.map((entry) => (
            <li key={`${entry.index}:${entry.text}`}>{entry.text}</li>
          ))}
        </ol>
      )}
    </section>
  );
}
