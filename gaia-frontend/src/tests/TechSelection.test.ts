import { describe, it, expect } from 'vitest';
import { canTakeLostFleetAdvancedTile, techSelectionModeForStage } from '../techSelection';

describe('research board choice during a technology upgrade', () => {
  it('asks for a tile, then for a track', () => {
    expect(techSelectionModeForStage('tile')).toBe('tile');
    expect(techSelectionModeForStage('track')).toBe('track');
  });

  // The track of an advanced tile was clickable only in the tutorial: in a real game the
  // popup said "연구판에서 올릴 트랙을 누르세요" and the tracks did not answer.
  it('asks for a track after an advanced tile too', () => {
    expect(techSelectionModeForStage('advanced-track')).toBe('track');
  });

  it('asks for nothing at the other stages', () => {
    expect(techSelectionModeForStage('cover')).toBeNull();
    expect(techSelectionModeForStage('bonus-mine')).toBeNull();
    expect(techSelectionModeForStage(undefined)).toBeNull();
  });
});

describe('the Lost Fleet extra advanced tile', () => {
  const ready = {
    tileId: 21,
    side: '25-vp' as const,
    vp: 25,
    exploredShips: [0],
    greenFederationTokens: 1,
    uncoveredStandardTiles: 1,
  };

  it('can be taken at 25 points with a green token and a tile to cover', () => {
    expect(canTakeLostFleetAdvancedTile(ready)).toBe(true);
    expect(canTakeLostFleetAdvancedTile({ ...ready, vp: 24 })).toBe(false);
    expect(canTakeLostFleetAdvancedTile({ ...ready, greenFederationTokens: 0 })).toBe(false);
    expect(canTakeLostFleetAdvancedTile({ ...ready, uncoveredStandardTiles: 0 })).toBe(false);
    expect(canTakeLostFleetAdvancedTile({ ...ready, tileId: null })).toBe(false);
  });

  it('asks for three different spaceships on the other board side', () => {
    const ships = { ...ready, side: 'exploration-shuttles' as const, vp: 0 };
    expect(canTakeLostFleetAdvancedTile({ ...ships, exploredShips: [0, 1, 3] })).toBe(true);
    expect(canTakeLostFleetAdvancedTile({ ...ships, exploredShips: [0, 1, 1] })).toBe(false);
    expect(canTakeLostFleetAdvancedTile({ ...ships, exploredShips: undefined })).toBe(false);
  });
});
