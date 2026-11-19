import React,{useEffect,useState} from 'react';
import {ArrowRight,CalendarDays,NotebookPen} from 'lucide-react';
import {studentApi} from './studentApi';
import QuestionAnswer,{questionPrompt} from './StudyQuestion';

export default function StudentRevision({learner,language,daily,data:curriculum,onNavigate,onPractice}){
  const hi=language==='hi';
  const [data,setData]=useState(null);
  const [error,setError]=useState('');
  const [active,setActive]=useState(null);
  const [response,setResponse]=useState('');
  const [feedback,setFeedback]=useState(null);
  const [busy,setBusy]=useState(false);
  const path='/revision?learner='+encodeURIComponent(learner);
  useEffect(()=>{
    let current=true;
    studentApi(path).then(value=>{if(current)setData(value);}).catch(err=>{if(current)setError(err.message);});
    return()=>{current=false;};
  },[path]);

  async function start(card){
    setBusy(true);setError('');
    try{
      const question=await studentApi('/revision/start',{learner,mistake:card.id});
      setResponse('');setFeedback(null);setActive({card,question});
    }catch(err){setError(err.message);}
    finally{setBusy(false);}
  }

  async function check(event){
    event.preventDefault();
    setBusy(true);setError('');
    try{
      const result=await studentApi('/revision/answer',{
        learner,mistake:active.card.id,retry:active.question.id,response
      });
      setFeedback(result);
      setData(await studentApi(path));
    }catch(err){setError(err.message);}
    finally{setBusy(false);}
  }

  const nodes=Object.fromEntries(curriculum.nodes.map(node=>[node.id,node]));
  const prerequisite=active&&curriculum.links.find(link=>link.target===active.card.concept_id&&
    nodes[link.source]&&curriculum.textbooks.concepts[link.source]?.versions?.[language])?.source;
  const incompleteTopics=new Set(data?.mistakes.filter(card=>card.due!==null).map(card=>card.concept_id));
  function completedLabel(card){
    if(incompleteTopics.has(card.concept_id))return hi?'इस प्रश्न की पुनरावृत्ति पूरी':'Question review complete';
    return hi?'विषय समझ लिया':'Topic marked understood';
  }
  const date=timestamp=>new Intl.DateTimeFormat(hi?'hi-IN':'en-IN',{dateStyle:'medium'}).format(timestamp*1000);
  return <div className="study-stack">
    <div className="platform-actions">
      <button className={daily?'primary-button':'secondary-button'} aria-pressed={daily} onClick={()=>onNavigate('revision')}>
        <CalendarDays size={17}/>{hi?'आज की पुनरावृत्ति':'Today’s revision'}
      </button>
      <button className={daily?'secondary-button':'primary-button'} aria-pressed={!daily} onClick={()=>onNavigate('notebook')}>
        <NotebookPen size={17}/>{hi?'गलतियों की कॉपी':'Mistake notebook'}
      </button>
    </div>
    {error&&<div className="alert danger" role="alert">{error}</div>}
    {active?<section className="platform-panel study-retry">
      <h2>{hi?'इसी तरह का एक प्रश्न':'Try a similar question'}</h2>
      <h3 lang={active.question.language}>{questionPrompt(active.question)}</h3>
      {feedback?<div role="status">
        <h3>{feedback.correct?(hi?'सही उत्तर':'Correct'):(hi?'फिर से कोशिश करें':'Try again')}</h3>
        <p>{feedback.explanation}</p>
        {feedback.correct&&<p>{feedback.due===null?completedLabel(active.card):
          (hi?'अगली पुनरावृत्ति ':'Next review ') + date(feedback.due)}</p>}
      </div>:<form onSubmit={check}>
        <QuestionAnswer question={active.question} value={response} onChange={setResponse} disabled={busy}
          language={language} id="revision-answer"/>
        <button className="primary-button" disabled={busy||!response.trim()}>{hi?'उत्तर जाँचें':'Check answer'}</button>
      </form>}
      <div className="platform-actions">
        <button className="text-button" disabled={busy} onClick={()=>{setActive(null);setError('');}}>
          {hi?'सूची में वापस जाएँ':'Back to the list'}
        </button>
        {prerequisite&&!feedback?.correct&&<button className="text-button" disabled={busy} onClick={()=>onPractice(prerequisite)}>
          {hi?'पहले यह विषय दोहराएँ':'Review a prerequisite'} · {nodes[prerequisite][language]}
        </button>}
      </div>
    </section>:data?<>
      {daily&&<section className="platform-panel study-summary">
        <h2>{hi?'आज की पुनरावृत्ति':'Your daily revision plan'}</h2>
        <p>{hi?`अभी ${data.due_count} प्रश्न दोहराने हैं। एक बार में अधिकतम 5 प्रश्न दिखते हैं।`:
          `${data.due_count} due now. The plan shows up to five questions at a time.`}</p>
      </section>}
      {(daily?data.daily:data.mistakes).map(card=><article className="platform-panel study-mistake" key={card.id}>
        <div className="section-title">
          <h2>{nodes[card.concept_id]?.[language]||card.concept_id}</h2>
          <span>{card.source==='practice'?(hi?'अभ्यास':'Practice'):(hi?'मॉक परीक्षा':'Mock exam')}</span>
        </div>
        <p lang={card.language}>{card.question}</p>
        <div className="study-comparison" lang={card.language}>
          <div><b>{hi?'आपका पिछला उत्तर':'Your original answer'}</b><p>{card.response}</p></div>
          <div><b>{hi?'हल और सही उत्तर':'Worked solution'}</b><p>{card.correct_answer} · {card.explanation}</p>
            {card.reference&&<a href={card.reference.url} target="_blank" rel="noreferrer">{card.reference.chapter} · {card.reference.page}</a>}
          </div>
        </div>
        <div className="platform-actions study-card-actions">
          {card.ready?<button className="primary-button" disabled={busy} onClick={()=>start(card)}>
            {hi?'मिलता-जुलता प्रश्न हल करें':'Try a similar question'}<ArrowRight size={16}/>
          </button>:<span>{card.due===null?completedLabel(card):(hi?'अगली पुनरावृत्ति ':'Next review ') + date(card.due)}</span>}
          <span>{card.streak}/3 {hi?'सही पुनरावृत्तियाँ':'successful reviews'}</span>
        </div>
      </article>)}
      {(daily?!data.daily.length:!data.mistakes.length)&&<div className="platform-panel">
        <p>{daily?(hi?'अभी कोई पुनरावृत्ति बाकी नहीं है।':'You’re caught up on today’s reviews.'):
          (hi?'अभ्यास और मॉक परीक्षा में गलत उत्तर यहाँ दिखेंगे।':'Missed answers from practice and mock exams will appear here.')}</p>
        <button className="secondary-button" onClick={()=>onNavigate('practice')}>{hi?'अभ्यास करें':'Go to practice'}</button>
      </div>}
    </>:!error&&<p role="status">{hi?'लोड हो रहा है…':'Loading your reviews…'}</p>}
  </div>;
}
