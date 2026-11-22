import React from 'react';
const statuses={'Evidence supports understanding':'जवाब समझ का समर्थन करते हैं','Possible prerequisite difficulty':'आधारभूत विषय में संभावित कठिनाई','Insufficient evidence':'पर्याप्त जानकारी नहीं','Unassessed':'जाँचा नहीं गया'};
export default function LearningContextLocalized({context,language='en',nodes={}}){
  if(!context)return null;const hi=language==='hi',name=c=>nodes[c.concept_id]?.[hi?'hi':'en']||c.concept;
  const foundations=context.prerequisites.filter(c=>c.selected_for_explanation),checked=context.learning_evidence.filter(c=>c.status!=='Unassessed');
  return <details className="chat-source-details"><summary>{hi?'इस उत्तर में आपकी सीख का उपयोग कैसे हुआ':'How this answer uses your learning'}</summary>
    {foundations.length>0&&<p>{hi?'शामिल आधारभूत विषय: ':'Foundations included: '}{foundations.map(name).join(', ')}.</p>}
    {checked.length?checked.map(c=><p key={c.concept_id}><b>{name(c)}</b>: {hi?statuses[c.status]||c.status:c.status} ({c.valid_observations} {hi?'हाल में सहेजे गए, जाँचे जा सकने वाले उत्तर':'scored observations in recent saved checks'}).</p>):<p>{hi?'इस विषय और उसकी सीधी आधारभूत बातों के लिए सहेजे गए उत्तर उपलब्ध नहीं हैं। कोई कमजोरी मानकर नहीं चले हैं।':'No saved answer evidence for this topic and its direct foundations. No weakness is assumed.'}</p>}
    {context.imported_background.map((c,i)=><p key={i}><b>{hi?'पहली रिपोर्ट — ':'Earlier report — '}{hi?c.concept_ids.map(cid=>nodes[cid]?.hi||'संबंधित विषय').join(', '):c.topic}:</b> {hi?'यह पहले की रिपोर्ट की पृष्ठभूमि है, इस बातचीत से निकला निदान नहीं।':c.source_signal+'. This is background, not a diagnosis from this chat.'}</p>)}
    {(context.activity_evidence||[]).map(c=><p key={'activity-'+c.concept_id}><b>{name(c)}</b>: {c.correct} {hi?'सही':'correct'}, {c.incorrect} {hi?'गलत':'incorrect'}, {c.observations-c.correct-c.incorrect} {hi?'अस्पष्ट उत्तर। अभ्यास और परीक्षा से पुनरावृत्ति की सहायता मिलती है, निदान नहीं।':'unscored responses. Practice and exams guide review, not diagnosis.'}</p>)}
    {(context.activity_evidence||[]).map(c=><p key={'activity-'+c.concept_id}><b>{name(c)}</b>: {c.correct} {hi?'सही':'correct'}, {c.incorrect} {hi?'गलत':'incorrect'}, {c.observations-c.correct-c.incorrect} {hi?'अस्पष्ट उत्तर। अभ्यास और परीक्षा से पुनरावृत्ति की सहायता मिलती है, निदान नहीं।':'unscored responses. Practice and exams guide review, not diagnosis.'}</p>)}
    <small>{hi?'सहेजे गए उत्तर सीमित जानकारी देते हैं, पूर्ण दक्षता का प्रमाण नहीं। आयातित रिपोर्ट अलग पृष्ठभूमि है; उसकी जाँच की तिथियाँ नहीं मिली हैं। ग्राफ संबंधों की मानवीय समीक्षा बाकी है। जिन विषयों को नहीं जाँचा गया, उन्हें कमजोर नहीं मानते।':context.notice}</small>
  </details>;
}
