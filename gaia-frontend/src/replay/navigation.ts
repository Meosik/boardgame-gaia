import type { ReplayFrame } from './records';
import { replayHighlight } from './highlight';
import { scrollBoardIntoView } from '../boardScroll';

const MARKED = '[data-replay-highlight="true"]';

/** Resolve against the committed replay DOM, never the live game or a previous move. */
export function replayScrollTarget(root: HTMLElement, frame: ReplayFrame, previous?: ReplayFrame): Element | null {
  const action = frame.action;
  if (!action || action.type === 'FreeAction' || action.type === 'ChargePower' || action.type === 'ChooseIncomeOrder') return null;
  const find = (selector: string) => root.querySelector(selector);
  const mark = replayHighlight(frame, previous);
  const researchTarget = () => {
    const actor = frame.state.players.find(player => player.player_id === frame.player);
    const reachedTop = actor && Object.entries(actor.research_tracks)
      .some(([track, level]) => level === 5 && mark.research.has(track));
    return (reachedTop ? find(`.research-board-token${MARKED}[data-research-level="5"]`) : null)
      ?? find('#game-research');
  };
  const actorBoard = find(`[data-replay-player="${frame.player}"]`);
  if (action.type === 'Pass' || action.type === 'SelectStartingBooster') return find('#game-round-boosters');
  if (action.type === 'ResearchAdvance') return researchTarget();
  const exploredShip = find(`.spaceship-board-explorer${MARKED}`)?.closest('.spaceship-board');
  if (exploredShip) return exploredShip;
  // Show the action's source, even when its outcome also changes a planet or research.
  const hotspot = find(`.board-action-hotspot${MARKED}`);
  if (hotspot) return hotspot.closest('#game-research') ? researchTarget() : hotspot;
  const personalAction = find(`.player-action-tile${MARKED}`);
  if (personalAction && action.type !== 'Upgrade') return personalAction;
  const hex = find('.replay-hex-highlight')?.closest('.hex-cell');
  const map = () => find('#game-map .game-board-container') ?? find('#game-map') ?? hex;
  if (action.type.startsWith('RoundBooster')) {
    // A booster build or Gaia formation happens on the map; show where it landed.
    if (hex) return map();
    return actorBoard?.querySelector('.faction-board-side-rack-booster') ?? actorBoard;
  }
  if (mark.research.size) return researchTarget();
  if (mark.standardTech.size || mark.advancedTech.size) {
    const tile = find(`.research-board-standard-tech${MARKED}, .research-board-advanced-tech${MARKED}, .spaceship-board img${MARKED}, .faction-board-side-rack-tech ${MARKED}`);
    if (tile) return tile;
  }
  if (hex) return map();
  // Free conversions/other faction abilities have no shared-board target.
  return null;
}

export function scrollReplayTargetIntoView(target: Element, root: Element | null): void {
  const map = target.matches('#game-map, .game-board-container');
  const topResearch = target.matches('.research-board-token[data-research-level="5"]');
  // The two shared-board views have one landing position, independent of the last
  // move/manual scroll. Other action sources retain their existing nearest behavior.
  scrollBoardIntoView(target, {
    fallbackViewport: root?.querySelector('.ai-replay-board') ?? root,
    preferred: map || topResearch ? 'center' : target.id === 'game-research' ? 'start' : 'nearest',
    allowBottomAlign: !map && !topResearch,
  });
}
