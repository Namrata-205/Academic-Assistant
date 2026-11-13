# Preliminary synthetic pilot comparison

Review status: expected diagnoses have NOT been independently reviewed. The human
question/rule review is also pending. These results are implementation observations,
not a final validated study and not results from learners.

Twenty separate cases were frozen before execution. Development unit examples are
stored separately in tests/test_diagnostic.py. Each case was run from empty history
under both methods, with the same question bank, eligible concepts and maximum budget
of three questions. The frozen input and bank hashes are in pilot_summary.json.

| Measure | Fixed sequence | Graph-guided |
|---|---:|---:|
| Mapping matches draft expectation | 18 / 20 | 18 / 20 |
| Concordant diagnostic labels matching synthetic profile | 10 | 10 |
| Issued diagnostic labels disagreeing with profile | 0 | 0 |
| Unresolved bank-covered concept opportunities | 17 | 17 |
| Cases with unresolved evidence or mapping | 16 / 20 | 16 / 20 |
| Total questions asked | 42 | 38 |

Mapping is shared by both methods, so it cannot explain a difference between them.
The 27 diagnostic opportunities are bank-covered targets and direct prerequisites
for cases that actually mapped. All other graph prerequisites still appear as
unassessed in interaction reports. A zero false-label count excludes unresolved
concepts and mapping failures; it must not be described as perfect diagnostic accuracy.
The six clarification outcomes have zero diagnostic questions. Five are expected
clarifications and one is an unexpected abstention. Four fewer questions arise from
the graph-guided method stopping after two concordant answers on single-concept cases;
this does not establish a general benefit from the graph itself.

## Observed errors and limits

1. P02: “समकोण कितने डिग्री का होता है?” was expected to map to right angle,
   but both right angle and degree matched. The mapper asks for clarification rather
   than silently choosing. This is an unresolved mapping, not evidence of a learner
   difficulty. Human review should decide whether the expected map is sufficiently clear.
2. P16: “भिन्नों का जोड़ कैसे करें?” matched the generic addition node, despite
   fractions being outside the graph. This is an incorrect context mapping against
   the draft expectation. The simulated unclear answers led to insufficient evidence,
   but generic term matching remains a known limitation. A production mapper needs
   reviewed coverage/intent checks or explicit learner confirmation before diagnosis.
3. Duplicate odd/even concepts occur in CH01 and CH03. P13 and P14 correctly ask the
   learner to choose a chapter; the implementation does not guess or merge their IDs.
4. P07 and P19 simulate mixed evidence. Both methods leave the relevant concepts
   insufficient rather than interpreting one wrong answer as a confirmed difficulty.
5. P08 has unscorable responses. They consume the shared budget and cannot support
   either a positive or negative knowledge label.
6. Numerous prerequisites are never tested within three questions. These stay
   unassessed, which explains the large unresolved count. No diagnosis propagates
   through the graph to those concepts.
7. P20 gives the learner a place-value difficulty with understanding of number
   patterns. The graph contains place value → number pattern, itself provisional.
   Treat this as a test of selection behavior, not validation of that relationship.

Synthetic response profiles produce answers from item keys and a preset pattern of
correct/incorrect/ambiguous responses. They do not model guessing, language barriers,
fatigue, real misconceptions or correlated items. Expectations were authored before
the run but are not an independent gold standard. No significance test is appropriate.

## Next review and study actions

Complete the question and rule review in review_checklist.csv. Have a separate reviewer
check every expected mapping and concept-level diagnosis implied by pilot_cases.json.
Obtain the actual textbook passages to validate graph references and proposed edges.
Keep this pilot result as an error record. After changes, use a newly frozen independent
case set for the final pilot; do not claim this set remains an untouched test set after
tuning to its errors. A later learner pilot should obtain responses rather than synthesize
them, and report unresolved outcomes alongside any accuracy estimate.
