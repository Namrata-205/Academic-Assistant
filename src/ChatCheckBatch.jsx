import React,{useState,useRef} from 'react';
import QuestionAnswer,{questionPrompt} from './StudyQuestion';

export default function ChatCheckBatch({questions,results,language,active,busy,onSend,onSkip}){
  const [index,setIndex]=useState(0),[answers,setAnswers]=useState(()=>questions.map(q=>results?.find(r=>r.question_id===q.id)?.response||''));
  const touch=useRef(null),hi=language==='hi',q=questions[index];
  const submitted=!!results?.length,blocked=busy||!active||submitted,filled=answers.every(a=>a.trim());
  const result=results?.find(r=>r.question_id===q.id);
  const shown={...q,text:q.translations?.[language]||q.text};
  function update(value){setAnswers(old=>old.map((a,i)=>i===index?value:a));}
  function next(){if(answers[index].trim()||submitted)setIndex(i=>Math.min(i+1,questions.length-1));}
  return <section className="chat-tutor-question chat-check-carousel" data-question-id={questions[0].id}>
    <small>{hi?'छोटी जाँच':'Quick check'} {index+1} / {questions.length}</small>
    <div className="check-dots">{questions.map((item,i)=><button type="button" key={item.id} disabled={busy||(!active&&!submitted)} aria-label={`Question ${i+1}`} aria-current={index===i?'step':undefined} onClick={()=>setIndex(i)}>{i+1}{(answers[i].trim()||submitted)?' ✓':''}</button>)}</div>
    <div key={q.id} className="check-slide" onTouchStart={e=>touch.current=e.touches[0].clientX} onTouchEnd={e=>{if(busy||touch.current===null)return;const delta=e.changedTouches[0].clientX-touch.current;if(delta < -50)next();if(delta>50)setIndex(i=>Math.max(0,i-1));touch.current=null;}}>
      <p><b>{questionPrompt(shown)}</b></p>
      <form className="inline-answer-form" onSubmit={e=>{e.preventDefault();if(blocked)return;if(index<questions.length-1)next();else if(filled)onSend('__check_batch__:'+JSON.stringify(answers));}}>
        <QuestionAnswer question={shown} value={result?.response||answers[index]} onChange={update} disabled={blocked} language={language} id={'batch-'+q.id}/>
        {!submitted&&<div className="chat-clarification">
          <button type="button" className="secondary-button" disabled={blocked||index===0} onClick={()=>setIndex(i=>i-1)}>{hi?'पिछला':'Back'}</button>
          <button className="primary-button" disabled={blocked||!answers[index].trim()||(index===questions.length-1&&!filled)}>{index<questions.length-1?(hi?'अगला सवाल':'Next question'):(hi?'उत्तर जाँचें':'Check all answers')}</button>
          <button type="button" className="secondary-button" disabled={blocked} onClick={()=>{update(hi?'मुझे नहीं पता':'not sure');if(index<questions.length-1)setIndex(i=>i+1);}}>{hi?'मुझे नहीं पता':'I’m not sure'}</button>
        </div>}
      </form>
      {result&&<div className="chat-quiz-feedback" role="status"><b>{result.score===1?(hi?'सही उत्तर':'Correct'):result.score===0?(hi?'फिर समझें':'Let’s review'):(hi?'अभी पक्का नहीं':'Not sure yet')}</b><p>{result.explanation}</p></div>}
    </div>
    {!submitted&&<button className="text-button" disabled={busy||!active} onClick={onSkip}>{hi?'जाँच छोड़ें और समझाएँ':'Skip check and explain'}</button>}
  </section>;
}
