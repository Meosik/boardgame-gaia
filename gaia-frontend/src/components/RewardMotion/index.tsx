import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { ResourceToken, VictoryPointToken } from '../ResourceTokens';
import type { RewardBatch, RewardGain } from './rewards';
import './motion.css';

type Flight = RewardGain & { id: string; x: number; y: number; dx: number; dy: number; phase: 'cost' | 'gain'; delay: number };
function visible(element: Element | null): element is Element {
  if (!element) return false;
  const box = element.getBoundingClientRect();
  return box.width > 0 && box.height > 0 && box.top >= 0 && box.bottom <= window.innerHeight && box.left >= 0 && box.right <= window.innerWidth;
}

export function RewardMotion({ batch, duration = 1000 }: { batch: RewardBatch | null; duration?: number }) {
  const [flights, setFlights] = useState<Flight[]>([]);
  const last = useRef<number | null>(null);
  const cleanup = useRef(new Set<() => void>());
  useEffect(() => () => { cleanup.current.forEach(cancel => cancel()); cleanup.current.clear(); }, []);
  useEffect(() => {
    if (!batch) { cleanup.current.forEach(cancel => cancel()); cleanup.current.clear(); setFlights([]); return; }
    if (last.current === batch.id) return;
    last.current = batch.id;
    const card = document.querySelector(`[data-reward-player="${batch.player}"]`);
    if (!card) return;
    const hex = batch.hex ? document.querySelector(`.hex-cell[aria-label="hex ${batch.hex.q},${batch.hex.r}"]`) : null;
    const source = visible(hex) ? hex.getBoundingClientRect() : null;
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const active: { flight: Flight; target: Element }[] = [];
    for (const phase of ['cost', 'gain'] as const) {
      const items = phase === 'cost' ? batch.costs ?? [] : batch.gains;
      const delay = !reduced && phase === 'gain' && active.some(a => a.flight.phase === 'cost') ? duration : 0;
      items.forEach((item, index) => {
        const target = card.querySelector(`[data-reward-kind="${item.kind}"]`);
        // Never move the viewport or animate into a hidden/another player's panel.
        if (!visible(target)) return;
        const panel = target.getBoundingClientRect();
        const panelX = panel.left + panel.width / 2;
        const panelY = panel.top + panel.height / 2;
        const point = source ? { x: source.left + source.width / 2, y: source.top + source.height / 2 } : batch.origin;
        const boardX = point ? Math.max(32, Math.min(window.innerWidth - 32, point.x)) : Math.max(32, panel.left - 80);
        const boardY = Math.max(32, Math.min(window.innerHeight - 32, (point?.y ?? panelY) + (index - (items.length - 1) / 2) * 56));
        const cost = phase === 'cost';
        active.push({ target, flight: { ...item, amount: cost ? -item.amount : item.amount,
          id: `${batch.id}-${phase}-${item.kind}`, phase, delay,
          x: cost ? panelX : boardX, y: cost ? panelY : boardY,
          dx: cost ? boardX - panelX : panelX - boardX,
          dy: cost ? boardY - panelY : panelY - boardY } });
      });
    }
    if (!active.length) return;
    if (!reduced) setFlights(current => [...current, ...active.map(a => a.flight)]);
    const arrivals: Animation[] = [];
    const timers: number[] = [];
    for (const phase of ['cost', 'gain'] as const) {
      const group = active.filter(a => a.flight.phase === phase);
      if (!group.length) continue;
      timers.push(window.setTimeout(() => {
        setFlights(current => current.filter(f => !group.some(a => a.flight.id === f.id)));
        if (phase !== 'gain') return;
        group.forEach(({ target }) => {
          if (!visible(target)) return;
          const animation = target.animate?.([
            { filter: 'drop-shadow(0 0 8px #a2f6dd)', outline: '2px solid #a2f6dd' },
            { filter: 'none', outline: '2px solid transparent' },
          ], { duration: reduced ? 200 : 400, easing: 'ease-out' });
          if (animation) arrivals.push(animation);
        });
      }, reduced ? 0 : group[0].flight.delay + duration));
    }
    const release = window.setTimeout(() => cleanup.current.delete(cancel), Math.max(...active.map(a => a.flight.delay)) + duration + 500);
    const cancel = () => {
      timers.forEach(clearTimeout); clearTimeout(release); arrivals.forEach(a => a.cancel());
    };
    cleanup.current.add(cancel);
  }, [batch, duration]);
  return <div className="reward-motion-layer" aria-hidden="true">
    {flights.map(f => <span className="reward-motion-flight" data-motion-phase={f.phase} key={f.id} style={{ left: f.x, top: f.y, animationDelay: `${f.delay}ms`, animationDuration: `${duration}ms`,
      '--reward-dx': `${f.dx}px`, '--reward-dy': `${f.dy}px` } as CSSProperties}>
      {f.kind === 'vp' ? <VictoryPointToken value={f.amount} /> : <ResourceToken resource={f.kind} value={f.amount} />}
    </span>)}
  </div>;
}
