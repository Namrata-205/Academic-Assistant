import React from 'react';
import {BookOpen,ArrowUpRight} from 'lucide-react';
import ChatTutor,{ChatFeedback} from './ChatTutor';
import ChatClarification from './ChatClarification';
import {sourceSection} from './chatText';

export default function ChatAnswer({message,language,nodes,bank,busy,active,onSend,onAnswer,onChoose,ui}){
  const hi=language==='hi',textLanguage=hi?'hi':'en';
  const decision=message.learning_context?.teaching_decision||message.teaching_decision;
  const focus=nodes[decision?.focus_concept_id]?.[textLanguage];
  const paragraphs=(message.paragraphs||[]).filter(p=>!(message.mode==='generated'&&p.kind==='original_worked_example'));
  const disclaimer=hi?'उत्तर में गलती हो सकती है। छोटी जाँच केवल आगे की मदद चुनने के लिए है; यह पूरी समझ या कमजोरी का प्रमाण नहीं है।':'Answers can contain mistakes. Short checks help us choose support; they do not prove mastery or a weakness.';
  return <article className="chat-book-message">
    <div className="chat-book-label"><BookOpen size={16}/>{message.mode==='learning_check'?ui.check:message.mode==='practice_feedback'?ui.feedback:message.mode==='calculated'?ui.example:['generated','guided_local'].includes(message.mode)?ui.explanation:message.mode==='extractive'?ui.extracts:ui.help}{message.concept&&<span>{message.concept[textLanguage]}</span>}</div>
    {message.status!=='clarify'&&message.message&&(!paragraphs.length||message.mode==='practice_feedback'||(language==='hinglish'&&message.mode==='extractive'))&&<p>{message.message}</p>}
    <ChatTutor message={message} language={language} nodes={nodes} busy={busy} active={active} onSend={onSend} onAnswer={onAnswer}/>
    <div className="chat-explanation">{paragraphs.map((p,i)=><div className={'chat-answer-paragraph '+(p.kind==='textbook_excerpt'?'source-extract':'')} lang={p.kind==='textbook_excerpt'?textLanguage:language==='hinglish'?'hi-Latn':language} key={i}><p>{p.text}</p></div>)}</div>
    <ChatTutor practiceOnly message={message} language={language} nodes={nodes} busy={busy} active={active} onSend={onSend} onAnswer={onAnswer}/>
    {message.status==='clarify'&&<ChatClarification message={message} language={textLanguage} bank={bank} busy={busy} onChoose={onChoose}/>}
    {message.sources?.length>0&&<details className="chat-source-details"><summary>{ui.references}</summary>{message.sources.map(s=><div key={s.id}><a href={s.url} target="_blank" rel="noreferrer">{s.chapter_title} · {sourceSection(s.section,language)} · {ui.page} {s.printed_page}<ArrowUpRight size={13}/></a><blockquote>{s.excerpt}</blockquote></div>)}</details>}
    {(message.paragraphs?.length>0||message.learning_context||message.tutor_summary)&&<footer className="chat-answer-disclaimer">
      {focus&&<small><b>{hi?'आपके सीखने का तरीका: ':'Your learning approach: '}</b>{hi?`${focus} से शुरू करके उदाहरणों से समझेंगे।`:`We’re starting with ${focus} and learning through examples.`}</small>}
      <small>{disclaimer}{message.mode==='extractive'&&(hi?' अभी पाठ्यपुस्तक के अंश दिखाए गए हैं।':' These are textbook excerpts while the explanation service is unavailable.')}</small>
    </footer>}
    <ChatFeedback message={message} language={language} active={active} busy={busy} onSend={onSend}/>
  </article>;
}
