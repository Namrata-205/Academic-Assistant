import React, { useEffect, useState } from 'react';
import { ArrowRight, ArrowLeft, Check, ChevronDown, FileDown, LoaderCircle, History, RotateCcw, CircleHelp } from 'lucide-react';
import { diagnosticCoverage } from './coverage.js';
import LearnerReport from './LearnerReport.jsx';
import EarlierReportLink from './EarlierReportLink.jsx';
import LearnerQuestion from './LearnerQuestion.jsx';
import ConceptPreview from './ConceptPreview.jsx';
import ProgressHistory from './ProgressHistory.jsx';

async function request(path, body) {
  const r = await fetch('/api' + path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await r.json();
  if (!r.ok) throw Error(data.error || 'Please try again.');
  return data;
}
const examples = ['How do I identify an acute angle?', 'How do I find place value?', 'अंकों का योग कैसे निकालें?'];

export default function Learner({data}) {
  const [learner,setLearner] = useState(() => {
    let code = localStorage.getItem('atlas-learner-code');
    if (!code) {code = 'learner-' + crypto.randomUUID(); localStorage.setItem('atlas-learner-code', code);}
    return code;
  });
  const [text,setText] = useState(''), [mapping,setMapping] = useState(null), [target,setTarget] = useState(''), [session,setSession] = useState(null), [response,setResponse] = useState(''), [busy,setBusy] = useState(false), [error,setError] = useState(''), [history,setHistory] = useState(null), [topics,setTopics] = useState(false), [resetKey,setResetKey] = useState(0);
  const nodes = Object.fromEntries(data.nodes.map(n => [n.id,n]));
  const supported = [...new Map(data.bank.map(q => [q.concept_id,q])).values()];
  const covered = diagnosticCoverage(target,data.bank,data.links);
  const prerequisites = [...new Set(data.links.filter(e => e.target === target && e.source !== target).map(e => e.source))];
  const stage = session?.report ? 3 : session ? 2 : 1;
  async function act(fn) {setError('');setBusy(true);try {await fn();} catch(e) {setError(e.message);} finally {setBusy(false);}}
  function reset() {setSession(null);setMapping(null);setTarget('');setResponse('');setText('');setError('');setHistory(null);setTopics(false);localStorage.removeItem('atlas-active-session');localStorage.removeItem('atlas-active-session:'+learner);window.scrollTo({top:0,behavior:'smooth'});}
  async function clearAll() {
    if(!window.confirm('Clear all saved checks, chats and the linked earlier report for this learner on this browser? The imported CSV reports and textbook files will be kept.'))return;
    await act(async()=>{await request('/reset',{learner});reset();setResetKey(k=>k+1);});
  }

  function useTopic(id) {setTarget(id);setMapping({status:'chosen'});setTopics(false);setSession(null);}
  async function identify(e) {e?.preventDefault(); await act(async()=>{const m=await request('/map',{question:text});setMapping(m);setTarget(m.concept_id||'');});}
  async function openSession(sid) {await act(async()=>{setSession(await request(`/sessions/${sid}?learner=${encodeURIComponent(learner)}`));localStorage.setItem('atlas-active-session',sid);localStorage.setItem('atlas-active-session:'+learner,sid);setHistory(null);setResponse('');});}
  useEffect(()=>{const sid=localStorage.getItem('atlas-active-session:'+learner)||localStorage.getItem('atlas-active-session');if(sid)openSession(sid);request('/profile?learner='+encodeURIComponent(learner)).then(r=>{if(r.profile){const map=JSON.parse(localStorage.getItem('atlas-student-learners')||'{}');map[r.profile.student_id]=learner;localStorage.setItem('atlas-student-learners',JSON.stringify(map));}else if(!localStorage.getItem('atlas-guest-learner'))localStorage.setItem('atlas-guest-learner',learner);}).catch(()=>{});},[learner]);
  async function switchStudent(studentId) {
    setBusy(true);setError('');
    try {
      const map=JSON.parse(localStorage.getItem('atlas-student-learners')||'{}');
      let code=studentId===null?(localStorage.getItem('atlas-guest-learner')||'learner-'+crypto.randomUUID()):(map[studentId]||'learner-'+crypto.randomUUID());
      if(studentId!==null){const space=await request('/profile/select',{learner,student_id:studentId});code=space.learner;map[studentId]=code;localStorage.setItem('atlas-student-learners',JSON.stringify(map));}
      else localStorage.setItem('atlas-guest-learner',code);
      setSession(null);setMapping(null);setTarget('');setResponse('');setText('');setHistory(null);setTopics(false);
      localStorage.removeItem('atlas-active-session');localStorage.setItem('atlas-learner-code',code);setLearner(code);setResetKey(k=>k+1);
    } catch(e){setError(e.message);throw e;} finally{setBusy(false);}
  }
  return <div className="learner-space">
    <div className="learner-utility"><span><span className="status-dot"/> Your progress saves on this browser</span><button className="text-button" disabled={busy} onClick={()=>act(async()=>{setHistory((await request('/sessions?learner='+encodeURIComponent(learner))).sessions);})}><History size={15}/> Previous checks</button></div>
    <div className="restart-controls"><button className="secondary-button" disabled={busy} onClick={reset}><RotateCcw size={14}/> Start again</button><button className="text-button clear-progress-button" disabled={busy} onClick={clearAll}>Clear all & start again</button><span>Start again keeps history. Clear all removes saved checks for this learner.</span></div>
    <EarlierReportLink key={resetKey} learner={learner} request={request} onSelectProfile={switchStudent} disabled={busy}/>
    <ProgressHistory learner={learner} request={request} nodes={nodes} refreshKey={(session?.id||'')+':'+(session?.answered||0)+':'+(session?.report?'done':'open')+':'+resetKey} onOpen={openSession}/>
    <ol className="simple-steps" aria-label="Your progress">{['Choose what to learn','Answer up to 3 questions','See your results'].map((label,i)=><li key={label} className={stage===i+1?'current':stage>i+1?'done':''}><span>{stage>i+1?<Check size={14}/>:i+1}</span>{label}</li>)}</ol>
    {error&&<div className="alert danger" role="alert">{error}</div>}
    {history&&<section className="panel history-panel"><div className="panel-header"><h2>Your previous checks</h2><button className="text-button" onClick={()=>setHistory(null)}>Close</button></div>{history.length?history.map(s=><button className="history-entry" key={s.id} disabled={busy} onClick={()=>openSession(s.id)}><span><b>{nodes[s.target]?.en}</b><small>{new Date(s.created).toLocaleDateString()} · {s.complete?'View results':'Continue answering'}</small></span><ArrowRight size={17}/></button>):<p className="body-copy">Your completed checks will appear here. Start with a question below.</p>}</section>}
    {!session&&<section className="learner-card">
      {!mapping?<><span className="learner-kicker">LET’S FIND YOUR STARTING POINT</span><h2>What would you like to understand?</h2><p className="learner-intro">Ask a maths question in English or Hindi. We’ll help you check the ideas you need.</p><form onSubmit={identify}><label className="sr-only" htmlFor="learner-question">Your maths question</label><textarea id="learner-question" value={text} onChange={e=>setText(e.target.value)} placeholder="Type your question here… / अपना प्रश्न लिखिए…" maxLength={4000}/><div className="learner-submit"><span>No sign-up needed · English & हिंदी</span><button className="primary-button" disabled={!text.trim()||busy}>{busy?<LoaderCircle size={17} className="spin"/>:null}Continue <ArrowRight size={17}/></button></div></form><div className="example-area"><span>Not sure what to ask? Try one:</span>{examples.map(example=><button key={example} onClick={()=>setText(example)}>{example}<ArrowRight size={14}/></button>)}</div><button className="text-button topic-toggle" onClick={()=>setTopics(!topics)} aria-expanded={topics}>Or choose a topic <ChevronDown size={14}/></button>{topics&&<div className="topic-grid">{supported.map(q=><button key={q.concept_id} onClick={()=>useTopic(q.concept_id)}>{q.concept_en}<small>{q.concept_hi}</small></button>)}</div>}</>:
      <><button className="text-button back-question" onClick={()=>{setMapping(null);setTarget('');}}><ArrowLeft size={14}/> Change my question</button>
      {!target?<><h2>Which idea do you mean?</h2><p className="learner-intro">We couldn’t identify one clear concept. Choose the closest topic, or go back and add more detail.</p><div className="topic-grid">{(mapping.candidates?.length?mapping.candidates.map(id=>nodes[id]):supported.map(q=>nodes[q.concept_id])).map(n=><button key={n.id} onClick={()=>useTopic(n.id)}>{n.en}<small>{n.hi} · {n.chapter}</small></button>)}</div></>:
      <><span className="learner-kicker">YOUR TOPIC</span><h2 className="capitalize">{nodes[target]?.en}</h2><p className="topic-hindi">{nodes[target]?.hi}</p>{covered.length?<><p className="learner-intro">We’ll ask up to three short questions to see which ideas you understand and what might need another look.</p><div className="before-start"><Check size={17}/><span>There’s no timer. It’s okay to say “I’m not sure.”</span></div><button className="primary-button" disabled={busy} onClick={()=>act(async()=>{const s=await request('/sessions',{learner,target});setSession(s);localStorage.setItem('atlas-active-session',s.id);localStorage.setItem('atlas-active-session:'+learner,s.id);setResponse('');})}>{busy?<LoaderCircle size={16} className="spin"/>:null}Start my check <ArrowRight size={17}/></button></>:<><p className="learner-intro">We don’t have a check for this topic yet. Choose a related topic below if it matches your question.</p><div className="topic-grid">{supported.map(q=><button key={q.concept_id} onClick={()=>useTopic(q.concept_id)}>{q.concept_en}<small>{q.concept_hi}</small></button>)}</div></>}
      <ConceptPreview target={target} request={request}/></>}
      </>}
    </section>}
    {session?.question&&<LearnerQuestion key={session.question.id} question={session.question} answered={session.answered} response={response} setResponse={setResponse} busy={busy} onAnswer={answer=>act(async()=>{setSession(await request(`/sessions/${session.id}/answer`,{learner,question_id:session.question.id,response:answer}));setResponse('');})} onFinish={()=>act(async()=>setSession(await request(`/sessions/${session.id}/finish`,{learner})))}/>}

    {session?.report&&<LearnerReport report={session.report} nodes={nodes} onReset={reset}/>}
    <div className="learner-footnote"><CircleHelp size={14}/> A short check can suggest a starting point. It cannot assess every prerequisite.</div>
  </div>;
}
