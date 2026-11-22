import React,{useEffect,useLayoutEffect,useRef,useState} from 'react';
import ChatAnswer from './ChatAnswer';
import {displayUserText} from './tutorText';
import {chatText} from './chatText';
import { BookOpen,Send,Plus,MessageCircle,ArrowUpRight,LoaderCircle } from 'lucide-react';

async function request(path,body){
  const response=await fetch('/api'+path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await response.json();if(!response.ok)throw Error(data.error||'Could not complete the request.');return data;
}
const starters=['What is an acute angle?','Explain the vertex of an angle.','स्थानीय मान कैसे समझें?'];

export default function BookChat({data,preferredLanguage,learnerCode,start,onStartConsumed}){
  const learner=learnerCode||localStorage.getItem('atlas-learner-code');
  const language=preferredLanguage||'en';
  const [input,setInput]=useState(''),[turns,setTurns]=useState([]),[threads,setThreads]=useState([]),[threadId,setThreadId]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[showHistory,setShowHistory]=useState(false);
  const textLanguage=language==='hinglish'?'en':language;
  const ui=chatText(language);
  const nodes=Object.fromEntries(data.nodes.map(n=>[n.id,n]));
  const messagesRef=useRef(),scrollIntent=useRef(null);
  const last=turns[turns.length-1];
  const waitingForAnswer=last?.role==='assistant'&&!!last.payload.check_question;
  async function refresh(){const r=await request('/chat/threads?learner='+encodeURIComponent(learner));setThreads(r.threads);}
  useEffect(()=>{if(learner)refresh().catch(e=>setError(e.message));},[learner]);
  useLayoutEffect(()=>{
    const container=messagesRef.current,intent=scrollIntent.current;
    if(!container||!intent)return;
    scrollIntent.current=null;
    if(intent.type==='preserve'){container.scrollTop=intent.top;return;}
    const messages=container.querySelectorAll('.chat-user-message,.chat-book-message');
    const target=messages[messages.length-1];
    if(target)container.scrollTop+=target.getBoundingClientRect().top-container.getBoundingClientRect().top-16;
    else container.scrollTop=0;
  },[turns]);
  async function send(text=input,conceptId=null,fromComposer=false,fromQuiz=false,label=null){
    if(!learner||!text.trim()||busy)return;
    const previousScroll=messagesRef.current?.scrollTop||0;
    if(!fromQuiz)scrollIntent.current={type:'latest'};
    setBusy(true);setError('');if(!fromQuiz){setInput('');setTurns(t=>[...t,{role:'user',payload:{text:label??(text==='__explain_now__'?(language==='hi'?'\u0905\u092d\u0940 \u0938\u092e\u091d\u093e\u0907\u090f':'Explain now'):text.startsWith('__check_batch__:')?(language==='hi'?'\u0938\u092d\u0940 \u0909\u0924\u094d\u0924\u0930 \u091c\u092e\u093e \u0915\u093f\u090f \u0917\u090f\u0964':'All check answers submitted.'):displayUserText(text,language)),language}}]);}
    try{
      const value=await request('/chat/message',{learner,message:fromComposer&&(last?.payload?.practice_question||waitingForAnswer)?'__chat_query__:'+text.trim():text.trim(),language:(fromComposer||last?.payload?.language==='hinglish')?'auto':language,thread_id:threadId,concept_id:conceptId,check_first:true});
      scrollIntent.current=value.append_message===false?{type:'preserve',top:messagesRef.current?.scrollTop??previousScroll}:{type:'latest'};
      setThreadId(value.thread_id);setTurns(t=>{let updated=t;if(value.quiz_update)updated=t.map(turn=>turn.role==='assistant'&&(turn.payload.practice_question?.id===value.quiz_update.question_id||turn.payload.check_question?.id===value.quiz_update.question_id||turn.payload.check_questions?.[0]?.id===value.quiz_update.question_id)?{...turn,payload:{...turn.payload,quiz_feedback:value.quiz_update.results}}:turn);return value.append_message===false?updated:[...updated,{role:'assistant',payload:value.message}];});await refresh();
    }catch(e){setError(e.message);if(label){setTurns(t=>t.slice(0,-1));setInput(label);return;}if(fromQuiz){return;}if(text.startsWith('__check_batch__:')){setTurns(t=>t[t.length-1]?.role==='user'?t.slice(0,-1):t);}else setInput(text);}finally{setBusy(false);}
  }
  const started=useRef(false);
  useEffect(()=>{
    if(!start||started.current)return;
    started.current=true;
    const command=start.action==='angle'?'__continue_angle__:'+(start.compare?'compare':'review'):
      start.action==='advance'?'__advance_topic__:'+start.text:
      start.action==='review'?'__continue_topic__:'+start.text:'__quick_check__:'+start.text;
    send(command,start.id,false,false,start.text);
    onStartConsumed?.();
  },[start]);
  function submitQuiz(text){const q=last?.payload?.practice_question||last?.payload?.check_question;const message=text.startsWith('__check_batch__:')?text:'__quiz_answer__:'+JSON.stringify({question_id:q?.id,answer:text});return send(message,null,false,true);}
  async function open(id){if(busy)return;setError('');try{const r=await request('/chat/threads/'+id+'?learner='+encodeURIComponent(learner));scrollIntent.current={type:'latest'};setTurns(r.messages);setThreadId(id);setShowHistory(false);}catch(e){setError(e.message);}}
  return <div className="book-chat"><header className="book-chat-toolbar"><div><span className="book-chat-icon"><BookOpen size={22}/></span><span><b>{ui.title}</b><small>{ui.subtitle}</small></span></div><div><button className="secondary-button" disabled={busy} onClick={()=>setShowHistory(!showHistory)}><MessageCircle size={15}/>{ui.saved}</button><button className="secondary-button" disabled={busy} onClick={()=>{setTurns([]);setThreadId(null);setError('');setInput('');}}><Plus size={15}/>{ui.newChat}</button></div></header>
    {showHistory&&<div className="book-chat-history">{threads.length?threads.map(t=><button disabled={busy} key={t.id} onClick={()=>open(t.id)}><b>{t.title}</b><small>{new Date(t.created).toLocaleString(language==='hi'?'hi-IN':'en-IN')}</small></button>):<p>{ui.emptyHistory}</p>}</div>}
    <div ref={messagesRef} className="book-chat-messages" aria-live="polite">{!turns.length&&<section className="book-chat-welcome"><BookOpen size={34}/><h2>{ui.welcome}</h2><p>{ui.intro}</p><div>{(language==='hi'?['\u0928\u094d\u092f\u0942\u0928 \u0915\u094b\u0923 \u0915\u094d\u092f\u093e \u0939\u0948?','\u0915\u094b\u0923 \u0915\u093e \u0936\u0940\u0930\u094d\u0937 \u0938\u092e\u091d\u093e\u0907\u090f\u0964']:['What is an acute angle?','Explain the vertex of an angle.','How does place value work?']).map(s=><button key={s} onClick={()=>setInput(s)}>{s}<ArrowUpRight size={14}/></button>)}</div><small>{ui.clarifyHint}</small></section>}
    {turns.map((turn,index)=>turn.role==='user'?<div className="chat-user-message" key={index}>{turn.payload.text==='Explain now'&&language==='hi'?'\u0905\u092d\u0940 \u0938\u092e\u091d\u093e\u0907\u090f':turn.payload.text}</div>:<ChatAnswer key={index} message={turn.payload} language={turn.payload.language||language} nodes={nodes} bank={data.bank} busy={busy} active={index===turns.length-1} onSend={send} onAnswer={submitQuiz} ui={chatText(turn.payload.language||language)} onChoose={c=>send(turns[index-1]?.payload.text||c[textLanguage],c.id)}/>)}
    {busy&&<div className="chat-thinking"><LoaderCircle size={17} className="spin"/>{ui.reading}</div>}</div>
    {error&&<div className="alert danger" role="alert">{language==='hi'?ui.error:error}</div>}
    <form className="book-chat-composer" onSubmit={e=>{e.preventDefault();send(input,null,true);}}><label className="sr-only" htmlFor="book-chat-input">{ui.question}</label><textarea id="book-chat-input" value={input} onChange={e=>setInput(e.target.value)} maxLength={2000} placeholder={language==='hi'?'अपना प्रश्न लिखिए...':'Ask a question about your topic...'} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send(input,null,true);}}}/><button className="primary-button" disabled={busy||!input.trim()||!learner}><Send size={17}/>{language==='hi'?'पूछें':'Ask'}</button></form>{waitingForAnswer&&<p className="chat-answer-location">{ui.answerHere}</p>}<p className="chat-footer-note">{ui.footer}</p>
  </div>;
}
