# First review: bilingual diagnostic materials

Reviewer: Codex (AI content/implementation review). Human final review: pending.

The 30 original items cover number pattern, odd number, even number, square number,
line segment, angle, right angle, acute angle, place value and digit sum. There are
three items per concept. Odd/even questions use the CH01 concept IDs; duplicate CH03
concepts are deliberately not silently merged.

First-pass checks: English/Hindi prompts have matching numbers, options and requested
operations. Arithmetic keys were recalculated. MCQ keys identify the unique intended
option. Numerical keys accept Devanagari digits and equivalent numeric representations.
Answer rules reject explanatory text as unscorable rather than treating it as incorrect.
Possible difficulties use tentative wording and acknowledge alternative explanations.

Item limitations for final review:

- Pattern items assume the simple displayed arithmetic/geometric progression. A finite
  sequence has many possible continuations; teaching convention is being assessed.
- DQ_0018_1 and DQ_0018_3 are closely related endpoint checks; they are not independent
  measurements of the full line-segment concept. Consider a reviewed diagram item later.
- Right-angle questions mainly assess recognition and recall. They do not establish
  competence in measuring or constructing angles.
- Numerical square-number questions also require multiplication. Incorrect answers
  do not uniquely establish a square-number misconception.
- Translations are a first-pass draft. A bilingual mathematics educator should check
  vocabulary, accessibility and suitability for the intended learners.
- Questions are original, not extracted from NCERT. Associated passage IDs come from
  provisional graph edges and have not been verified against source textbook text.
- The dataset includes questionable relationships (for example place value leading to
  number pattern). Pedagogical edge validation is required before educational claims.

Decision-rule review: a single wrong response cannot produce a difficulty label.
Two agreeing valid observations permit a provisional label; mixed evidence remains
insufficient even after a third question. Historical observations are displayed when
used, are version limited, and cannot label an entirely untested concept in a new report.
No inference propagates from a target response to untested prerequisites. Three
questions cannot diagnose every prerequisite; the interface makes that limitation visible.

These are transparent development rules, not psychometrically validated cutoffs.
Independent pilot expectations and the final bank/rules review remain pending.

For final review, complete reports/review_checklist.csv with reviewer, date,
approve/revise/reject and corrections. Edit approved corrections in the bank and bump
diagnostic.engine.VERSION if scoring or item meaning changes. Keep review exports in
sync. Do not rerun prepare_review.py over completed review records. Review decisions
are not automatically promoted to a production claim.
