# Knowledge graph v2 vs v1

Same measures, same chapter 1-5 clean text, for both graphs. "Name occurs" is a strict check of the concept label itself (prior-knowledge roots excluded).

| Measure | v1 | v2 |
| --- | ---: | ---: |
| Concepts (all) | 53 | 85 |
| Chapters with concepts (of 5) | 3 | 5 |
|   concepts in CH01 | 15 | 19 |
|   concepts in CH02 | 21 | 20 |
|   concepts in CH03 | 17 | 11 |
|   concepts in CH04 | 0 | 10 |
|   concepts in CH05 | 0 | 15 |
| Sections (of 40) where a concept name occurs | 29 | 37 |
| English name occurs in its chapter text | 75% | 84% |
| Hindi name occurs in its Hindi chapter text | 75% | 96% |
| Duplicate concept names | 3 | 0 |
| Prerequisite edges | 307 | 140 |
| Nodes on a prerequisite cycle | 7 | 0 |
| Edges inside a cycle | 13 | 0 |
| Edges citing a textbook location | 90% | 59% |

## v1 names not found in the text

- English: Kaprekar number, Virahanka numbers, arm of angle, complete angle, consecutive number, intersecting lines, magic square, natural number, number pattern, parallel lines, place value, rounding, visual pattern
- Hindi: Kaprekar number / कापरेकर संख्या, consecutive number / क्रमागत संख्या, intersecting lines / प्रतिच्छेदी रेखाएँ, magic square / जादुई वर्ग, natural number / प्राकृत संख्या, number pattern / संख्या पैटर्न, parallel lines / समांतर रेखाएँ, perpendicular / लंबवत रेखाएँ, place value / स्थानीय मान, rounding / निकटतम मान तक पूर्णांकन, shape pattern / आकृति पैटर्न, subtraction / घटाव, visual pattern / दृश्य पैटर्न

## v2 names not found in the text

- English: angle as amount of turn, arms of an angle, complete angle (full turn), divisibility tests for 2, 5 and 10, divisibility tests for 4 and 8, drawing angles of a given measure, number pattern, quick sums using number patterns, scale or key of a graph, vertex of an angle, vertical and horizontal bar graphs, winning strategy in number games
- Hindi: divisibility tests for 2, 5 and 10 / 2, 5 और 10 से विभाज्यता की जाँच, divisibility tests for 4 and 8 / 4 और 8 से विभाज्यता की जाँच, perpendicular lines / लंब रेखाएँ

v2 misses are descriptive labels whose textbook term is an anchor (e.g. "vertex of an angle" → "vertex"), and लंब रेखाएँ, which the Hindi extraction prints as "लब रेखाएँ".

## Duplicates in v1

- pattern: MATH6_C0002, MATH6_C0049
- odd number: MATH6_C0006, MATH6_C0044
- even number: MATH6_C0007, MATH6_C0045

## Limits

- v2 is AI-authored from the text; prerequisite edges await human review, like v1.
- Finding a name in the text shows grounding, not that the prerequisite direction is pedagogically right.
- The app still loads v1; switching it to v2 is a separate decision (IDs used by the bank are kept in v2).
