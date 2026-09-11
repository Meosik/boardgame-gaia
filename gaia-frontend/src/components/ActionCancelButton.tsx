import { useLayoutEffect, useRef } from 'react';

interface Props {
  anchor: Element | null;
  onCancel: () => void;
}

export function ActionCancelButton({ anchor, onCancel }: Props) {
  const buttonRef = useRef<HTMLButtonElement>(null);

  useLayoutEffect(() => {
    function position() {
      const button = buttonRef.current;
      if (!button) return;
      // A selection popup takes precedence over the board space that opened it.
      const target = document.querySelector('.structure-action-popup, .target-action-popup') ?? anchor;
      const rect = target?.isConnected ? target.getBoundingClientRect() : null;
      const width = button.offsetWidth;
      const height = button.offsetHeight;
      const gap = 12;
      let left = rect ? rect.right + gap : window.innerWidth / 2;
      let top = rect ? rect.top : 72;
      if (rect && left + width > window.innerWidth - gap) {
        left = rect.left - width - gap;
        if (left < gap) {
          left = rect.left;
          top = rect.bottom + gap;
          if (top + height > window.innerHeight - gap) top = rect.top - height - gap;
        }
      }
      button.style.left = `${Math.max(gap, Math.min(left, window.innerWidth - width - gap))}px`;
      button.style.top = `${Math.max(64, Math.min(top, window.innerHeight - height - gap))}px`;
    }
    position();
    window.addEventListener('scroll', position, true);
    window.addEventListener('resize', position);
    return () => {
      window.removeEventListener('scroll', position, true);
      window.removeEventListener('resize', position);
    };
  });

  return (
    <button ref={buttonRef} type="button" className="floating-action-cancel" onClick={onCancel}>
      행동 취소
    </button>
  );
}
