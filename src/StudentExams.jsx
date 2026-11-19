import React,{useEffect,useRef,useState} from 'react';
import {ArrowRight,Clock3,Maximize,Minimize} from 'lucide-react';
import {studentApi} from './studentApi';
import QuestionAnswer,{questionPrompt} from './StudyQuestion';

const papers=[
  ['mixed','Mixed chapters','सभी अध्याय',12,6],
  ['CH01','Patterns','पैटर्न',8,4],
  ['CH02','Lines and angles','रेखाएँ और कोण',8,4],
  ['CH03','Number play','संख्याओं के खेल',8,4],
];

export default function StudentExams({learner,language,onNavigate}){
  const hi=language==='hi';
  const [catalog,setCatalog]=useState(null),[exam,setExam]=useState(null),[mode,setMode]=useState('mixed');
  const [examLanguage,setExamLanguage]=useState(language),[index,setIndex]=useState(0),[draft,setDraft]=useState('');
  const [timer,setTimer]=useState(null),[remaining,setRemaining]=useState(0);
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[fullscreen,setFullscreen]=useState(false);
  const [focusView,setFocusView]=useState(false);
  const workspace=useRef(null);
  const learnerQuery='?learner='+encodeURIComponent(learner);
  const examId=exam?.id,finished=exam?.finished;
  const paperName=id=>papers.find(paper=>paper[0]===id)?.[hi?2:1];

  useEffect(()=>{
    let live=true;
    studentApi('/exams'+learnerQuery).then(value=>{if(live)setCatalog(value);})
      .catch(err=>{if(live)setError(err.message);});
    return()=>{live=false;};
  },[learnerQuery]);

  useEffect(()=>{
    const update=()=>setFullscreen(document.fullscreenElement===workspace.current);
    document.addEventListener('fullscreenchange',update);
    return()=>document.removeEventListener('fullscreenchange',update);
  },[]);

  useEffect(()=>{
    if(!focusView)return;
    const close=event=>{if(event.key==='Escape')setFocusView(false);};
    document.addEventListener('keydown',close);
    return()=>document.removeEventListener('keydown',close);
  },[focusView]);

  useEffect(()=>{
    if(!examId||finished!==null||timer===null)return;
    let live=true,nextSync=0,pending=false;
    async function tick(){
      const now=performance.now();
      const left=Math.max(0,Math.ceil((timer-now)/1000));
      setRemaining(left);
      if(left||pending||now<nextSync)return;
      pending=true;
      try{
        const result=await studentApi('/exams/'+examId+learnerQuery);
        if(live&&result.finished!==null){setError('');setExam(result);}
      }catch(err){if(live)setError(err.message);}
      finally{pending=false;nextSync=performance.now()+2000;}
    }
    tick();
    const interval=setInterval(tick,250);
    return()=>{live=false;clearInterval(interval);};
  },[examId,finished,timer,learnerQuery]);

  function show(result,position){
    setExam(result);setIndex(position);setDraft(result.questions[position].response);
    if(result!==exam){
      const seconds=Math.max(0,result.deadline-result.server_time);
      setRemaining(Math.ceil(seconds));setTimer(performance.now()+seconds*1000);
    }
  }

  async function open(id){
    setBusy(true);setError('');
    try{
      const result=id?await studentApi('/exams/'+id+learnerQuery):
        await studentApi('/exams',{learner,mode,language:examLanguage});
      const unanswered=result.questions.findIndex(question=>!question.response);
      show(result,result.finished===null&&unanswered>=0?unanswered:0);
    }catch(err){setError(err.message);}
    finally{setBusy(false);}
  }

  async function saveAnswer(){
    if(draft.trim()===exam.questions[index].response)return exam;
    return studentApi('/exams/'+examId+'/answer',{learner,ordinal:index,response:draft});
  }

  async function move(position){
    if(busy||remaining===0)return;
    setBusy(true);setError('');
    try{show(await saveAnswer(),position);}
    catch(err){setError(err.message);}
    finally{setBusy(false);}
  }

  async function submit(){
    if(busy||remaining===0)return;
    if(!window.confirm(hi?'परीक्षा जमा करें और परिणाम देखें?':'Submit this exam and see your results?'))return;
    setBusy(true);setError('');
    try{
      const saved=await saveAnswer();
      show(saved.finished!==null?saved:await studentApi('/exams/'+examId+'/submit',{learner}),index);
    }catch(err){setError(err.message);}
    finally{setBusy(false);}
  }

  async function toggleFullscreen(){
    if(focusView){setFocusView(false);return;}
    if(document.fullscreenElement===workspace.current){await document.exitFullscreen();return;}
    try{await workspace.current.requestFullscreen();}
    catch{setFocusView(true);}
  }

  async function list(){
    setBusy(true);setError('');
    try{
      if(exam.finished===null&&remaining>0)await saveAnswer();
      if(document.fullscreenElement===workspace.current)await document.exitFullscreen();
      setFocusView(false);setExam(null);
      setCatalog(await studentApi('/exams'+learnerQuery));
    }catch(err){setError(err.message);}
    finally{setBusy(false);}
  }

  if(!exam)return <div className="study-stack">
    {error&&<div className="alert danger" role="alert">{error}</div>}
    {!catalog&&!error&&<p role="status">{hi?'लोड हो रहा है…':'Loading mock exams…'}</p>}
    {catalog?.active?<section className="platform-panel">
      <h2>{paperName(catalog.active.mode)}</h2>
      <p>{hi?'आपकी परीक्षा जारी है। समय चलता रहता है।':'You have an exam in progress. The timer keeps running.'}</p>
      <button className="primary-button" disabled={busy} onClick={()=>open(catalog.active.id)}>
        {hi?'परीक्षा जारी रखें':'Resume exam'}<ArrowRight size={17}/>
      </button>
    </section>:catalog&&<form className="platform-panel exam-setup" onSubmit={event=>{event.preventDefault();open();}}>
      <h2>{hi?'प्रश्नपत्र चुनें':'Choose a paper'}</h2>
      <div className="exam-paper-grid">{papers.map(([id,en,hindi,minutes,questions])=><label key={id} className={mode===id?'chosen':''}>
        <input type="radio" name="paper" checked={mode===id} onChange={()=>setMode(id)}/>
        <span><b>{hi?hindi:en}</b><small>{questions} {hi?'प्रश्न':'questions'} · {minutes} {hi?'मिनट':'min'}</small></span>
      </label>)}</div>
      <label className="exam-language">{hi?'परीक्षा की भाषा':'Exam language'}
        <select value={examLanguage} onChange={event=>setExamLanguage(event.target.value)}><option value="en">English</option><option value="hi">हिंदी</option></select>
      </label>
      <p>{hi?'शुरू करते ही समय चलने लगेगा। समय पूरा होने पर सहेजे गए उत्तर जमा हो जाएँगे।':
        'The timer starts when you begin. Saved answers submit automatically when time expires.'}</p>
      <button className="primary-button" disabled={busy}>{hi?'परीक्षा शुरू करें':'Start exam'}<ArrowRight size={17}/></button>
    </form>}
    {!!catalog?.history.length&&<section className="platform-panel">
      <h2>{hi?'पिछली परीक्षाएँ':'Exam history'}</h2>
      <div className="study-next-list">{catalog.history.map(entry=><button key={entry.id} className="secondary-button"
        disabled={busy} onClick={()=>open(entry.id)}>
        <span>{paperName(entry.mode)} · {new Date(entry.finished*1000).toLocaleString(hi?'hi-IN':'en-IN')}</span>
        <b>{entry.correct}/{entry.total}</b>
      </button>)}</div>
    </section>}
  </div>;

  const question=exam.questions[index];
  const displayTime=`${String(Math.floor(remaining/60)).padStart(2,'0')}:${String(remaining%60).padStart(2,'0')}`;
  return <section ref={workspace} className={'platform-panel exam-workspace'+(focusView?' exam-focus-view':'')}>
    <div className="exam-inner">
      <div className="section-title exam-heading">
        <h2>{paperName(exam.mode)}</h2>
        <div className="platform-actions">
          {finished===null&&<span className={'exam-timer'+(remaining<60?' urgent':'')} aria-label={hi?'शेष समय':'Time remaining'}>
            <Clock3 size={18}/><span>{displayTime}</span>
          </span>}
          <button className="secondary-button" onClick={toggleFullscreen}>
            {fullscreen||focusView?<Minimize size={16}/>:<Maximize size={16}/>}
            {fullscreen||focusView?(hi?'पूर्ण स्क्रीन से बाहर':'Exit fullscreen'):(hi?'पूर्ण स्क्रीन':'Fullscreen')}
          </button>
        </div>
      </div>
      {error&&<div className="alert danger" role="alert">{error}</div>}
      {finished!==null?<div className="study-stack">
        <div className="study-summary">
          <h3>{hi?'परीक्षा परिणाम':'Exam results'} · {exam.correct}/{exam.questions.length}</h3>
          {exam.reason==='expired'&&<p>{hi?'समय पूरा हो गया। सहेजे गए उत्तर जमा किए गए।':'Time expired. Your saved answers were submitted.'}</p>}
          <div className="platform-actions">
            <button className="secondary-button" disabled={busy} onClick={list}>{hi?'सभी प्रश्नपत्र':'All papers'}</button>
            <button className="primary-button" onClick={()=>onNavigate('notebook')}>{hi?'गलतियों की कॉपी':'Mistake notebook'}</button>
          </div>
        </div>
        {exam.questions.map(item=><article key={item.ordinal} className="exam-result">
          <h3>{item.ordinal+1}. <span lang={exam.language}>{item.text}</span></h3>
          <p><b>{hi?'आपका उत्तर':'Your answer'}</b> · {item.response||(hi?'खाली':'Unanswered')} · {item.score===1?'✓':'0/1'}</p>
          <p lang={exam.language}><b>{item.correct_answer}</b> · {item.explanation}</p>
        </article>)}
      </div>:<>
        <div className="exam-pages" aria-label={hi?'प्रश्न':'Questions'}>
          {exam.questions.map((item,position)=><button key={item.ordinal} type="button"
            className={'secondary-button'+(item.response?' answered':'')} aria-current={index===position?'step':undefined}
            aria-label={`${hi?'प्रश्न':'Question'} ${position+1}, ${item.response?(hi?'सहेजा गया':'saved'):(hi?'खाली':'unanswered')}`}
            disabled={busy||remaining===0} onClick={()=>move(position)}>{position+1}</button>)}
        </div>
        <form onSubmit={event=>{event.preventDefault();move(Math.min(index+1,exam.questions.length-1));}}>
          <p>{hi?'प्रश्न':'Question'} {index+1}/{exam.questions.length}</p>
          <h3 lang={exam.language}>{questionPrompt(question)}</h3>
          <QuestionAnswer key={index} question={question} value={draft} onChange={setDraft}
            id="exam-answer" disabled={busy||remaining===0} language={language}/>
          <div className="platform-actions">
            <button type="submit" className="primary-button" disabled={busy||remaining===0}>
              {index+1===exam.questions.length?(hi?'उत्तर सहेजें':'Save answer'):(hi?'सहेजें और आगे बढ़ें':'Save & next')}
            </button>
            <button type="button" className="secondary-button" disabled={busy||remaining===0} onClick={submit}>
              {hi?'परीक्षा जमा करें':'Submit exam'}
            </button>
            <button type="button" className="text-button" disabled={busy} onClick={list}>
              {hi?'प्रश्नपत्रों पर लौटें':'Back to papers'}
            </button>
          </div>
          {draft.trim()!==question.response&&<small>{hi?'उत्तर अभी सहेजा नहीं गया है।':'This answer has unsaved changes.'}</small>}
        </form>
      </>}
    </div>
  </section>;
}
