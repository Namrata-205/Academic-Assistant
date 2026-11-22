# Hybrid retrieval development comparison

Identical concept-scoped pages, graph anchors, 650-character context budget, evidence labels, and model.

| Arm | Evidence Hit@1 | Hit@2 | MRR@2 | Precision@2 | Recall@2 | Anchor Hit@1 | Anchor Hit@2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v3_baseline | 0.8333 | 0.8333 | 0.8333 | 0.6667 | 0.2916 | 0.5833 | 0.6667 |
| hybrid | 0.8333 | 0.8333 | 0.8333 | 0.7083 | 0.3166 | 0.6667 | 0.7500 |

## By language

| Language | Arm | Evidence Hit@1 | Anchor Hit@1 | MRR@2 |
| --- | --- | ---: | ---: | ---: |
| en | v3_baseline | 0.8333 | 0.8333 | 0.8333 |
| en | hybrid | 0.8333 | 0.8333 | 0.8333 |
| hi | v3_baseline | 0.8333 | 0.3333 | 0.8333 |
| hi | hybrid | 0.8333 | 0.5000 | 0.8333 |

## Warm retrieval latency

Three repeats per case per arm, alternating arm order after initial case execution. Includes retrieval and excludes generation and model loading.

| Arm | Requests | Mean seconds | Median seconds | P95 seconds |
| --- | ---: | ---: | ---: | ---: |
| v3_baseline | 36 | 0.0266 | 0.0260 | 0.0318 |
| hybrid | 36 | 0.0271 | 0.0267 | 0.0342 |

## Limits

- Known 12-case development set; independent review pending; not held-out accuracy.
- Page/substring proxy is not human-rated relevance or mathematical correctness.
- Expanded evidence and ranking anchors are scored separately.
- Recall denominators may vary after context deduplication.
- Per-case elapsed time includes caches/model startup and is not a fair latency comparison.

Reproduce: `venv/Scripts/python.exe scripts/evaluate_hybrid_retrieval.py`
