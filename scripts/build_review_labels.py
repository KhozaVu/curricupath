import csv, json, re, hashlib, io
from openpyxl import load_workbook
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
RAW=BASE/'data'/'raw'
OUT=BASE/'data'/'rules'
PL=str(RAW/'Student_Curricular_Planner_2026.xlsx')
CR=str(RAW/'Cross_Curricular_Registration_-_Requirement_and_Clashes.xlsx')
PK=str(RAW/'review_pack')+'/'
sha=lambda p:hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]
norm=lambda s: re.sub(r'[A-Z]$','',s.strip()) if re.fullmatch(r'[A-Z]{4}\d{4}[A-Z]?',s.strip()) else s.strip()
def codes(cell):
    return sorted({norm(x) for x in re.findall(r'[A-Z]{4}\s?\d{4}[A-Z]?',str(cell or '').replace(' ',''))})

# ---- 1. Planner grids (colour-coded) -> clash / prereq / coreq pairs
wb=load_workbook(PL)
KIND={'FF92D050':'prerequisite','FFFFFF00':'corequisite','FF00B0F0':'timetable_clash'}
grid=[]
for sheet,label in [('EE YOS 2','EE YoS2 repeat -> YoS3 target'),('Elec YoS 3','EE YoS3 repeat -> YoS4 target'),('Info YoS 3','IE YoS3 repeat -> YoS4 target')]:
    ws=wb[sheet]
    hr=next(r for r in range(1,10) if any(str(c.value).startswith(('ELEN3000','ELEN4000','ELEN4006')) for c in ws[r] if c.value))
    heads={c.column:str(c.value).split()[0] for c in ws[hr] if c.value and c.column>1}
    for r in range(hr+1,hr+16):
        a=ws.cell(r,1).value
        if not a or str(a).startswith('*'): continue
        for col,h in heads.items():
            c=ws.cell(r,col); f=c.fill
            if f.fill_type and f.fgColor.type=='rgb' and f.fgColor.rgb in KIND:
                grid.append(dict(sheet=sheet,direction=label,repeating=norm(str(a).split()[0]),target=norm(h),kind=KIND[f.fgColor.rgb],detail=(c.value or '').strip()))
# ---- 2. Cross-curricular tables -> prereq/coreq text per course
wc=load_workbook(CR)
tbl={}
for sheet in ['EE YOS 2','EE YOS 3','IE YOS 3']:
    ws=wc[sheet]
    for row in ws.iter_rows(values_only=True):
        if row[0] and re.match(r'[A-Z]{4}\d{4}',str(row[0])) and len(row)>4:
            tbl[(sheet,norm(str(row[0]).split()[0].split('/')[0]))]=dict(prereq=codes(row[3]),coreq=codes(row[4]),clashes=str(row[5] or ''))
# ---- 3. Handbook rules from pack
rules=list(csv.DictReader(open(PK+'curriculum_rules.csv',encoding='utf-8-sig')))
def ev(cond,have):
    if isinstance(cond,str): return cond in have
    if 'all_of' in cond: return all(ev(x,have) for x in cond['all_of'])
    if 'any_of' in cond: return any(ev(x,have) for x in cond['any_of'])
    raise ValueError(cond)
def flat(cond):
    if isinstance(cond,str): return {cond}
    out=set()
    for k in ('all_of','any_of'):
        for x in cond.get(k,[]): out|=flat(x)
    return out
def missing(cond,have):
    if isinstance(cond,str): return [] if cond in have else [cond]
    if 'all_of' in cond: return [m for x in cond['all_of'] for m in missing(x,have)]
    if 'any_of' in cond:
        return [] if ev(cond,have) else ['(' + ' or '.join(sorted(flat(cond))) + ')']
pre={};co={}
for r in rules:
    if r['rule_type'] in('prerequisite','corequisite') and 'all_courses_in_programme_year' not in r['condition_json']:
        d=pre if r['rule_type']=='prerequisite' else co
        d.setdefault(r['target_course_code'],[]).append(r)
def rules_for(d,t,prog):
    return [r for r in d.get(t,[]) if r['scope'] in('ALL_EFA03_EFA04',prog)]


LEG={'ELEN2004':'ELEN2020','ELEN2001':'ELEN2016','ELEN2006':'ELEN2021','MATH1048':'MATH1042','MATH1049':'MATH1043'}
DROP={'MATH1014','ELEN1000','ELEN1005'}   # legacy codes, reviewer: code changes do not change decisions
def nz(codes_):
    return {LEG.get(x,x) for x in codes_ if x not in DROP}
def sheet_for(t,prog):
    if t[4]=='2' or t.startswith(('COMS2','MATH2','PHYS2')): return 'EE YOS 2'
    return 'EE YOS 3' if prog=='EFA03' else 'IE YOS 3'
