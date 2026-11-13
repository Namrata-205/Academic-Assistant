import React,{useState,useRef} from 'react';

export default function ChatCheckBatch({questions,language,active,busy,onSend}){
  const [index,setIndex]=useState(0),[answers,setAnswers]=useState(()=>questions.map(()=>''));
  const touch=useRef(null),hi=language==='hi',hh=language==='hinglish',q=questions[index];
  const blocked=busy||!active,filled=answers.every(a=>a.trim());
  function update(value){setAnswers(old=>old.map((a,i)=>i===index?value:a));}
  function next(){if(answers[index].trim())setIndex(i=>Math.min(i+1,questions.length-1));}
  return <section className="chat-tutor-question chat-check-carousel">
    <small>{hi?'छोटा सवाल':hh?'Chhota check':'Quick check'} {index+1} / {questions.length}</small>
    <div className="check-dots">{questions.map((item,i)=><button type="button" key={item.id} disabled={blocked} aria-label={`Question ${i+1}`} aria-current={index===i?'step':undefined} onClick={()=>setIndex(i)}>{i+1}{answers[i].trim()?' ✓':''}</button>)}</div>
    <div key={q.id} className="check-slide" onTouchStart={e=>touch.current=e.touches[0].clientX} onTouchEnd={e=>{if(blocked||touch.current===null)return;const delta=e.changedTouches[0].clientX-touch.current;if(delta < -50)next();if(delta>50)setIndex(i=>Math.max(0,i-1));touch.current=null;}}>
      <p><b>{q.translations?.[language]||q.text}</b></p>
      {q.type==='mcq'&&<div className="chat-clarification">{['A','B','C','D'].filter(a=>q.text.includes(a+':')).map(a=><button type="button" className="secondary-button" aria-pressed={answers[index]===a} disabled={blocked} key={a} onClick={()=>update(a)}>{a}</button>)}</div>}
      <form className="inline-answer-form" onSubmit={e=>{e.preventDefault();if(blocked)return;if(index<questions.length-1)next();else if(filled)onSend('__check_batch__:'+JSON.stringify(answers));}}>
        <label htmlFor={'batch-'+q.id}>{hi?'आपका उत्तर':hh?'Tumhara jawab':'Your answer'}</label>
        <input id={'batch-'+q.id} value={answers[index]} disabled={blocked} maxLength={500} autoComplete="off" onChange={e=>update(e.target.value)}/>
        <div className="chat-clarification">
          <button type="button" className="secondary-button" disabled={blocked||index===0} onClick={()=>setIndex(i=>i-1)}>{hi?'पिछला':'Back'}</button>
          <button className="primary-button" disabled={blocked||!answers[index].trim()||(index===questions.length-1&&!filled)}>{index<questions.length-1?(hi?'अगला सवाल':hh?'Agla sawaal':'Next question'):(hi?'सभी उत्तर जाँचें':hh?'Saare jawab check karo':'Check all answers')}</button>
          <button type="button" className="secondary-button" disabled={blocked} onClick={()=>{update(hi?'मुझे नहीं पता':'not sure');if(index<questions.length-1)setIndex(i=>i+1);}}>{hi?'मुझे नहीं पता':hh?'Pakka nahi pata':'I’m not sure'}</button>
        </div>
      </form>
    </div>
    <small>{hi?'सभी उत्तर देने के बाद व्याख्या दिखाई जाएगी। बाएँ स्वाइप करके अगला सवाल देखें।':hh?'Saare jawab dene ke baad explanation milega. Agle sawaal ke liye left swipe karo.':'Your explanation follows after all answers are checked. Swipe left for the next question.'}</small>
  </section>;
}
