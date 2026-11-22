import { describe, it, expect } from 'vitest';
import { techSelectionModeForStage } from '../techSelection';

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
