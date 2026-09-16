import { useEffect, useRef } from 'react';

export function FeedbackDialog({ reason, plan, setReason, setPlan, onClose }: {
  reason: string; plan: string; setReason: (text: string) => void; setPlan: (text: string) => void;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement;
    dialog.current?.querySelector('textarea')?.focus();
    return () => { if (previous instanceof HTMLElement) previous.focus(); };
  }, []);
  return <div className="coach-feedback-scrim"><section ref={dialog} role="dialog" aria-modal="true"
    aria-label="AI 추천과 다른 수" className="coach-feedback-dialog" onKeyDown={event => {
      if (event.key === 'Escape') { event.preventDefault(); onClose(); }
      if (event.key !== 'Tab') return;
      const fields = [...(dialog.current?.querySelectorAll<HTMLElement>('textarea, button:not(:disabled)') ?? [])];
      const first = fields[0], last = fields[fields.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }}>
    <h2>AI 추천과 다른 수를 골랐습니다</h2>
    <p>선택 이유와 다음 계획을 적어 주세요. 아직 게임은 진행되지 않았습니다.</p>
    <fieldset><legend>이 수가 더 좋은 이유와 다음 계획은?</legend>
      <label>선택 이유<textarea maxLength={8000} rows={3} value={reason} onChange={e => setReason(e.target.value)} /></label>
      <label>다음 계획<textarea maxLength={8000} rows={2} value={plan} onChange={e => setPlan(e.target.value)} /></label>
    </fieldset>
    <div className="coach-board-shortcuts">
      <button type="button" onClick={onClose}>돌아가서 더 보기</button>
      <button type="button" disabled={!reason.trim() || !plan.trim()} onClick={onClose}>입력 완료 · 선택 유지</button>
    </div>
    <p className="coach-muted">입력 후에도 마지막 실행 승인이 필요합니다.</p>
  </section></div>;
}
