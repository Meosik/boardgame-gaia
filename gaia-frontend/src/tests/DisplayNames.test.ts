import { describe, expect, it } from 'vitest';
import {
  FACTION_DISPLAY_NAMES,
  LOST_FLEET_DISPLAY_NAME,
  PLANET_TYPE_DISPLAY_NAMES,
  SPACESHIP_DISPLAY_NAMES,
} from '../displayNames';

describe('Korean display names', () => {
  it('keeps faction names consistent', () => {
    expect(FACTION_DISPLAY_NAMES).toEqual({
      Terrans: '테란',
      Lantids: '란티다',
      Xenos: '제노스',
      Gleens: '글린',
      Taklons: '타클론',
      Ambas: '앰바스',
      HadschHallas: '하드쉬 할라',
      Ivits: '하이브',
      Geodens: '기오덴',
      BalTaks: '발 타크',
      Firaks: '파이락',
      Bescods: '매드 안드로이드',
      Nevlas: '네블라',
      Itars: '아이타',
      Tinkeroids: '팅커로이드',
      Darkanians: '다카니안',
      Moweyds: '모웨이드',
      SpaceGiants: '스페이스자이언트',
    });
  });

  it('keeps spaceship and expansion names consistent', () => {
    expect(SPACESHIP_DISPLAY_NAMES).toEqual({
      Twilight: '트와일라잇',
      Rebellion: '리벨리온',
      TFMars: 'T F 마스',
      Eclipse: '이클립스',
    });
    expect(LOST_FLEET_DISPLAY_NAME).toBe('잃어버린 함대');
  });

  it('keeps planet names consistent', () => {
    expect(PLANET_TYPE_DISPLAY_NAMES).toEqual({
      Terra: '대지',
      Desert: '사막',
      Ice: '얼음',
      Swamp: '늪',
      Oxide: '산성',
      Titanium: '티타늄',
      Volcanic: '화산',
      Transdim: '차원변형행성',
      Gaia: '가이아',
      LostPlanet: '검은 행성',
      Asteroid: '소행성',
      ProtoPlanet: '원시 행성',
    });
  });
});
