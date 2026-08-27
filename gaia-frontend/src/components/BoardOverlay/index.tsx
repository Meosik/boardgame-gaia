import { useEffect } from 'react';
import type { ReactNode } from 'react';

interface Props {
  title: string;
  onClose: () => void;
  children: ReactNode;
}

export function BoardOverlay({ title, onClose, children }: Props) {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <div className="board-overlay-backdrop" onClick={onClose}>
      <div className="board-overlay-panel" onClick={(e) => e.stopPropagation()}>
        <div className="board-overlay-header">
          <h3>{title}</h3>
          <button className="board-overlay-close" onClick={onClose} aria-label="닫기">
            ✕
          </button>
        </div>
        <div className="board-overlay-body">{children}</div>
      </div>
    </div>
  );
}
