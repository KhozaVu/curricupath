"""Recount archived failures and produce readable monochrome report assets."""
from pathlib import Path
from collections import Counter
import csv, json, hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent
ROOT=next(p for p in OUT.parents if (p/'app/evaluation/scoring.py').exists())
BASE=ROOT/'experiments/evaluation/test_set_v1'
cases={r['case_id']:r for r in csv.DictReader((BASE/'curricupath_test_set_v1.csv').open(encoding='utf-8-sig'))}
failure_data={}
for level in ['low','medium','high']:
    failures=[]
    path=BASE/f'results_post_grid_final/raw/curricupath__{level}.jsonl'
    for line in path.read_text(encoding='utf8').splitlines():
        r=json.loads(line);p=r.get('parsed_output') or {}
        if r['status']=='valid' and p.get('decision') in ['eligible','ineligible','manual_review_required']:
            continue
        c=cases[r['case_id']]
        if p.get('status')=='clarification_unresolved':
            cause='status_reply_unresolved'
            assert p.get('clarification_exhausted') is True
            assert p.get('course_code')==c['target_course_code']
            assert c['scripted_reply']=='I have listed every module I am currently taking or planning.'
        else:
            cause='target_unresolved'
            assert p.get('status')=='clarification_required'
            assert not p.get('course_code')
            assert 'module code or full module name' in p.get('answer','')
        assert c['reference_label']=='ineligible'
        failures.append({'case_id':r['case_id'],'target':c['target_course_code'],'reference':c['reference_label'],'cause':cause,'reply':c['scripted_reply'],'answer':p.get('answer'),'unresolved_predicates':p.get('unresolved_predicates',[])})
    failure_data[level]={'counts':dict(Counter(r['cause'] for r in failures)),'cases':failures,'raw_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
assert [len(failure_data[l]['cases']) for l in ['low','medium','high']]==[8,12,11]
summary={}
for phase,folder in [('before','results'),('after','results_post_grid_final')]:
    d=json.loads((BASE/folder/'metrics_summary.json').read_text())['results']['all']
    summary[phase]={}
    for level in ['low','medium','high']:
        m=d[level]['curricupath'];cm=m['confusion_matrix']['counts']
        summary[phase][level]={'correct':sum(cm[i][i] for i in range(3)),'n':m['n_cases'],'macro_f1':m['macro_f1'],'unsafe':m['safety']['unsafe_false_positive_rate'],'invalid':m['safety']['invalid_output_rate']}
result={'failures':failure_data,'pre_post_grid':summary,'failure_interpretation':'All eight common failures were exhausted status-reply clarification, not missing target resolution. Rules-only receives module_history_confirmed=True from the benchmark adapter when the scripted reply contains every module, whereas the conversational payload relies on the text reply. No historical observations were changed.'}
(OUT/'failure_analysis.json').write_text(json.dumps(result,indent=2),encoding='utf8')

d=json.loads((ROOT/'experiments/evaluation/clarification_set_v3/results/summary.json').read_text())
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],'font.size':9,'pdf.fonttype':42,'hatch.linewidth':.45,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(figsize=(3.23,2.35))
arms=['no_clarification','assume_absent','clarify','oracle']
labels=['No clarification','Assume absent','Clarify then decide','Oracle facts supplied']
rs=[next(r for r in d['arms'] if r['population']=='ask' and r['arm']==arm) for arm in arms]
left=[0]*4
for key,label,color,hatch in [('correct','Correct','0.22',''),('wrong_decision','Wrong','0.70','/'),('unresolved','Unresolved','0.96','.')]:
    vals=[r[key] for r in rs]
    ax.barh(range(4),vals,left=left,label=label,color=color,hatch=hatch,edgecolor='black',linewidth=.5,height=.56)
    for i,(v,x) in enumerate(zip(vals,left)):
        if v:
            ax.text(x+v/2,i,str(v),ha='center',va='center',color='white' if key=='correct' else 'black',fontsize=9,bbox=dict(facecolor=color,edgecolor='none',pad=.8))
    left=[x+v for x,v in zip(left,vals)]
ax.set_yticks(range(4),labels);ax.invert_yaxis();ax.set_xlim(0,33);ax.set_xticks([0,11,22,33]);ax.set_xlabel('Cases after the permitted interaction');ax.legend(loc='lower left',bbox_to_anchor=(-.55,1.01),ncol=3,frameon=False,fontsize=8,columnspacing=.8,handlelength=1.1)
fig.tight_layout(pad=.3);fig.savefig(OUT/'clarification.pdf',bbox_inches='tight');plt.close(fig)
print(json.dumps({l:failure_data[l]['counts'] for l in failure_data}))
print('Pre/post and failure records written; historical evidence unchanged.')
