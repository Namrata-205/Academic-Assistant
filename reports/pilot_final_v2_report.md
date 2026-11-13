# Paired diagnostic pilot — final candidate v2

**Synthetic cases; independent expectation review pending. Not a real-learner study.**

Twenty cases were frozen before this execution, separately from development tests. The inputs use known development topics; this is not a claim of an unseen holdout. Existing legacy pilot files remain unchanged.

| Measure | Fixed | Graph-guided |
| --- | ---: | ---: |
| mapping correct | 11 | 11 |
| correct diagnoses | 4 | 4 |
| false diagnoses | 0 | 0 |
| unresolved concepts | 21 | 21 |
| insufficient evidence agreements | 1 | 1 |
| off target assessed concepts | 0 | 0 |
| case unresolved | 13 | 13 |
| questions asked | 15 | 14 |

## Per-case comparison

C = correct conclusive labels; F = false conclusive labels; U = unresolved eligible concepts; Q = questions. Expected clarifications with no diagnosis are successful routing, not unresolved diagnostic cases.

| Case | Language | Response profile | Mapping matches | Fixed C/F/U/Q | Guided C/F/U/Q |
| --- | --- | --- | --- | --- | --- |
| F01 | en | correct | True | 1/0/1/3 | 1/0/1/3 |
| F02 | hi | incorrect | False | 0/0/2/0 | 0/0/2/0 |
| F03 | en | incorrect | True | 1/0/2/3 | 1/0/2/3 |
| F04 | hi | correct | False | 0/0/3/0 | 0/0/3/0 |
| F05 | en | correct | False | 0/0/1/0 | 0/0/1/0 |
| F06 | hi | incorrect | False | 0/0/1/0 | 0/0/1/0 |
| F07 | en | mixed | True | 0/0/2/3 | 0/0/2/3 |
| F08 | hi | ambiguous | False | 0/0/2/0 | 0/0/2/0 |
| F09 | en | correct | True | 1/0/0/3 | 1/0/0/2 |
| F10 | hi | incorrect | False | 0/0/1/0 | 0/0/1/0 |
| F11 | en | mixed | False | 0/0/1/0 | 0/0/1/0 |
| F12 | hi | ambiguous | False | 0/0/1/0 | 0/0/1/0 |
| F13 | en | correct | True | 1/0/1/3 | 1/0/1/3 |
| F14 | hi | mixed | False | 0/0/3/0 | 0/0/3/0 |
| F15 | en | ambiguous | True | 0/0/0/0 | 0/0/0/0 |
| F16 | hi | ambiguous | True | 0/0/0/0 | 0/0/0/0 |
| F17 | en | ambiguous | True | 0/0/0/0 | 0/0/0/0 |
| F18 | hi | ambiguous | True | 0/0/0/0 | 0/0/0/0 |
| F19 | en | ambiguous | True | 0/0/0/0 | 0/0/0/0 |
| F20 | hi | ambiguous | True | 0/0/0/0 | 0/0/0/0 |

## Protocol and metric definitions

- The same bank, empty initial history, eligible target/direct-prerequisite concepts and maximum three questions are used by both methods. Neither method receives the simulated learner profile.
- Fixed selection sorts concept ID then item ID and is response-independent. Graph-guided selection uses the production rule below and can stop before three questions. Both use the same scoring and decision rules.
- Each item has one frozen response per case, independent of method and question order. Hindi numerical responses use Devanagari digits. No student records are written.
- Correct/false diagnoses count conclusive concept labels against the draft synthetic profile. Insufficient evidence and unassessed concepts are unresolved, not correct/false diagnoses; appropriate insufficient-label agreements are separately counted.
- Opportunity counts use bank-covered targets and direct prerequisites for the EXPECTED mapped target, so unexpected clarification cannot remove a case from the denominator. Off-target assessments are separately reported.
- An expected clarification is successful routing, with no diagnostic opportunity. An incorrect mapping or clarification makes a case unresolved. Cases may include multiple concept opportunities.
- This compares question-selection strategies, not prerequisite-graph construction or RAG retrieval. Both methods use the graph to define eligible concepts, so no causal claim about the graph itself follows.

Maximum 3 new questions. Eligible concepts: target plus direct incoming prerequisites with bank items; exclude self-loops. Fixed: concept ID then item ID. Graph-guided: finish checking a concept with one valid observation first; otherwise direct prerequisites before target, descending graph confidence, then concept ID. Pick the lowest unused item ID. Use at most two most recent same-version historical observations per concept, never repeat their items. Stop when budget exhausted or no unresolved eligible item remains. Two correct and no incorrect: understanding; two incorrect and no correct: possible difficulty; mixed, one observation, or no valid observations: insufficient. Invalid answers consume a question but supply no knowledge evidence. Untested in this interaction remains unassessed even if historical evidence exists.

## Observed outcomes and limits

Mapping disagreements against draft expectations: F02, F04, F05, F06, F08, F10, F11, F12, F14.
Graph-guided used 1 fewer questions overall. This is an observed stopping/selection difference on these fixtures, not proof of greater educational usefulness.
- F01: limited evidence and/or untested eligible concepts remain unresolved within the three-question budget.
- F02: mapping mismatch/clarification; inspect actual versus expected mapping in the CSV; limited evidence and/or untested eligible concepts remain unresolved within the three-question budget.
- F03: limited evidence and/or untested eligible concepts remain unresolved within the three-question budget.
- F04: mapping mismatch/clarification; inspect actual versus expected mapping in the CSV; limited evidence and/or untested eligible concepts remain unresolved within the three-question budget.
- F05: mapping mismatch/clarification; inspect actual versus expected mapping in the CSV; limited evidence and/or untested eligible concepts remain unresolved within the three-question budget.
- F06: mapping mismatch/clarification; inspect actual versus expected mapping in the CSV; limited evidence and/or untested eligible concepts remain unresolved within the three-question budget.
- F07: mixed answers do not support a conclusive concept label; limited evidence and/or untested eligible concepts remain unresolved within the three-question budget.
- F08: mapping mismatch/clarification; inspect actual versus expected mapping in the CSV; unclear responses consume budget but provide no knowledge evidence; limited evidence and/or untested eligible concepts remain unresolved within the three-question budget.
- F10: mapping mismatch/clarification; inspect actual versus expected mapping in the CSV; limited evidence and/or untested eligible concepts remain unresolved within the three-question budget.
- F11: mapping mismatch/clarification; inspect actual versus expected mapping in the CSV; mixed answers do not support a conclusive concept label; limited evidence and/or untested eligible concepts remain unresolved within the three-question budget.
- F12: mapping mismatch/clarification; inspect actual versus expected mapping in the CSV; unclear responses consume budget but provide no knowledge evidence; limited evidence and/or untested eligible concepts remain unresolved within the three-question budget.
- F13: limited evidence and/or untested eligible concepts remain unresolved within the three-question budget.
- F14: mapping mismatch/clarification; inspect actual versus expected mapping in the CSV; mixed answers do not support a conclusive concept label; limited evidence and/or untested eligible concepts remain unresolved within the three-question budget.

Review `pilot_final_v2_blind_review.csv` independently before consulting the draft expectations or method outputs. The item pack provides all potential item responses, not an actual sequence of thirty asked questions. An independent reviewer can disagree with the author; preserve disagreements and version any revised cases. Do not label this study final or independently validated until review is completed.

Synthetic responses omit guessing, language barriers, fatigue and genuine misconceptions. The bank, decision rules and graph remain provisional. Zero false diagnoses does not imply perfect accuracy when many concepts remain unresolved. No real learning gain or statistically established superiority is claimed.
