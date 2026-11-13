import React,{useState} from 'react';
import {ArrowRight,BookOpen,MessageCircle,Target,TrendingUp,RotateCcw} from 'lucide-react';
import EarlierReportLink from './EarlierReportLink';
import PerformanceCharts from './PerformanceCharts';
import {studentApi} from './studentApi';

export default function StudentDashboard({learner,data,language,summary,onSwitch,onNavigate,onRefresh,progressOnly=false}){
  const hi=language==='hi',nodes=Object.fromEntries(data.nodes.map(n=>[n.id,n]));
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[resetKey,setResetKey]=useState(0);
  const scored=summary?.attempts.reduce((n,a)=>n+a.scorable,0)||0,correct=summary?.attempts.reduce((n,a)=>n+a.correct,0)||0;
  async function clear(){if(!confirm(hi?'इस विद्यार्थी के सभी अभ्यास, चैट और जाँच हटाएँ?':'Clear this learner’s saved practice, chats and checks? This cannot be undone.'))return;setBusy(true);try{await studentApi('/reset',{learner});localStorage.removeItem('atlas-practice:'+learner);setResetKey(k=>k+1);onRefresh();}catch(e){setError(e.message);}finally{setBusy(false);}}
  return <div className="student-dashboard">{error&&<div role="alert" className="alert danger">{error}</div>}
    {!progressOnly&&<EarlierReportLink key={learner+':'+resetKey} learner={learner} request={studentApi} onSelectProfile={onSwitch} disabled={busy} language={language}/>}
    <div className="student-stat-grid">{[
      [Target,summary?.completed_sessions||0,hi?'अभ्यास पूरे':'Practice sessions completed'],
      [BookOpen,summary?.total_answers||0,hi?'प्रश्नों के उत्तर':'Practice questions answered'],
      [TrendingUp,scored?Math.round(correct/scored*100)+'%':'—',hi?'अभ्यास में सही उत्तर':'Practice accuracy'],
      [MessageCircle,summary?.topics.length||0,hi?'विषय आज़माए':'Topics explored']
    ].map(([Icon,value,label])=><article className="student-stat" key={label}><Icon size={20}/><strong>{value}</strong><span>{label}</span></article>)}</div>
    {!progressOnly&&<div className="dashboard-action-grid"><button className="dashboard-action tutor-action" onClick={()=>onNavigate('chat')}><MessageCircle size={26}/><span><small>{hi?'समझने से शुरू करें':'START WITH UNDERSTANDING'}</small><h2>{hi?'कहाँ अटक रहे हैं?':'What’s on your mind?'}</h2><p>{hi?'अपने शिक्षक से पूछें। पहले आधार जाँचें, फिर उदाहरण से समझें।':'Ask your tutor. Check the foundations, then work through an explanation.'}</p></span><ArrowRight/></button><button className="dashboard-action practice-action" onClick={()=>onNavigate('practice')}><Target size={26}/><span><small>{hi?'थोड़ा अभ्यास, रोज़':'SMALL STEPS, EVERY DAY'}</small><h2>{hi?'कोई विषय आज़माएँ':'Find your next challenge'}</h2><p>{hi?'विषय चुनें। यहीं उत्तर दें और तुरंत प्रतिक्रिया पाएँ।':'Choose a topic, answer in the question card, and get feedback.'}</p></span><ArrowRight/></button></div>}
    <PerformanceCharts summary={summary} nodes={nodes} language={language}/>
    {progressOnly&&<section className="platform-panel"><h2>{hi?'अभ्यास का इतिहास':'Your practice history'}</h2>{summary?.attempts.length?<div className="practice-history-table"><table><thead><tr><th>{hi?'विषय':'Topic'}</th><th>{hi?'तिथि':'Date'}</th><th>{hi?'भाषा':'Language'}</th><th>{hi?'परिणाम':'Result'}</th><th>{hi?'स्थिति':'Status'}</th></tr></thead><tbody>{[...summary.attempts].reverse().map(a=><tr key={a.id}><td>{nodes[a.concept_id]?.[hi?'hi':'en']}</td><td>{new Date(a.created).toLocaleString()}</td><td>{a.language==='hi'?'हिंदी':'English'}</td><td>{a.correct}/{a.scorable}{a.accuracy!==null?` · ${a.accuracy}%`:''}</td><td>{a.completed?(hi?'पूरा':'Completed'):(hi?'जारी':'In progress')}</td></tr>)}</tbody></table></div>:<p>{hi?'अभी कोई अभ्यास नहीं हुआ।':'No practice attempts yet. Your history will appear here.'}</p>}</section>}
    {!progressOnly&&<div className="dashboard-reset"><span>{hi?'आपकी सीखने की जगह, आपके नियंत्रण में।':'Your learning space, your choice.'}</span><button className="text-button" disabled={busy} onClick={clear}><RotateCcw size={14}/>{hi?'सभी परिणाम हटाएँ':'Clear all saved results'}</button></div>}
  </div>;
}
