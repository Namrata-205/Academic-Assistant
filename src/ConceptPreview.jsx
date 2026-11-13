import React,{useEffect,useState} from 'react';
import { BookOpen,ArrowUpRight } from 'lucide-react';

function BookLinks({item}) {
  if(!item.textbook?.versions||!Object.keys(item.textbook.versions).length)return <p className="body-copy">{item.textbook?.reason||'No verified textbook location mapped yet.'}</p>;
  return <div className="preview-book-links">{Object.entries(item.textbook.versions).map(([lang,v])=><a key={lang} href={v.read_url} target="_blank" rel="noreferrer"><BookOpen size={14}/>{lang==='en'?'English':'हिंदी'}<span>{v.section} · Book p. {v.read_printed_page} / PDF p. {v.read_pdf_page}</span><ArrowUpRight size={13}/></a>)}</div>;
}
export default function ConceptPreview({target,request}) {
  const [details,setDetails]=useState(null),[error,setError]=useState('');
  useEffect(()=>{let alive=true;setDetails(null);setError('');request('/concepts/'+encodeURIComponent(target)).then(r=>{if(alive)setDetails(r);}).catch(e=>{if(alive)setError(e.message);});return()=>{alive=false;};},[target]);
  if(error)return <p className="body-copy" role="alert">Could not load topic references: {error}</p>;
  if(!details)return <p className="body-copy">Loading foundations and book references...</p>;
  return <section className="concept-preview"><h3>Ideas that support this topic</h3>{details.prerequisites.length?<div className="preview-prerequisites">{details.prerequisites.map(n=><span key={n.id}>{n.en}<small>{n.hi}</small></span>)}</div>:<p className="body-copy">No direct prerequisites are recorded.</p>}<h3>Read about your topic</h3><BookLinks item={details.concept}/><details><summary>Book references for the foundations</summary>{details.prerequisites.map(n=><div className="foundation-reference" key={n.id}><h4>{n.en} / {n.hi}</h4><BookLinks item={n}/>{!n.textbook&&<p className="reference-text">Unverified graph passage IDs: {n.graph_references.map(r=>r.passage_ids).filter(Boolean).join('; ')||'Not supplied'}</p>}</div>)}</details><p className="feedback-caption">Textbook locations shown here were checked in the uploaded copies. Prerequisite relationships and learning-check rules still await human review.</p></section>;
}
