# Wits-only advisor update ? 20 October 2026

Live project: C:/Users/giftv/Downloads/Cirricupath/curricupath

## Result

The advisor recognises plural eligibility questions, including third-year modules, elective lists, and a year plus fourth-year electives in one request. It runs the same eligibility service and enabled School-grid/timetable gates used for individual checks. Available modules are listed first; unknown facts, academic-review cases, unmet requirements and completed/current modules remain distinct. No completion history is inferred from the student's year.

Interest requests use Wits module titles and recorded course-outline content. Explicit message interests take priority; otherwise saved profile interests can be used. Suggestions include short match reasons and eligibility status. Relevant modules with unmet requirements are shown as future planning options, not as eligible choices.

The public-course recommendation implementation, API routes, semantic-search option, learned-ranker configuration, discovery/ratings/comparison controls and provider source entries were removed from the active product. Both `/` and `/v2` now serve the Wits-only interface. Historical experimental datasets, evaluation outputs and older user records were retained; they are not recommendation sources in the live interface. Conversations and saved answers now use a new Wits-only namespace so archived public-course replies are not displayed as current answers.

## Verification

259 selected backend, intent, API, scope, configuration and eligibility regression tests passed. Tests include both programmes, all candidates in a year, partial history, manual review, combined year/elective requests, profile interests and removed API routes. Gemini was disabled for repeatable regression tests; no model calls were needed for those checks. Vite production build passed (existing large graphics chunk warning).

The live browser was checked for Wits-only browsing, prefilled year-wide eligibility requests, a returned third-year eligibility list and brief interest-match reasons. The Downloads copy's broken Node dependency folder was preserved as `node_modules.before-wits`; its active dependency junction uses the working Investigation workspace installation. Python uses that workspace's working virtual environment, as the copied Downloads virtual environment points to a missing old Python installation.

These software checks are not a rerun of the research accuracy benchmark. The earlier experimental results remain unchanged.
