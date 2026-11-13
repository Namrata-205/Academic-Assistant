// Feedback describes the actual item response; it does not change diagnostic rules.
const facts = {
  '0003_1': ['Continue the pattern by adding 3.', '3, 6, 9, 12, 15: each step adds 3.'],
  '0003_2': ['Continue a pattern by doubling.', '2, 4, 8, 16, 32: each number is twice the previous one.'],
  '0003_3': ['Continue a pattern by subtracting 3.', '20, 17, 14, 11, 8: each step subtracts 3.'],
  '0006_1': ['Identify an odd number.', '15 is odd: dividing it by 2 leaves a remainder of 1.'],
  '0006_2': ['Identify an odd number.', '37 is odd: its units digit is 7. Odd integers end in 1, 3, 5, 7 or 9.'],
  '0006_3': ['Identify an odd number.', '51 is odd: its units digit is 1.'],
  '0007_1': ['Identify an even number.', '28 is even because 28 ÷ 2 = 14, with no remainder.'],
  '0007_2': ['Identify an even number.', '56 is even: its units digit is 6. Even integers end in 0, 2, 4, 6 or 8.'],
  '0007_3': ['Identify an even number.', '60 is even because it is divisible by 2.'],
  '0009_1': ['Count dots in a square array.', 'Four rows of four dots give 4 × 4 = 16 dots.'],
  '0009_2': ['Find the square of a number.', '7 squared means 7 × 7 = 49, not 7 + 7.'],
  '0009_3': ['Recognise a square number.', '25 is a square number because 5 × 5 = 25.'],
  '0018_1': ['Count a line segment’s endpoints.', 'A line segment has exactly two endpoints.'],
  '0018_2': ['Distinguish a segment from a line or ray.', 'A segment has two endpoints and a fixed length. A ray extends indefinitely in one direction; a line in both.'],
  '0018_3': ['Identify the endpoints of a segment.', 'A and B name the two endpoints of segment AB.'],
  '0020_1': ['Identify the two arms of an angle.', 'An angle has two arms: two rays that share an endpoint.'],
  '0020_2': ['Name the vertex of an angle.', 'The common endpoint of an angle’s two arms is called its vertex. It is not a length.'],
  '0020_3': ['Recognise how an angle is formed.', 'Two rays with a common endpoint form an angle. Two separate points alone do not form its arms.'],
  '0024_1': ['Recall the size of a right angle.', 'A right angle measures exactly 90 degrees.'],
  '0024_2': ['Recognise a right angle.', '90° is a right angle. 45° and 60° are acute; 120° is obtuse.'],
  '0024_3': ['Recognise a square’s corner angle.', 'Every corner of a square is a right angle, measuring 90°.'],
  '0025_1': ['Recognise an acute angle.', '35° is acute because it is greater than 0° and less than 90°.'],
  '0025_2': ['Compare an angle with 90 degrees.', '70° is acute. 90° is a right angle and 100° is obtuse.'],
  '0025_3': ['Use the boundaries for an acute angle.', 'An acute angle is strictly greater than 0° and strictly less than 90°; 90° itself is not acute.'],
  '0038_1': ['Identify the value of a digit in the hundreds place.', 'In 3452, the 4 is in the hundreds place: 4 × 100 = 400.'],
  '0038_2': ['Identify the value of a digit in the hundreds place.', 'In 5721, the 7 is in the hundreds place: 7 × 100 = 700.'],
  '0038_3': ['Identify the value of a digit in the tens place.', 'In 268, the 6 is in the tens place: 6 × 10 = 60.'],
  '0039_1': ['Add digits without using their place values.', 'For 352, add 3 + 5 + 2 = 10.'],
  '0039_2': ['Include zero correctly when adding digits.', 'For 409, add 4 + 0 + 9 = 13.'],
  '0039_3': ['Add every digit once.', 'For 1263, add 1 + 2 + 6 + 3 = 12.'],
};
export function reportInsights(report) {
  const assessed = report.concepts.filter(c => c.assessment === 'Assessed');
  const observations = assessed.flatMap(c => c.observations.map(o => ({...o, concept_id:c.concept_id})));
  const current = observations.filter(o => o.evidence_origin !== 'saved history');
  const explain = o => {
    const fact = facts[o.question_id.replace(/^DQ_/, '')];
    return {...o, skill:fact?.[0] || o.question_en, explanation:fact?.[1] || `The correct answer to this item is ${o.correct_answer}.`};
  };
  return {
    assessed,
    correct:current.filter(o => o.score === 1).map(explain),
    revisit:current.filter(o => o.score === 0).map(explain),
    uncertain:current.filter(o => o.score == null).map(explain),
    historicalCount:observations.length-current.length,
    targetAssessed:assessed.some(c => c.concept_id === report.target),
    unassessed:report.concepts.filter(c => c.assessment !== 'Assessed'),
    sourceIds:[...new Set(report.concepts.flatMap(c => c.references.flatMap(r => (r.passage_ids||'').split(';').map(s=>s.trim()).filter(Boolean))))],
  };
}