def grid_req(t,prog):
    v=tbl.get((sheet_for(t,prog),t[:-1]))
    return None if not v else (nz(v['prereq']),nz(v['coreq']),sheet_for(t,prog))
def hb_req(t,prog):
    hp=set();hc=set()
    for r in rules_for(pre,t,prog): hp|=nz({norm(x) for x in flat(json.loads(r['condition_json']))})
    for r in rules_for(co,t,prog):  hc|=nz({norm(x) for x in flat(json.loads(r['condition_json']))})
    return hp,hc
# substantive differences (after legacy-code normalisation); handbook any_of alternatives flattened
xcheck=[]
for (sheet,t) in sorted(tbl):
    code=t+'A'
    for prog in ('EFA03','EFA04'):
        if sheet_for(code,prog)!=sheet: continue
        if not (pre.get(code) or co.get(code)): continue
        gp,gc=grid_req(code,prog)[:2]; hp,hc=hb_req(code,prog)
        d=dict(course=code,programme=prog,sheet=sheet,grid_prereq=sorted(gp),handbook_prereq=sorted(hp),grid_coreq=sorted(gc),handbook_coreq=sorted(hc),
               prereq_diff={'grid_only':sorted(gp-hp),'handbook_only':sorted(hp-gp)},coreq_diff={'grid_only':sorted(gc-hc),'handbook_only':sorted(hc-gc)})
        d['differs']=bool(gp^hp or gc^hc)
        xcheck.append(d)
cases=list(csv.DictReader(open(PK+'eligibility_cases_pilot_blinded.csv',encoding='utf-8-sig')))
mods=list(csv.DictReader(open(PK+'curriculum_modules.csv',encoding='utf-8-sig')))
member={(m['programme_code'],m['course_code']) for m in mods}
G='EIE_REG_GRID_2026'
clash_rules=list(csv.DictReader(open(OUT/'grid_clash_rules.csv',encoding='utf-8-sig')))
def canonical(c):
    base=norm(str(c).upper())
    return LEG.get(base,base)+'A' if base and base not in DROP else ''
def case_clashes(target,programme,repeating):
    target=canonical(target); repeating={canonical(x) for x in repeating}
    return [r for r in clash_rules if r['scope']==programme and r['target_course_code']==target and r['repeating_course'] in repeating]
def decide(t,prog,done,cur,plan,req):
    """req=(prereq set, coreq set). prereq must be completed; coreq may be completed/current/planned."""
    P,C=req; bad=[];planned=[]
    mp=sorted(x for x in P if not any(d.startswith(x) for d in done))
    for x in C:
        if any(d.startswith(x) for d in done|cur): continue
        if any(d.startswith(x) for d in plan): planned.append(x)
        else: bad.append(x)
    return mp,sorted(bad),sorted(planned)
