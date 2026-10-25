"""Recount existing raw outputs on the common frozen subset; no model calls."""
from pathlib import Path
import sys, csv, json, statistics, hashlib

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT))
from app.evaluation.scoring import decision_from_record

DATA = ROOT / 'experiments/evaluation/test_set_v1'
ids = json.loads((DATA/'subset_40.json').read_text())['case_ids']
refs = {r['case_id']:r['reference_label'] for r in csv.DictReader((DATA/'curricupath_test_set_v1.csv').open(encoding='utf-8-sig'))}
scores = []
for arm in ['curricupath','curricupath_no_clarification','rules_only','structured_rules_llm','handbook_rag']:
    stage = 'results' if arm in ['structured_rules_llm','handbook_rag'] else 'results_post_grid_final'
    values, hashes, unsafe = [], {}, 0
    for level in ['low','medium','high']:
        path = DATA/stage/'raw'/f'{arm}__{level}.jsonl'
        hashes[level] = hashlib.sha256(path.read_bytes()).hexdigest()
        records = {r['case_id']:decision_from_record(r) for r in map(json.loads,path.read_text().splitlines())}
        per_class = []
        for label in ['eligible','ineligible','manual_review_required']:
            tp = sum(refs[i]==label and records[i]==label for i in ids)
            fp = sum(refs[i]!=label and records[i]==label for i in ids)
            fn = sum(refs[i]==label and records[i]!=label for i in ids)
            per_class.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
        values.append(statistics.mean(per_class))
        unsafe += sum(refs[i]!='eligible' and records[i]=='eligible' for i in ids)
    scores.append(dict(arm=arm,n_per_wording=40,mean_macro_f1=statistics.mean(values),macro_f1_by_wording=values,unsafe_numerator=unsafe,unsafe_denominator=78,raw_sha256=hashes,stage=stage))
(OUT/'matched_subset_audit.json').write_text(json.dumps(scores,indent=2))
for row in scores:
    print(row['arm'],f"{row['mean_macro_f1']:.3f}",f"{row['unsafe_numerator']}/{row['unsafe_denominator']}")
