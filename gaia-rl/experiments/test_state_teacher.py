"""Checks the generated B actually reuses the frozen control's search code."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'gaia-rl/tools'))
from build_state_teacher import build, PATCHES
import teacher_ab as ab


class StateTeacherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=ROOT/'gaia-rl'/('state-b-test-'+uuid.uuid4().hex[:8])
        cls.record=build(cls.source)
        cls.baseline=Path(ab.resolve_teacher('baseline')['source'])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.source)

    def probe(self, source, code):
        env={**os.environ,'PYTHONPATH':str(source),'GAIA_STATE_EVALUATION':'0','GAIA_CONSERVATION_OFF':'0'}
        result=subprocess.run([sys.executable,'-c',code],env=env,cwd=source,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def test_frozen_A_and_search_settings_openings_unchanged(self):
        self.assertEqual(ab.frozen_problems(ab.resolve_teacher('baseline')),[])
        for name in self.record['unchanged_search']:
            self.assertEqual((self.source/name).read_bytes(),(self.baseline/name).read_bytes())
        def functions(path):
            return {node.name:ast.dump(node) for node in ast.parse(path.read_text()).body
                    if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
        # Only the leaf evaluation differs in the complete planner module.
        before=functions(self.baseline/'four_factions/preparation.py')
        after=functions(self.source/'four_factions/preparation.py')
        self.assertEqual({k:v for k,v in before.items() if k!='leaf_value'},
                         {k:v for k,v in after.items() if k!='leaf_value'})
        self.assertEqual(set(self.record['modified']),set(PATCHES))

    def test_setup_candidates_scores_and_goal_order_match_A(self):
        code="""
import json
from gaia_rl import Environment
from four_factions.preparation import Policies,goals_for
from dataclasses import asdict
env=Environment('state-evaluation-ab-20260917-1580',2000)
s=json.loads(json.dumps(json.loads(env.snapshot_json()),sort_keys=True))
print(json.dumps({'candidates':s['candidates'],'scores':Policies(shared_factions=True).rank(env,s),
                  'goals':[asdict(g) for g in goals_for(s,shared_factions=True)]}))
"""
        self.assertEqual(self.probe(self.baseline,code),self.probe(self.source,code))

    def test_B_callbacks_and_OFF_gate_in_generated_worker(self):
        code="""
import os,json
from gaia_rl import Environment
from four_factions.preparation import Policies
from current_actions.conservation import FORBIDDEN,Conservation
from four_factions.teacher import NativeFactionTeacher
from state_evaluation_bridge import value,score
from state_evaluation import evaluate_state
env=Environment('state-evaluation-ab-20260917-1580',2000)
s=json.loads(env.snapshot_json())
while 'Setup' in s['state']['phase']:
 env.step(s['decision_id'],0);s=json.loads(env.snapshot_json())
os.environ['GAIA_STATE_EVALUATION']='1'
a=s['player'];assert NativeFactionTeacher().value(s['state'],a)==evaluate_state(s['state'],a).total_vp
scores=Policies(shared_factions=True).rank(env,s)
assert len(scores)==len(s['candidates'])
assert 'OreToCredit' in FORBIDDEN
os.environ['GAIA_CONSERVATION_OFF']='1'
assert 'OreToCredit' not in FORBIDDEN
assert Conservation().protect(env,s,scores)==scores
print(json.dumps({'scores':len(scores),'finite':all(__import__('math').isfinite(v) for v,_ in scores)}))
"""
        result=self.probe(self.source,code)
        self.assertTrue(result['finite'])


if __name__=='__main__':
    unittest.main()
