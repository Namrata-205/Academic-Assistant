// Attributed background context, never interpreted as a scored response.
export function externalFeedback(context,report) {
  if (!context) return [];
  return context.items.slice(0,3).map(item=>{
    const current=(report?.concepts||[]).filter(c=>item.concept_ids.includes(c.concept_id)&&c.assessment==='Assessed');
    const positive=current.some(c=>c.status.startsWith('Evidence'));
    const difficulty=current.some(c=>c.status.startsWith('Possible'));
    const flagged=['confirmed','pending','inconclusive','revision'].includes(item.source_status);
    let explanation;
    if (positive&&flagged) explanation='The earlier report flagged this area, while this check supports understanding of the items asked. The reports may cover different skills and times; this does not establish improvement or rule out other difficulties.';
    else if(difficulty&&['not_supported','strength'].includes(item.source_status)) explanation='This check suggests a possible difficulty, while the earlier report gave a different signal. Keep both findings in context and use the item feedback to decide what to practise.';
    else if(flagged) explanation='This earlier finding is another reason to revisit the related idea. It does not confirm a difficulty in this check.';
    else if(item.source_status==='not_supported') explanation='The earlier report did not support a gap in this area. That is not proof of mastery, and any concepts untested here remain unassessed.';
    else if(item.source_status==='strength') explanation='The earlier report lists this area as a strength. It is useful background, not a substitute for checking the current concept.';
    else explanation='The source status is not recognised, so it has not been interpreted as either understanding or difficulty.';
    return {...item,explanation};
  });
}
