# Pilot measurements and published benchmarks

> **DRAFT: developer-side labels, not independent evidence.**

Published figures use other institutions, datasets and definitions. They are listed for context and are not directly comparable.

| Dimension | Measured here | Published | Why not comparable |
| --- | --- | --- | --- |
| Response time | CurricuPath median 5 ms (deterministic path, no model call); Handbook RAG median 1.6 s (one model call); structured-rules LLM median 1.8 s (one model call) | B6: average query time 2.07 (single institution; Gemini to Cypher over Neo4j) | The published time includes a language-model pipeline. Our CurricuPath figure contains no model call, so only the model-backed baselines are the same kind of measurement. |
| Decision quality | CurricuPath macro-F1 0.89 (developer labels), 0.65 (briefing labels) | B6: f1 0.958 (300 processed queries listed (420 described); 3 tracks); B1: prerequisite classification 0.99 (synthetic: 101330 interactions, 10000 simulated students; reported as above 99%) | Different task, metric and data. Our answer keys are developer-side, so this measures agreement with our labels, not accuracy. |
| Intent understanding | 85/100 prompts correct (85%); 0/10 on ambiguous module names (bare topic words) | B6: query success 0.93 (curated query collection; single institution) | Different query sets. Ours are unreviewed developer drafts, and the extractor was measured without Gemini. |

## Published figures with no measurement here yet

| Benchmark | Metric | Value | Data |
| --- | --- | --- | --- |
| B5 ARGObot (Tamascelli et al. 2025) | answer correctness | 0.878 | 18 handbook questions |
| B5 ARGObot (Tamascelli et al. 2025) | faithfulness | 0.927 | 18 handbook questions |
| B4 MyAdvisor (Kuhail et al. 2023) | student task success | 0.92 | 17 students and 4 advisors |
| B4 MyAdvisor (Kuhail et al. 2023) | sus students | 86.47 | 17 students |
| B3 Course recommender chatbot (Tan et al. 2022) | usability acceptance | 8.2 | 35-student requirements survey |
| B2 Prerequisite-based recommender (Chanaa and El Faddouli 2024) | ndcg at 10 | 0.8648 | public learning objects; not institutional rules |

## How the pilot runs were configured

Pilot configuration: One run per case instead of three, so repeatability is not measured. LLM arms used gemini-3.5-flash-lite, not the pinned gemini-3.6-flash, because of quota. CurricuPath arms ran without Gemini intent extraction, so they show the deterministic path only. An earlier Handbook-RAG attempt lost 27 of 60 runs to a per-minute quota limit; it was re-run paced and all 60 are valid.