def cover(x,s): return any(d.startswith(x) for d in s)
out=[]
clash_exercised=0
for c in cases:
    p=json.loads(c['student_profile_json']); t=c['target_course_code']; prog=p['programme_code']
    done=set(p['completed_modules']); cur=set(p['current_modules']); plan=set(p['planned_modules'])
    # treat equivalent maths codes as satisfying
    for a,b in (('MATH1048A','MATH1042A'),('MATH1049A','MATH1043A')):
        if a in done: done.add(b)
    reasons=[];basis=[];flag=[]
    if p.get('manual_review_reasons'):
        label='manual_review_required'
        reasons=[f"{p['manual_review_reasons'][0]} The approved evidence cannot settle the case; academic review is required."]
        basis.append('rubric step 6'); flag.append('academic discretion: reviewer to confirm')
    elif (prog,t) not in member:
        label='ineligible'; reasons=[f'{t} is not in the {prog} curriculum (EBE_2026).']
    else:
        clar=c['clarification_permitted']=='true'
        if clar: basis.append('scripted_reply used: student confirms all current/planned modules are listed')
        g=grid_req(t,prog); hp,hc=hb_req(t,prog)
        gm,gb,gpl=decide(t,prog,done,cur,plan,(g[0],g[1]))
        hm,hb_,hpl=decide(t,prog,done,cur,plan,(hp,hc))
        label='ineligible' if (gm or gb) else 'eligible'
        hlabel='ineligible' if (any(missing(json.loads(r['condition_json']),done) for r in rules_for(pre,t,prog)) or any(missing(json.loads(r['condition_json']),done|cur|plan) for r in rules_for(co,t,prog))) else 'eligible'
        pg=next((r['handbook_page'] for r in rules if r['target_course_code']==t),'')
        for x in gm:
            reasons.append(f"{x}A is required before {t} and is not listed as completed ({G}, sheet '{g[2]}'" + (f"; EBE_2026 p.{pg}" if x in hp else "; NOT in EBE_2026 p."+pg) + ").")
        for x in gb:
            reasons.append(f"{x}A must be taken with {t} and is not completed, current or planned ({G}, sheet '{g[2]}'" + ("; EBE_2026 p."+pg if any(not missing(json.loads(r['condition_json']),done|cur|plan) for r in rules_for(co,t,prog))==False else "; EBE_2026 p."+pg+" would accept an alternative corequisite already planned - see needs_reviewer_confirmation") + ")." + (" The student confirmed the list of modules is complete." if clar else ""))
        if label=='eligible':
            reasons.append(f"Programme membership and all recorded prerequisite conditions are satisfied ({G}; EBE_2026).")
            for x in gpl:
                reasons.append(f"{x}A is a corequisite of {t} and is planned concurrently ({G}, sheet '{g[2]}'; EBE_2026 p.{pg}); rubric step 3 accepts planned corequisites where the rule allows.")
            if gpl: flag.append('Rule 1.9: label depends on planned corequisite counting; reviewer to confirm')
        clashes=case_clashes(t,prog,p.get('repeating_modules',[]))
        if clashes:
            clash_exercised+=1; label='ineligible'
            for clash in clashes:
                kind={'LEC':'lecture timetable clash','LAB':'laboratory timetable clash','TUT':'tutorial timetable clash','UNSPECIFIED':'timetable clash'}[clash['clash_type']]
                reasons.append(f"{clash['rule_id']}: {t} has a {kind} with {clash['repeating_course']}, which the student is repeating, so it cannot be taken ({clash['source_ids']}).")
        if label!=hlabel:
            flag.append(f'SOURCE CONFLICT: grid gives {label}, EBE_2026 rules give {hlabel}')
            basis.append(f'grid and handbook disagree; grid used as primary reference')
        elif g and (g[0]^hp or g[1]^hc):
            basis.append('grid/handbook requirement lists differ but the label is the same')
        else: basis.append('grid and handbook agree')
        basis.append('clash gate not applicable: profile lists no repeated course')
    out.append(dict(case_id=c['case_id'],label=label,reasons=reasons,basis='; '.join(basis),flag='; '.join(dict.fromkeys(flag))))
with open(OUT/'grid_rules.json','w',encoding='utf-8',newline='\n') as grid_file:
 json.dump(dict(provenance=dict(sources={'Student_Curricular_Planner_2026.xlsx':sha(PL),'Cross_Curricular_Registration_-_Requirement_and_Clashes.xlsx':sha(CR),'curriculum_rules.csv':sha(PK+'curriculum_rules.csv')},
  supplied_by='School of EIE Admin Manager (M. Ismail), email 30 Sep 2026',
  colour_key={'FF92D050 green':'prerequisite missing','FFFFFF00 yellow':'corequisite missing','FF00B0F0 blue':'timetable clash'},
  clash_rule='Reviewer statement, pending written confirmation: a timetable clash means the course cannot be taken.',
  legacy_code_map=LEG,ignored_legacy_codes=sorted(DROP),
  how_to_read='repeating = course the student is repeating; target = higher-year course; kind = what the repeat blocks.'),
  planner_grid_pairs=grid, requirements_from_cross_curricular_tables={f'{k[0]}|{k[1]}A':v for k,v in tbl.items()}),grid_file,indent=1)
with open(OUT/'grid_vs_handbook_crosscheck.json','w',encoding='utf-8',newline='\n') as crosscheck_file:
 json.dump(xcheck,crosscheck_file,indent=1)
fields=list(cases[0].keys())+['proposed_basis','needs_reviewer_confirmation']
with open(str(OUT)+'/eligibility_cases_pilot_proposed.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for c,o in zip(cases,out):
        c=dict(c); c['reference_label']=o['label']; c['expected_material_reasons_json']=json.dumps(o['reasons'],ensure_ascii=False)
        c['proposed_basis']=o['basis']; c['needs_reviewer_confirmation']=o['flag']; w.writerow(c)
from collections import Counter
print(Counter(o['label'] for o in out)); print(len(grid),'grid pairs',Counter(g['kind'] for g in grid))
print(f'clash gate exercised on {clash_exercised} of {len(cases)} cases')
for o in out: print(o['case_id'],o['label'],'|',o['flag'] or '-','\n    ',' / '.join(o['reasons'])[:230])
print('--- substantive grid vs handbook differences')
for x in xcheck:
    if x['differs']: print(x['course'],x['programme'],'prereq',x['prereq_diff'],'coreq',x['coreq_diff'])
