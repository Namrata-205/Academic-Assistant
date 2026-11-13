# Development evaluation results

Synthetic development evaluation, not learner outcome evidence. Independent review pending.

| Metric | Value |
| --- | --- |
| Retrieval cases | 12 |
| hit_at_1 | 0.5833 |
| hit_at_2 | 0.7500 |
| mrr_at_2 | 0.6667 |
| precision_at_2 | 0.4167 |
| recall_at_2 | 0.7429 |
| Recall-defined cases | 10 |
| Cases without relevant evidence | 2 |
| cold_page_cache_seconds | 0.8574 |
| warm_page_cache_seconds | 0.0567 |
| Mapping cases | 24 |
| Mapping accuracy | 0.7500 |
| Mapping mapped_precision | 1.0000 |
| Mapping supported_concept_recall | 0.5714 |
| Mapping clarification_recall | 1.0000 |
| Mapping false_mapping_rate | 0.0000 |
| Personalisation synthetic_checks | 14 |
| Personalisation passed | 14 |
| Personalisation pass_rate | 1.0000 |
| Generation cases | 2 |
| Generation generated_answer_rate | 0.0000 |
| Generation fallback_rate | 1.0000 |
| Generation citation_coverage | 1.0000 |
| Generation citation_id_validity | 1.0000 |
| Generation exact_evidence_span_rate | 1.0000 |
| Generation mean_latency_seconds | 3.3812 |

All proportions are 0–1. Latencies are seconds. Hit@k: any proxy-relevant passage in the first k results. MRR@2: reciprocal rank of the first relevant passage, zero if absent. Precision@2: relevant retrieved passages / 2. Mapping accuracy includes correct clarification. Mapped precision conditions on a returned concept. Supported recall conditions on an expected concept; clarification recall conditions on an expected clarification. False-mapping rate uses all mapping cases as denominator.

Generation rates use tested requests; citation rates use returned paragraphs (including excerpt fallbacks). Zero denominators are not measured. Human correctness, faithfulness, terminology and learning benefit remain unmeasured.

## Limits

- Known development cases, independent review pending; no statistical generalisation.
- Retrieval relevance is an explicit page-and-substring proxy, not human-rated semantic relevance. Precision@2 uses two slots; missing results count as failures.
- Concept IDs are supplied to retrieval tests; mapping is evaluated separately. Search is limited to catalogued concept pages.
- Recall@2 is macro-averaged only over cases with at least one proxy-relevant chunk in the scoped search pool; zero-evidence cases are reported separately. This is not corpus-wide recall.
- No baseline superiority claim: no comparable retrieval baseline was run.
- Citation IDs and copied evidence do not establish factual entailment. Excerpt fallbacks can score perfectly on structural checks.
- Generation without a learner history does not measure personalised answer quality. No real learner improvement was measured.
- Latency is sequential on this machine; cold page cache does not mean cold OS or model cache.

Recall@2 is the proportion of all proxy-relevant chunks in the concept-scoped search pool retrieved in the first two results, macro-averaged over 10 cases with nonzero relevant evidence. Two cases without relevant evidence are excluded and counted separately. This is not corpus-wide recall.
