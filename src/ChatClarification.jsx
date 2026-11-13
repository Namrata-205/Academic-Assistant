import React from 'react';

const chapters={CH01:{en:'number patterns',hi:'संख्या पैटर्न'},CH02:{en:'geometry',hi:'ज्यामिति'},CH03:{en:'number play',hi:'संख्याओं के खेल'}};
export default function ChatClarification({message,language,busy,onChoose,bank}){
  const hi=language==='hi';
  const candidates=message.candidates||[];
  const labels=candidates.map(c=>c[language]);
  const choices=candidates.length?candidates:bank.filter((q,i,all)=>all.findIndex(x=>x.concept_id===q.concept_id)===i).slice(0,4).map(q=>({id:q.concept_id,en:q.concept_en,hi:q.concept_hi}));
  return <div className="chat-topic-choice">
    <p>{hi?'आप किस बारे में पूछ रहे हैं? नीचे से चुनें या अपना सवाल थोड़ा और समझाएँ।':'I can help—pick the idea you mean, or tell me a little more in your own words.'}</p>
    <div className="chat-clarification">{choices.map(c=>{
      const duplicate=labels.filter(label=>label===c[language]).length>1;
      const chapter=chapters[c.chapter]?.[language];
      return <button className="secondary-button" disabled={busy} key={c.id} onClick={()=>onChoose(c)}>{c[language]}{duplicate&&chapter&&<small>{hi?'संदर्भ: ':'In '}{chapter}</small>}</button>;
    })}</div>
  </div>;
}
