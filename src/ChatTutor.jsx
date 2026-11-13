import React,{useEffect,useState} from 'react';
import ChatCheckBatch from './ChatCheckBatch';

export default function ChatTutor({message,language,active,busy,onSend,practiceOnly=false,nodes={}}){
  const hi=language==='hi',hh=language==='hinglish',q=practiceOnly?message.practice_question:message.check_question,blocked=busy||!active;
  const [answer,setAnswer]=useState('');
  useEffect(()=>setAnswer(''),[q?.id]);
  if(!practiceOnly&&message.check_questions?.length)return <ChatCheckBatch questions={message.check_questions} language={language} active={active} busy={busy} onSend={onSend}/>;
  return <>
    {!practiceOnly&&message.tutor_summary&&<div className="chat-tutor-summary"><b>{hi?'आपके जवाबों से शुरुआत':'Your starting point'}</b>
      <p>{message.tutor_summary.questions_asked} {hi?'छोटे सवाल जाँचे गए।':'short questions checked.'}</p>
      {message.tutor_summary.concepts.filter(c=>c.status!=='Unassessed').map(c=><p key={c.concept_id}><b>{nodes[c.concept_id]?.[hi?'hi':'en']||c.concept}</b> — {c.status==='Possible prerequisite difficulty'?(hi?'इसे फिर समझते हैं':'Let’s revisit this'):c.status==='Evidence supports understanding'?(hi?'जवाब समझ का समर्थन करते हैं':'Your answers support understanding'):(hi?'और जानकारी चाहिए':'More evidence needed')}</p>)}
      <details><summary>{hi?'अपने जवाब देखें':'See your answers'}</summary>{message.tutor_summary.answers.map((a,i)=><p key={i}>{a.question}<br/>{hi?'आपका उत्तर':'Your answer'}: {a.response} · {a.score===null?(hi?'अस्पष्ट':'Unscored'):a.score+'/1'}</p>)}</details>
      <small>{hi?'जिन बातों को नहीं जाँचा गया, उनके बारे में कोई निष्कर्ष नहीं है।':'Untested foundations remain unassessed. A short check is not proof of mastery.'}</small>
    </div>}
    {q&&<section className="chat-tutor-question">
      <small>{message.check_question?(hi?`छोटा सवाल ${message.check_number} / 3`:hh?`Chhota check ${message.check_number} / 3`:`Quick check ${message.check_number} / 3`):(hi?'आपके लिए नया अभ्यास':hh?'Ab yeh practice try karo':'A new practice question for you')}</small>
      <p><b>{q.translations?.[language]||q.text}</b></p>
      {message.practice_question&&<small>{q.concept_names?.[hi?'hi':'en']||q.concept}</small>}
      {q.type==='mcq'&&<div className="chat-clarification">{['A','B','C','D'].filter(letter=>q.text.includes(letter+':')).map(letter=><button key={letter} disabled={blocked} className="secondary-button" onClick={()=>onSend(letter)}>{letter}</button>)}</div>}
      <form className="inline-answer-form" onSubmit={e=>{e.preventDefault();if(answer.trim()&&!blocked)onSend(answer.trim());}}>
        <label htmlFor={'answer-'+q.id}>{hi?'आपका उत्तर':hh?'Tumhara jawab':'Your answer'}</label>
        <div><input id={'answer-'+q.id} disabled={blocked} value={answer} onChange={e=>setAnswer(e.target.value)} maxLength={500} placeholder={hi?'यहीं अपना उत्तर लिखें':hh?'Yahin apna jawab likho':'Type your answer here'} autoComplete="off"/><button className="primary-button" disabled={blocked||!answer.trim()}>{hi?'उत्तर भेजें':hh?'Jawab check karo':'Check answer'}</button></div>
      </form>
      <div className="chat-clarification"><button disabled={blocked} className="secondary-button" onClick={()=>onSend(hi?'मुझे नहीं पता':'not sure')}>{hi?'मुझे नहीं पता':hh?'Abhi pakka nahi pata':'I’m not sure'}</button>
      {message.check_question&&<button disabled={blocked} className="secondary-button" onClick={()=>onSend('__explain_now__')}>{hi?'अभी समझाइए':hh?'Ab samjhao':'Explain now'}</button>}</div>
      {message.practice_notice&&<small>{hi?'यह नया बनाया गया अभ्यास है, NCERT से हूबहू लिया गया प्रश्न नहीं।':'Newly created practice, not an actual NCERT exercise. It does not change your diagnosis.'}</small>}
    </section>}
  </>;
}
