import { describe, expect, it } from 'vitest';
import { chargeAmount, chargeOfferText } from '../components/chargeAmount';
import type { PowerCycle } from '../types/game';

function power(bowl1: number, bowl2: number, bowl3: number, brainstone?: PowerCycle['brainstone']): PowerCycle {
  return { bowl1, bowl2, bowl3, gaia_bowl: 0, gaia_forming: 0, brainstone } as PowerCycle;
}

describe('chargeAmount', () => {
  it('gives the whole offer when the power cycle and the VP allow it', () => {
    expect(chargeAmount(3, power(4, 4, 0), 10)).toBe(3);
  });

  it('is cut down to what moves every token to Area III', () => {
    // The rulebook's example: one token left in Area II charges 1 of the institute's 3.
    expect(chargeAmount(3, power(0, 1, 5), 10)).toBe(1);
    // A token in Area I takes two power.
    expect(chargeAmount(3, power(1, 0, 5), 10)).toBe(2);
    expect(chargeAmount(3, power(1, 1, 4), 10)).toBe(3);
    expect(chargeAmount(3, power(0, 0, 6), 10)).toBe(0);
  });

  it('counts the Brainstone as a token', () => {
    expect(chargeAmount(3, power(0, 0, 6, 'Area1'), 10)).toBe(2);
    expect(chargeAmount(3, power(0, 0, 6, 'Area2'), 10)).toBe(1);
    expect(chargeAmount(3, power(0, 0, 6, 'Area3'), 10)).toBe(0);
  });

  it('is cut down to VP + 1', () => {
    expect(chargeAmount(3, power(4, 4, 0), 1)).toBe(2);
    expect(chargeAmount(3, power(4, 4, 0), 0)).toBe(1);
  });

  it('counts a token gained into Area I before the charge', () => {
    expect(chargeAmount(3, power(0, 1, 5), 10, 1)).toBe(3);
  });
});

describe('chargeOfferText', () => {
  it('names the amount really charged and its VP cost', () => {
    expect(chargeOfferText(3, 3)).toBe('파워 3 충전 (승점 2점 소모).');
    expect(chargeOfferText(3, 1)).toContain('지금은 1만 충전됩니다 (승점 0점 소모)');
    expect(chargeOfferText(3, 0)).toContain('충전할 수 있는 파워가 없습니다');
  });
});
