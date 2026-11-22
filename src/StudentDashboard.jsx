import {curriculumChapters,chapterTitle} from './curriculum';
import React,{useState} from 'react';
import {ArrowRight,BookOpen,MessageCircle,Target,TrendingUp,RotateCcw,CalendarDays,ClipboardList,Network,RefreshCw} from 'lucide-react';
import ProfileOverviewLocalized from './ProfileOverviewLocalized';
import DailyProblem from './DailyProblem';
import PerformanceCharts from './PerformanceCharts';
import {studentApi} from './studentApi';

export default function StudentDashboard({learner,data,language,summary,summaryState='ready',profile,nextStep,onTutor,onPractice,onChapter,onNavigate,onExam,onRefresh,progressOnly=false}){
  const hi=language==='hi',nodes=Object.fromEntries(data.nodes.map(n=>[n.id,n])),attempts=summary?.attempts||[];
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const [checkTopic,setCheckTopic]=useState('');
  const nextNode=nodes[nextStep?.concept_id];
  const checkOptions=[...new Set(data.bank.map(q=>q.concept_id))]
    .map(id=>nodes[id]).filter(node=>node&&data.textbooks.concepts[node.id]?.versions?.[language])
    .sort((a,b)=>a[language].localeCompare(b[language],language));
  const overview=summary?.overview;
  const overviewStats=[
    [Target,overview?.completed??'—',hi?'अभ्यास, परीक्षाएँ और दैनिक सवाल पूरे':'Practice, exams and daily solves','teal'],
    [BookOpen,overview?.answers??'—',hi?'जमा किए गए उत्तर':'Answers submitted','blue'],
    [TrendingUp,overview?.accuracy==null?'—':overview.accuracy+'%',hi?'जाँचे गए उत्तरों में सही':'Answer accuracy','orange'],
    [Network,overview?.topics??'—',hi?'विषय आज़माए':'Topics attempted','purple']
  ];
  const resume=[...attempts].reverse().find(a=>!a.completed);
  const recentMisses=(summary?.topics||[]).filter(t=>t.scorable&&t.latest_accuracy<100).sort((a,b)=>a.latest_accuracy-b.latest_accuracy)
    .map(t=>({id:t.concept_id,reason:hi?'पिछला अभ्यास दोहराएँ':'Review your latest practice'}));
  const recommendations=[...recentMisses,...(profile?.revision_concepts||[]).map(id=>({id,reason:hi?'पिछली रिपोर्ट का सुझाव':'Suggested by your earlier report'}))]
    .filter(({id},i,all)=>nodes[id]&&data.textbooks.concepts[id]?.versions?.[language]&&all.findIndex(item=>item.id===id)===i).slice(0,3);
  function continuePractice(){if(resume)localStorage.setItem('atlas-practice:'+learner,resume.id);else localStorage.removeItem('atlas-practice:'+learner);onNavigate('practice');}
  async function clear(){if(!confirm(hi?'सहेजे गए अभ्यास, चैट, जाँच, दैनिक सवाल, पुनरावृत्तियाँ, परीक्षाएँ और पुराने प्रश्नपत्र हटाएँ? इसे वापस नहीं लाया जा सकता।':'Clear saved practice, chats, checks, daily problem history, reviews, exams, and uploaded past papers? This cannot be undone.'))return;setBusy(true);try{await studentApi('/reset',{learner});localStorage.removeItem('atlas-practice:'+learner);onRefresh();}catch(e){setError(e.message);}finally{setBusy(false);}}
  const chapters=curriculumChapters.map(c=>[c.id,c.id.slice(2),hi?c.hi:c.en,hi?'\u090f\u0915 \u0935\u093f\u0937\u092f \u091a\u0941\u0928\u0947\u0902 \u0914\u0930 \u0909\u0926\u093e\u0939\u0930\u0923\u094b\u0902 \u0938\u0947 \u0938\u0940\u0916\u0947\u0902\u0964':'Choose a topic and learn with examples.',c.id==='CH02'?'angles':c.id==='CH01'?'patterns':'numbers']);
  const actions=[['chat',MessageCircle,hi?'मेरी किताब से पूछें':'Ask my book',hi?'जहाँ अटके हैं, वहाँ से शुरू करें।':'Work through something that feels tricky.','teal'],['revision',CalendarDays,hi?'पुनरावृत्ति करें':'Revisit a mistake',hi?'एक नई कोशिश से समझ पक्की करें।':'Try a fresh question on an earlier mistake.','orange'],['exams',ClipboardList,hi?'मॉक परीक्षा':'Try a mock exam',hi?'समयबद्ध अभ्यास के लिए तैयार हों।':'Put your understanding into practice.','purple'],['explore',Network,hi?'अवधारणाएँ जोड़ें':'Connect the ideas',hi?'देखें कि विषय कैसे जुड़ते हैं।':'See how topics build on one another.','blue']];
  return <div className="student-dashboard">
    {error&&<div role="alert" className="alert danger">{error}</div>}
    {!progressOnly&&<section className="dashboard-hero" aria-labelledby="next-step-heading">
      <div><h2 id="next-step-heading">{hi?'सीखना जारी रखें':'Continue learning'}</h2>
        {nextNode?<><h3>{nextStep.angle_contrast?(hi?'समकोण और सरल कोण की तुलना':'Compare right and straight angles'):nextNode[language]}</h3>
          <p>{nextStep.reason==='followup_correct'?(hi?'पिछला सवाल सही था। अब एक नया सवाल आज़माएँ।':'You got the last follow-up right. Try a new question.'):
            nextStep.reason==='followup_review'?(hi?'पिछले सवाल के बाद इस विषय को एक नए उदाहरण से समझें।':'Revisit this topic with a new example after your last follow-up.'):
            (hi?'पिछली जाँच में यह विषय कठिन लगा। एक नया सवाल आज़माएँ।':'This topic was tricky in a recent activity. Try a fresh question.')}</p>
          <button className="primary-button" onClick={()=>nextStep.angle_contrast
            ?onTutor({id:nextNode.id,text:hi?'कोणों की तुलना करें':'Compare angles',action:'angle',compare:nextStep.reason==='followup_correct'})
            :onTutor({id:nextNode.id,text:nextNode[language],action:nextStep.reason==='followup_correct'?'advance':'review'})}>
            {hi?'अगला कदम शुरू करें':'Start next step'}<ArrowRight size={18} aria-hidden="true"/>
          </button></>:<form onSubmit={event=>{event.preventDefault();if(checkTopic)onTutor({id:checkTopic,text:nodes[checkTopic][language],action:'check'});}}>
          <p>{hi?'छोटी जाँच के लिए कोई विषय चुनें।':'Choose a topic for a quick check.'}</p>
          <div className="platform-actions"><select aria-label={hi?'जाँच का विषय':'Quick check topic'} value={checkTopic} onChange={e=>setCheckTopic(e.target.value)}>
            <option value="">{hi?'विषय चुनें':'Choose a topic'}</option>
            {checkOptions.map(node=><option key={node.id} value={node.id}>{node[language]}</option>)}
          </select><button className="primary-button" disabled={!checkTopic}>{hi?'जाँच शुरू करें':'Start quick check'}</button></div>
        </form>}
        {resume&&<button className="hero-secondary" onClick={continuePractice}>{hi?'अधूरा अभ्यास जारी रखें':'Resume unfinished practice'}</button>}
      </div><MathIllustration/>
    </section>}
    {summaryState==='error'&&<div className="platform-panel" role="alert"><p>{hi?'प्रगति लोड नहीं हो सकी।':'Your progress couldn’t be loaded.'}</p><button className="secondary-button" onClick={onRefresh}><RefreshCw size={18} aria-hidden="true"/>{hi?'फिर कोशिश करें':'Retry progress'}</button></div>}
    {!progressOnly&&<section aria-labelledby="overview-heading" aria-busy={summaryState==='loading'}>
      <div className="dashboard-section-heading">
        <h2 id="overview-heading">{hi?'सीखने का सारांश':'Learning overview'}</h2>
        <span>{hi?'अभ्यास, जाँच, परीक्षाएँ और दैनिक सवाल':'Practice, checks, exams and daily problems'}</span>
      </div>
      <div className="student-stat-grid">{overviewStats.map(([Icon,value,label,tone])=>
        <article className="student-stat" key={label}><span className={'stat-icon '+tone}><Icon size={21} aria-hidden="true"/></span>
          <strong>{value}</strong><span>{label}</span>
        </article>)}</div>
    </section>}
    {!progressOnly&&<><section aria-labelledby="chapters-heading"><div className="dashboard-section-heading"><h2 id="chapters-heading">{hi?'अपने अध्याय चुनें':'Your chapters'}</h2><button className="text-button" onClick={()=>onNavigate('practice')}>{hi?'सभी विषय देखें':'View all topics'}<ArrowRight size={16} aria-hidden="true"/></button></div><div className="chapter-card-grid">{chapters.map(([id,index,title,description,tone])=><button className={'chapter-card '+tone} key={id} onClick={()=>onChapter(id)}><div className="chapter-card-top"><span className="chapter-number">{index}</span><span className="chapter-art" aria-hidden="true">{id==='CH01'?'2 · 4 · 6':id==='CH02'?'∠':'123'}</span></div><h3>{title}</h3><p>{description}</p><span className="chapter-card-bottom"><span>{data.nodes.filter(n=>n.chapter===id&&data.textbooks.concepts[n.id]?.versions?.[language]).length} {hi?'उपलब्ध विषय':'available topics'}</span><ArrowRight size={19} aria-hidden="true"/></span></button>)}</div></section>
      <section aria-labelledby="tools-heading"><div className="dashboard-section-heading"><h2 id="tools-heading">{hi?'आपकी सीखने की चीज़ें':'A little help along the way'}</h2></div><div className="dashboard-action-grid">{actions.map(([id,Icon,title,description,tone])=><button className="dashboard-action" key={id} onClick={()=>onNavigate(id)}><span className={'stat-icon '+tone}><Icon size={22} aria-hidden="true"/></span><h3>{title}</h3><p>{description}</p><span className="action-arrow"><ArrowRight size={19} aria-hidden="true"/></span></button>)}</div></section>
      {recommendations.length>0&&<section className="platform-panel"><h2>{hi?'अब क्या दोहराएँ?':'A good place to revisit'}</h2><div className="study-next-list">{recommendations.map(({id,reason})=><button className="secondary-button" key={id} onClick={()=>onPractice(id)}><span>{nodes[id][language]}<small>{reason}</small></span><ArrowRight size={18} aria-hidden="true"/></button>)}</div></section>}
    </>}
    {progressOnly?<><ProgressActivity summary={summary} language={language} onNavigate={onNavigate} onExam={onExam}/><DailyProblem key={learner+language} learner={learner} language={language} nodes={nodes} onSaved={onRefresh}/><ExamScoreChart papers={summary?.exams?.recent} language={language} onExam={onExam}/><PerformanceCharts summary={summary} nodes={nodes} language={language}/><section className="platform-panel"><h2>{hi?'अभ्यास का इतिहास':'Your practice history'}</h2>{attempts.length?<div className="practice-history-table" role="region" aria-label={hi?'अभ्यास का इतिहास':'Practice history'} tabIndex={0}><table><caption className="sr-only">{hi?'आपके सहेजे गए अभ्यास':'Your saved practice sessions'}</caption><thead><tr>{[hi?'विषय':'Topic',hi?'तिथि':'Date',hi?'भाषा':'Language',hi?'परिणाम':'Result',hi?'स्थिति':'Status'].map(t=><th scope="col" key={t}>{t}</th>)}</tr></thead><tbody>{[...attempts].reverse().map(a=><tr key={a.id}><th scope="row">{nodes[a.concept_id]?.[language]}</th><td>{new Date(a.created).toLocaleDateString(hi?'hi-IN':'en-IN')}</td><td>{a.language==='hi'?'हिन्दी':'English'}</td><td>{a.correct}/{a.scorable}{a.accuracy!==null?` · ${a.accuracy}%`:''}</td><td>{a.completed?(hi?'पूरा':'Completed'):(hi?'जारी':'In progress')}</td></tr>)}</tbody></table></div>:<div className="dashboard-empty"><BookOpen size={30} aria-hidden="true"/><h3>{hi?'आपकी पहली कोशिश यहाँ दिखेगी':'Your first attempt starts your story'}</h3><p>{hi?'एक अभ्यास पूरा करें और अपने परिणाम यहाँ देखें।':'Complete a practice session to see your results here.'}</p><button className="primary-button" onClick={()=>onNavigate('practice')}>{hi?'अभ्यास शुरू करें':'Start practising'}</button></div>}</section></>:
      <section className="platform-panel recent-practice"><div className="dashboard-section-heading"><h2>{hi?'हाल के प्रयास':'Recent practice'}</h2><button className="text-button" onClick={()=>onNavigate('progress')}>{hi?'प्रगति देखें':'View progress'}<ArrowRight size={16} aria-hidden="true"/></button></div>{attempts.length?<ul className="recent-practice-list">{[...attempts].reverse().slice(0,3).map(a=><li key={a.id}><span className="stat-icon teal"><BookOpen size={20} aria-hidden="true"/></span><div><b>{nodes[a.concept_id]?.[language]}</b><small>{new Date(a.created).toLocaleDateString(hi?'hi-IN':'en-IN')} · {a.language==='hi'?'हिन्दी':'English'}</small></div><span>{a.completed?`${a.correct}/${a.scorable} ${hi?'सही':'correct'}`:(hi?'जारी':'In progress')}</span></li>)}</ul>:<div className="dashboard-empty"><BookOpen size={30} aria-hidden="true"/><h3>{hi?'हर शुरुआत मायने रखती है।':'Every first step counts.'}</h3><p>{hi?'आपके अभ्यास के बाद हाल के परिणाम यहाँ दिखेंगे।':'Your recent sessions will appear here after you start practising.'}</p></div>}</section>}
    {profile&&<details className="earlier-report-panel"><summary>{hi?'अपनी पिछली सीखने की रिपोर्ट देखें':'View your earlier learning report'}</summary><ProfileOverviewLocalized profile={profile} language={language}/></details>}
    {!progressOnly&&<details className="dashboard-settings"><summary>{hi?'सीखने की जगह की सेटिंग':'Learning space settings'}</summary><p>{hi?'सहेजे गए परिणाम हटाने से पहले पुष्टि माँगी जाएगी।':'You’ll be asked to confirm before removing saved results.'}</p><button className="text-button danger-text" disabled={busy} onClick={clear}><RotateCcw size={17} aria-hidden="true"/>{hi?'सभी सहेजे गए परिणाम हटाएँ':'Clear all saved results'}</button></details>}
  </div>;
}

