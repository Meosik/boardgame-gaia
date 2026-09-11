import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { GamePieceIcon } from '../GamePieceIcon';
import { ResourceToken, VictoryPointToken } from '../ResourceTokens';
import './preview.css';

type Resource = 'ore' | 'knowledge' | 'credits' | 'vp';
type Reward = { kind: Resource; amount: number };
type Flight = Reward & { id: number; x: number; y: number; dx: number; dy: number };
const LABELS: Record<Resource, string> = { ore: '광석', knowledge: '지식', credits: '크레딧', vp: '점수' };
const FLIGHT_DURATION = 1000;
const INITIAL: Record<Resource, number> = { ore: 4, knowledge: 3, credits: 15, vp: 10 };
const EXAMPLES: { label: string; rewards: Reward[] }[] = [
  { label: '광석 +2', rewards: [{ kind: 'ore', amount: 2 }] },
  { label: '지식 +1 · 크레딧 +3', rewards: [{ kind: 'knowledge', amount: 1 }, { kind: 'credits', amount: 3 }] },
  { label: '점수 +3', rewards: [{ kind: 'vp', amount: 3 }] },
];

/** Isolated animation sandbox: no room/store/socket imports or persistence. */
export function RewardPreview() {
  const [totals, setTotals] = useState(INITIAL);
  const [flights, setFlights] = useState<Flight[]>([]);
  const [arrivals, setArrivals] = useState<Partial<Record<Resource, number>>>({});
  const [status, setStatus] = useState('버튼을 눌러 획득 모션을 확인하세요.');
  const arena = useRef<HTMLDivElement>(null);
  const source = useRef<HTMLDivElement>(null);
  const targets = useRef<Partial<Record<Resource, HTMLDivElement | null>>>({});
  const sequence = useRef(0);
  const timers = useRef(new Set<ReturnType<typeof setTimeout>>());

  function clearTimers() {
    timers.current.forEach(clearTimeout);
    timers.current.clear();
  }
  useEffect(() => () => clearTimers(), []);

  function later(callback: () => void, delay: number) {
    const timer = setTimeout(() => { timers.current.delete(timer); callback(); }, delay);
    timers.current.add(timer);
  }

  function showReward(rewards: Reward[]) {
    if (!arena.current || !source.current) return;
    const bounds = arena.current.getBoundingClientRect();
    const origin = source.current.getBoundingClientRect();
    const batch = rewards.map((reward, index): Flight => {
      const end = targets.current[reward.kind]!.getBoundingClientRect();
      const x = origin.left + origin.width / 2 - bounds.left;
      const y = origin.top + origin.height / 2 - bounds.top + (index - (rewards.length - 1) / 2) * 72;
      return { ...reward, id: ++sequence.current, x, y,
        dx: end.left + end.width / 2 - bounds.left - x,
        dy: end.top + end.height / 2 - bounds.top - y };
    });
    setFlights(current => [...current, ...batch]);
    const duration = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 0 : FLIGHT_DURATION;
    later(() => {
      setTotals(current => {
        const next = { ...current };
        rewards.forEach(({ kind, amount }) => { next[kind] += amount; });
        return next;
      });
      setArrivals(current => ({ ...current, ...Object.fromEntries(batch.map(f => [f.kind, f.id])) }));
      setFlights(current => current.filter(f => !batch.some(b => b.id === f.id)));
      setStatus(`${rewards.map(r => `${LABELS[r.kind]} +${r.amount}`).join(' · ')} 획득 (미리보기)`);
    }, duration);
  }

  function reset() {
    clearTimers();
    setFlights([]); setTotals(INITIAL); setArrivals({});
    setStatus('미리보기 숫자를 초기화했습니다.');
  }

  return (
    <main className="reward-preview">
      <header className="reward-preview-header">
        <div><p className="reward-preview-eyebrow">MOTION PREVIEW</p><h1>자원 획득 미리보기</h1></div>
        <a className="btn btn-secondary" href="?">첫 화면</a>
      </header>
      <p className="reward-preview-description">실제 게임과 연결되지 않은 연출 예시입니다. 방과 자원은 변경되지 않습니다.</p>
      <div className="reward-preview-arena" ref={arena}>
        <section className="reward-preview-origin">
          <span className="reward-preview-caption">행동한 위치</span>
          <div className="reward-preview-source" ref={source}>
            <GamePieceIcon kind="ore" />
            <strong>보상 획득</strong>
          </div>
          <p>건물이나 행동 타일 자리</p>
        </section>
        <section className="reward-preview-destination" aria-label="미리보기 내 자원">
          <h2>내 자원 <small>미리보기</small></h2>
          <div className="reward-preview-resources">
            {(Object.keys(INITIAL) as Resource[]).map(kind => (
              <div className="reward-preview-resource" ref={element => { targets.current[kind] = element; }} key={kind}>
                <span key={arrivals[kind] ?? 0} className={arrivals[kind] ? 'reward-preview-arrived' : ''}>
                  <span aria-label={`${LABELS[kind]} 수량`}>
                    {kind === 'vp' ? <VictoryPointToken value={totals[kind]} /> : <ResourceToken resource={kind} value={totals[kind]} />}
                  </span>
                </span>
                <small>{LABELS[kind]}</small>
              </div>
            ))}
          </div>
        </section>
        <div className="reward-preview-flight-layer" aria-hidden="true">
          {flights.map(f => <span key={f.id} className="reward-preview-flight" style={{
            left: f.x, top: f.y, '--reward-dx': `${f.dx}px`, '--reward-dy': `${f.dy}px`,
          } as CSSProperties}>{f.kind === 'vp' ? <VictoryPointToken value={f.amount} /> : <ResourceToken resource={f.kind} value={f.amount} />}</span>)}
        </div>
      </div>
      <section className="reward-preview-examples" aria-label="획득 모션 실행">
        {EXAMPLES.map(example => <button className="btn btn-primary" key={example.label}
          onClick={() => showReward(example.rewards)}>{example.label}</button>)}
        <button className="btn btn-secondary" onClick={reset}>미리보기 초기화</button>
      </section>
      <p className="reward-preview-status" role="status">{status}</p>
      <p className="reward-preview-description">약 1초 · 연속 클릭 가능 · 화면 자동 이동 없음 · 기기의 동작 줄이기 설정을 따릅니다.</p>
    </main>
  );
}
