import React,{useState} from 'react';
import {ArrowRight,BookOpen,MessageCircle,Target,TrendingUp,RotateCcw} from 'lucide-react';
import ProfileOverviewLocalized from './ProfileOverviewLocalized';
import PerformanceCharts from './PerformanceCharts';
import {studentApi} from './studentApi';

export default function StudentDashboard({learner,data,language,summary,profile,onPractice,onNavigate,onRefresh,progressOnly=false}){
  const hi=language==='hi',nodes=Object.fromEntries(data.nodes.map(n=>[n.id,n]));
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const scored=summary?.attempts.reduce((n,a)=>n+a.scorable,0)||0,correct=summary?.attempts.reduce((n,a)=>n+a.correct,0)||0;
  const recentMisses = (summary?.topics || [])
    .filter(topic => topic.scorable && topic.latest_accuracy < 100)
    .sort((a,b) => a.latest_accuracy-b.latest_accuracy)
    .map(topic => ({id:topic.concept_id,reason:hi?'पिछला अभ्यास दोहराएँ':'Review your latest practice'}));
  const reportTopics = (profile?.revision_concepts || [])
    .map(id => ({id,reason:hi?'पिछली रिपोर्ट का सुझाव':'Suggested by your earlier report'}));
  const recommendations = [...recentMisses,...reportTopics]
    .filter(({id}, index, entries)=>nodes[id]&&data.textbooks.concepts[id]?.versions?.[language]&&entries.findIndex(item=>item.id===id)===index)
    .slice(0,3);
  async function clear(){if(!confirm(hi?'क्या सहेजे गए अभ्यास, चैट, जाँच, पुनरावृत्तियाँ और परीक्षाएँ हटाएँ?':'Clear saved practice, chats, checks, reviews, and exams? This cannot be undone.'))return;setBusy(true);try{await studentApi('/reset',{learner});localStorage.removeItem('atlas-practice:'+learner);onRefresh();}catch(e){setError(e.message);}finally{setBusy(false);}}
  return <div className="student-dashboard">{error&&<div role="alert" className="alert danger">{error}</div>}
    {!progressOnly&&profile&&<ProfileOverviewLocalized profile={profile} language={language}/>}
    {!progressOnly&&recommendations.length>0&&<section className="platform-panel">
      <h2>{hi?'अब क्या दोहराएँ?':'What to review next'}</h2>
      <div className="study-next-list">{recommendations.map(({id, reason})=><button className="secondary-button" key={id} onClick={()=>onPractice(id)}>
        <span>{nodes[id][language]} ? {reason}</span><ArrowRight size={16}/>
      </button>)}</div>
    </section>}
    <div className="student-stat-grid">{[
      [Target,summary?.completed_sessions||0,hi?'अभ्यास पूरे':'Practice sessions completed'],
      [BookOpen,summary?.total_answers||0,hi?'प्रश्नों के उत्तर':'Practice questions answered'],
      [TrendingUp,scored?Math.round(correct/scored*100)+'%':'—',hi?'अभ्यास में सही उत्तर':'Practice accuracy'],
      [MessageCircle,summary?.topics.length||0,hi?'विषय आज़माए':'Topics explored']
    ].map(([Icon,value,label])=><article className="student-stat" key={label}><Icon size={20}/><strong>{value}</strong><span>{label}</span></article>)}</div>
    {!progressOnly&&<div className="dashboard-action-grid"><button className="dashboard-action tutor-action" onClick={()=>onNavigate('chat')}><MessageCircle size={26}/><span><small>{hi?'समझने से शुरू करें':'START WITH UNDERSTANDING'}</small><h2>{hi?'कहाँ अटक रहे हैं?':'What’s on your mind?'}</h2><p>{hi?'अपने शिक्षक से पूछें। पहले आधार जाँचें, फिर उदाहरण से समझें।':'Ask your tutor. Check the foundations, then work through an explanation.'}</p></span><ArrowRight/></button><button className="dashboard-action practice-action" onClick={()=>onNavigate('practice')}><Target size={26}/><span><small>{hi?'थोड़ा अभ्यास, रोज़':'SMALL STEPS, EVERY DAY'}</small><h2>{hi?'कोई विषय आज़माएँ':'Find your next challenge'}</h2><p>{hi?'विषय चुनें। यहीं उत्तर दें और तुरंत प्रतिक्रिया पाएँ।':'Choose a topic, answer in the question card, and get feedback.'}</p></span><ArrowRight/></button></div>}
    {!progressOnly&&<div className="platform-actions">
      <button className="secondary-button" onClick={()=>onNavigate('revision')}>{hi?'आज की पुनरावृत्ति':'Today’s revision'}</button>
      <button className="secondary-button" onClick={()=>onNavigate('notebook')}>{hi?'गलतियों की कॉपी':'Mistake notebook'}</button>
      <button className="secondary-button" onClick={()=>onNavigate('exams')}>{hi?'मॉक परीक्षा दें':'Take a mock exam'}</button>
    </div>}
    <PerformanceCharts summary={summary} nodes={nodes} language={language}/>
    {progressOnly&&<section className="platform-panel"><h2>{hi?'अभ्यास का इतिहास':'Your practice history'}</h2>{summary?.attempts.length?<div className="practice-history-table"><table><thead><tr><th>{hi?'विषय':'Topic'}</th><th>{hi?'तिथि':'Date'}</th><th>{hi?'भाषा':'Language'}</th><th>{hi?'परिणाम':'Result'}</th><th>{hi?'स्थिति':'Status'}</th></tr></thead><tbody>{[...summary.attempts].reverse().map(a=><tr key={a.id}><td>{nodes[a.concept_id]?.[hi?'hi':'en']}</td><td>{new Date(a.created).toLocaleString()}</td><td>{a.language==='hi'?'हिंदी':'English'}</td><td>{a.correct}/{a.scorable}{a.accuracy!==null?` · ${a.accuracy}%`:''}</td><td>{a.completed?(hi?'पूरा':'Completed'):(hi?'जारी':'In progress')}</td></tr>)}</tbody></table></div>:<p>{hi?'अभी कोई अभ्यास नहीं हुआ।':'No practice attempts yet. Your history will appear here.'}</p>}</section>}
    {!progressOnly&&<div className="dashboard-reset"><span>{hi?'आपकी सीखने की जगह, आपके नियंत्रण में।':'Your learning space, your choice.'}</span><button className="text-button" disabled={busy} onClick={clear}><RotateCcw size={14}/>{hi?'सभी परिणाम हटाएँ':'Clear all saved results'}</button></div>}
  </div>;
}
