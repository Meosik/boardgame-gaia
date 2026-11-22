import type { PowerCycle } from '../types/game';

/**
 * The power a charge offer really gives when accepted (engine `passive_charge_amount`, rulebook
 * p.17): the structure's power value, cut down to what moves every token of the power cycle to
 * Area III (2 power per token in Area I, 1 per token in Area II, the Brainstone counting as a
 * token) and to VP + 1 (charging n power costs n - 1 VP).
 *
 * `extraAreaOneTokens`: tokens gained into Area I before the charge (the Taklons institute's
 * "token first" choice).
 */
export function chargeAmount(
  maxPower: number,
  power: PowerCycle,
  vp: number,
  extraAreaOneTokens = 0,
): number {
  const brainstone = power.brainstone === 'Area1' ? 2 : power.brainstone === 'Area2' ? 1 : 0;
  const chargeable = 2 * (power.bowl1 + extraAreaOneTokens) + power.bowl2 + brainstone;
  return Math.max(0, Math.min(maxPower, chargeable, Math.max(0, vp) + 1));
}

/** The prompt's sentence for an offer of `maxPower` that gives `amount`. */
export function chargeOfferText(maxPower: number, amount: number): string {
  if (amount <= 0) return `건물 파워는 ${maxPower}이지만 지금은 충전할 수 있는 파워가 없습니다.`;
  const cost = `승점 ${amount - 1}점 소모`;
  if (amount < maxPower) {
    return `건물 파워는 ${maxPower}이지만 지금은 ${amount}만 충전됩니다 (${cost}). 파워 토큰이 3구역으로 다 가거나 승점이 모자라면 그만큼만 충전합니다.`;
  }
  return `파워 ${amount} 충전 (${cost}).`;
}
