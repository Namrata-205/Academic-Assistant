import React,{useEffect,useState} from 'react';
import ChatCheckBatch from './ChatCheckBatch';
import AngleDiagram from './AngleDiagram';
import QuestionAnswer,{questionPrompt} from './StudyQuestion';

export default function ChatTutor({message,language,active,busy,onSend,onAnswer=onSend,practiceOnly=false,nodes={}}){
  const hi=language==='hi',hh=language==='hinglish',q=practiceOnly?message.practice_question:message.check_question,blocked=busy||!active;
  const feedback=message.quiz_feedback?.find(r=>r.question_id===q?.id);
  const [answer,setAnswer]=useState('');
  const displayQuestion=q?{...q,text:q.translations?.[language]||q.text}:null;
  useEffect(()=>setAnswer(feedback?.response||''),[q?.id,feedback?.response]);
  if(!practiceOnly&&message.check_questions?.length)return <ChatCheckBatch questions={message.check_questions} results={message.quiz_feedback} language={language} active={active} busy={busy} onSend={onAnswer} onSkip={()=>onSend('__explain_now__')}/>;
  return <>
    {q&&<section className="chat-tutor-question" data-question-id={q.id}>
      <small>{message.check_question?(hi?`छोटा सवाल ${message.check_number} / 3`:hh?`Chhota check ${message.check_number} / 3`:`Quick check ${message.check_number} / 3`):(hi?'आपके लिए नया अभ्यास':hh?'Ab yeh practice try karo':'A new practice question for you')}</small>
      <p><b>{questionPrompt(displayQuestion)}</b></p>
      {q.diagram&&<AngleDiagram diagram={q.diagram} language={language}/>}
      {message.practice_question&&<small>{q.concept_names?.[hi?'hi':'en']||q.concept}</small>}
      <form className="inline-answer-form" onSubmit={e=>{e.preventDefault();if(answer.trim()&&!blocked&&!feedback)onAnswer(answer.trim());}}>
        <QuestionAnswer question={displayQuestion} value={answer} onChange={setAnswer} disabled={blocked||!!feedback} language={language} id={'answer-'+q.id}/>
        {!feedback&&<button className="primary-button" disabled={blocked||!answer.trim()}>{hi?'उत्तर भेजें':hh?'Jawab check karo':'Check answer'}</button>}
      </form>
      {!feedback&&<div className="chat-clarification"><button disabled={blocked} className="secondary-button" onClick={()=>onAnswer(hi?'मुझे नहीं पता':'not sure')}>{hi?'मुझे नहीं पता':hh?'Abhi pakka nahi pata':'I’m not sure'}</button>
      {message.check_question&&<button disabled={blocked} className="secondary-button" onClick={()=>onSend('__explain_now__')}>{hi?'अभी समझाइए':hh?'Ab samjhao':'Explain now'}</button>}</div>}
      {feedback&&<div className="chat-quiz-feedback" role="status"><b>{feedback.score===1?(hi?'सही उत्तर':hh?'Bilkul sahi':'Correct'):feedback.score===0?(hi?'फिर समझें':hh?'Chalo, dobara samjhein':'Let’s review'):(hi?'अभी पक्का नहीं':hh?'Abhi pakka nahi':'Not sure yet')}</b><p>{feedback.explanation}</p></div>}
      {feedback?.next_action&&<div className="chat-quiz-feedback">
        <b>{hi?'आपका अगला कदम':'Your next step'}</b>
        <p>{{compare_angles:hi?'चित्र में कोण सही पहचाना। अब दोनों कोणों के माप की तुलना करें।':'You identified the angle. Now compare the two angle measures.',
          review_half_turn:hi?'घड़ी की सुई से आधा घुमाव समझें।':'Use a clock hand to work through a half-turn.',
          another_example:hi?'अब एक अलग उदाहरण आज़माएँ।':'Build on that answer with a different example.',
          review:hi?'इस विचार को सरल चरणों में फिर समझें।':'Revisit this idea in smaller steps.'}[feedback.next_action]}</p>
        {active&&<button className="secondary-button" disabled={busy} onClick={()=>onSend(
          {compare_angles:'__angle_compare__',review_half_turn:'__feedback__:another_example',another_example:'__feedback__:another_example',review:'__feedback__:still_confused'}[feedback.next_action])}>
          {{compare_angles:hi?'माप की तुलना करें':'Compare angle measures',review_half_turn:hi?'आधा घुमाव समझें':'Review a half-turn',
            another_example:hi?'नया उदाहरण':'Try another example',review:hi?'फिर समझें':'Review the idea'}[feedback.next_action]}
        </button>}
      </div>}
      {message.practice_notice&&<small>{hi?'यह नया अभ्यास है। उत्तर आगे की सहायता के लिए सहेजा जाता है; एक उत्तर से समझ सिद्ध नहीं होती।':'Original practice. Your answer is saved as follow-up evidence; one answer does not establish understanding.'}</small>}
    </section>}

  </>;
}

export function ChatFeedback({message,language,active,busy,onSend}){
  const hi=language==='hi',hh=language==='hinglish',blocked=busy||!active;
  if(!message.feedback_actions?.length)return null;
  return (<div className="chat-clarification" aria-label={hi?'अगला कदम':'Next step'}>
      {['simpler','another_example','still_confused','language_help'].filter(action=>message.feedback_actions.includes(action)).map(action=><button className="secondary-button" disabled={blocked} key={action} onClick={()=>onSend('__feedback__:'+action)}>
        {{simpler:hi?'सरल भाषा में समझाइए':hh?'Aur simple tareeke se samjhao':'Simpler explanation',another_example:hi?'एक और उदाहरण':hh?'Ek aur example dikhao':'Show another example',still_confused:hi?'अभी भी समझ नहीं आया':hh?'Abhi bhi samajh nahi aaya':'I still don’t understand',language_help:hi?'शब्दों का अर्थ समझाइए':hh?'Terms ka matlab samjhao':'Explain the terms'}[action]}
      </button>)}
    </div>);
}
