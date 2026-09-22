"""Four-way (e)/(f) invariant gate. No games or automatic tuning."""
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
    e: bool = False

    def evaluate_state(self, state, actor, **kwargs):
        return variant.evaluate_state(state, actor, token_shortfall=True, remaining_income=True,
            distributed_research=True, round_resource_prices=self.f, expansion_rescale=self.e, **kwargs)


MODELS={'B⁗':Configured(), 'B⁗+e':Configured(e=True),
        'B⁗+f':Configured(f=True), 'B⁗+e+f':Configured(e=True,f=True)}


def run(output, *, round_five_invariants=False):
    output.mkdir(parents=True,exist_ok=True)
    results={name:[] for name in MODELS}
    token_cases=[]
    cases=list(invariants())
    if round_five_invariants:
        from validate_bprime import fixtures, CONVERSIONS
        from validate_bc import cap_state
        for scenario, state, actor in fixtures():
            if state['round']==3:
                state=copy.deepcopy(state)
                state['round']=5
                cases.append(('existing',scenario,state,actor,CONVERSIONS))
        state,actor=cap_state(5,4,stress=True)
        cases.append(('cap-boundary','cap-boundary',state,actor,CONVERSIONS[:-1]))
    for suite, scenario, before, actor, conversions in cases:
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
        values={}
        for name,model in MODELS.items():
            row=compare(before,after,actor,'OreToPower',f'tokens:{token["active_tokens"]}',token['conservation'],model=model)
            row['suite']='token-shortfall'
            results[name].append(row)
            values[name]=row
        token_cases.append({'round':before['round'],'tokens':token['active_tokens'],
                            'conservation':token['conservation'],'values':values})
    # R5 is a directional probe, not an expansion of the requested 1/3/6R invariant corpus.
    from validate_bc import cap_state
    for count in (3,7):
        before,actor=cap_state(5,count,stress=True)
        after=successor(before,actor,{'type':'FreeAction','kind':'OreToPower','count':1})
        for conserve in (True,False):
            values={name:compare(before,after,actor,'OreToPower',f'tokens:{count}',conserve,model=model)
                    for name,model in MODELS.items()}
            token_cases.append({'round':5,'tokens':count,'conservation':conserve,'values':values})
            if round_five_invariants:
                for name,row in values.items():
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
    record={'counts':counts,'invariants':results,'token_cases':token_cases,
            'rounds_validated':[1,3,5,6] if round_five_invariants else [1,3,6],
            'corrected_steps':steps,'corrected_breadth':breadth,
            'games_run':0,'e_status':'approved direct/QIC/public terra routes; existing Transdim opportunity retained',
            'prices':{str(r):{'resources':variant.stock_prices(r),'bowls':variant.bowl_prices(r)} for r in range(1,7)},
            'scope':'(e) native paid mine previews with priced liquidity deficits; (f) held stocks and (b) penalty share the round multiplier. Future income unchanged.',
            'downstream_status':'Not run if invariants fail: requested failure-case-only report gate.'}
    write_json(output/'comparison.json',record)
    lines=['| 실패 | 구성 | R | 상태·보존 | 전→후 VP | ΔVP | breakdown |','|---|---|---:|---|---|---:|---|']
    for name,rows in results.items():
        for row in rows:
            if row['passed']:continue
            parts='; '.join(f'{key} {part["delta"]:+.6f}' for key,part in row['changed_breakdown'].items())
            lines.append(f'| {row["action"]} | {name} | {row["round"]} | {row["scenario"]} {row["conservation"]} | '
                         f'{row["before"]:.6f}→{row["after"]:.6f} | {row["delta"]:+.6f} | {parts} |')
    (output/'failures.md').write_text('\n'.join(lines)+'\n')
    summary={'counts':counts,'token_sign_failures':sum(value['delta']>=-1e-9
                 for case in token_cases for value in case['values'].values()),
             'corrected_step_passes':sum(row['passed'] for row in steps),
             'corrected_breadth_passes':sum(row['passed'] for row in breadth),'games_run':0}
    write_json(output/'summary.json',summary)
    print(summary)
    return any(c.get('fail',0) for c in counts.values())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(int(run(parser.parse_args().output)))
