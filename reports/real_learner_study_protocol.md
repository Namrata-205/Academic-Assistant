# Real learner evaluation protocol - v1

Status: collector and analysis implemented; no real learner study has been completed.
The participant count and independent reviewer have not been supplied. A response of
"ok" to the planning question does not supply participant data or a reviewer identity.

## Before collection

1. A mathematics educator reviews the bilingual bank, graph edges and decision rules.
2. The organiser arranges applicable school/parent permission and voluntary participation.
   Use participant codes, not names; do not use generated profile aliases as study identities.
3. Prespecify the target topics, participant recruitment, exclusions and sample-size
   rationale. A convenience sample of 20 cases is preliminary, not proof of efficacy.
4. Independently review expected diagnoses using separate assessment evidence. The
   reviewer should not use the algorithm's label as the expected answer. Where practical,
   conceal the assigned method during review.

## Collection

Open `/study` on the local app. Each participant is assigned once, at random, to
fixed sequence or graph-guided selection. Assignment is persisted and resumed under
the same participant code. Each interaction uses the same frozen bank and at most
three diagnostic questions, with empty response history to avoid unequal prior evidence.
Do not enrol the same person under another code to obtain a preferred assignment.
Record dropout and actual question counts. The ordinary learner interface is unchanged.

This tests selection and diagnostic usefulness; it does not by itself show improved
learning. To study learning gains, prespecify independent pre/post transfer tasks and
have their scoring reviewed. Do not simply reuse the diagnostic questions as the only
outcome measure. Track clarity/usefulness separately from accuracy or learning gains.

## Export and review

`GET /api/study/export` exports only study sessions, including allocation, question
responses, scores, bank/graph hashes and algorithm output. No test/synthetic fixtures
are inserted into this database. Save the JSON locally. For completed cases fill:

- `reviewer`: independent reviewer's identifier;
- `review_status`: APPROVED after checking the gold labels;
- `independent_expected_statuses`: map concept ID to one of the three exact status labels.

Keep draft/unreviewed cases pending. Untested concepts must remain visible as unresolved;
do not exclude them merely to inflate accuracy. Record which concepts the independent
assessment covered. Retain disagreements rather than overwriting raw algorithm reports.

Analyse with:

```
python -m diagnostic.learner_study reviewed_export.json --output reports/real_learner_results.json
```

The analyser counts reviewed cases, correct diagnoses, false diagnoses, unresolved
concept opportunities and questions asked by method. Interpret differences alongside
target-topic mix, assignment balance, dropout, participant differences and uncertainty.
An educational-usefulness conclusion requires independent evidence and human judgement;
the analyser deliberately does not certify efficacy automatically.

No imported aggregate student CSV is passed off as a real prospective evaluation.
Retrospective replay remains a distinct source of background feedback.
