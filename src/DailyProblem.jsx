import React,{useEffect,useState} from 'react';
import {Check,Flame} from 'lucide-react';
import {studentApi} from './studentApi';
import AngleDiagram from './AngleDiagram';
import QuestionAnswer,{questionPrompt} from './StudyQuestion';

export default function DailyProblem({learner,language,nodes,compact=false,onSaved}){
  const hi=language==='hi';
  const [problem,setProblem]=useState(null),[answer,setAnswer]=useState(''),[busy,setBusy]=useState(false);
  const [error,setError]=useState(''),[reload,setReload]=useState(0);
  const nextReset=problem?.next_reset;
  useEffect(()=>{
    let live=true;
    studentApi('/learning/daily?learner='+encodeURIComponent(learner)+'&language='+language)
      .then(value=>{if(live){setProblem(value);setError('');}})
      .catch(err=>{if(live)setError(err.message);});
    return()=>{live=false;};
  },[learner,language,reload]);
  useEffect(()=>{
    if(!nextReset)return;
    const timer=setTimeout(()=>{setAnswer('');setReload(n=>n+1);},Math.max(1000,nextReset*1000-Date.now()+1000));
    return()=>clearTimeout(timer);
  },[nextReset]);
  async function submit(event){
    event.preventDefault();
    if(busy||problem.solved||!answer.trim())return;
    setBusy(true);setError('');
    try{
      const result=await studentApi('/learning/daily/answer',{learner,language,day:problem.day,question_id:problem.question.id,response:answer});
      setProblem(result);setAnswer('');
      onSaved?.();
    }catch(err){setError(err.message);}
    finally{setBusy(false);}
  }

  const locale=hi?'hi-IN':'en-IN';
  const date=new Intl.DateTimeFormat(locale,{dateStyle:'long',timeZone:'UTC'});
  const weekday=new Intl.DateTimeFormat(locale,{weekday:'short',timeZone:'UTC'});
  const weekdays=Array.from({length:7},(_,i)=>weekday.format(new Date(Date.UTC(2024,0,1+i))));
  return <section className="platform-panel daily-progress" aria-labelledby="daily-problem-heading">
    <h2 id="daily-problem-heading">{hi?'आज का सवाल':'Daily Problem'}</h2>
    {compact&&<p>{hi?'इस सवाल का सही उत्तर मेरी प्रगति में आपकी दैनिक शृंखला में गिना जाता है।':'Solving this problem counts toward your daily streak in My Progress.'}</p>}
    {error&&<p className="alert danger" role="alert">{error} <button type="button" className="text-button" onClick={()=>setReload(n=>n+1)}>{hi?'फिर लोड करें':'Reload problem'}</button></p>}
    {!problem&&!error&&<p role="status">{hi?'आज का सवाल लोड हो रहा है…':'Loading today’s problem…'}</p>}
    {problem&&<div className={compact?"daily-progress-grid daily-progress-compact":"daily-progress-grid"}>
      <div>
        <p className="daily-topic">{date.format(new Date(problem.day))} · {nodes[problem.question.concept_id]?.[language]}</p>
        <h3>{questionPrompt(problem.question)}</h3>
        {problem.question.diagram&&<AngleDiagram diagram={problem.question.diagram} language={language}/>}
        {problem.solved?<div className="daily-solved" role="status"><b><Check size={17} aria-hidden="true"/> {hi?'आज का सवाल हल हो गया':'Solved today'}</b>
          <p>{problem.feedback}</p>
        </div>:<form onSubmit={submit}>
          <QuestionAnswer value={answer} onChange={setAnswer} language={language} question={problem.question} disabled={busy} id="daily-answer"/>
          <button className="primary-button" disabled={busy||!answer.trim()}>{hi?'उत्तर जाँचें':'Check daily answer'}</button>
          {problem.attempts>0&&<p role="status">{hi?'उत्तर सही नहीं था। फिर कोशिश करें।':'Keep going. Try a different answer.'}</p>}
        </form>}
      </div>
      {!compact&&<div className="daily-streak">
        <h3><Flame size={20} aria-hidden="true"/> {hi?'लगातार अभ्यास':'Daily streak'}</h3>
        <dl className="daily-stats">
          <div><dt>{hi?'वर्तमान':'Current'}</dt><dd>{problem.current_streak}</dd></div>
          <div><dt>{hi?'सबसे लंबी':'Longest'}</dt><dd>{problem.best_streak}</dd></div>
          <div><dt>{hi?'कुल हल किए':'Total solved'}</dt><dd>{problem.total_solved}</dd></div>
        </dl>
        <div className="daily-weekdays" aria-hidden="true">{weekdays.map((name,index)=><span key={index}>{name}</span>)}</div>
        <ol className="daily-calendar" aria-label={hi?'दैनिक सवालों का कैलेंडर':'Daily Problem calendar'}>
          {problem.calendar.map(cell=>{
            const label=date.format(new Date(cell.day))+' · '+(cell.solved?(hi?'हल किया':'Solved'):(hi?'हल नहीं किया':'Unsolved'));
            return <li key={cell.day} className={cell.solved?'solved':''} aria-current={cell.day===problem.day?'date':undefined} title={label}>
              <span aria-hidden="true">{Number(cell.day.slice(-2))}{cell.solved&&<Check size={11}/>}</span><span className="sr-only">{label}</span>
            </li>;
          })}
        </ol>
        <WeeklySolves calendar={problem.calendar} language={language}/>
        <p className="field-hint">{hi?'हर दिन सही उत्तर से क्रम बढ़ता है। नया सवाल भारतीय समय के अनुसार आधी रात को आता है।':'Solve the Daily Problem on consecutive days to build your streak. A new problem opens at midnight India time.'}</p>
      </div>}
    </div>}
  </section>;
}

function WeeklySolves({calendar,language}){
  const hi=language==='hi';
  const format=new Intl.DateTimeFormat(hi?'hi-IN':'en-IN',{month:'short',day:'numeric',timeZone:'UTC'});
  const weeks=Array.from({length:Math.ceil(calendar.length/7)},(_,i)=>calendar.slice(i*7,i*7+7)).slice(-5);
  return <div className="weekly-solves">
    <h4>{hi?'हर हफ़्ते हल किए गए सवाल':'Daily problems solved by week'}</h4>
    <ol>{weeks.map(week=>{
      const day=week[0].day,count=week.filter(cell=>cell.solved).length;
      return <li key={day}><b>{count}<span className="sr-only"> {hi?'हल किए':'solved'}</span></b>
        <span className="weekly-solve-track" aria-hidden="true"><i style={{height:count/7*100+'%'}}/></span>
        <small>{format.format(new Date(day))}</small></li>;
    })}</ol>
  </div>;
}
