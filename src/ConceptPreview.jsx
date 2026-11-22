import React,{useEffect,useState} from 'react';
import {BookOpen,ArrowUpRight} from 'lucide-react';

function BookLinks({item,language}){
  const hi=language==='hi',v=item.textbook?.versions?.[language];
  if(!v)return <p className="body-copy">{hi?'इस भाषा में सत्यापित पाठ्य संदर्भ उपलब्ध नहीं है।':'No verified textbook reference is available in this language.'}</p>;
  return <div className="preview-book-links"><a href={v.read_url} target="_blank" rel="noreferrer"><BookOpen size={14} aria-hidden="true"/>{v.section}<span>{hi?'पुस्तक पृष्ठ':'Book page'} {v.read_printed_page} / PDF {v.read_pdf_page}</span><ArrowUpRight size={13} aria-hidden="true"/></a></div>;
}

export default function ConceptPreview({target,request,language='en'}){
  const [details,setDetails]=useState(null),[error,setError]=useState(''),hi=language==='hi';
  useEffect(()=>{let alive=true;setDetails(null);setError('');request('/concepts/'+encodeURIComponent(target)).then(r=>{if(alive)setDetails(r);}).catch(e=>{if(alive)setError(e.message);});return()=>{alive=false;};},[target]);
  if(error)return <p role="alert">{hi?'संदर्भ लोड नहीं हुए।':'Could not load references.'}</p>;
  if(!details)return <p role="status">{hi?'संदर्भ लोड हो रहे हैं…':'Loading references…'}</p>;
  return <section className="concept-preview"><h3>{hi?'इस विषय की आधारभूत बातें':'Ideas that support this topic'}</h3>
    <div className="preview-prerequisites">{details.prerequisites.map(n=><span key={n.id}>{n[language]}</span>)}</div>
    <h3>{hi?'पाठ्यपुस्तक में पढ़ें':'Read about your topic'}</h3><BookLinks item={details.concept} language={language}/>
    <details><summary>{hi?'आधारभूत विषयों के संदर्भ':'References for the foundations'}</summary>{details.prerequisites.map(n=><div className="foundation-reference" key={n.id}><h4>{n[language]}</h4><BookLinks item={n} language={language}/></div>)}</details>
    <p className="feedback-caption">{hi?'ग्राफ के संबंध प्रस्तावित हैं और शिक्षक समीक्षा बाकी है।':'Graph relationships are proposed and await teacher review.'}</p>
  </section>;
}
