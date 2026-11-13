# Results and interpretation

The system was evaluated on 12 bilingual development retrieval cases (six English
and six Hindi), a 24-case concept-mapping set, 14 synthetic personalisation policy
checks, and two live answer requests (one per language). Expectations await independent
review. These cases were available during development and do not represent an unseen
test set or a real-learner study.

Retrieval achieved Hit@1 of 58.33%, Hit@2 of 75.00%, MRR@2 of 0.667, and Precision@2
of 41.67%. Relevance was measured using expected PDF pages and required evidence
substrings, not a human semantic-relevance judgement. Hit@2 was 5/6 in English and
4/6 in Hindi. These results measure ranking within concept-selected pages, not
unrestricted retrieval across complete books.

Concept mapping matched expectations in 18/24 cases (75.00%). The eight returned
concept mappings were correct, giving mapped precision of 100%, while supported-topic
recall was 8/14 (57.14%). All ten cases requiring clarification received clarification.
The six remaining supported questions were also sent for clarification. Thus, the
zero false-mapping rate reflects conservative abstention and does not imply complete
semantic understanding.

All 14 synthetic personalisation checks passed, including evidence-status handling,
learner isolation, prioritisation of a foundation with possible difficulty, and keeping
imported background separate from current evidence. This demonstrates functional
policy behaviour, not the educational effectiveness of personalised explanations.

Both live requests used direct textbook excerpt fallback (generated-answer rate 0%,
fallback rate 100%). Returned paragraphs had 100% citation coverage, citation-ID
validity, and exact-evidence-span agreement. These structural results are expected
for copied excerpts and must not be reported as 100% factual faithfulness or answer
accuracy. Mean answer latency was 2.815 seconds for this two-request run. Mean
retrieval latency was 0.307 seconds with page caches reset and 0.025 seconds with
warm page caches; these are machine-specific development timings.

## Observed errors

- The Hindi right-angle case (R06) did not retrieve a top-two chunk satisfying the
  expected angle-and-90 evidence markers, despite retrieving the expected PDF page.
  This indicates a chunk-ranking or extraction limitation rather than missing the chapter.
- Both place-value cases (R09/R10) failed the direct-explanation evidence criteria.
  The catalogued page is a related supercell activity, not a direct hundreds-place
  lesson. This exposes a source-coverage limitation that embeddings cannot repair.
- In R04 (Hindi vertex) and R07 (English acute-angle bounds), proxy-relevant evidence
  appeared only at rank two. Retrieving the correct page alone is not sufficient.
- The generation checks produced excerpts, so fluency, explanatory usefulness and
  generated mathematical correctness remain unestablished.

Human ratings of mathematical correctness, source support, Hindi terminology,
relevance and personalisation should be collected using the exported review worksheet.
A separate frozen, independently reviewed test set and learner study are needed before
claims about generalisation or improved learning. No retrieval baseline comparison was
run, so these measurements do not establish superiority over keyword retrieval.

Reproduce with `python -m diagnostic.evaluate_rag --generation-cases 2`.
Full values and definitions are in `rag_results.md` and `rag_metrics.json`; case-level
outputs are in `rag_retrieval_results.csv`, `rag_generation_results.csv`, and
`rag_personalisation_results.csv`. Timings and model outputs can vary between runs.

## Added retrieval recall

Scoped macro Recall@2 is 74.29% across 10 cases with at least one proxy-relevant chunk. The two place-value cases contain no proxy-relevant chunks in the searched pool and are reported separately rather than assigned a zero-denominator recall. English Recall@2 is 85.71%; Hindi Recall@2 is 62.86%. This is scoped retrieval recall, not full-book recall. Timing figures earlier in this discussion describe the initial run; current run timings are in rag_metrics.json.
