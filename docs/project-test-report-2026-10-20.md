# Project verification ? 20 October 2026

Tested the Downloads application at C:/Users/giftv/Downloads/Cirricupath/curricupath.

- Complete Python tests directory: 2,462 passed, 9 skipped, 24 warnings (21.56 seconds). Live Gemini calls and the reasoning reviewer were disabled in the test process; paid/live model behavior was not tested.
- Frontend JavaScript tests in frontend and frontend_v2: 9 passed, no failures.
- Version 2 production build: passed. Vite reports large graphics chunks; this is a bundle-size warning, not a compilation failure.
- Dataset validation: passed with zero errors and zero warnings. Includes codes, sources, JSON requirements, prerequisite references, selection groups, CBO records, missing-CBO register and duplicate checks.
- Running server: /health returns status ok; /v2 returns HTTP 200.

Six initial failures were stale expectations. Replaced four retired public-ranker advisor integration tests with four Wits-only recommendation guard cases; updated the online-course clarification guard to expect Wits recommendation routing. Preserved the frozen historical evaluation CSV: its RULE127 label is explicitly documented in the regression test as superseded by the source-backed Physics IB prerequisite fix. Historical scores and labels were not rewritten.

Database integration tests requiring the unavailable imported PostgreSQL catalogue are skipped. No claim is made that external database connections, live Gemini interpretation or untested manual browser interactions passed. Registration progression/aggregate/credit-cap limitations remain as described in eligibility-audit-2026-10-20.md.

Logs: tmp/full-project-tests.log; tmp/frontend-project-tests.log; tmp/project-ui-build.log; tmp/full-data-validation.log.
