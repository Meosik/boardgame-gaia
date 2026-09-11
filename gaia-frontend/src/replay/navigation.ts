import type { ReplayFrame } from './records';
import { replayHighlight } from './highlight';

const MARKED = '[data-replay-highlight="true"]';

/** Resolve against the committed replay DOM, never the live game or a previous move. */
export function replayScrollTarget(root: HTMLElement, frame: ReplayFrame, previous?: ReplayFrame): Element | null {
  const action = frame.action;
  if (!action || action.type === 'FreeAction' || action.type === 'ChargePower' || action.type === 'ChooseIncomeOrder') return null;
  const find = (selector: string) => root.querySelector(selector);
  const mark = replayHighlight(frame, previous);
  const actorBoard = find(`[data-replay-player="${frame.player}"]`);
  if (action.type === 'Pass' || action.type === 'SelectStartingBooster') return find('#game-round-boosters');
  if (action.type === 'ResearchAdvance') return find('#game-research');
  const exploredShip = find(`.spaceship-board-explorer${MARKED}`)?.closest('.spaceship-board');
  if (exploredShip) return exploredShip;
  // Show the action's source, even when its outcome also changes a planet or research.
  const hotspot = find(`.board-action-hotspot${MARKED}`);
  if (hotspot) return hotspot;
  const personalAction = find(`.player-action-tile${MARKED}`);
  if (personalAction && action.type !== 'Upgrade') return personalAction;
  if (action.type.startsWith('RoundBooster')) {
    return actorBoard?.querySelector('.faction-board-side-rack-booster') ?? actorBoard;
  }
  if (mark.research.size) return find('#game-research');
  if (mark.standardTech.size || mark.advancedTech.size) {
    const tile = find(`.research-board-standard-tech${MARKED}, .research-board-advanced-tech${MARKED}, .spaceship-board img${MARKED}, .faction-board-side-rack-tech ${MARKED}`);
    if (tile) return tile;
  }
  const hex = find('.replay-hex-highlight')?.closest('.hex-cell');
  if (hex) {
    const map = find('#game-map');
    const viewport = find('.ai-replay-board');
    if (map && viewport) {
      const bounds = map.getBoundingClientRect();
      const view = viewport.getBoundingClientRect();
      const middle = (view.top + view.bottom) / 2;
      if (view.height > 0 && bounds.top <= middle && bounds.bottom >= middle) return null;
    }
    return hex;
  }
  // Free conversions/other faction abilities have no shared-board target.
  return null;
}
