# Chunking method comparison

Baseline check: `semantic` + scoped protocol reproduces the live chatbot ranking (`book_chat.retrieve_sources`) for every test case.

Stored report `rag_k_comparison.md` (2026-11-02): English matches, Hindi differs. The stored Hindi run used the earlier, corrupted Hindi extraction (e.g. "न्ून कोण", "लिखाा जााए"); the app now reads the repaired v4.5 text. All comparisons below re-run the current method on the current text, so they are like-for-like.

| Stored report (old Hindi text), semantic, scoped | Hit@1 | Hit@2 | MRR@2 |
| --- | ---: | ---: | ---: |
| all | 0.417 | 0.583 | 0.500 |
| en | 0.667 | 0.833 | 0.750 |
| hi | 0.167 | 0.333 | 0.250 |

## Settings

| Method | Settings | Chunks | Mean chars | Share truncated at 128 tokens |
| --- | --- | ---: | ---: | ---: |
| fixed | `{"size": 650}` | 513 | 488.2 | 0.649 |
| semantic | `current (.48, 650)` | 3332 | 74.3 | 0.012 |
| semantic_tuned | `{"mode": "relative", "threshold": 0.0, "max_chars": 300, "min_chars": 150}` | 1247 | 200.3 | 0.001 |
| graph | `{"max_chars": 650, "min_chars": 120}` | 727 | 344.2 | 0.329 |

## Test set (12 existing cases), scoped protocol — current app search

| Method | Lang | Hit@1 | Hit@2 | MRR@2 | P@2 | Hit@5 | MRR@10 | Recall@10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed | all | 0.500 | 0.833 | 0.667 | 0.500 | 0.833 | 0.667 | 1.000 |
| fixed | en | 0.333 | 0.833 | 0.583 | 0.500 | 0.833 | 0.583 | 1.000 |
| fixed | hi | 0.667 | 0.833 | 0.750 | 0.500 | 0.833 | 0.750 | 1.000 |
| semantic | all | 0.583 | 0.750 | 0.667 | 0.458 | 0.750 | 0.679 | 1.000 |
| semantic | en | 0.667 | 0.833 | 0.750 | 0.500 | 0.833 | 0.750 | 1.000 |
| semantic | hi | 0.500 | 0.667 | 0.583 | 0.417 | 0.667 | 0.607 | 1.000 |
| semantic_tuned | all | 0.500 | 0.750 | 0.625 | 0.500 | 0.833 | 0.653 | 1.000 |
| semantic_tuned | en | 0.667 | 0.833 | 0.750 | 0.500 | 0.833 | 0.750 | 1.000 |
| semantic_tuned | hi | 0.333 | 0.667 | 0.500 | 0.500 | 0.833 | 0.556 | 1.000 |
| graph | all | 0.583 | 0.833 | 0.708 | 0.458 | 0.833 | 0.708 | 1.000 |
| graph | en | 0.833 | 0.833 | 0.833 | 0.500 | 0.833 | 0.833 | 1.000 |
| graph | hi | 0.333 | 0.833 | 0.583 | 0.417 | 0.833 | 0.583 | 1.000 |

## Test set (12 existing cases), chapter-wide protocol

| Method | Lang | Hit@1 | Hit@2 | MRR@2 | P@2 | Hit@5 | MRR@10 | Recall@10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed | all | 0.250 | 0.417 | 0.333 | 0.208 | 0.417 | 0.347 | 0.600 |
| fixed | en | 0.167 | 0.500 | 0.333 | 0.250 | 0.500 | 0.333 | 0.600 |
| fixed | hi | 0.333 | 0.333 | 0.333 | 0.167 | 0.333 | 0.361 | 0.600 |
| semantic | all | 0.250 | 0.417 | 0.333 | 0.250 | 0.583 | 0.389 | 0.629 |
| semantic | en | 0.167 | 0.500 | 0.333 | 0.333 | 0.833 | 0.444 | 1.000 |
| semantic | hi | 0.333 | 0.333 | 0.333 | 0.167 | 0.333 | 0.333 | 0.257 |
| semantic_tuned | all | 0.333 | 0.500 | 0.417 | 0.250 | 0.583 | 0.449 | 0.675 |
| semantic_tuned | en | 0.500 | 0.667 | 0.583 | 0.333 | 0.667 | 0.607 | 0.950 |
| semantic_tuned | hi | 0.167 | 0.333 | 0.250 | 0.167 | 0.500 | 0.292 | 0.400 |
| graph | all | 0.333 | 0.500 | 0.417 | 0.250 | 0.667 | 0.465 | 0.750 |
| graph | en | 0.500 | 0.667 | 0.583 | 0.333 | 0.833 | 0.639 | 1.000 |
| graph | hi | 0.167 | 0.333 | 0.250 | 0.167 | 0.500 | 0.292 | 0.500 |

## Dev set (20 cases, ch 1/4/5), chapter-wide protocol — used to tune semantic_tuned

| Method | Lang | Hit@1 | Hit@2 | MRR@2 | P@2 | Hit@5 | MRR@10 | Recall@10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed | all | 0.350 | 0.550 | 0.450 | 0.325 | 0.700 | 0.502 | 0.535 |
| fixed | en | 0.600 | 0.700 | 0.650 | 0.450 | 0.800 | 0.680 | 0.616 |
| fixed | hi | 0.100 | 0.400 | 0.250 | 0.200 | 0.600 | 0.325 | 0.454 |
| semantic | all | 0.350 | 0.500 | 0.425 | 0.300 | 0.650 | 0.496 | 0.523 |
| semantic | en | 0.300 | 0.400 | 0.350 | 0.250 | 0.700 | 0.460 | 0.622 |
| semantic | hi | 0.400 | 0.600 | 0.500 | 0.350 | 0.600 | 0.531 | 0.433 |
| semantic_tuned | all | 0.700 | 0.750 | 0.725 | 0.475 | 0.850 | 0.748 | 0.480 |
| semantic_tuned | en | 0.600 | 0.600 | 0.600 | 0.400 | 0.800 | 0.645 | 0.521 |
| semantic_tuned | hi | 0.800 | 0.900 | 0.850 | 0.550 | 0.900 | 0.850 | 0.440 |
| graph | all | 0.400 | 0.450 | 0.425 | 0.300 | 0.650 | 0.495 | 0.457 |
| graph | en | 0.400 | 0.400 | 0.400 | 0.250 | 0.700 | 0.491 | 0.502 |
| graph | hi | 0.400 | 0.500 | 0.450 | 0.350 | 0.600 | 0.500 | 0.412 |

Hit@k = share of cases with a proxy-relevant chunk in the top k. MRR@k = mean reciprocal rank of the first relevant chunk (0 if none in top k). P@2 = relevant chunks in top 2 / 2. Recall@10 = relevant chunks in top 10 / all relevant chunks in the searched pool, averaged over cases where that pool is non-empty. Proportions 0-1.

## Limits

- 12 test and 20 dev cases are AI-authored development sets; differences of one case (0.083 on test) are within noise.
- Relevance is the page-plus-substring proxy, which favours longer chunks (more likely to contain every term).
- Only semantic_tuned was tuned (on dev). fixed and graph use fixed a-priori settings (650 chars, graph min 120).
- The embedding model reads at most 128 tokens; longer chunks are embedded by their beginning only.
- No generation was run; better retrieval is not shown to give better answers.
