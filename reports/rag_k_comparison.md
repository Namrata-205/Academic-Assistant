# Retrieval depth comparison

| Language | k | Precision@k | Recall@k | MRR@k | Hit@k | Cases | Recall-defined cases |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 1 | 0.4167 | 0.3651 | 0.4167 | 0.4167 | 12 | 9 |
| all | 2 | 0.3333 | 0.5476 | 0.5000 | 0.5833 | 12 | 9 |
| all | 3 | 0.2778 | 0.5794 | 0.5000 | 0.5833 | 12 | 9 |
| all | 5 | 0.2333 | 0.6429 | 0.5000 | 0.5833 | 12 | 9 |
| all | 10 | 0.1833 | 1.0000 | 0.5258 | 0.7500 | 12 | 9 |
| en | 1 | 0.6667 | 0.6286 | 0.6667 | 0.6667 | 6 | 5 |
| en | 2 | 0.5000 | 0.8571 | 0.7500 | 0.8333 | 6 | 5 |
| en | 3 | 0.3889 | 0.8857 | 0.7500 | 0.8333 | 6 | 5 |
| en | 5 | 0.3000 | 0.9429 | 0.7500 | 0.8333 | 6 | 5 |
| en | 10 | 0.1833 | 1.0000 | 0.7500 | 0.8333 | 6 | 5 |
| hi | 1 | 0.1667 | 0.0357 | 0.1667 | 0.1667 | 6 | 4 |
| hi | 2 | 0.1667 | 0.1607 | 0.2500 | 0.3333 | 6 | 4 |
| hi | 3 | 0.1667 | 0.1964 | 0.2500 | 0.3333 | 6 | 4 |
| hi | 5 | 0.1667 | 0.2679 | 0.2500 | 0.3333 | 6 | 4 |
| hi | 10 | 0.1833 | 1.0000 | 0.3016 | 0.6667 | 6 | 4 |

Precision = relevant chunks in top k / k. Recall = relevant chunks in top k / all proxy-relevant chunks in the scoped pool, averaged only where that denominator is positive. MRR = mean reciprocal rank of the first relevant result within k; absent relevant results score zero. Hit@k = proportion of cases with any relevant top-k result. Values are proportions, not percentages.

- Development cases with page-and-substring relevance proxy; independent review pending.
- One fixed ranking per case, truncated at each k. No generation calls or live app retrieval settings changed.
- Precision uses k slots, with missing results counting as irrelevant. Recall excludes zero-evidence cases.
- Recall is within concept-scoped catalogued pages, not the full textbook corpus.
- MRR and Hit@k use all 12 cases, including 3 cases with no proxy-relevant chunk in the scoped pool.
- Selecting k on these cases is development tuning, not an independently validated optimum.
