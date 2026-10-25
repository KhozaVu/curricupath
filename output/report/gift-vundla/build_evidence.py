"""Read frozen observations and create report assets without changing experiments."""
from pathlib import Path
import csv
import hashlib
import json
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT))
from app.evaluation.scoring import arm_metrics, encode, decision_from_record

BASE = ROOT / 'experiments/evaluation/test_set_v1'
def read_csv(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
cases = read_csv(BASE / 'curricupath_test_set_v1.csv')
assert digest(BASE / 'curricupath_test_set_v1.csv') == json.loads((BASE/'freeze.json').read_text())['sha256']
subset = set(json.loads((BASE/'subset_40.json').read_text())['case_ids'])
sub = [c for c in cases if c['case_id'] in subset]
data = {'reference_labels': dict(Counter(c['reference_label'] for c in cases)), 'subset_labels': dict(Counter(c['reference_label'] for c in sub)), 'metrics':{}, 'sufficiency':{}, 'hashes':{}, 'historical_config_note':'This reads archived observations; it does not rerun the changed live application.'}
for folder in ['results','results_post_grid_final','results_school_grid_llm/scored']:
    data['hashes'][f'{folder}/metrics_summary.json'] = digest(BASE/folder/'metrics_summary.json')

for level in ['low','medium','high']:
    data['metrics'][level] = {}
    for arm in ['curricupath','curricupath_no_clarification','rules_only','handbook_rag','structured_rules_llm']:
        path=BASE/f'results_school_grid_llm/raw/{arm}__{level}.jsonl'
        records=[json.loads(s) for s in path.read_text(encoding='utf8').splitlines() if s.strip()]
        by={r['case_id']:r for r in records}
        assert len(by)==len(records)
        assert subset <= set(by)
        m=arm_metrics(encode([c['reference_label'] for c in sub]),encode([decision_from_record(by[c['case_id']]) for c in sub]))
        stored=json.loads((BASE/'results_school_grid_llm/scored/metrics_summary.json').read_text())['results']['subset40'][level][arm]
        for key in ['n_cases','macro_f1','accuracy','confusion_matrix','safety']:
            assert m[key] == stored[key], (arm,level,key)
        m['macro_f1_ci95']=stored['macro_f1_ci95']
        data['metrics'][level][arm]=m
        data['hashes'][str(path.relative_to(ROOT))]=digest(path)

for arm in ['curricupath','rules_only','handbook_rag']:
    data['sufficiency'][arm]={}
    for phase in ['before','after']:
        folder='results' if phase=='before' else ('results_school_grid_llm' if arm=='handbook_rag' else 'results_post_grid_final')
        counts={key:{'correct':0,'n':0} for key in ['sufficient','insufficient']}
        for level in ['low','medium','high']:
            path=BASE/f'{folder}/raw/{arm}__{level}.jsonl'
            records={r['case_id']:r for r in map(json.loads,path.read_text(encoding='utf8').splitlines())}
            for c in sub:
                k='sufficient' if c['answerable_from_handbook']=='true' else 'insufficient'
                counts[k]['n']+=1
                counts[k]['correct']+=decision_from_record(records[c['case_id']])==c['reference_label']
        data['sufficiency'][arm][phase]=counts

clar=ROOT/'experiments/evaluation/clarification_set_v3'
assert digest(clar/'clarification_set_v3.csv')==json.loads((clar/'freeze.json').read_text())['sha256']
data['clarification']=json.loads((clar/'results/summary.json').read_text())
data['hashes']['clarification_summary']=digest(clar/'results/summary.json')
(OUT/'report_evidence.json').write_text(json.dumps(data,indent=2),encoding='utf8')

plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],'font.size':9,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(figsize=(3.23,2.35))
arms=['no_clarification','assume_absent','clarify','oracle']
labels=['No clarification','Assume absent','Clarify then decide','Oracle facts supplied']
rs=[next(r for r in data['clarification']['arms'] if r['population']=='ask' and r['arm']==arm) for arm in arms]
left=[0]*4
for key,label,color,hatch in [('correct','Correct','0.22',''),('wrong_decision','Wrong','0.62','///'),('unresolved','Unresolved','0.94','..')]:
    vals=[r[key] for r in rs]
    ax.barh(range(4),vals,left=left,label=label,color=color,hatch=hatch,edgecolor='black',linewidth=.5,height=.56)
    for i,(v,x) in enumerate(zip(vals,left)):
        if v:ax.text(x+v/2,i,str(v),ha='center',va='center',color='white' if key=='correct' else 'black',fontsize=9)
    left=[x+v for x,v in zip(left,vals)]
ax.set_yticks(range(4),labels);ax.invert_yaxis();ax.set_xlim(0,33);ax.set_xticks([0,11,22,33]);ax.set_xlabel('Cases after the permitted interaction');ax.legend(loc='lower left',bbox_to_anchor=(-.55,1.01),ncol=3,frameon=False,fontsize=8,columnspacing=.8,handlelength=1.1)
fig.tight_layout(pad=.3);fig.savefig(OUT/'clarification.pdf',bbox_inches='tight');plt.close(fig)

fig,ax=plt.subplots(figsize=(3.23,2.75));ax.set(xlim=(0,10),ylim=(0,10));ax.axis('off')
def box(x,y,w,h,label,shade='white'):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.05,rounding_size=0.08',facecolor=shade,edgecolor='black',linewidth=.7))
    ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=8.5)
def arrow(a,b):
    ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',lw=.7))
box(.3,8.6,9.4,1,'Student question and declared module record')
box(.3,6.8,9.4,1.15,'Controlled parsing and module resolution\nOptional Gemini API interpretation')
box(.3,4.8,6.3,1.25,'Deterministic eligibility checks\nSource, programme and rule conditions','0.94')
box(7.2,4.5,2.5,1.8,'Wits\nevidence\nand rules')
box(.3,2.5,9.4,1.3,'Known facts: eligible or ineligible\nMissing student fact: ask and recheck\nInstitutional uncertainty: manual review')
box(.3,.55,9.4,1,'Response with rule trace and source links')
for a,b in [((5,8.6),(5,7.95)),((3.4,6.8),(3.4,6.05)),((7.2,5.4),(6.6,5.4)),((3.4,4.8),(3.4,3.8)),((5,2.5),(5,1.55))]:arrow(a,b)
ax.annotate('',xy=(.3,7.35),xytext=(.3,3.1),arrowprops=dict(arrowstyle='->',connectionstyle='arc3,rad=-0.25',lw=.7))
fig.tight_layout(pad=.1);fig.savefig(OUT/'decision_flow.pdf',bbox_inches='tight');plt.close(fig)
print('Reference labels',data['reference_labels'],'Subset',data['subset_labels'])
print('Evidence sufficiency',json.dumps(data['sufficiency']))
print('Verified report metrics against raw observations and frozen case hashes.')

