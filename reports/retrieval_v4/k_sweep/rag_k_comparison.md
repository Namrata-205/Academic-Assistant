# Retrieval depth comparison

| Language | k | Precision@k | Recall@k | MRR@k | Hit@k | Cases | Recall-defined cases |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 1 | 0.8333 | 0.2042 | 0.8333 | 0.8333 | 12 | 10 |
| all | 2 | 0.7083 | 0.3166 | 0.8333 | 0.8333 | 12 | 10 |
| all | 3 | 0.6111 | 0.3841 | 0.8333 | 0.8333 | 12 | 10 |
| all | 5 | 0.5000 | 0.4824 | 0.8333 | 0.8333 | 12 | 10 |
| all | 10 | 0.3750 | 0.6963 | 0.8333 | 0.8333 | 12 | 10 |
| en | 1 | 0.8333 | 0.2072 | 0.8333 | 0.8333 | 6 | 5 |
| en | 2 | 0.6667 | 0.2977 | 0.8333 | 0.8333 | 6 | 5 |
| en | 3 | 0.5556 | 0.3482 | 0.8333 | 0.8333 | 6 | 5 |
| en | 5 | 0.5000 | 0.4893 | 0.8333 | 0.8333 | 6 | 5 |
| en | 10 | 0.3667 | 0.7047 | 0.8333 | 0.8333 | 6 | 5 |
| hi | 1 | 0.8333 | 0.2011 | 0.8333 | 0.8333 | 6 | 5 |
| hi | 2 | 0.7500 | 0.3356 | 0.8333 | 0.8333 | 6 | 5 |
| hi | 3 | 0.6667 | 0.4200 | 0.8333 | 0.8333 | 6 | 5 |
| hi | 5 | 0.5000 | 0.4756 | 0.8333 | 0.8333 | 6 | 5 |
| hi | 10 | 0.3833 | 0.6878 | 0.8333 | 0.8333 | 6 | 5 |

## Ranking anchors and context cost

| Language | k | Anchor Hit@k | Anchor MRR@k | Mean returned chunks | Mean context characters |
| --- | ---: | ---: | ---: | ---: | ---: |
| all | 1 | 0.6667 | 0.6667 | 1.00 | 459.9 |
| all | 2 | 0.7500 | 0.7083 | 2.00 | 916.9 |
| all | 3 | 0.8333 | 0.7361 | 3.00 | 1285.1 |
| all | 5 | 0.8333 | 0.7361 | 5.00 | 1920.4 |
| all | 10 | 0.8333 | 0.7361 | 9.83 | 3176.8 |
| en | 1 | 0.8333 | 0.8333 | 1.00 | 469.8 |
| en | 2 | 0.8333 | 0.8333 | 2.00 | 914.0 |
| en | 3 | 0.8333 | 0.8333 | 3.00 | 1274.5 |
| en | 5 | 0.8333 | 0.8333 | 5.00 | 1988.2 |
| en | 10 | 0.8333 | 0.8333 | 9.67 | 3141.8 |
| hi | 1 | 0.5000 | 0.5000 | 1.00 | 450.0 |
| hi | 2 | 0.6667 | 0.5833 | 2.00 | 919.8 |
| hi | 3 | 0.8333 | 0.6389 | 3.00 | 1295.7 |
| hi | 5 | 0.8333 | 0.6389 | 5.00 | 1852.7 |
| hi | 10 | 0.8333 | 0.6389 | 10.00 | 3211.7 |

Precision = relevant chunks in top k / k. Recall = relevant chunks in top k / all proxy-relevant chunks in the scoped pool, averaged only where that denominator is positive. MRR = mean reciprocal rank of the first relevant result within k; absent relevant results score zero. Hit@k = proportion of cases with any relevant top-k result. Values are proportions, not percentages.
Anchor metrics score the original passage before neighboring context is added. Context characters include overlap and are not tokenizer counts. This is a retrieval-only sweep; larger k has not been evaluated for generated-answer quality.

- Development cases with page-and-substring relevance proxy; independent review pending.
- One fixed ranking per case, truncated at each k. No generation calls or live app retrieval settings changed.
- Precision uses k slots, with missing results counting as irrelevant. Recall excludes zero-evidence cases.
- Recall is within concept-scoped catalogued pages, not the full textbook corpus.
- MRR and Hit@k use all 12 cases, including 2 cases with no proxy-relevant chunk in the scoped pool.
- Selecting k on these cases is development tuning, not an independently validated optimum.
