import {curriculumChapters} from './curriculum';
import React,{useEffect,useState,useRef} from 'react';
import {ArrowRight,Clock3,Maximize,Upload,Trash2} from 'lucide-react';
import {studentApi} from './studentApi';
import AngleDiagram from './AngleDiagram';
import QuestionAnswer,{questionPrompt} from './StudyQuestion';

const allChapters=curriculumChapters.map(chapter=>chapter.id);

export default function StudentExams({learner,language,data,initialExam,onInitialExamConsumed}){
  const hi=language==='hi',query='?learner='+encodeURIComponent(learner)+'&language='+language;
  const [catalog,setCatalog]=useState(null),[exam,setExam]=useState(null),[chapters,setChapters]=useState(['CH01']);
  const [index,setIndex]=useState(0),[draft,setDraft]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [remaining,setRemaining]=useState(0),[focusView,setFocusView]=useState(false),[file,setFile]=useState(null),[pattern,setPattern]=useState('');
  const [resultFilter,setResultFilter]=useState('all');
  const [paperError,setPaperError]=useState(''),[uploading,setUploading]=useState(false);
  const [inspected,setInspected]=useState('');
  const [count,setCount]=useState('4'),[minutes,setMinutes]=useState('8'),[timed,setTimed]=useState(true);
  const nodes=Object.fromEntries((data?.nodes||[]).map(node=>[node.id,node]));
  const formatNames=hi?{mcq:'बहुविकल्पीय',short_answer:'लघु उत्तर',numeric:'संख्यात्मक उत्तर',written:'लिखित व्याख्या',diagram:'चित्र आधारित'}:
    {mcq:'Multiple choice',short_answer:'Short answer',numeric:'Numeric answer',written:'Written explanation',diagram:'Diagram'};
  const timer=useRef(0),ownedFullscreen=useRef(false),examId=exam?.id,finished=exam?.finished;
  const chapterName=id=>curriculumChapters.find(chapter=>chapter.id===id)?.[language]||id;
  const paperName=paper=>{
    const scope=paper.chapters||paper.mode.split(',');
    if(paper.mode==='mixed'||scope.length===allChapters.length)return hi?'सभी दस अध्याय':'All ten chapters';
    return scope.length===1?chapterName(scope[0]):hi?`${scope.length} अध्यायों का पेपर`:`${scope.length}-chapter paper`;
  };
  const paperChapters=paper=>paper.chapters?.length>1&&paper.chapters.length<allChapters.length
    ?paper.chapters.map(chapterName).join(' · '):null;
  const minimum=Math.max(1,chapters.length);
  const date=timestamp=>new Intl.DateTimeFormat(hi?'hi-IN':'en-IN',{dateStyle:'medium',timeStyle:'short'}).format(timestamp*1000);
  function chooseChapters(next){
    setChapters(next);
    if(Number(count)<next.length)setCount(String(next.length));
  }
  const levelName=level=>(hi?['','आसान','मध्यम','कठिन']:['','Easy','Medium','Difficult'])[level]||'';
  async function refresh(){setCatalog(await studentApi('/exams'+query));}
  useEffect(()=>{let live=true;studentApi('/exams'+query).then(r=>{if(live)setCatalog(r);}).catch(e=>{if(live)setError(e.message);});return()=>{live=false;};},[learner]);
  useEffect(()=>{let live=true;if(examId)studentApi('/exams/'+examId+query).then(r=>{if(live)setExam(r);}).catch(e=>setError(e.message));return()=>{live=false;};},[language]);
  useEffect(()=>{if(!examId||finished!==null||exam.deadline===null)return;let pending=false;
    const tick=async()=>{const left=Math.max(0,Math.ceil((timer.current-performance.now())/1000));setRemaining(left);
      if(!left&&!pending){pending=true;try{const r=await studentApi('/exams/'+examId+query);if(r.finished!==null){setExam(r);await leaveFullscreen();}}catch(e){setError(e.message);}finally{pending=false;}}};
    tick();const id=setInterval(tick,1000);return()=>clearInterval(id);
  },[examId,finished,exam?.deadline,language]);
  useEffect(()=>{const close=()=>{if(!document.fullscreenElement)setFocusView(false);};document.addEventListener('fullscreenchange',close);return()=>document.removeEventListener('fullscreenchange',close);},[]);
  useEffect(()=>{const close=e=>{if(e.key==='Escape')setFocusView(false);};document.addEventListener('keydown',close);return()=>document.removeEventListener('keydown',close);},[]);
  useEffect(()=>()=>{if(ownedFullscreen.current&&document.fullscreenElement)document.exitFullscreen().catch(()=>{});},[]);
  async function enterFullscreen(){setFocusView(true);try{if(!document.fullscreenElement){await document.documentElement.requestFullscreen();ownedFullscreen.current=true;}}catch{/* Focus layout remains available when the browser declines fullscreen. */}}
  async function leaveFullscreen(){setFocusView(false);if(ownedFullscreen.current&&document.fullscreenElement)await document.exitFullscreen();ownedFullscreen.current=false;}
  function show(r,position){setExam(r);setIndex(position);setDraft(r.questions[position]?.response||'');const seconds=r.deadline===null?null:Math.max(0,r.deadline-r.server_time);
    timer.current=performance.now()+(seconds??0)*1000;setRemaining(seconds===null?null:Math.ceil(seconds));}
  async function open(id=null,resume=false){
    if(busy)return;
    setResultFilter('all');
    const full=(!id||resume)?enterFullscreen():Promise.resolve(); // Request within the user's click, before awaiting the API.
    setBusy(true);setError('');try{const r=id?await studentApi('/exams/'+id+query):await studentApi('/exams',{learner,chapters,language,pattern_id:selectedPattern?.id||null,question_count:Number(count),minutes:timed?Number(minutes):0});
      await full;window.scrollTo({top:0,behavior:'auto'});show(r,r.finished===null?Math.max(0,r.questions.findIndex(q=>!q.response)):0);
    }catch(e){setError(e.message);await leaveFullscreen();}finally{setBusy(false);}
  }
  useEffect(()=>{
    if(!initialExam)return;
    open(initialExam);
    onInitialExamConsumed?.();
  },[initialExam]);
  async function save(){if(draft.trim()===exam.questions[index].response)return exam;return studentApi('/exams/'+exam.id+'/answer',{learner,ordinal:index,response:draft,language});}
  async function move(position){if(busy||remaining===0)return;setBusy(true);setError('');try{show(await save(),position);}catch(e){setError(e.message);}finally{setBusy(false);}}
  async function submit(){if(busy||remaining===0)return;if(!confirm(hi?'परीक्षा जमा करें?':'Submit this exam?'))return;setBusy(true);setError('');try{await save();show(await studentApi('/exams/'+exam.id+'/submit',{learner,language}),index);await leaveFullscreen();}catch(e){setError(e.message);}finally{setBusy(false);}}
  async function list(){setBusy(true);try{if(exam?.finished===null&&remaining!==0)await save();await leaveFullscreen();setExam(null);window.scrollTo({top:0,behavior:'auto'});await refresh();}catch(e){setError(e.message);}finally{setBusy(false);}}
  async function upload(){if(!file||busy)return;setBusy(true);setUploading(true);setPaperError('');try{
      if(file.size>5*1024*1024)throw Error(hi?'फ़ाइल 5 MB से छोटी होनी चाहिए।':'Choose a file no larger than 5 MB.');
      const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file);});
      const paper=await studentApi('/exams/past-papers',{learner,filename:file.name,content:encoded});
      setCatalog(previous=>({...previous,past_papers:[paper,...previous.past_papers.filter(saved=>saved.id!==paper.id)]}));
      if(paper.analysis_status==='ready')setPattern(paper.id);
      setInspected(paper.id);setFile(null);
      const picker=document.getElementById('past-paper-file');
      if(picker)picker.value='';
    }catch(e){
      setPaperError(e.message||(hi?'फ़ाइल पढ़ी नहीं जा सकी।':'Could not read the file.'));
    }finally{setUploading(false);setBusy(false);}}
  async function removePattern(){setBusy(true);try{await studentApi('/exams/past-papers/delete',{learner,id:paperAnalysis.id});if(pattern===paperAnalysis.id)setPattern('');setInspected('');await refresh();}catch(e){setError(e.message);}finally{setBusy(false);}}
  const usablePatterns=(catalog?.past_papers||[]).filter(p=>!p.analysis_status||p.analysis_status==='ready');
  const selectedPattern=usablePatterns.find(p=>p.id===pattern);
  const paperAnalysis=catalog?.past_papers?.find(p=>p.id===inspected)||selectedPattern||catalog?.past_papers?.[0];
  if(!exam)return <div className="study-stack">
    {error&&<div className="alert danger" role="alert">{error}<button className="text-button" onClick={()=>refresh().catch(e=>setError(e.message))}>{hi?'फिर प्रयास करें':'Try again'}</button></div>}
    {!catalog&&!error&&<p role="status">{hi?'परीक्षाएँ लोड हो रही हैं…':'Loading mock exams…'}</p>}
    {catalog&&<section className="platform-panel exam-results-box" aria-labelledby="exam-results-heading">
      <h2 id="exam-results-heading">{hi?'परिणाम':'Results'}</h2>
      {catalog.history.length?<ul className="exam-history-list">{catalog.history.map(paper=><li key={paper.id}>
        <div><h3>{paperName(paper)}</h3>
          {paperChapters(paper)&&<p>{paperChapters(paper)}</p>}
          <p><time dateTime={new Date(paper.finished*1000).toISOString()}>{date(paper.finished)}</time>
            {paper.reason==='expired'&&(hi?' · समय पूरा हुआ':' · Time expired')}</p></div>
        <div className="exam-history-score">
          <b>{paper.correct}/{paper.total} · {Math.round(100*paper.correct/paper.total)}%</b>
          <small>{hi?`${paper.answered}/${paper.total} के उत्तर दिए`:`${paper.answered}/${paper.total} answered`}</small>
        </div>
        <button type="button" className="secondary-button" disabled={busy} onClick={()=>open(paper.id)}>{hi?'उत्तर और प्रतिक्रिया देखें':'Review paper'}</button>
      </li>)}</ul>:<p>{hi?'पूरी की गई परीक्षाएँ, अंक और हल यहाँ दिखेंगे।':'Your completed papers, scores and feedback will appear here.'}</p>}
    </section>}
    {catalog?.active?<section className="platform-panel"><h2>{paperName(catalog.active)}</h2><p>{hi?(catalog.active.deadline===null?'आपकी बिना समय सीमा वाली परीक्षा जारी है।':'परीक्षा जारी है। समय चलता रहता है।'):(catalog.active.deadline===null?'Your untimed exam is in progress.':'Your exam is in progress. The timer keeps running.')}</p><button className="primary-button" disabled={busy} onClick={()=>open(catalog.active.id,true)}>{hi?'परीक्षा जारी रखें':'Resume exam'}</button></section>:catalog&&<>
      <form className="platform-panel exam-setup" onSubmit={e=>{e.preventDefault();if(chapters.length)open();}}>
        <fieldset className="exam-chapter-picker">
          <legend>{hi?'अपने अध्याय चुनें':'Choose your chapters'}</legend>
          <p>{hi?'एक या अधिक अध्याय चुनें। हर चुने हुए अध्याय से कम से कम एक प्रश्न आएगा।':'Choose one or more chapters. Each selected chapter gets at least one question.'}</p>
          <div className="platform-actions">
            <button type="button" className="secondary-button" onClick={()=>chooseChapters(allChapters)} disabled={chapters.length===allChapters.length}>{hi?'सभी अध्याय चुनें':'Select all chapters'}</button>
            <button type="button" className="text-button" onClick={()=>chooseChapters([])} disabled={!chapters.length}>{hi?'चयन हटाएँ':'Clear selection'}</button>
          </div>
          <div className="exam-paper-grid">{curriculumChapters.map(chapter=>{
            const checked=chapters.includes(chapter.id);
            return <label key={chapter.id} className={checked?'chosen':''}><input type="checkbox" checked={checked}
              onChange={()=>chooseChapters(checked?chapters.filter(id=>id!==chapter.id):[...chapters,chapter.id])}/>
              <span><b>{chapter[language]}</b></span>
            </label>;
          })}</div>
        </fieldset>
        <div className="platform-actions exam-custom-settings">
          <label>{hi?'प्रश्नों की संख्या':'Number of questions'}<input type="number" min={minimum} max="30" step="1" required value={count} onChange={e=>setCount(e.target.value)}/></label>
          <label>{hi?'समय (मिनट)':'Time limit (minutes)'}<input type="number" min="1" max="180" step="1" required={timed} disabled={!timed} value={minutes} onChange={e=>setMinutes(e.target.value)}/></label>
          <label className="exam-timer-toggle"><input type="checkbox" checked={timed} onChange={e=>setTimed(e.target.checked)}/>{hi?'समय सीमा रखें':'Use a timer'}</label>
        </div>
        <p>{hi?'प्रश्न आसान से कठिन होंगे। पहले के उत्तरों के आधार पर दोहराने योग्य विषयों पर ध्यान दिया जाएगा।':'Questions progress from easy to difficult, with topics prioritized using your previous responses.'}</p>
        {usablePatterns.length>0&&<div className="exam-field"><label htmlFor="past-paper-pattern">{hi?'प्रश्नपत्र का प्रारूप':'Paper pattern'}</label><select id="past-paper-pattern" aria-label={hi?"\u092a\u094d\u0930\u0936\u094d\u0928\u092a\u0924\u094d\u0930 \u0915\u093e \u092a\u094d\u0930\u093e\u0930\u0942\u092a":"Paper pattern"} value={selectedPattern?.id||''} onChange={e=>setPattern(e.target.value)}><option value="">{hi?'सामान्य प्रारूप':'Standard pattern'}</option>{usablePatterns.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></div>}
        {selectedPattern&&<p>{hi?'चुने हुए अध्याय में पुराने प्रश्नपत्र के विषय और प्रारूप, तथा आपके हाल के गलत उत्तर, प्रश्नों के चयन को प्रभावित करते हैं।':
          'The mock uses topics and formats from the selected paper alongside your past mistakes, within the chapter scope you chose.'}</p>}
        <p>{hi?'शुरू करने पर फ़ोकस दृश्य खुलेगा। समय सीमा चुनी है तो समय तभी शुरू होगा।':'Starting opens a focused exam view and starts the timer if enabled.'}</p>
        <button className="primary-button" disabled={busy||!chapters.length}>{hi?'परीक्षा शुरू करें':'Start exam'}<ArrowRight size={17}/></button>
      </form>
      <section className="platform-panel paper-upload"><h2>{hi?'पुराने प्रश्नपत्र':'Past papers'}</h2>
        <p>{hi?'विश्लेषण के लिए 5 MB तक का पढ़ने योग्य PDF या UTF-8 टेक्स्ट जोड़ें।':'Save a readable PDF or UTF-8 text paper up to 5 MB to see its question types and frequently asked topics.'}</p>
        <div className="exam-field"><label htmlFor="past-paper-file">{hi?'प्रश्नपत्र चुनें':'Past paper file'}</label>
        <input id="past-paper-file" type="file" accept=".pdf,.txt" onChange={e=>{setFile(e.target.files?.[0]||null);setPaperError('');}}/></div>
        <button type="button" className="secondary-button" disabled={busy||!file} onClick={upload}><Upload size={17}/>{uploading?(hi?'विश्लेषण जारी है…':'Analyzing…'):(hi?'सहेजें और विश्लेषण करें':'Save and analyze')}</button>
        {paperError&&<p className="alert danger" role="alert">{paperError}</p>}
        {!!catalog.past_papers.length&&<div className="exam-field"><label htmlFor="saved-paper-selector">{hi?'विश्लेषण के लिए प्रश्नपत्र':'View a saved paper'}</label><select id="saved-paper-selector" value={paperAnalysis?.id||''} onChange={e=>setInspected(e.target.value)}>
          {catalog.past_papers.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}
        </select></div>}
        {paperAnalysis&&<article className="paper-analysis">
          <h3>{paperAnalysis.name}</h3>
          {paperAnalysis.analysis_status==='no_text'?<p role="status">{hi?
            'फ़ाइल सहेज ली गई। इस PDF में पढ़ने योग्य टेक्स्ट नहीं मिला। OCR से टेक्स्ट जोड़कर फिर अपलोड करें।':
            'Paper saved. This PDF has no readable text. Run OCR and upload the searchable PDF to analyze its questions.'}</p>:
          paperAnalysis.analysis_status==='no_questions'?<p role="status">{hi?
            'फ़ाइल सहेज ली गई, लेकिन सवाल पहचाने नहीं गए। सवालों को क्रमांक देकर एक टेक्स्ट फ़ाइल अपलोड करें।':
            'Paper saved. No questions were detected. Upload a UTF-8 text copy with one numbered question per line to analyze the pattern.'}</p>:
          paperAnalysis.format_counts?<><p>{hi?'पहचाने गए प्रश्न':'Detected questions'} · {paperAnalysis.detected_questions}</p>
            <ul>{Object.entries(paperAnalysis.format_counts).filter(([,n])=>n>0).map(([kind,n])=><li key={kind}>{formatNames[kind]} · {n}</li>)}</ul>
            <h4>{hi?'बार-बार पूछे गए विषय':'Frequently asked topics'}</h4>
            {paperAnalysis.topics.length>0?<ol>{paperAnalysis.topics.slice(0,8).map(({concept_id,count})=><li key={concept_id}>{nodes[concept_id]?.[language]||concept_id} · {count}</li>)}</ol>:
              <p>{hi?'प्रश्नों में पाठ्यक्रम के विषय स्पष्ट रूप से नहीं मिले।':'No explicit curriculum topic names were detected.'}</p>}
          </>:<p>{hi?'अनुमानित बहुविकल्पीय अनुपात':'Estimated multiple-choice share'} · {Math.round(paperAnalysis.mcq_ratio*100)}%</p>}
          {usablePatterns.some(p=>p.id===paperAnalysis.id)&&<p><small>{hi?'विश्लेषण पहचाने गए प्रश्नों और विषयों पर आधारित है। मॉक में बहुविकल्पीय, संख्यात्मक और उपलब्ध कोण-चित्र वाले प्रश्न आते हैं।':
            'Analysis estimates frequency from detected questions and topic names. Mocks use multiple-choice, numeric, and available angle-diagram questions.'}</small></p>}
          <div className="platform-actions">
            {usablePatterns.some(p=>p.id===paperAnalysis.id)&&<button className="secondary-button" disabled={pattern===paperAnalysis.id||busy} type="button" onClick={()=>setPattern(paperAnalysis.id)}>
              {pattern===paperAnalysis.id?(hi?'मॉक के लिए चुना गया':'Selected for the mock'):(hi?'मॉक में यह प्रारूप अपनाएँ':'Use this pattern in my mock')}
            </button>}
            {paperAnalysis.has_file&&<a className="secondary-button" href={'/api/exams/past-papers/'+paperAnalysis.id+query} download>{hi?'प्रश्नपत्र डाउनलोड करें':'Download paper'}</a>}
            <button type="button" className="text-button" onClick={removePattern} disabled={busy}><Trash2 size={15}/>{hi?'प्रश्नपत्र हटाएँ':'Remove paper'}</button>
          </div>
        </article>}
      </section>
    </>}
  </div>;
  const q=exam.questions[index];
  const answered=exam.questions.filter(item=>item.response).length;
  const missed=exam.finished===null?[]:[...new Set(exam.questions.filter(item=>item.score!==1).map(item=>item.concept_id))];
  const displayed=resultFilter==='mistakes'?exam.questions.filter(item=>item.score!==1):exam.questions;
  const missedTopics=missed.map(id=>nodes[id]?.[language]).filter(Boolean);
  return <section className={'platform-panel exam-workspace'+(focusView?' exam-focus-view':'')}><div className="exam-inner">
    <div className="section-title"><h2>{paperName(exam)}</h2><div className="platform-actions">{exam.finished===null&&exam.deadline!==null&&<span className="exam-timer" aria-label={hi?'शेष समय':'Time remaining'}><Clock3 size={18}/>{String(Math.floor(remaining/60)).padStart(2,'0')}:{String(remaining%60).padStart(2,'0')}</span>}<button className="secondary-button" onClick={()=>document.fullscreenElement||focusView?leaveFullscreen():enterFullscreen()}><Maximize size={16}/>{document.fullscreenElement||focusView?(hi?'पूर्ण स्क्रीन से बाहर':'Exit fullscreen'):(hi?'पूर्ण स्क्रीन':'Fullscreen')}</button></div></div>
    {paperChapters(exam)&&<p>{paperChapters(exam)}</p>}
    {error&&<div className="alert danger" role="alert">{error}</div>}
    {exam.finished!==null?<div className="study-stack"><div className="exam-score-summary">
      <h3>{hi?'परीक्षा परिणाम':'Exam results'} · {exam.correct}/{exam.questions.length} ({Math.round(100*exam.correct/exam.questions.length)}%)</h3>
      <p>{hi?'सही':'Correct'} {exam.correct} · {hi?'गलत':'Incorrect'} {answered-exam.correct} · {hi?'छोड़े गए':'Unanswered'} {exam.questions.length-answered}</p>
      {missedTopics.length>0?<p><b>{hi?'इन विषयों को दोहराएँ':'Topics to review'}</b> · {missedTopics.join(', ')}</p>:
        exam.correct===exam.questions.length&&<p>{hi?'सभी उत्तर सही हैं।':'You answered every question correctly.'}</p>}
      </div>
      <p>{Object.entries(exam.questions.reduce((formats,item)=>({...formats,[item.format]:(formats[item.format]||0)+1}),{}))
        .map(([kind,n])=>formatNames[kind]+' '+n).join(' · ')}</p><div className="platform-actions"><button className="secondary-button" onClick={list}>{hi?'परिणामों पर वापस जाएँ':'Back to results'}</button></div><div className="platform-actions exam-result-filters" role="group" aria-label={hi?'परिणाम फ़िल्टर':'Result filters'}>
        <button className={resultFilter==='all'?'primary-button':'secondary-button'} aria-pressed={resultFilter==='all'} onClick={()=>setResultFilter('all')}>{hi?'सभी उत्तर':'All answers'}</button>
        <button className={resultFilter==='mistakes'?'primary-button':'secondary-button'} aria-pressed={resultFilter==='mistakes'} onClick={()=>setResultFilter('mistakes')}>{hi?'गलतियाँ दोहराएँ':'Review mistakes'}</button>
      </div>
      {resultFilter==='mistakes'&&<p role="status">{displayed.length
        ?(hi?'इस प्रश्नपत्र के गलत और छूटे हुए उत्तर।':'Incorrect and unanswered questions from this paper.')
        :(hi?'इस प्रश्नपत्र में कोई गलती नहीं है।':'You got every question right on this paper.')}</p>}
      {displayed.map(item=><article className="exam-result" key={item.ordinal}><h3>{item.ordinal+1}. {item.text}</h3>
      {item.selection_reason==='review_previous_errors'&&<small>{hi?'पिछले गलत उत्तर पर आधारित':'Based on a past mistake'}</small>}
      {item.selection_reason==='past_paper_topic'&&<small>{hi?'पुराने प्रश्नपत्र के विषय पर आधारित':'Based on a topic from your past paper'}</small>}{item.diagram&&<AngleDiagram diagram={item.diagram} language={language}/>}<p>{hi?'आपका उत्तर':'Your answer'}: {item.response||(hi?'खाली':'Unanswered')} · {item.score}/1</p><p><b>{hi?'सही उत्तर':'Correct answer'}</b> · {item.correct_answer}</p><p>{item.explanation}</p></article>)}</div>:<>
      <div className="exam-pages" aria-label={hi?'प्रश्न':'Questions'}>{exam.questions.map((item,i)=><button key={i} className={'secondary-button'+(item.response?' answered':'')} disabled={busy||remaining===0} aria-current={index===i?'step':undefined} onClick={()=>move(i)}>{i+1}</button>)}</div>
      <form onSubmit={e=>{e.preventDefault();move(Math.min(index+1,exam.questions.length-1));}}><p>{hi?'प्रश्न':'Question'} {index+1}/{exam.questions.length} · <b>{levelName(q.difficulty)}</b></p><h3 lang={language}>{questionPrompt(q)}</h3>{q.diagram&&<AngleDiagram diagram={q.diagram} language={language}/>}<QuestionAnswer key={index} question={q} value={draft} onChange={setDraft} language={language} disabled={busy||remaining===0} id="exam-answer"/>
        <div className="platform-actions"><button className="primary-button" disabled={busy||remaining===0}>{index+1===exam.questions.length?(hi?'उत्तर सहेजें':'Save answer'):(hi?'सहेजें और आगे बढ़ें':'Save & next')}</button><button type="button" className="secondary-button" disabled={busy||remaining===0} onClick={submit}>{hi?'परीक्षा जमा करें':'Submit exam'}</button><button type="button" className="text-button" disabled={busy} onClick={list}>{hi?'प्रश्नपत्रों पर लौटें':'Back to papers'}</button></div>
      </form>
    </>}
  </div></section>;
}
