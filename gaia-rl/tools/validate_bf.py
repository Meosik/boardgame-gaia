"""Independent (f) invariant stage while (e) construction scope awaits approval."""
import argparse
from collections import Counter
import copy
from dataclasses import dataclass
from pathlib import Path

from validate_bc import invariants, compare, successor, write_json
from diagnose_research_bc import token_rows
from validate_bd import step_rows, concentration_rows
import state_evaluation_bef as variant


@dataclass(frozen=True)
class Configured:
    f: bool = False

    def evaluate_state(self, state, actor, **kwargs):
        return variant.evaluate_state(state, actor, token_shortfall=True, remaining_income=True,
            distributed_research=True, round_resource_prices=self.f, **kwargs)


MODELS={'B⁗':Configured(), 'B⁗+f':Configured(f=True)}


def run(output):
    output.mkdir(parents=True,exist_ok=True)
    results={name:[] for name in MODELS}
    for suite, scenario, before, actor, conversions in invariants():
        operations=[(f'add:{key}',None) for key in variant.base.base.PRICES]
        operations += [(kind,{'type':'FreeAction','kind':kind,'count':1}) for kind in conversions]
        for conserve in (True,False):
            for label,action in operations:
                if action is None:
                    after=copy.deepcopy(before)
                    after['players'][actor]['resources'][label[4:]]+=1
                else:
                    after=successor(before,actor,action)
                for name,model in MODELS.items():
                    row=compare(before,after,actor,label,scenario,conserve,model=model)
                    row['suite']=suite
                    results[name].append(row)
    for token in token_rows():
        before,after=token['before_state'],token['after_state']
        actor=next(p['player_id'] for p in before['players'] if p['faction']=='Xenos')
        for name,model in MODELS.items():
            row=compare(before,after,actor,'OreToPower',f'tokens:{token["active_tokens"]}',token['conservation'],model=model)
            row['suite']='token-shortfall'
            results[name].append(row)
    counts={name:dict(Counter(r['status'] for r in rows)) for name,rows in results.items()}
    steps=step_rows()
    concentration=concentration_rows()
    breadth=[]
    for r in (1,3):
        same=[row for row in concentration if row['round']==r]
        def research_delta(row):
            parts=row['values']['B⁗']['changed_breakdown']
            return sum(parts.get(key,{}).get('delta',0) for key in ('research_final_vp','research_progress'))
        reference=min(research_delta(row) for row in same if row['existing'])
        for row in same:
            if not row['existing']:
                breadth.append({'round':r,'track':row['track'],'fourth_research_delta':research_delta(row),
                                'existing_research_delta':reference,'passed':research_delta(row)<reference-1e-9})
    record={'counts':counts,'invariants':results,'corrected_steps':steps,'corrected_breadth':breadth,
            'games_run':0,'e_status':'pending construction scope / Transdim treatment answer',
            'prices':{str(r):{'resources':variant.stock_prices(r),'bowls':variant.bowl_prices(r)} for r in range(1,7)},
            'scope':'Only held resource stocks and active bowl prices scale. Future income and (b) unchanged.'}
    write_json(output/'comparison.json',record)
    lines=['| 실패 | 구성 | R | 상태·보존 | 전→후 VP | ΔVP | breakdown |','|---|---|---:|---|---|---:|---|']
    for name,rows in results.items():
        for row in rows:
            if row['passed']:continue
            parts='; '.join(f'{key} {part["delta"]:+.6f}' for key,part in row['changed_breakdown'].items())
            lines.append(f'| {row["action"]} | {name} | {row["round"]} | {row["scenario"]} {row["conservation"]} | '
                         f'{row["before"]:.6f}→{row["after"]:.6f} | {row["delta"]:+.6f} | {parts} |')
    (output/'failures.md').write_text('\n'.join(lines)+'\n')
    summary={'counts':counts,'corrected_step_passes':sum(row['passed'] for row in steps),
             'corrected_breadth_passes':sum(row['passed'] for row in breadth),'games_run':0}
    write_json(output/'summary.json',summary)
    print(summary)
    return any(c.get('fail',0) for c in counts.values())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(int(run(parser.parse_args().output)))
