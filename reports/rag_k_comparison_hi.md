# Hindi retrieval evaluation

Run: 2026-11-02T04:06:47.389360+00:00
Cases: 6. Recall-defined cases: 4.
No proxy-relevant chunk in scoped pool: R08, R10.

| k | Precision@k | Recall@k | MRR@k |
| --- | ---: | ---: | ---: |
| 1 | 16.67% | 3.57% | 0.167 |
| 2 | 16.67% | 16.07% | 0.250 |
| 3 | 16.67% | 19.64% | 0.250 |
| 5 | 16.67% | 26.79% | 0.250 |
| 10 | 18.33% | 100.00% | 0.302 |

Relevance uses expected PDF pages and exact normalised keyword matches. Hindi extraction errors can cause false negatives. Recall is scoped to the retrieved candidate pool and excludes cases with no matching evidence. Precision and MRR include all six cases. Development labels await independent review. This evaluates retrieval, not generated-answer correctness.
