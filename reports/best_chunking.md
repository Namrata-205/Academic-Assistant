# Best chunking method

Every method tuned on 20 dev cases; tested on 52 held-out cases (chapter-wide search). "+meta" adds a boost for chunks whose metadata tags the question's KG concept.

## Tuned settings

| Method | Settings | Concept boost β | Chunks | Mean chars | Truncated share |
| --- | --- | ---: | ---: | ---: | ---: |
| fixed | `{"size": 900}` | 0.2 | 407 | 615.6 | 0.686 |
| semantic | `{}` | 0.2 | 3332 | 74.3 | 0.012 |
| semantic_tuned | `{"mode": "relative", "threshold": 0.0, "max_chars": 300, "min_chars": 150}` | 0.2 | 1248 | 200.1 | 0.001 |
| graph | `{"max_chars": 450, "min_chars": 200}` | 0.2 | 796 | 314.3 | 0.126 |

## Test results (52 cases)

| Variant | Strict MRR@10 | Strict Hit@1 | Strict Hit@2 | Page MRR@10 | Page Hit@1 | Combined MRR | vs current (strict / page, Holm p) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| **semantic_tuned+meta** | 0.671 | 0.577 | 0.692 | 0.818 | 0.750 | 0.744 | +0.165 (p=0.01, sig.) / +0.149 (p=0.01, sig.) |
| graph+meta | 0.686 | 0.577 | 0.673 | 0.802 | 0.692 | 0.744 | +0.179 (p=0.00, sig.) / +0.133 (p=0.03, sig.) |
| graph | 0.605 | 0.462 | 0.596 | 0.749 | 0.615 | 0.677 | +0.099 (p=0.13) / +0.080 (p=0.20) |
| semantic+meta | 0.585 | 0.462 | 0.615 | 0.760 | 0.654 | 0.672 | +0.078 (p=0.01, sig.) / +0.092 (p=0.01, sig.) |
| semantic_tuned | 0.581 | 0.481 | 0.577 | 0.759 | 0.673 | 0.670 | +0.075 (p=0.32) / +0.091 (p=0.20) |
| fixed+meta | 0.635 | 0.481 | 0.712 | 0.665 | 0.500 | 0.650 | +0.129 (p=0.13) / -0.004 (p=0.95) |
| semantic | 0.506 | 0.385 | 0.519 | 0.669 | 0.538 | 0.587 | — |
| fixed | 0.478 | 0.346 | 0.462 | 0.529 | 0.385 | 0.504 | -0.029 (p=0.63) / -0.139 (p=0.12) |

Best by the pre-set rule (highest mean of strict and page-only MRR@10 on the 52 test cases): **semantic_tuned+meta**.

## Limits

- AI-authored cases with a page/substring relevance proxy; human review pending.
- Holm correction is over all 7 challengers; with 52 cases only gains of roughly ≥0.15 MRR are detectable.
- Retrieval only; answer quality not measured.
