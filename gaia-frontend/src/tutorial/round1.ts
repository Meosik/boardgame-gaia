import type { GameAction, GameState, TutorialState } from '../types/game';

export function currentTutorialStep(tutorial: TutorialState) {
  return tutorial.steps[tutorial.step - 1];
}

export function tutorialNotice(tutorial: TutorialState): string {
  const step = currentTutorialStep(tutorial);
  return step ? `지금은 ${step.instruction}` : '튜토리얼을 마쳤습니다. 로비로 돌아가세요.';
}

function normalized(value: unknown): unknown {
  if (Array.isArray(value)) {
    const items = value.map(normalized);
    return items.every(item => item && typeof item === 'object' && 'q' in item && 'r' in item)
      ? items.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b))) : items;
  }
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value)
    .filter(([, v]) => v != null).sort(([a], [b]) => a.localeCompare(b))
    .map(([key, v]) => [key, normalized(v)]));
  return value;
}

export function matchesTutorialAction(tutorial: TutorialState, action: GameAction): boolean {
  return JSON.stringify(normalized(currentTutorialStep(tutorial)?.action)) === JSON.stringify(normalized(action));
}

export function tutorialTargets(state: GameState): string[] {
  const step = state.tutorial && currentTutorialStep(state.tutorial);
  if (!step) return [];
  const action = step.action;
  const targets = [step.target, `action:${action.type}`];
  if (action.type === 'ChooseIncomeOrder') targets.push('income:building', 'income:research', 'income:booster');
  if (action.type === 'Build') targets.push('cost:Mine');
  if (action.type === 'ChargePower') targets.push('power:I', 'power:II', 'power:III', 'hex:-2,0', 'hex:-1,-1');
  if (action.type === 'FreeAction' && action.kind.startsWith('PowerTo')) targets.push('power:III', 'power:I');
  if (action.type === 'Upgrade') {
    const to = typeof action.to === 'string' ? action.to : 'Academy';
    targets.push(`cost:${to}`);
    if (to === 'TradingStation') targets.push('hex:-2,0');
  }
  if (action.type === 'GaiaFormation') targets.push('power:G');
  if (action.type === 'PowerAction') targets.push('power:III', 'power:I');
  if (action.type === 'FreeAction' && action.kind === 'KnowledgeToCredit') targets.push('free-actions');
  if ('ship' in action) {
    const coord = state.board.spaceship_tiles?.[action.ship];
    if (coord) targets.push(`hex:${coord.q},${coord.r}`);
  }
  if (action.type === 'Upgrade') {
    targets.push(`upgrade:${typeof action.to === 'string' ? action.to : `Academy:${action.to.Academy}`}`);
    const choice = action.tech_tile_choice;
    if (choice?.kind === 'Standard') targets.push(`tech:${choice.tile}`);
    if (choice?.kind === 'Advanced') targets.push(`advanced:${choice.track}`);
    if (choice?.kind === 'LostFleetAdvanced') targets.push('advanced:LostFleet');
    if (choice && choice.kind !== 'Standard') targets.push(`cover:${choice.covered_tile}`);
    if (choice?.advance_track) targets.push(`research:${choice.advance_track}`);
  }
  if (action.type === 'FormFederation') {
    [...action.hexes, ...(action.satellite_hexes ?? [])].forEach(c => targets.push(`hex:${c.q},${c.r}`));
    if (action.token.source === 'Supply') targets.push(`federation:${action.token.kind}`);
  }
  if (action.type === 'RoundBoosterRangeExploreSpaceship') targets.push('booster');
  if (action.type === 'TwilightReplayFederationToken') targets.push(`federation:${action.token_kind}`);
  return targets;
}

// These boards are permanently mounted; selecting a step reveals its scroll region.
export function tutorialPanel(state: GameState): string | null {
  const action = state.tutorial && currentTutorialStep(state.tutorial)?.action;
  if (!action) return null;
  switch (action.type) {
    case 'FreeAction': return 'game-free-actions';
    case 'ChargePower': return 'game-factions';
    case 'ResearchAdvance':
    case 'PowerAction': return 'game-research';
    case 'ExamineArtifact':
    case 'TwilightReplayFederationToken': return 'game-ships';
    case 'TechTileSpecialAction':
    case 'AcademyQicAction': return 'game-player-actions';
    case 'Pass': return 'game-round-boosters';
    default: return 'game-map';
  }
}
