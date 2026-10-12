/**
 * Where a jump to one of the big shared boards should stop — used by the in-game section shortcuts
 * and by the replay's action-follow.
 */

export interface ScrollBox {
  top: number;
  bottom: number;
  height: number;
}

/**
 * The box a jump is measured against: the nearest scrolling ancestor of the target. The replay
 * nests `.game-table-scroll` (the element that actually scrolls) inside `.ai-replay-board`, and the
 * two differ by the playback bar's height, so measuring the outer one would call a board that
 * overflows by less than that difference a fit.
 */
export function scrollViewportFor(target: Element, fallback: Element | null): Element | null {
  for (let element = target.parentElement; element; element = element.parentElement) {
    const overflowY = getComputedStyle(element).overflowY;
    if (overflowY === 'auto' || overflowY === 'scroll') return element;
  }
  return fallback;
}

/**
 * How far to scroll, in pixels down, so the jump shows what the player needs:
 *
 * - A board taller than the viewport lands on its **bottom** rows — the research board's power
 *   actions, the map's lower sectors — and only its top (research level 5) scrolls away.
 * - `keepVisible` overrides that: a hex the action just changed near the board's top pulls the
 *   view back up just far enough to include it, never past the board's own top edge.
 * - A board that fits uses `preferred`: 'start' for a section shortcut, 'nearest' to leave the
 *   replay camera alone when the target is already on screen.
 */
export function boardScrollDelta(
  target: ScrollBox,
  viewport: ScrollBox,
  options: {
    preferred?: ScrollLogicalPosition;
    keepVisible?: ScrollBox | null;
    /** Off for boards whose top matters as much as their bottom, like the map. */
    allowBottomAlign?: boolean;
  } = {},
): number {
  const preferred = options.preferred ?? 'nearest';
  const allowBottomAlign = options.allowBottomAlign ?? true;
  // A viewport with no measurable height (detached node, display:none ancestor) says nothing about
  // what would be visible, and scrolling on that guess would throw the view somewhere arbitrary.
  if (viewport.height <= 0) return 0;
  let delta: number;

  if (allowBottomAlign && target.height > viewport.height) {
    delta = target.bottom - viewport.bottom;
  } else if (preferred === 'center') {
    delta = target.top + target.height / 2 - (viewport.top + viewport.height / 2);
  } else if (preferred === 'start') {
    delta = target.top - viewport.top;
  } else if (target.top < viewport.top) {
    delta = target.top - viewport.top;
  } else if (target.bottom > viewport.bottom) {
    delta = target.bottom - viewport.bottom;
  } else {
    delta = 0;
  }

  const keep = options.keepVisible;
  if (keep) {
    const keepTopAfter = keep.top - delta;
    if (keepTopAfter < viewport.top) delta -= viewport.top - keepTopAfter;
    const boardTop = target.top - viewport.top;
    if (delta < boardTop) delta = boardTop;
  }
  return Math.round(delta);
}

function box(element: Element): ScrollBox {
  const rect = element.getBoundingClientRect();
  return { top: rect.top, bottom: rect.bottom, height: rect.height };
}

/**
 * The visible part of the page when the page itself scrolls (the narrow layout): the sticky
 * shortcut bar covers the top of the window, so a board is only visible below the bar's bottom
 * edge. Null when there is no bar to measure.
 */
function pageViewport(): ScrollBox | null {
  const bar = document.querySelector('.game-table-top-nav');
  if (!bar) return null;
  const rect = bar.getBoundingClientRect();
  if (rect.height <= 0) return null;
  const top = Math.max(0, rect.bottom);
  const bottom = window.visualViewport?.height ?? window.innerHeight;
  return { top, bottom, height: bottom - top };
}

export function scrollBoardIntoView(
  target: Element,
  options: {
    fallbackViewport?: Element | null;
    behavior?: ScrollBehavior;
    preferred?: ScrollLogicalPosition;
    /** Something the jump must not scroll past, e.g. the hex an action just changed. */
    keepVisible?: Element | null;
    allowBottomAlign?: boolean;
  } = {},
): void {
  const viewport = scrollViewportFor(target, options.fallbackViewport ?? null);
  const behavior = options.behavior ?? 'instant';
  if (!viewport || typeof (viewport as HTMLElement).scrollBy !== 'function') {
    const page = viewport ? null : pageViewport();
    if (!page) {
      target.scrollIntoView?.({ behavior, block: 'nearest', inline: 'nearest' });
      return;
    }
    const pageDelta = boardScrollDelta(box(target), page, {
      preferred: options.preferred,
      keepVisible: options.keepVisible ? box(options.keepVisible) : null,
      allowBottomAlign: options.allowBottomAlign,
    });
    if (pageDelta !== 0) window.scrollBy({ top: pageDelta, behavior });
    return;
  }

  const delta = boardScrollDelta(box(target), box(viewport), {
    preferred: options.preferred,
    keepVisible: options.keepVisible ? box(options.keepVisible) : null,
    allowBottomAlign: options.allowBottomAlign,
  });
  if (delta !== 0) (viewport as HTMLElement).scrollBy({ top: delta, behavior });
}

/** The hex a just-committed action highlighted, in live play or a replay frame. */
export function recentActionHex(root: ParentNode = document): Element | null {
  return root.querySelector('.replay-hex-highlight')?.closest('.hex-cell') ?? null;
}
