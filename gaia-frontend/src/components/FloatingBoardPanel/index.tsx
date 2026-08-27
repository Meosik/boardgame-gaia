import { useEffect } from 'react';
import type { ReactNode } from 'react';

interface Props {
  title: string;
  onClose: () => void;
  children: ReactNode;
}

/** A pinned, non-modal board reference panel. It deliberately has no
 * backdrop so players can keep inspecting and selecting map hexes while the
 * reference board remains open. */
export function FloatingBoardPanel({ title, onClose, children }: Props) {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    <section
      className="floating-board-panel"
      role="dialog"
      aria-modal="false"
      aria-label={title}
    >
      <header className="floating-board-panel-header">
        <h3>{title}</h3>
        <button className="board-overlay-close" onClick={onClose} aria-label="닫기">
          ✕
        </button>
      </header>
      <div className="floating-board-panel-body">{children}</div>
    </section>
  );
}
