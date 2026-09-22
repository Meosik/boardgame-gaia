"""Native paid e/e-prime building and track comparisons after invariant gate."""
import argparse
import copy
import json
from pathlib import Path

from validate_beprime import MODELS
from validate_bc import representative, structure, successor, write_json
from validate_bprime import compare, opportunity_fixture
import state_evaluation_bef as evaluator


def evaluate(before: dict, actor: int, action: dict, label: str) -> dict:
    after = successor(before, actor, action)
    values = {}
    for name, model in MODELS.items():
        row = compare(before, after, actor, label, 'e-prime diagnostic', True, model=model)
        assert abs(row['delta']-sum(change['delta'] for change in row['changed_breakdown'].values())) < 1e-8
        values[name] = {key: row[key] for key in ('before', 'after', 'delta', 'changed_breakdown',
                                                 'before_breakdown', 'after_breakdown')}
    return {'label':label, 'round':before['round'], 'action':action,
            'before_state':before, 'after_state':after, 'values':values}


def buildings() -> list[dict]:
    rows=[]
    for rnd in (1,3,5):
        state,actor=representative(rnd)
        home=copy.deepcopy(state)
        home['board']['hexes']['1,0']['planet']['planet_type']='Desert'
        rows.append(evaluate(home,actor,{'type':'Build','coord':'1,0'},'모행성 광산'))
        rows.append(evaluate(state,actor,{'type':'PowerAction','id':6,'coord':'1,0'},'공용 1테라+광산'))
        lab=copy.deepcopy(state)
        structure(lab,actor,'0,0','TradingStation')
        rows.append(evaluate(lab,actor,{'type':'Upgrade','coord':'0,0','to':'ResearchLab',
            'tech_tile_choice':{'kind':'Standard','tile':3,'advance_track':'Terraforming'}},
            '교역소→연구소+std-03'))
    return rows


def budget(state: dict, actor: int) -> None:
    player=state['players'][actor]
    player['booster']=None
    # Research is native-paid (4K); other holdings match representative().
    player['resources'].update(ore=6,credits=10,knowledge=4,qic=1)
    player['resources']['power'].update(bowl1=4,bowl2=4,bowl3=8,brainstone=None,gaia_forming=0)
    state['board']['spaceship_tiles']={}


def navigation_state(rnd: int, planets: int) -> tuple[dict,int]:
    state,actor=opportunity_fixture(target='Desert',distance=4,count=min(3,planets))
    state['round']=rnd
    budget(state,actor)
    if planets==5:
        for coord in ('3,1','1,3'):
            state['board']['hexes'][coord]={
                'coord':coord,
                'planet':{'planet_type':'Desert','owner':None,'is_gaia_formed':False},
                'space_tile_kind':None,'structures':[],'satellites':[]}
    return state,actor


def special_state(rnd: int, kind: str) -> tuple[dict,int]:
    target,count={'terraforming':('Terra',3),'gaia':('Transdim',1)}[kind]
    state,actor=opportunity_fixture(target=target,distance=1,count=count)
    state['round']=rnd
    budget(state,actor)
    return state,actor


def research() -> tuple[list[dict],list[dict],list[dict]]:
    nav,summary,reference=[],[],[]
    for rnd in (1,3):
        for count in (1,3,5):
            before,actor=navigation_state(rnd,count)
            nav_row=evaluate(before,actor,{'type':'ResearchAdvance','track':'Navigation'},
                             f'항해1→2 · 적합행성{count}개')
            economy=evaluate(before,actor,{'type':'ResearchAdvance','track':'Economy'},
                             '경제1→2 · 동일상태')
            nav.append(nav_row)
            player=before['players'][actor]
            after_player=nav_row['after_state']['players'][actor]
            initial=evaluator.base.base.planet_opportunities(before,player)
            after=evaluator.base.base.planet_opportunities(nav_row['after_state'],after_player)
            summary.append({'round':rnd,'planets':count,'navigation':nav_row,'economy':economy,
                'native_reachable_before':len(initial),'native_reachable_after':len(after),
                'navigation_minus_economy':{name:nav_row['values'][name]['delta']-
                    economy['values'][name]['delta'] for name in MODELS}})
        for kind,track in (('terraforming','Terraforming'),('gaia','GaiaProject')):
            before,actor=special_state(rnd,kind)
            row=evaluate(before,actor,{'type':'ResearchAdvance','track':track},
                         '테라1→2 · 3테라행성3개' if kind=='terraforming' else
                         '가이아0→1 · 트랜스디멘셔널 참고')
            reference.append(row)
    return nav,summary,reference


def run(output: Path, gate: Path) -> None:
    summary=json.loads(gate.read_text())
    if any(count.get('fail',0) for count in summary['counts'].values()) or summary['token_sign_failures']:
        raise ValueError('Invariant gate failed; follow-up diagnostics not run')
    output.mkdir(parents=True,exist_ok=True)
    build=buildings()
    nav,nav_summary,reference=research()
    sign_failures=[row for row in build if row['round'] in (1,3)
        and row['label'] in ('모행성 광산','공용 1테라+광산')
        and row['values']['B⁗+e′+f']['delta'] <= 0]
    record={'buildings':build,'navigation':nav,'navigation_summary':nav_summary,
            'reference':reference,'mine_sign_failures':sign_failures,
            'invariant_gate':str(gate),'games_run':0,
            'notes':['K4 for native paid research; O6 C10 QIC1 and power4/4/8 match the representative state.',
                     'Distance-4 home planets are beyond Nav1 even with the available one QIC; Nav2 brings them within QIC range.',
                     'Only the income horizon is shortened inside e-prime; current round/stock prices/round tile/public actions remain.',
                     'Transdim Gaia is reference-only without an expected sign.']}
    write_json(output/'downstream.json',record)
    names=list(MODELS)
    lines=['| 진단 ΔVP | R | '+' | '.join(names)+' |','|---|---:|'+'---:|'*len(names)]
    for title,rows in (('건설',build),('항해 1→2',nav),('참고',reference)):
        lines.append(f'| **{title}** | | | |')
        for row in rows:
            lines.append(f'| {row["label"]} | {row["round"]} | '+
                ' | '.join(f'{row["values"][name]["delta"]:+.6f}' for name in names)+' |')
    lines += ['', '| 경제 1→2 (동일 상태) | R | '+' | '.join(names)+' |',
              '|---|---:|'+'---:|'*len(names)]
    for row in nav_summary:
        lines.append(f'| 적합 행성 {row["planets"]}개 | {row["round"]} | '+
            ' | '.join(f'{row["economy"]["values"][name]["delta"]:+.6f}' for name in names)+' |')
    lines += ['', '| 항해−경제 ΔVP | R | '+' | '.join(names)+' |',
              '|---|---:|'+'---:|'*len(names)]
    for row in nav_summary:
        lines.append(f'| 적합 행성 {row["planets"]}개 | {row["round"]} | '+
            ' | '.join(f'{row["navigation_minus_economy"][name]:+.6f}' for name in names)+' |')
    (output/'downstream.md').write_text('\n'.join(lines)+'\n')
    print({'buildings':len(build),'navigation':len(nav),'reference':len(reference),
           'mine_sign_failures':len(sign_failures),'games_run':0})


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--gate',type=Path,required=True)
    args=parser.parse_args()
    run(args.output,args.gate)
