import { describe, expect, it } from 'vitest';
import { decodeHexCoordinates } from '../api/websocket';
import { projectedIncome } from '../income';
import data from '../data/income.json';
import cases from './fixtures/incomeProjection.json';
import type { EconomyResearchTileSide, PlayerState } from '../types/game';

describe('current-state recurring income', () => {
  for (const [index, sample] of cases.entries()) {
    it(`matches native faction income ${sample.player.faction} / ${sample.side} / ${index}`, () => {
      const before = structuredClone(sample.player);
      const result = projectedIncome(decodeHexCoordinates(sample.player) as PlayerState, sample.side as EconomyResearchTileSide);
      expect(data.fields.map((field) => result[field as keyof typeof result])).toEqual(sample.income);
      expect(sample.player).toEqual(before);
    });
  }

  it('updates on station/lab upgrades and rewind without any events', () => {
    const player = decodeHexCoordinates(cases.find((c) => c.player.faction === 'Xenos')!.player) as PlayerState;
    const before = projectedIncome(player);
    const mine = player.structures.find((s) => s.kind === 'Mine')!;
    mine.kind = 'TradingStation';
    const station = projectedIncome(player);
    expect(station.ore).toBe(before.ore - 1);
    expect(station.credits).toBe(before.credits + 4);
    mine.kind = 'ResearchLab';
    const lab = projectedIncome(player);
    expect(lab.credits).toBe(before.credits);
    expect(lab.knowledge).toBe(before.knowledge + 1);
    mine.kind = 'Mine';
    expect(projectedIncome(player)).toEqual(before);
  });

  it('removes level-four income at five and uses the newly held booster', () => {
    const player = decodeHexCoordinates(cases[0].player) as PlayerState;
    player.research_tracks.economy = 4;
    player.research_tracks.science = 4;
    const four = projectedIncome(player);
    player.research_tracks.economy = 5;
    player.research_tracks.science = 5;
    const five = projectedIncome(player);
    expect(four.ore - five.ore).toBe(2);
    expect(four.credits - five.credits).toBe(2);
    expect(four.power_charge - five.power_charge).toBe(2);
    expect(four.knowledge - five.knowledge).toBe(4);
    player.booster = 12;
    expect(projectedIncome(player).qic).toBe(five.qic - 1);
  });

  it('does not count QIC academy activation as automatic income', () => {
    const player = decodeHexCoordinates(cases.find((c) => c.player.faction === 'Geodens')!.player) as PlayerState;
    const before = projectedIncome(player);
    player.structures.push({ hex: { q: 1, r: 0 }, kind: { Academy: 'Qic' } });
    expect(projectedIncome(player)).toEqual(before);
  });
});
