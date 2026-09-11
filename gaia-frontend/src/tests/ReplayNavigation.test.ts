import { describe, expect, it, vi } from 'vitest';
import { replayScrollTarget } from '../replay/navigation';
import { parseReplay } from '../replay/records';
import fixture from './fixtures/replay.json';

const initial = parseReplay(fixture).frames[0];
function root(markup: string) {
  const element = document.createElement('div');
  element.innerHTML = markup;
  return element;
}
function frame(type: string) {
  return { ...structuredClone(initial), player: 0, action: { type } };
}
describe('replay action-follow destination', () => {
  it.each(['ExploreSpaceship', 'RoundBoosterRangeExploreSpaceship', 'TwilightRangeExploreSpaceship', 'GleensExploreSpaceship'])(
    'scrolls to the ship containing the marked shuttle for %s', (type) => {
      const dom = root('<button class="board-action-hotspot" data-replay-highlight="true"></button><article data-replay-player="0"><aside class="faction-board-side-rack-booster"></aside></article><figure id="other" class="spaceship-board"><span class="spaceship-board-explorer"></span></figure><figure id="target" class="spaceship-board"><span class="spaceship-board-explorer" data-replay-highlight="true"></span></figure>');
      expect(replayScrollTarget(dom, frame(type))?.id).toBe('target');
    },
  );
  it('leaves initial state alone and sends pass/starting booster to boosters', () => {
    const dom = root('<div id="game-round-boosters"></div><div id="game-research"></div>');
    expect(replayScrollTarget(dom, initial)).toBeNull();
    for (const type of ['Pass', 'SelectStartingBooster']) {
      expect(replayScrollTarget(dom, frame(type))?.id).toBe('game-round-boosters');
    }
    expect(replayScrollTarget(dom, frame('ResearchAdvance'))?.id).toBe('game-research');
  });
  it('prioritizes the used action space over its construction result', () => {
    const dom = root('<button id="power" class="board-action-hotspot" data-replay-highlight="true"></button><svg><g class="hex-cell"><g class="replay-hex-highlight"></g></g></svg>');
    expect(replayScrollTarget(dom, frame('PowerAction'))?.id).toBe('power');
    dom.querySelector('button')!.className = 'spaceship-board-action-space board-action-hotspot';
    expect(replayScrollTarget(dom, frame('SpaceshipCreditTerraform'))?.id).toBe('power');
  });
  it('shows research after a lab upgrade, but the hex for an ordinary upgrade', () => {
    const before = structuredClone(initial);
    const after = frame('Upgrade');
    after.state.players[0].research_tracks.science += 1;
    const dom = root('<div id="game-research"></div><svg><g id="hex" class="hex-cell"><g class="replay-hex-highlight"></g></g></svg>');
    expect(replayScrollTarget(dom, after, before)?.id).toBe('game-research');
    expect(replayScrollTarget(dom, frame('Upgrade'), before)?.id).toBe('hex');
    expect(replayScrollTarget(dom, frame('Build'), before)?.id).toBe('hex');
  });
  it('shows another player’s own booster rather than the focal player’s action shelf', () => {
    const dom = root('<div id="game-player-actions"></div><article data-replay-player="0"><aside id="booster" class="faction-board-side-rack-booster"></aside></article><svg><g class="hex-cell"><g class="replay-hex-highlight"></g></g></svg>');
    expect(replayScrollTarget(dom, frame('RoundBoosterRangeBuild'))?.id).toBe('booster');
  });
  it('finds ship technology and actor-specific abilities without targeting another player', () => {
    const before = structuredClone(initial);
    const after = frame('RebellionGainTechTile');
    after.state.players[0].tech_tiles = [99];
    const dom = root('<figure class="spaceship-board"><img id="tile" data-replay-highlight="true"></figure><article id="other" data-replay-player="1"></article><article id="actor" data-replay-player="0"></article>');
    expect(replayScrollTarget(dom, after, before)?.id).toBe('tile');
    expect(replayScrollTarget(dom, frame('FreeAction'), before)).toBeNull();
  });
});

it('keeps the camera stationary when the map already occupies the viewport', () => {
  const dom = root('<div class="ai-replay-board"><section id="game-map"><svg><g class="hex-cell"><g class="replay-hex-highlight"></g></g></svg></section></div>');
  vi.spyOn(dom.querySelector('.ai-replay-board')!, 'getBoundingClientRect').mockReturnValue({top: 50, bottom: 750, height: 700} as DOMRect);
  const bounds = vi.spyOn(dom.querySelector('#game-map')!, 'getBoundingClientRect');
  bounds.mockReturnValue({top: -100, bottom: 900} as DOMRect);
  expect(replayScrollTarget(dom, frame('Build'), initial)).toBeNull();
  bounds.mockReturnValue({top: 900, bottom: 1800} as DOMRect);
  expect(replayScrollTarget(dom, frame('Build'), initial)?.classList.contains('hex-cell')).toBe(true);
});
it('does not jump to faction boards for resource decisions', () => {
  const dom = root('<article data-replay-player="0"></article>');
  for (const type of ['FreeAction', 'ChargePower', 'ChooseIncomeOrder']) {
    expect(replayScrollTarget(dom, frame(type), initial)).toBeNull();
  }
});
