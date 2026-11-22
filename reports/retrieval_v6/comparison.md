# Cross-encoder reranking development experiment

Same saved v5 candidate pool, query, labels, up-to-three-passage policy and 1300-character maximum.

| Language | Arm | Precision | Original recall | Hit | Support-span coverage | Mean passages | Mean chars |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| all | v5_baseline | 0.7083 | 0.3475 | 0.8333 | 0.8510 | 2.4167 | 1008.9167 |
| all | cross_encoder | 0.8056 | 0.4391 | 0.8333 | 0.7882 | 2.3333 | 1015.7500 |
| en | v5_baseline | 0.6667 | 0.3082 | 0.8333 | 0.7935 | 2.3333 | 982.3333 |
| en | cross_encoder | 0.8333 | 0.4249 | 0.8333 | 0.7575 | 2.1667 | 962.8333 |
| hi | v5_baseline | 0.7500 | 0.3867 | 0.8333 | 0.9084 | 2.5000 | 1035.5000 |
| hi | cross_encoder | 0.7778 | 0.4533 | 0.8333 | 0.8189 | 2.5000 | 1068.6667 |

Model load: 1.555s. Mean uncached cross-encoder scoring: 0.678s per query.

## Limits

- Known 12-case development set; no independent relevance or answer-correctness review.
- Only the top 20 hybrid/diversity candidates are cross-encoder scored; the remaining pool is retained.
- Original recall uses the same complete candidate-pool denominator in both arms.
- Support-span coverage is a separate overlap-adjusted text metric, not fact recall.
- Timing is uncached pair scoring on CPU after model load; it excludes initial retrieval and generation.
- No LLM generation, final scenarios, or learner database changes.

Reproduce: `venv/Scripts/python.exe scripts/evaluate_passage_reranker.py`
