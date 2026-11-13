# Mapping, source coverage and learner evaluation - v2

## Implemented

- A pinned multilingual MiniLM embedding model runs locally on CPU through ONNX Runtime.
  Query text is not sent to a hosted inference service. The code uses model sentence
  similarity, explicit scope checks and mathematical constraints; it does not claim
  unrestricted semantic understanding. Scores are similarities, not probabilities.
- Explicit ambiguity checks preserve distinctions between concepts in different chapters.
  The known right-angle/degree and Hindi fraction/addition regressions have tests.
- Semantic candidates are accepted only above minimum similarity .57 and margin .07.
  Otherwise the UI asks the learner to clarify. Model failures also abstain safely.
- A new 24-case holdout was authored before execution. Matches: legacy 13/24, v2 18/24.
  False assignments: legacy 5, v2 0. Both abstained on 16 queries; v2 removed false
  assignments and improved accepted matches but still abstained on answerable cases.
  Expectations remain draft, not independently reviewed; no tuning was performed after
  this run. The original 20-case pilot explicitly retains the old mapper for reproduction.
- All 53 graph concepts have source-audit records. 51 have English/Hindi book locations.
  Related-only activities are distinguished from direct explanations. Parallel lines and
  magic square have no verified matching lesson in these supplied chapters and are
  explicitly unavailable. No page was invented to make the count look complete.
- `/study` collects real entered responses under persisted random fixed/graph-guided
  allocation, with the same bank and maximum three-question budget and empty starting
  history. Sessions can be resumed by participant code. The normal learner navigation
  does not expose research/developer tools.
- `/api/study/export` produces a reviewable record with source hashes and blank
  independent-review fields. The analyser excludes unreviewed cases from gold-label
  comparisons and reports unresolved outcomes, not just issued labels.

## External work that remains

There are no completed real-learner cases or independent reviewer diagnoses supplied
for this study. "ok" acknowledged preparation; it did not identify a reviewer, provide
a participant count, or supply observations. Therefore educational usefulness is NOT
established. Complete the protocol in real_learner_study_protocol.md with actual
learners and an independent educator. To claim learning gains, collect separately
reviewed pre/post transfer outcomes; diagnostic agreement alone is insufficient.

Obtain an approved supplemental source or revise the graph for parallel lines and
magic square. The current uploaded textbook cannot honestly be cited as a verified
direct lesson for those concepts. A location audit does not validate every graph edge.

All first-pass content, source and benchmark reviews remain distinct from human
pedagogical validation. Learner bank review and decision-rule sign-off are still pending.
