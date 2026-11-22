# Retrieval v3 development comparison

Same 12 known development cases and unchanged page/substring relevance rules. Independent review pending.

| Arm | Evidence Hit@1 | Hit@2 | MRR@2 | Precision@2 | Chunk recall@2 | Anchor Hit@1 | Mean excerpt chars |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.5833 | 0.6667 | 0.6250 | 0.4167 | 0.6071 | 0.5833 | 170.2083 |
| baseline_same_context | 0.7500 | 0.8333 | 0.7917 | 0.6250 | 0.2716 | 0.5833 | 428.1250 |
| candidate_anchors | 0.5833 | 0.6667 | 0.6250 | 0.4167 | 0.6071 | 0.5833 | 170.3750 |
| candidate | 0.8333 | 0.8333 | 0.8333 | 0.6667 | 0.2916 | 0.5833 | 447.0000 |

## Language-specific evidence retrieval

| Language | Arm | Hit@1 | Hit@2 | MRR@2 |
| --- | --- | ---: | ---: | ---: |
| en | baseline | 0.8333 | 0.8333 | 0.8333 |
| en | candidate | 0.8333 | 0.8333 | 0.8333 |
| hi | baseline | 0.3333 | 0.5000 | 0.4167 |
| hi | candidate | 0.8333 | 0.8333 | 0.8333 |

## Interpretation

Evidence metrics score the actual returned excerpt; anchor metrics score the text used for ranking before neighboring evidence is added.
The same-context baseline isolates the benefit of evidence expansion from ranking changes. All expanded excerpts remain bounded to 650 characters and one page.
Chunk recall denominators change with overlapping contexts. Do not present its change as corpus-wide recall or hide a regression.
No benchmark labels were changed. Experiments used no cloud generation, learner database, or final scenario cases.
attempt_01.json and attempt_02.json preserve the initial unsuccessful development experiments.
The two place-value cases lack matching evidence in the candidate pool; related activities are not a verified direct lesson.
These results do not establish mathematical correctness, held-out accuracy, statistical superiority, or learning benefit.

Reproduce: `venv/Scripts/python.exe scripts/evaluate_retrieval_improvements.py`