function ExamScoreChart({papers,language,onExam}){
  const hi=language==='hi';
  const date=new Intl.DateTimeFormat(hi?'hi-IN':'en-IN',{dateStyle:'medium'});
  const chronological=[...(papers||[])].reverse();
  return <section className="platform-panel exam-score-chart" aria-labelledby="exam-chart-heading">
    <h2 id="exam-chart-heading">{hi?'हाल की मॉक परीक्षाओं के अंक':'Recent mock exam scores'}</h2>
    {chronological.length?<ol>{chronological.map(paper=>{
      const score=Math.round(100*paper.correct/paper.total);
      return <li key={paper.id}>
        <button className="text-button" onClick={()=>onExam(paper.id)}>
          {date.format(paper.finished*1000)}
          <span className="sr-only"> · {paper.correct}/{paper.total} · {hi?'हल देखें':'Review solved paper'}</span>
        </button>
        <span className="exam-score-track" aria-hidden="true"><i style={{width:score+'%'}}/></span>
        <b>{score}%</b>
      </li>;
    })}</ol>:<p>{hi?'पहली मॉक परीक्षा पूरी करने के बाद यहाँ अंक दिखेंगे।':'Complete a mock exam to see your scores here.'}</p>}
  </section>;
}

function ProgressActivity({summary,language,onNavigate,onExam}){
  if(!summary?.checks)return null;
  const hi=language==='hi';
  const {checks,exams,revision,daily}=summary;
  const date=new Intl.DateTimeFormat(hi?'hi-IN':'en-IN',{dateStyle:'medium'});
  return <section className="platform-panel progress-activity" aria-labelledby="other-activity-heading">
    <h2 id="other-activity-heading">{hi?'जाँच, परीक्षाएँ, पुनरावृत्ति और दैनिक सवाल':'Checks, exams, revision and daily results'}</h2>
    <div className="progress-activity-grid">
      <div><h3>{hi?'सीखने की जाँच':'Learning checks'}</h3>
        <p>{checks.answered} {hi?'उत्तर दिए':'answered'}
          {checks.scored>0&&<> · {checks.correct}/{checks.scored} {hi?'जाँचे गए उत्तर सही':'scored answers correct'}</>}</p>
        {!checks.answered&&<p>{hi?'ट्यूटर की छोटी जाँच का जवाब दें।':'Answer a quick check in the tutor to see results here.'}</p>}
        <button className="text-button" onClick={()=>onNavigate('chat')}>{hi?'किताब से पूछें':'Open tutor'}<ArrowRight size={15} aria-hidden="true"/></button>
      </div>
      <div><h3>{hi?'मॉक परीक्षाएँ':'Mock exams'}</h3>
        <p>{exams.completed} {hi?'परीक्षाएँ पूरी':'completed'}</p>
        {exams.active&&<p>{exams.active.deadline
          ?(hi?'एक परीक्षा जारी है। जमा करने या समय पूरा होने पर परिणाम दिखेगा।':'One exam in progress. Results appear after submission or when time expires.')
          :(hi?'एक परीक्षा जारी है। उत्तर जमा करने पर परिणाम दिखेगा।':'One exam in progress. Submit it to see your result.')}</p>}
        {!!exams.recent.length&&<ul className="progress-paper-list">{exams.recent.map(paper=><li key={paper.id}>
          <span>{paper.mode==='mixed'?(hi?'सभी अध्याय':'All chapters'):paper.chapters.map(id=>chapterTitle(id,language)).join(' · ')}
            <small>{date.format(paper.finished*1000)}</small></span>
          <button className="text-button" onClick={()=>onExam(paper.id)}>
            <b>{paper.correct}/{paper.total}</b><span className="sr-only"> {hi?'हल देखें':'Review paper'}</span><ArrowRight size={14} aria-hidden="true"/>
          </button>
        </li>)}</ul>}
        <button className="text-button" onClick={()=>onNavigate('exams')}>{hi?'परीक्षा परिणाम देखें':'View exam results'}<ArrowRight size={15} aria-hidden="true"/></button>
      </div>
      <div><h3>{hi?'पुनरावृत्ति':'Revision'}</h3>
        <p>{revision.reviewed} {hi?'गलतियों पर फिर प्रयास किया':'mistakes revisited'}</p>
        <p>{revision.completed} {hi?'पूरी':'completed'} · {revision.due} {hi?'अभी बाकी':'due now'}</p>
        <button className="text-button" onClick={()=>onNavigate('revision')}>{hi?'पुनरावृत्ति खोलें':'Open revision'}<ArrowRight size={15} aria-hidden="true"/></button>
      </div>
      {daily&&<div><h3>{hi?'दैनिक सवालों के परिणाम':'Daily Problem results'}</h3>
        <p>{daily.solved} {hi?'हल किए':'solved'} · {daily.attempts} {hi?'प्रयास':daily.attempts===1?'attempt':'attempts'}</p>
      </div>}
    </div>
  </section>;
}

function MathIllustration(){return <svg className="dashboard-math-art" viewBox="0 0 300 210" aria-hidden="true"><defs><pattern id="math-dots" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#7ba9a2" opacity=".35"/></pattern></defs><rect x="0" y="0" width="300" height="210" fill="url(#math-dots)"/><g transform="rotate(-8 150 105)"><rect x="58" y="28" width="160" height="150" rx="18" fill="#f4f8ed"/><path d="M85 145V72M85 145H170" fill="none" stroke="#125f58" strokeWidth="5" strokeLinecap="round"/><path d="M85 127H103V145" fill="none" stroke="#70a49b" strokeWidth="3"/><circle cx="182" cy="65" r="25" fill="#f0c780"/><text x="168" y="71" fill="#5b421b" fontSize="18" fontWeight="700">90°</text><path d="M122 103h70M122 115h44" stroke="#c6d9d2" strokeWidth="4" strokeLinecap="round"/></g><g fill="#e9b768"><circle cx="35" cy="80" r="6"/><circle cx="258" cy="150" r="9"/><path d="M235 30h20v20h-20z" transform="rotate(20 245 40)"/></g></svg>;}
