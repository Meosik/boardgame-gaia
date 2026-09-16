import type { FactionId } from '../types/game';

export function academyActionReward(faction: FactionId | null): {
  resource: 'credits' | 'qic';
  label: string;
  amount: number;
} {
  return faction === 'Geodens' || faction === 'BalTaks'
    ? { resource: 'credits', label: '크레딧', amount: 4 }
    : { resource: 'qic', label: '정보 큐브', amount: 1 };
}
