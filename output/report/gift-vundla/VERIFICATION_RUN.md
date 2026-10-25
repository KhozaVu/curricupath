# Focused verification - 23 October 2026

Run from the repository root:

```powershell
python -m pytest tests/test_eligibility.py tests/test_clarification.py tests/test_clarification_fixes.py tests/test_response_invariants.py tests/test_postgres_schema.py tests/test_postgres_repository.py -q -ra --junitxml=output/report/gift-vundla/verification_run_2026-10-23.xml
```

55 passed,7 skipped,0 failed;11.91 seconds. Seven live PostgreSQL repository comparisons skipped because imported catalogue was unavailable. Two warnings: httpx/Starlette deprecation and unavailable hosted demo configuration. No new hosted-model benchmark calls. test_clarification.py collected no tests; five modules contributed62 collected checks. Existing deliberately invalid fixtures exercise guards, not new live defect discovery.

Recount historical matched40 metrics with `python output/report/gift-vundla/recount_shared_metrics.py`. This reads frozen raw outputs without calling providers.
