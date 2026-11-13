import React from 'react';

export default function ChatLearningContext({context}){
  if(!context)return null;
  const foundations=context.prerequisites.filter(c=>c.selected_for_explanation);
  const checked=context.learning_evidence.filter(c=>c.status!=='Unassessed');
  return <details className="chat-source-details"><summary>How this answer uses your learning</summary>
    {foundations.length>0&&<p>Foundations included: {foundations.map(c=>c.concept).join(', ')}.</p>}
    {checked.length?checked.map(c=><p key={c.concept_id}><b>{c.concept}</b>: {c.status} ({c.valid_observations} scored observations in recent saved checks).</p>):<p>No saved answer evidence for this topic and its direct foundations. No weakness is assumed.</p>}
    {context.imported_background.map((c,i)=><p key={i}><b>Earlier report — {c.topic}:</b> {c.source_signal}. This is background, not a diagnosis from this chat.</p>)}
    <small>{context.notice}</small>
  </details>;
}
