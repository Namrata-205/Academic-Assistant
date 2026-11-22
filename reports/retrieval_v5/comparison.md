# Evidence diversity and fixed-reference coverage

Same candidate excerpts, pages, relevance labels and context limits. Only result order changes.

| Language | k | Arm | Precision | Original recall | Hit | Support-span coverage | Redundant fraction |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| all | 1 | v4_baseline | 0.8333 | 0.2042 | 0.8333 | 0.6926 | 0.0000 |
| all | 1 | diverse | 0.8333 | 0.2042 | 0.8333 | 0.6926 | 0.0000 |
| all | 2 | v4_baseline | 0.7083 | 0.3166 | 0.8333 | 0.7917 | 0.2909 |
| all | 2 | diverse | 0.7083 | 0.3166 | 0.8333 | 0.8048 | 0.2543 |
| all | 3 | v4_baseline | 0.6111 | 0.3841 | 0.8333 | 0.8793 | 0.3747 |
| all | 3 | diverse | 0.6111 | 0.3841 | 0.8333 | 0.9004 | 0.3462 |
| all | 5 | v4_baseline | 0.5000 | 0.4824 | 0.8333 | 0.9363 | 0.4598 |
| all | 5 | diverse | 0.5000 | 0.4824 | 0.8333 | 0.9553 | 0.4506 |
| all | 10 | v4_baseline | 0.3750 | 0.6963 | 0.8333 | 1.0000 | 0.6473 |
| all | 10 | diverse | 0.3750 | 0.6963 | 0.8333 | 1.0000 | 0.6473 |
| en | 1 | v4_baseline | 0.8333 | 0.2072 | 0.8333 | 0.6746 | 0.0000 |
| en | 1 | diverse | 0.8333 | 0.2072 | 0.8333 | 0.6746 | 0.0000 |
| en | 2 | v4_baseline | 0.6667 | 0.2977 | 0.8333 | 0.7361 | 0.3194 |
| en | 2 | diverse | 0.6667 | 0.2977 | 0.8333 | 0.7361 | 0.3194 |
| en | 3 | v4_baseline | 0.5556 | 0.3482 | 0.8333 | 0.8501 | 0.3925 |
| en | 3 | diverse | 0.5556 | 0.3482 | 0.8333 | 0.8924 | 0.3355 |
| en | 5 | v4_baseline | 0.5000 | 0.4893 | 0.8333 | 0.9434 | 0.4794 |
| en | 5 | diverse | 0.5000 | 0.4893 | 0.8333 | 0.9434 | 0.4794 |
| en | 10 | v4_baseline | 0.3667 | 0.7047 | 0.8333 | 1.0000 | 0.6488 |
| en | 10 | diverse | 0.3667 | 0.7047 | 0.8333 | 1.0000 | 0.6488 |
| hi | 1 | v4_baseline | 0.8333 | 0.2011 | 0.8333 | 0.7107 | 0.0000 |
| hi | 1 | diverse | 0.8333 | 0.2011 | 0.8333 | 0.7107 | 0.0000 |
| hi | 2 | v4_baseline | 0.7500 | 0.3356 | 0.8333 | 0.8473 | 0.2624 |
| hi | 2 | diverse | 0.7500 | 0.3356 | 0.8333 | 0.8735 | 0.1891 |
| hi | 3 | v4_baseline | 0.6667 | 0.4200 | 0.8333 | 0.9084 | 0.3569 |
| hi | 3 | diverse | 0.6667 | 0.4200 | 0.8333 | 0.9084 | 0.3569 |
| hi | 5 | v4_baseline | 0.5000 | 0.4756 | 0.8333 | 0.9291 | 0.4402 |
| hi | 5 | diverse | 0.5000 | 0.4756 | 0.8333 | 0.9672 | 0.4217 |
| hi | 10 | v4_baseline | 0.3833 | 0.6878 | 0.8333 | 1.0000 | 0.6457 |
| hi | 10 | diverse | 0.3833 | 0.6878 | 0.8333 | 1.0000 | 0.6457 |

## Live target-evidence policy

Original recall below uses the same full baseline pool denominator. The bounded policy uses up to three passages within the original maximum of 1300 characters. The fixed-two arm uses up to two passages.

| Language | Policy | Precision | Original recall | Hit | Support-span coverage | Redundant fraction | Mean passages | Mean chars |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | v4_fixed_two | 0.7083 | 0.3166 | 0.8333 | 0.7917 | 0.2909 | 2.0000 | 916.9167 |
| all | bounded_three | 0.7083 | 0.3475 | 0.8333 | 0.8510 | 0.2868 | 2.4167 | 1008.9167 |
| en | v4_fixed_two | 0.6667 | 0.2977 | 0.8333 | 0.7361 | 0.3194 | 2.0000 | 914.0000 |
| en | bounded_three | 0.6667 | 0.3082 | 0.8333 | 0.7935 | 0.2987 | 2.3333 | 982.3333 |
| hi | v4_fixed_two | 0.7500 | 0.3356 | 0.8333 | 0.8473 | 0.2624 | 2.0000 | 919.8333 |
| hi | bounded_three | 0.7500 | 0.3867 | 0.8333 | 0.9084 | 0.2749 | 2.5000 | 1035.5000 |

## Interpretation and limits

- Known 12-case development set; independent review pending.
- Original chunk recall retained; candidates are never removed or relabelled.
- Support-span coverage is a new metric, not a replacement for chunk recall.
- Reference spans are the union of baseline proxy-relevant excerpts in reconstructed-page coordinates.
- Coverage measures overlapping source text, not independently reviewed facts or answer correctness.
- Recall and support coverage exclude cases with no relevant candidate evidence.
- The live policy may return three rather than two passages; both obey a 1300-character maximum, not identical actual lengths.
- Policy precision uses actual returned count; fixed-k precision remains separately reported.
- No generation, final scenario evaluation or learner database changes.

Reproduce: `venv/Scripts/python.exe scripts/evaluate_evidence_coverage.py`
