# English retrieval evaluation

Run: 2026-11-02T04:06:47.389360+00:00
Cases: 6. Recall-defined cases: 5.
No proxy-relevant chunk in scoped pool: R09.

| k | Precision@k | Recall@k | MRR@k |
| --- | ---: | ---: | ---: |
| 1 | 66.67% | 62.86% | 0.667 |
| 2 | 50.00% | 85.71% | 0.750 |
| 3 | 38.89% | 88.57% | 0.750 |
| 5 | 30.00% | 94.29% | 0.750 |
| 10 | 18.33% | 100.00% | 0.750 |

Relevance uses expected PDF pages and exact normalised keyword matches. Hindi extraction errors can cause false negatives. Recall is scoped to the retrieved candidate pool and excludes cases with no matching evidence. Precision and MRR include all six cases. Development labels await independent review. This evaluates retrieval, not generated-answer correctness.
