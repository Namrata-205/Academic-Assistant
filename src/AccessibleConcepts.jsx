import {curriculumChapters,chapterTitle} from './curriculum';
import React,{useState} from 'react';
import {ArrowLeft,ArrowRight,BookOpen,GitBranch,Search} from 'lucide-react';

export default function AccessibleConcepts({data,language,selected,onSelect,onPractice,activity,progressState,onTutor}){
  const hi=language==='hi';
  const [search,setSearch]=useState(''),[chapter,setChapter]=useState('all'),[trail,setTrail]=useState([]),[reviewOnly,setReviewOnly]=useState(false);
  const nodes=Object.fromEntries(data.nodes.map(node=>[node.id,node]));
  const current=nodes[selected];
  const incoming=data.links.filter(edge=>edge.target===selected&&nodes[edge.source]);
  const outgoing=data.links.filter(edge=>edge.source===selected&&nodes[edge.target]);
  const visible=data.nodes.filter(node=>(chapter==='all'||node.chapter===chapter)&&
    (!reviewOnly||activity?.[node.id]?.latest_score===0)&&
    (node.en+' '+node.hi).toLowerCase().includes(search.trim().toLowerCase()));
  const direct=new Set([selected,...incoming.map(edge=>edge.source)]);
  const earlier=data.links.filter(edge=>incoming.some(parent=>parent.source===edge.target)&&
    nodes[edge.source]&&!direct.has(edge.source));
  const foundationIds=[...new Set(earlier.map(edge=>edge.source))];
  const source=data.textbooks.concepts[selected]?.versions?.[language];

  function choose(id,fromConnection=false){
    if(id===selected)return;
    setTrail(previous=>[...previous.slice(-9),selected]);
    if(fromConnection){
      setSearch('');setReviewOnly(false);
      if(chapter!=='all'&&nodes[id]?.chapter!==chapter)setChapter('all');
    }
    onSelect(id);
  }
  function goBack(){
    const previous=trail.at(-1);
    if(!previous)return;
    setTrail(trail.slice(0,-1));
    setChapter('all');setSearch('');setReviewOnly(false);onSelect(previous);
  }
  function status(id){
    const score=activity?.[id]?.latest_score;
    if(score===1)return hi?'पिछला जाँचा गया उत्तर सही':'Latest scored answer correct';
    if(score===0)return hi?'दोहराएँ':'Review suggested';
    if(activity?.[id])return hi?'उत्तर जाँचा नहीं गया':'Answer unscored';
    if(progressState==='loading')return hi?'प्रगति लोड हो रही है…':'Loading progress…';
    if(progressState==='error')return hi?'प्रगति उपलब्ध नहीं है':'Progress unavailable';
    return null;
  }
  function linkedTopics(edges,direction){
    if(!edges.length)return <p>{hi?'कोई संबंध दर्ज नहीं है।':'No connections recorded.'}</p>;
    return <ul>{edges.map(edge=>{
      const id=edge[direction];
      return <li key={edge.id}><button className="concept-link" onClick={()=>choose(id,true)}>
        <span>{nodes[id][language]}</span><small>{chapterTitle(nodes[id].chapter,language)}</small>
        {activity?.[id]&&<small className={activity[id].latest_score===0?'concept-needs-review':'concept-score-status'}>{status(id)}</small>}
      </button></li>;
    })}</ul>;
  }

  return <section className="platform-panel concept-directory">
    <div className="section-title"><div>
      <h2><GitBranch size={22} aria-hidden="true"/> {hi?'ज्ञान मानचित्र':'Knowledge graph'}</h2>
      <p>{hi?`${data.nodes.length} अवधारणाएँ और ${data.links.length} आधारभूत संबंध`:`${data.nodes.length} concepts and ${data.links.length} prerequisite links`}</p>
    </div></div>
    <div className="concept-directory-grid">
      <div className="concept-picker">
        <h3><Search size={16} aria-hidden="true"/> {hi?'विषय खोजें':'Browse concepts'}</h3>
        <label htmlFor="concept-chapter">{hi?'अध्याय':'Chapter'}</label>
        <select id="concept-chapter" value={chapter} onChange={event=>{
          const next=event.target.value;
          setChapter(next);
          if(next!=='all'&&current?.chapter!==next){
            const first=data.nodes.find(node=>node.chapter===next);
            if(first){setSearch('');choose(first.id);}
          }
        }}>
          <option value="all">{hi?'सभी अध्याय':'All chapters'}</option>
          {curriculumChapters.map(item=><option key={item.id} value={item.id}>{item[language]}</option>)}
          <option value="PRIOR">{chapterTitle('PRIOR',language)}</option>
        </select>
        <label htmlFor="concept-search">{hi?'अवधारणा खोजें':'Find a concept'}</label>
        <input id="concept-search" type="search" value={search} onChange={event=>setSearch(event.target.value)} placeholder={hi?'जैसे: कोण':'For example: angle'}/>
        <label className="concept-review-filter"><input type="checkbox" checked={reviewOnly}
          onChange={event=>setReviewOnly(event.target.checked)}/>{hi?'जिन विषयों को दोहराना है':'Topics to review'}</label>
        <p className="concept-match-count">{hi?`${visible.length} अवधारणाएँ`:`${visible.length} concepts`}</p>
        <div className="concept-directory-list" role="group" aria-label={hi?'अवधारणाएँ':'Concepts'}>
          {visible.map(node=><button key={node.id} aria-pressed={selected===node.id} onClick={()=>choose(node.id)}>
            {node[language]}<small>{chapterTitle(node.chapter,language)}</small>
          </button>)}
          {!visible.length&&<p role="status">{hi?'कोई अवधारणा नहीं मिली।':'No matching concepts.'}</p>}
        </div>
      </div>
      {current&&<div className="concept-directory-detail">
        <button className="text-button concept-back" disabled={!trail.length} onClick={goBack}>
          <ArrowLeft size={16} aria-hidden="true"/>{hi?'पिछली अवधारणा':'Previous concept'}
        </button>
        <div className="concept-relationship-map">
          <section><h4>{hi?'आधारभूत अवधारणाएँ':'Prerequisites'} <span>{incoming.length}</span></h4>{linkedTopics(incoming,'source')}</section>
          <section className="concept-map-selected">{incoming.length>0&&<ArrowRight className="concept-direction-arrow" size={18} aria-hidden="true"/>}
            <p className="concept-selected-chapter">{chapterTitle(current.chapter,language)}</p>
            <h3 aria-live="polite">{current[language]}</h3>
            {status(selected)&&<p>{status(selected)}</p>}
            {activity?.[selected]&&<small>{activity[selected].correct}/{activity[selected].scored} {hi?'जाँचे गए उत्तर सही':'scored answers correct'}</small>}
          </section>
          <section>{outgoing.length>0&&<ArrowRight className="concept-direction-arrow" size={18} aria-hidden="true"/>}<h4>{hi?'इससे आगे सीखें':'Leads to'} <span>{outgoing.length}</span></h4>{linkedTopics(outgoing,'target')}</section>
        </div>
        <div className="platform-actions">
          <button className="primary-button" onClick={()=>onTutor({id:selected,text:current[language],action:'check'})}>
            {hi?'छोटी जाँच शुरू करें':'Start a quick check'}<ArrowRight size={16} aria-hidden="true"/>
          </button>
          {source&&<><button className="secondary-button" onClick={()=>onPractice(selected)}>{hi?'इस विषय का अभ्यास करें':'Practise this topic'}</button>
            <a className="secondary-button" href={source.read_url} target="_blank" rel="noreferrer"><BookOpen size={16} aria-hidden="true"/>
              {hi?'पाठ्यपुस्तक खोलें':'Open textbook'}
            </a></>}
        </div>
        {!!foundationIds.length&&<details className="deeper-foundations">
          <summary>{hi?'और पहले की बुनियाद देखें':'Explore earlier foundations'}</summary>
          <ul>{foundationIds.map(id=><li key={id}>
            <button className="concept-link" onClick={()=>choose(id,true)}>{nodes[id][language]}</button>
            <small>{hi?'इसके लिए आधार':'Supports'} · {[...new Set(earlier.filter(edge=>edge.source===id).map(edge=>nodes[edge.target][language]))].join(', ')}</small>
          </li>)}</ul>
        </details>}
        <p className="field-hint">{hi?'संबंध प्रस्तावित हैं और शिक्षक की समीक्षा बाकी है।':'Connections are proposed and await teacher review.'}</p>
      </div>}
    </div>
  </section>;
}
