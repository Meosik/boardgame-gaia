import type { ReactNode } from 'react';

interface Props {
  onClose: () => void;
  children: ReactNode;
  title?: string;
}

export function PersonalBoardDrawer({ onClose, children, title = '개인 보드' }: Props) {
  return (
    <aside className="personal-board-drawer" role="dialog" aria-modal="false" aria-label={title} aria-live="polite">
      <header className="personal-board-drawer-header">
        <h3>{title}</h3>
        <button type="button" onClick={onClose} aria-label="개인 보드 닫기">×</button>
      </header>
      <div className="personal-board-drawer-body">{children}</div>
    </aside>
  );
}
