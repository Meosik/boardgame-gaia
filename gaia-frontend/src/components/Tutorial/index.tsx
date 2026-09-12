import { useMemo, useState } from 'react';
import { GUIDE_CATEGORIES, GUIDE_ENTRIES, searchGuide, type GuideCategory } from '../../tutorial/guide';
import './tutorial.css';

interface Props {
  /** Rendered as a page when absent; the in-game panel passes its own close handler. */
  onClose?: () => void;
  /** Keeps the standalone page's title out of the in-game panel, which has its own header. */
  compact?: boolean;
}

export function Tutorial({ onClose, compact = false }: Props) {
  const [category, setCategory] = useState<GuideCategory>('flow');
  const [query, setQuery] = useState('');

  const entries = useMemo(() => {
    const searched = searchGuide(GUIDE_ENTRIES, query);
    // A search looks across every category, since a beginner rarely knows which one holds the term.
    return query.trim() ? searched : searched.filter((entry) => entry.category === category);
  }, [category, query]);

  const active = GUIDE_CATEGORIES.find((item) => item.id === category);

  return (
    <div className={`tutorial${compact ? ' tutorial--compact' : ''}`}>
      {!compact && (
        <header className="tutorial-header">
          <div>
            <p className="tutorial-eyebrow">가이아 프로젝트 · 처음 하는 분을 위한 안내</p>
            <h1>튜토리얼 · 행동 설명</h1>
          </div>
          <a className="btn btn-secondary" href="?">첫 화면</a>
        </header>
      )}

      <div className="tutorial-controls">
        <div className="tutorial-tabs" role="tablist" aria-label="설명 분류">
          {GUIDE_CATEGORIES.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={!query.trim() && item.id === category}
              className={!query.trim() && item.id === category ? 'is-active' : undefined}
              onClick={() => { setQuery(''); setCategory(item.id); }}
            >
              {item.label}
            </button>
          ))}
        </div>
        <label className="tutorial-search">
          <span className="tutorial-search-label">검색</span>
          <input
            type="search"
            value={query}
            placeholder="예: 테라포밍, 연방, 파워"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </div>

      <p className="tutorial-blurb">
        {query.trim() ? `"${query.trim()}" 검색 결과 ${entries.length}개` : active?.blurb}
      </p>

      {entries.length === 0 ? (
        <p className="tutorial-empty">찾는 내용이 없습니다. 다른 낱말로 검색해보세요.</p>
      ) : (
        <ol className="tutorial-entries">
          {entries.map((entry) => (
            <li key={entry.id} className="tutorial-entry">
              <h2>{entry.title}</h2>
              <p className="tutorial-summary">{entry.summary}</p>
              {(entry.cost || entry.requires) && (
                <dl className="tutorial-facts">
                  {entry.cost && (<><dt>비용</dt><dd>{entry.cost}</dd></>)}
                  {entry.requires && (<><dt>조건</dt><dd>{entry.requires}</dd></>)}
                </dl>
              )}
              <ul className="tutorial-detail">
                {entry.detail.map((line, index) => <li key={index}>{line}</li>)}
              </ul>
              {entry.tip && <p className="tutorial-tip">팁 · {entry.tip}</p>}
            </li>
          ))}
        </ol>
      )}

      {onClose && (
        <div className="tutorial-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>닫기</button>
        </div>
      )}
    </div>
  );
}
