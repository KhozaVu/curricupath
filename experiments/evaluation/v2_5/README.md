# CurricuPath Evaluation v2.5

This directory implements the frozen protocol in
`docs/revised_evaluation_plan_2026-09-18.md`.

Official generation is intentionally blocked until:

1. `personnel.json` contains named reviewers, judges, owners, and committed hours;
2. independent labels are approved in `eligibility_cases.csv`;
3. `rag_retrieval_config.json` contains a selected `top_k` from the separate
   development set;
4. `manifest.json` records a clean Git commit and final file hashes; and
5. the raw evaluation corpus has been extracted, embedded, and checked.

Use `docs/evaluation_reviewer_request.md` to secure and record the required independent
reviewers, grounding judge, and committed hours without inventing assignments.

Preparation commands:

```powershell
py scripts/prepare_evaluation_v2_5.py
py scripts/prepare_evaluation_corpus.py
py scripts/embed_catalogue.py
py scripts/select_evaluation_top_k.py
py scripts/check_evaluation_readiness.py
```

Only after readiness passes:

```powershell
py scripts/run_evaluation.py --arm handbook_rag
py scripts/run_evaluation.py --arm structured_rules_llm
py scripts/run_evaluation.py --arm rules_only
py scripts/run_evaluation.py --arm curricupath
py scripts/run_evaluation.py --arm curricupath_no_clarification
py scripts/run_grounding_evaluation.py --arm handbook_rag
py scripts/run_grounding_evaluation.py --arm structured_rules_llm
py scripts/run_grounding_evaluation.py --arm curricupath
```

The runner writes three immutable observations per case. Pre-registered run 1 is the
primary result; runs 2 and 3 measure stability.
