"""Materialize B from frozen A with an auditable, bounded evaluation-only diff.

Never edits A or the working historical teacher. Non-evaluation functions must
remain identical; conservation changes are separately flagged as the OFF arm.
"""
import argparse
import difflib
import json
from pathlib import Path
import shutil
import teacher_ab as ab

# Exact substitutions fail closed if the frozen baseline ever changes.
PATCHES = {
 'four_factions/teacher.py': [
  ('def brainstone_committed(before, after, actor):', 'def brainstone_committed(before, after, actor):\n    if state_bridge.conservation_off():\n        return False'),
  ('    def value(self, state, actor, *, guide_tracks=False):', '    def value(self, state, actor, *, guide_tracks=False):\n        if state_bridge.active():\n            return state_bridge.value(state, actor)'),
  ("qic_conversion = action['type'] == 'FreeAction' and action['kind'] == 'QicToOre'", "qic_conversion = (action['type'] == 'FreeAction' and action['kind'] == 'QicToOre'\n                              and not state_bridge.conservation_off())"),
  ("if action['type'] == 'FreeAction':\n                value -= .25", "if action['type'] == 'FreeAction' and not state_bridge.active():\n                value -= .25"),
  ("-base-.25*action.get('count', 1)", "-base-(0 if state_bridge.active() else .25*action.get('count', 1))"),
 ],
 'four_factions/quick.py': [
  ('from four_factions.value import placement, potential', 'from four_factions.value import placement\nfrom state_evaluation_bridge import potential'),
  ("elif action['type'] == 'FreeAction' and action['kind'] == 'QicToOre':", "elif (action['type'] == 'FreeAction' and action['kind'] == 'QicToOre'\n              and not state_bridge.conservation_off()):"),
  ("if action['type'] == 'FreeAction':\n            value -= .25", "if action['type'] == 'FreeAction' and not state_bridge.active():\n            value -= .25"),
 ],
 'four_factions/preparation.py': [
  ('def leaf_value(snapshot, actor, root_player, *, guide_tracks=False):', 'def leaf_value(snapshot, actor, root_player, *, guide_tracks=False):\n    if state_bridge.active():\n        return state_bridge.value(snapshot[\'state\'], actor)'),
 ],
 'current_actions/teacher.py': [
  ('    def score(self, snapshot, action):\n        if action', '    def score(self, snapshot, action):\n        if state_bridge.active():\n            return state_bridge.score(snapshot, action)\n        if action'),
  ('    def route_value(self, before, after, already_legal, actions):', '    def route_value(self, before, after, already_legal, actions):\n        if state_bridge.active():\n            return state_bridge.route_value(self, before, after, already_legal, actions)'),
  ("scores[i] = (-12.0, 'purpose: no verified productive follow-up')", "scores[i] = (state_bridge.score(snapshot, action) if state_bridge.active() else\n                         (-12.0, 'purpose: no verified productive follow-up'))"),
 ],
 'current_actions/conservation.py': [
  ("FORBIDDEN = {'OreToCredit', 'KnowledgeToCredit'}", "FORBIDDEN = state_bridge.PolicyBans({'OreToCredit', 'KnowledgeToCredit'})"),
  ('    def protect(self, env, snapshot, scores):', '    def protect(self, env, snapshot, scores):\n        if state_bridge.conservation_off():\n            self.continuations = {}\n            return scores'),
 ],
 'action_purpose/teacher.py': [
  ('    def adjust_pass(self, snapshot, scores):', '    def adjust_pass(self, snapshot, scores):\n        if state_bridge.active():\n            return'),
  ('    def adjust_research_order(self, snapshot, scores):', '    def adjust_research_order(self, snapshot, scores):\n        if state_bridge.active():\n            return'),
  # Keep the same bounded ship-preview calls; replace only the numerical score.
  ("scores[i] = (20+value-4*max(0, len(player['explored_ships'])-1),", "if state_bridge.active():\n                scores[i] = (state_bridge.value(state, snapshot['player']) -\n                             state_bridge.value(snapshot['state'], snapshot['player']), 'state VP ship successor')\n                continue\n            scores[i] = (20+value-4*max(0, len(player['explored_ships'])-1),"),
 ],
}


def build(destination):
    baseline = ab.resolve_teacher('baseline')
    if ab.frozen_problems(baseline):
        raise ValueError('Frozen A changed')
    source = Path(baseline['source'])
    destination = Path(destination)
    if destination.exists():
        raise ValueError('Use a fresh destination; never overwrite experiment sources')
    # Same directory depth preserves frozen relative rule/catalog references.
    if destination.parent.resolve() != (ab.ROOT/'gaia-rl').resolve():
        raise ValueError('B source must be a direct gaia-rl child')
    destination.mkdir()
    for path in source.rglob('*'):
        if not path.is_file() or path.name == 'FROZEN.json' or '__pycache__' in path.parts:
            continue
        target = destination/path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    diff = []
    for name, replacements in PATCHES.items():
        before = (source/name).read_text()
        after = before
        for old,new in replacements:
            if after.count(old) != 1:
                raise ValueError(f'Patch mismatch: {name}: {old!r}')
            after = after.replace(old,new)
        # After the module docstring/imports: no __future__ imports in these modules.
        import ast
        node = ast.parse(after).body[0]
        lines = after.splitlines(keepends=True)
        lines.insert(node.end_lineno,'import state_evaluation_bridge as state_bridge\n')
        after = ''.join(lines)
        (destination/name).write_text(after)
        diff.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='A/'+name,tofile='B/'+name))
    for name in ('state_teacher.py','state_evaluation.py','state_evaluation_bridge.py'):
        shutil.copy2(ab.ROOT/'gaia-rl/experiments'/name,destination/name)
    (destination/'evaluation-only.diff').write_text(''.join(diff))
    changed = [str(p.relative_to(source)) for p in source.rglob('*') if p.is_file()
               and p.name != 'FROZEN.json' and '__pycache__' not in p.parts
               and p.read_bytes() != (destination/p.relative_to(source)).read_bytes()]
    if set(changed) != set(PATCHES):
        raise ValueError(f'Unexpected differences: {changed}')
    record = {'baseline_fingerprint':ab.fingerprint(baseline),'modified':changed,
              'unchanged_search':['four_factions/timed.py','faction_teachers/clock.py',
                                  'bgg_openings/planning.py','bgg_openings/catalog.py'],
              'conservation_off':'explicit second comparison; not an evaluation-only claim',
              'setup':'same A evaluation throughout initial-placement decisions and their rollouts'}
    (destination/'adapter-manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination')
    print(json.dumps(build(parser.parse_args().destination),indent=2))
