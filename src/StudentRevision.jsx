import {curriculumChapters} from './curriculum';
import React,{useEffect,useState} from 'react';
import {ArrowRight,CalendarDays,NotebookPen} from 'lucide-react';
import {studentApi} from './studentApi';
import DailyProblem from './DailyProblem';
import AngleDiagram from './AngleDiagram';
import QuestionAnswer,{questionPrompt} from './StudyQuestion';

export default function StudentRevision({learner,language,daily,data:curriculum,onNavigate,onPractice}){
  const hi=language==='hi';
  const [data,setData]=useState(null);
  const [error,setError]=useState('');
  const [active,setActive]=useState(null);
  const [response,setResponse]=useState('');
  const [feedback,setFeedback]=useState(null);
  const [busy,setBusy]=useState(false);
  const [filter,setFilter]=useState('all');
  const path='/revision?learner='+encodeURIComponent(learner)+'&language='+language;
  useEffect(()=>{
    let current=true;
    setActive(null);setFeedback(null);setResponse('');
    studentApi(path).then(value=>{if(current)setData(value);}).catch(err=>{if(current)setError(err.message);});
    return()=>{current=false;};
  },[path]);

  async function start(card){
    setBusy(true);setError('');
    try{
      const question=await studentApi('/revision/start',{learner,mistake:card.id,language});
      setResponse('');setFeedback(null);setActive({card,question});
    }catch(err){setError(err.message);}
    finally{setBusy(false);}
  }

  async function check(event){
    event.preventDefault();
    setBusy(true);setError('');
    try{
      const result=await studentApi('/revision/answer',{
        learner,mistake:active.card.id,retry:active.question.id,response,language
      });
      setFeedback(result);
      setData(await studentApi(path));
    }catch(err){setError(err.message);}
    finally{setBusy(false);}
  }

  const nodes=Object.fromEntries(curriculum.nodes.map(node=>[node.id,node]));
  const prerequisite=active&&curriculum.links.find(link=>link.target===active.card.concept_id&&
    nodes[link.source]&&curriculum.textbooks.concepts[link.source]?.versions?.[language])?.source;
  const nextCard=data?.daily.find(card=>card.id!==active?.card.id);
  const visibleCards=daily?data?.daily:data?.mistakes.filter(card=>filter==='all'||
    (filter==='due'&&card.ready)||(filter==='scheduled'&&!card.ready&&card.due!==null)||(filter==='complete'&&card.due===null));
  const incompleteTopics=new Set(data?.mistakes.filter(card=>card.due!==null).map(card=>card.concept_id));
  function completedLabel(card){
    if(incompleteTopics.has(card.concept_id))return hi?'इस प्रश्न की पुनरावृत्ति पूरी':'Question review complete';
    return hi?'पुनरावृत्ति चक्र पूरा':'Review cycle complete';
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
    {daily&&!active&&<DailyProblem key={learner+language} learner={learner} language={language} nodes={nodes} compact/>}
    {error&&<div className="alert danger" role="alert">{error}<button className="text-button" onClick={()=>{setError('');studentApi(path).then(setData).catch(e=>setError(e.message));}}>{hi?'फिर प्रयास करें':'Try again'}</button></div>}
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
        {feedback&&!feedback.correct&&<button className="primary-button" disabled={busy} onClick={()=>start(active.card)}>{hi?'एक और प्रश्न आज़माएँ':'Try another question'}</button>}
        {feedback&&daily&&nextCard&&<button className="secondary-button" disabled={busy} onClick={()=>start(nextCard)}>
          {hi?'अगला प्रश्न':'Next due question'}<ArrowRight size={16}/>
        </button>}
        <button className="text-button" disabled={busy} onClick={()=>{setActive(null);setError('');}}>
          {hi?'सूची में वापस जाएँ':'Back to the list'}
        </button>
        {prerequisite&&!feedback?.correct&&<button className="text-button" disabled={busy} onClick={()=>onPractice(prerequisite)}>
          {hi?'पहले यह विषय दोहराएँ':'Review a prerequisite'} · {nodes[prerequisite][language]}
        </button>}
      </div>
    </section>:data?<>
      {daily&&<section className="platform-panel study-summary">
        <h2>{hi?'समीक्षा के लिए बाकी गलतियाँ':'Mistakes due for review'}</h2>
        <p>{hi?`अभी ${data.due_count} प्रश्न दोहराने हैं। एक बार में अधिकतम 5 प्रश्न दिखते हैं।`:
          `${data.due_count} due now. The plan shows up to five questions at a time.`}</p>
        {data.daily[0]&&<button className="primary-button" disabled={busy} onClick={()=>start(data.daily[0])}>
          {hi?'बाकी गलतियों की समीक्षा करें':'Start due reviews'}<ArrowRight size={16}/>
        </button>}
      </section>}
      {!daily&&<label className="revision-filter">{hi?'पुनरावृत्ति की स्थिति':'Review status'}<select value={filter} onChange={e=>setFilter(e.target.value)}>
        <option value="all">{hi?'सभी':'All'}</option>
        <option value="due">{hi?'अभी बाकी':'Due now'}</option>
        <option value="scheduled">{hi?'आगामी':'Upcoming'}</option>
        <option value="complete">{hi?'पूरी':'Completed'}</option>
      </select></label>}
      {visibleCards.map(card=><article className="platform-panel study-mistake" key={card.id}>
        <div className="section-title">
          <h2>{nodes[card.concept_id]?.[language]||card.concept_id}</h2>
          <span>{card.source==='practice'?(hi?'अभ्यास':'Practice'):card.source==='exam'?(hi?'मॉक परीक्षा':'Mock exam'):(hi?'सीखने की जाँच':'Learning check')}</span>
        </div>
        <p lang={card.language}>{card.question}</p>
        {card.diagram&&<AngleDiagram diagram={card.diagram} language={language}/>}
        <details className="revision-solution">
          <summary>{hi?'पिछला उत्तर और हल देखें':'View original answer and solution'}</summary>
        <div className="study-comparison" lang={card.language}>
          <div><b>{hi?'आपका पिछला उत्तर':'Your original answer'}</b><p>{card.response||(hi?'उत्तर नहीं दिया':'Unanswered')}</p></div>
          <div><b>{hi?'हल और सही उत्तर':'Worked solution'}</b><p>{card.correct_answer} · {card.explanation}</p>
            {card.reference&&<a href={card.reference.url} target="_blank" rel="noreferrer">{card.reference.chapter} · {card.reference.page}</a>}
          </div>
        </div>
        </details>
        <div className="platform-actions study-card-actions">
          {card.ready?<button className="primary-button" disabled={busy} onClick={()=>start(card)}>
            {hi?'मिलता-जुलता प्रश्न हल करें':'Try a similar question'}<ArrowRight size={16}/>
          </button>:<span>{card.due===null?completedLabel(card):(hi?'अगली पुनरावृत्ति ':'Next review ') + date(card.due)}</span>}
          <span>{card.streak}/3 {hi?'सही पुनरावृत्तियाँ':'successful reviews'}</span>
        </div>
      </article>)}
      {!visibleCards.length&&<div className="platform-panel">
        <p>{!daily&&data.mistakes.length?(hi?'इस स्थिति में कोई प्रश्न नहीं है।':'No reviews match this status.') : daily?(hi?'अभी कोई पुनरावृत्ति बाकी नहीं है।':'You’re caught up on today’s reviews.'):
          (hi?'अभ्यास और मॉक परीक्षा में गलत उत्तर यहाँ दिखेंगे।':'Missed answers from practice, learning checks, and mock exams will appear here.')}</p>
        <button className="secondary-button" onClick={()=>onNavigate('practice')}>{hi?'अभ्यास करें':'Go to practice'}</button>
        {!!data.mistakes.length&&<button className="text-button" onClick={()=>onNavigate('notebook')}>{hi?'आगामी पुनरावृत्तियाँ देखें':'View upcoming reviews'}</button>}
      </div>}
      <section className="platform-panel"><h2>{hi?'अध्याय की पुनरावृत्ति शुरू करें':'Start a chapter review'}</h2><p>{hi?'गलती दर्ज न होने पर भी किसी अध्याय का छोटा अभ्यास कर सकते हैं।':'You can revise a chapter even when no mistakes are due.'}</p><div className="revision-chapters">{curriculumChapters.map(ch=>({ch,cid:Object.values(nodes).find(n=>n.chapter===ch.id)?.id})).filter(item=>item.cid).map(({ch,cid})=><button key={cid} className="secondary-button" onClick={()=>onPractice(cid)}>{language==='hi'?ch.hi:ch.en}<ArrowRight size={16}/></button>)}</div></section>
    </>:!error&&<p role="status">{hi?'लोड हो रहा है…':'Loading your reviews…'}</p>}
  </div>;
}
