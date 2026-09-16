import type { ReactNode } from 'react';

/** Disable command inputs without introducing a layout box or blocking board scrolling. */
export function GameCommandControls({ blocked, children }: { blocked: boolean; children: ReactNode }) {
  return (
    <fieldset
      disabled={blocked}
      style={{ display: 'contents' }}
      onClickCapture={(event) => {
        if (blocked) { event.preventDefault(); event.stopPropagation(); }
      }}
      onKeyDownCapture={(event) => {
        if (blocked && (event.key === 'Enter' || event.key === ' ')) {
          event.preventDefault(); event.stopPropagation();
        }
      }}
    >
      {children}
    </fieldset>
  );
}

export function GameCommandStatus({ ready, pending }: { ready: boolean; pending: boolean }) {
  if (ready && !pending) return null;
  return <span role="status" aria-live="polite" aria-atomic="true">
    {!ready ? '서버 연결·방 복구 중…' : '명령 처리 중…'}
  </span>;
}
