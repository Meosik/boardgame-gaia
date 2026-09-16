import { describe, expect, it, vi } from 'vitest';
import { replayScrollTarget, scrollReplayTargetIntoView } from '../replay/navigation';
import { boardScrollDelta, scrollViewportFor } from '../boardScroll';
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
    expect(replayScrollTarget(dom, frame('RoundBoosterTerraformBuild'))?.id).toBe('booster');
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

it('always targets the same whole map, even when it is already partially visible', () => {
  const dom = root('<div class="ai-replay-board"><section id="game-map"><div class="game-board-container"><svg><g class="hex-cell"><g class="replay-hex-highlight"></g></g></svg></div></section></div>');
  vi.spyOn(dom.querySelector('.ai-replay-board')!, 'getBoundingClientRect').mockReturnValue({top: 50, bottom: 750, height: 700} as DOMRect);
  const bounds = vi.spyOn(dom.querySelector('#game-map')!, 'getBoundingClientRect');
  bounds.mockReturnValue({top: -100, bottom: 900} as DOMRect);
  expect(replayScrollTarget(dom, frame('Build'), initial)).toBe(dom.querySelector('.game-board-container'));
  bounds.mockReturnValue({top: 900, bottom: 1800} as DOMRect);
  expect(replayScrollTarget(dom, frame('Build'), initial)).toBe(dom.querySelector('.game-board-container'));
});

it('frames the research board for power actions, retaining precedence over construction', () => {
  const dom = root('<article id="game-research"><button class="board-action-hotspot" data-replay-highlight="true"></button></article><section id="game-map"><g class="hex-cell"><g class="replay-hex-highlight"></g></g></section>');
  expect(replayScrollTarget(dom, frame('PowerAction'), initial)?.id).toBe('game-research');
});

it('keeps a newly reached level5 visible for direct and compound research advances', () => {
  const dom = root('<article id="game-research"><span id="top" class="research-board-token" data-research-level="5" data-replay-highlight="true"></span></article>');
  const before = structuredClone(initial);
  before.state.players[0].research_tracks.science = 4;
  for (const type of ['ResearchAdvance', 'Upgrade']) {
    const after = frame(type);
    after.state.players[0].research_tracks.science = 5;
    expect(replayScrollTarget(dom, after, before)?.id).toBe('top');
    after.state.players[0].research_tracks.science = 4;
    before.state.players[0].research_tracks.science = 3;
    expect(replayScrollTarget(dom, after, before)?.id).toBe('game-research');
    before.state.players[0].research_tracks.science = 4;
  }
});

it.each([
  ['map', '<section id="game-map"><div id="target" class="game-board-container"></div></section>', 2150],
  ['research', '<article id="game-research"></article>', 2300],
  ['level5', '<article id="game-research"><span id="target" class="research-board-token" data-research-level="5"></span></article>', 1660],
])('gives %s the same landing position regardless of the previous scroll', (_name, markup, expected) => {
  const dom = root(`<div class="game-table-scroll">${markup}</div>`);
  const viewport = dom.querySelector<HTMLElement>('.game-table-scroll')!;
  viewport.style.overflowY = 'auto';
  const target = dom.querySelector('#target') ?? dom.querySelector('#game-research')!;
  const height = _name === 'level5' ? 20 : 1000;
  vi.spyOn(viewport, 'getBoundingClientRect').mockReturnValue({ top: 50, bottom: 750, height: 700 } as DOMRect);
  for (const previous of [0, 1500, 2100, 3000]) {
    vi.spyOn(target, 'getBoundingClientRect').mockReturnValue({ top: 2050 - previous, bottom: 2050 + height - previous, height } as DOMRect);
    const scrollBy = vi.fn();
    Object.defineProperty(viewport, 'scrollBy', { configurable: true, value: scrollBy });
    scrollReplayTargetIntoView(target, dom);
    const delta = scrollBy.mock.calls[0]?.[0].top ?? 0;
    expect(previous + delta).toBe(expected);
  }
});
describe('board jump alignment', () => {
  const viewport = { top: 0, bottom: 600, height: 600 };

  it('lands a too-tall board on its bottom rows, cutting only its top', () => {
    const board = { top: 100, bottom: 958, height: 858 };
    // Scrolling down 358 puts the board's bottom (power actions) on the viewport's bottom edge.
    expect(boardScrollDelta(board, viewport)).toBe(358);
    expect(boardScrollDelta(board, viewport, { preferred: 'start' })).toBe(358);
  });

  it('keeps a hex the action just changed in frame, pulling back up from the bottom', () => {
    const board = { top: 0, bottom: 858, height: 858 };
    expect(boardScrollDelta(board, viewport)).toBe(258);
    const hexNearTop = { top: 40, bottom: 80, height: 40 };
    expect(boardScrollDelta(board, viewport, { keepVisible: hexNearTop })).toBe(40);
    // A hex already inside the bottom-aligned view does not move the jump.
    const hexNearBottom = { top: 700, bottom: 740, height: 40 };
    expect(boardScrollDelta(board, viewport, { keepVisible: hexNearBottom })).toBe(258);
  });

  it('never scrolls above the board itself while keeping a hex visible', () => {
    const board = { top: 120, bottom: 978, height: 858 };
    const hexAtTop = { top: 120, bottom: 160, height: 40 };
    expect(boardScrollDelta(board, viewport, { keepVisible: hexAtTop })).toBe(120);
  });

  it('uses the caller preference for a board that fits', () => {
    const board = { top: 250, bottom: 650, height: 400 };
    expect(boardScrollDelta(board, viewport, { preferred: 'start' })).toBe(250);
    expect(boardScrollDelta(board, viewport)).toBe(50);
    const onScreen = { top: 100, bottom: 500, height: 400 };
    expect(boardScrollDelta(onScreen, viewport)).toBe(0);
  });

  it('does not scroll at all when the viewport cannot be measured', () => {
    const board = { top: 0, bottom: 858, height: 858 };
    expect(boardScrollDelta(board, { top: 0, bottom: 0, height: 0 })).toBe(0);
  });

  it('measures against the scrolling ancestor, not the outer replay frame', () => {
    const dom = root('<div class="ai-replay-board"><div class="game-table-scroll"><section id="target"></section></div></div>');
    const scroller = dom.querySelector<HTMLElement>('.game-table-scroll')!;
    scroller.style.overflowY = 'auto';
    const target = dom.querySelector('#target')!;

    expect(scrollViewportFor(target, dom.querySelector('.ai-replay-board'))).toBe(scroller);
  });

  it('falls back to the replay frame when nothing between scrolls', () => {
    const dom = root('<div class="ai-replay-board"><section id="target"></section></div>');
    const board = dom.querySelector('.ai-replay-board');

    expect(scrollViewportFor(dom.querySelector('#target')!, board)).toBe(board);
  });

});

it('does not jump to faction boards for resource decisions', () => {
  const dom = root('<article data-replay-player="0"></article>');
  for (const type of ['FreeAction', 'ChargePower', 'ChooseIncomeOrder']) {
    expect(replayScrollTarget(dom, frame(type), initial)).toBeNull();
  }
});
