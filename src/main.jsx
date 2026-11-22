import {chapterStyles as chapters} from './curriculum';
import React, { Component, Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Network, Compass, ScanLine, BookOpen, FlaskConical, ArrowUpRight, ArrowRight, ArrowLeft, Search, ChevronRight, ChevronLeft, SlidersHorizontal, Maximize2, RotateCcw, Check, X, Download, CircleHelp, Layers3, Menu, Plus, Minus, Pin, EyeOff, Expand, Save, LoaderCircle, FileText, CircleDot, CheckCircle2, AlertCircle } from 'lucide-react';
import './styles.css';
import { diagnosticCoverage } from './coverage.js';
import { neighbours, expandVisible, visibleWorkspace, resetPositions } from './graphWorkspace.js';
import Learner from './Learner.jsx';
import './learner.css';
import './readability.css';
import LearnerStudy from './LearnerStudy.jsx';
import BookChat from './BookChat.jsx';
import StudentPlatform from './StudentPlatform.jsx';
import {mapHindi} from './mapText';

const ForceGraph = lazy(() => import('react-force-graph-3d'));
const endpoint = n => typeof n === 'object' ? n.id : n;
const escape = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
async function api(path, body) {
  const response = await fetch('/api' + path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Something went wrong. Please try again.');
  return data;
}
function download(name, value) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
  const a = document.createElement('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function Tag({ children, tone = '' }) { return <span className={'tag ' + tone}>{children}</span>; }
function Empty({ title, children }) { return <div className="empty"><CircleHelp size={28}/><h3>{title}</h3><p>{children}</p></div>; }
class GraphBoundary extends Component {
  state = { error: false };
  static getDerivedStateFromError() { return { error: true }; }
  render() { return this.state.error ? <Empty title="3D view unavailable">Enable WebGL in your browser. You can still navigate every concept using the connection list.</Empty> : this.props.children; }
}

function App(){return window.location.pathname==='/study'?<LegacyApp/>:<StudentPlatform Explorer={Explorer}/>;}

function LegacyApp() {
  const [data,setData] = useState(null), [error,setError] = useState(''), [page,setPage] = useState('diagnostic');
  const [selected,setSelected] = useState('MATH6_C0024');
  useEffect(()=>{api('/bootstrap').then(setData).catch(e=>setError(e.message));},[]);
  if(window.location.pathname==='/study')return <div className="learner-app"><header className="learner-header"><a className="learner-brand" href="/">Concept Atlas</a><span>Optional development study</span></header><main className="learner-main">{error?<div className="alert danger">{error}</div>:data?<LearnerStudy data={data}/>:<div className="loading">Preparing study...</div>}</main></div>;
  return <div className="learner-app"><header className="learner-header"><button className="learner-brand" onClick={()=>setPage('diagnostic')}><span className="brand-icon"><Network size={23}/></span><span>concept atlas<span className="brand-period">.</span></span></button><nav aria-label="Main navigation"><button className={page==='diagnostic'?'active':''} onClick={()=>setPage('diagnostic')}>My learning</button><button className={page==='explore'?'active':''} onClick={()=>setPage('explore')}>My concept map</button><button className={page==='chat'?'active':''} onClick={()=>setPage('chat')}>Ask my book</button></nav><span className="learner-class">Class 6 Maths</span></header><main className={'learner-main '+(page==='explore'?'explore-main':'')}><div className="learner-page-title"><span className="learner-kicker">LEARN AT YOUR OWN PACE</span><h1>{page==='chat'?'Ask, understand, and explore.':page==='diagnostic'?'Your next maths adventure starts here.':'See how ideas connect.'}</h1><p>{page==='chat'?'Bilingual explanations with the textbook open beside you.':page==='diagnostic'?'Pick your learning space, explore your progress, and try something new.':'Choose a concept to see what comes before it and where it leads.'}</p></div>{error?<div className="alert danger" role="alert">{error} Please reload the page.</div>:!data?<div className="loading"><LoaderCircle className="spin"/>Getting ready...</div>:<><div hidden={page!=='diagnostic'}><Learner data={data}/></div>{page==='chat'&&<BookChat data={data}/>}{page==='explore'&&<Explorer data={data} selected={selected} setSelected={setSelected} diagnose={()=>setPage('diagnostic')}/>}</>}<footer className="learner-footer">Concept Atlas | English &amp; Hindi | Learn a little more every day</footer></main></div>;
}

function Explorer({ data, selected, setSelected, diagnose, activity, language: uiLanguage = "en" }) {
  const graph = useRef(), graphBox = useRef();
  const language=uiLanguage==='hi'?'hindi':'english';
  const t=text=>uiLanguage==='hi'?(mapHindi[text]||text):text;
  const [size, setSize] = useState({ width: 700, height: 525 }), [local, setLocal] = useState(true), [query, setQuery] = useState(''), [chapter, setChapter] = useState('all'), [tab, setTab] = useState('before'), [trail, setTrail] = useState([]), [edge, setEdge] = useState(null), [walk, setWalk] = useState(0), [labels, setLabels] = useState([]), [settings, setSettings] = useState(false), [ready, setReady] = useState(false), [expanded,setExpanded]=useState(()=>neighbours(selected,data.links)), [hiddenNodes,setHiddenNodes]=useState(new Set()), [pinned,setPinned]=useState(new Set()), [notice,setNotice]=useState('');
  const graphData = useMemo(() => ({ nodes: data.nodes.map((n, i) => ({ ...n, x: Math.cos(i * 2.4) * Math.sqrt(i + 1) * 22, y: Math.sin(i * 2.4) * Math.sqrt(i + 1) * 22, z: (i % 9 - 4) * 30 })), links: data.links.map(e => ({ ...e })) }), [data]);
  useEffect(()=>{try{const saved=JSON.parse(localStorage.getItem('atlas-map-layout')||'{}');for(const n of graphData.nodes){const p=saved[n.id];if(p&&[p.x,p.y,p.z].every(Number.isFinite)){Object.assign(n,p);n.fx=n.x;n.fy=n.y;n.fz=n.z;}}}catch{}},[graphData]);
  const nodes = useMemo(() => Object.fromEntries(data.nodes.map(n => [n.id, n])), [data]);
  const name = id => language === 'hindi' ? nodes[id]?.hi || nodes[id]?.en : nodes[id]?.en || id;
  const current = nodes[selected];
  const latestScore = activity?.[selected]?.latest_score;
  useEffect(()=>{
    setExpanded(previous=>new Set([...previous,...neighbours(selected,data.links)]));
    setHiddenNodes(previous=>new Set([...previous].filter(id=>id!==selected)));
    setWalk(0);setEdge(null);
    setChapter(previous=>previous==='all'||previous===nodes[selected]?.chapter?previous:'all');
  },[selected,data.links,nodes]);
  const allowed = useMemo(() => new Set(data.nodes.filter(n => chapter === 'all' || n.chapter === chapter).map(n => n.id)), [data, chapter]);
  const adjacent = useMemo(() => data.links.filter(e => allowed.has(e.source) && allowed.has(e.target) && (e.source === selected || e.target === selected)), [data, selected, allowed]);
  const visible = useMemo(()=>visibleWorkspace({all:!local,allowed,expanded,hidden:hiddenNodes}),[local,allowed,expanded,hiddenNodes]);
  const visibleLinks = data.links.filter(e => visible.has(e.source) && visible.has(e.target));
  const incoming = adjacent.filter(e => e.target === selected), outgoing = adjacent.filter(e => e.source === selected);
  const connections = tab === 'before' ? incoming : outgoing;
  const activeEdge = adjacent[walk % (adjacent.length || 1)];
  function choose(id, remember = true) { setExpanded(ids=>new Set([...ids,id]));setHiddenNodes(ids=>new Set([...ids].filter(n=>n!==id))); if (id === selected) return; if (remember && selected) setTrail(t => [...t, selected]); setSelected(id); setWalk(0); setEdge(null); setQuery(''); }
  function expand(id=selected){const next=neighbours(id,data.links);setExpanded(ids=>expandVisible(ids,id,data.links));setHiddenNodes(ids=>new Set([...ids].filter(n=>!next.has(n))));setNotice('Connections added. Select another idea and expand again to keep exploring.');}
  function pinSelected(){const n=graphData.nodes.find(n=>n.id===selected);if(!n)return;const isPinned=pinned.has(selected);if(isPinned){delete n.fx;delete n.fy;delete n.fz;}else{n.fx=n.x;n.fy=n.y;n.fz=n.z;}setPinned(ids=>{const next=new Set(ids);isPinned?next.delete(selected):next.add(selected);return next;});graph.current?.d3ReheatSimulation();}
  function moveCoordinate(axis,value){if(value.trim()===''||!Number.isFinite(Number(value)))return;const n=graphData.nodes.find(n=>n.id===selected);if(!n)return;n[axis]=Number(value);n['f'+axis]=n[axis];setPinned(ids=>new Set([...ids,selected]));graph.current?.d3ReheatSimulation();}
  function saveLayout(){localStorage.setItem('atlas-map-layout',JSON.stringify(Object.fromEntries(graphData.nodes.filter(n=>[n.x,n.y,n.z].every(Number.isFinite)).map(n=>[n.id,{x:n.x,y:n.y,z:n.z}]))));setNotice('Your map layout is saved on this browser.');}
  function resetMap(){localStorage.removeItem('atlas-map-layout');resetPositions(graphData.nodes);setHiddenNodes(new Set());setExpanded(neighbours(selected,data.links));setPinned(new Set());setChapter('all');setLocal(true);setEdge(null);graph.current?.d3ReheatSimulation();setNotice('Map reset. Your learning results are unchanged.');}
  async function fullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else await graphBox.current.closest('.explorer-card').requestFullscreen();}catch{setNotice('Full screen is unavailable in this browser.');}}
  function fit() { graph.current?.zoomToFit(reducedMotion() ? 0 : 650, 90, n => visible.has(n.id)); }
  useEffect(() => { const el = graphBox.current; if (!el) return; const obs = new ResizeObserver(([entry]) => setSize({ width: entry.contentRect.width, height: entry.contentRect.height })); obs.observe(el); return () => obs.disconnect(); }, []);
  useEffect(() => { if (ready) { const timer = setTimeout(fit, 100); return () => clearTimeout(timer); } }, [selected, local, chapter, ready, expanded, hiddenNodes]);
  useEffect(() => {
    const timer = setInterval(() => {
      const g = graph.current; if (!g) return;
      const occupied = [];
      const points = [...graphData.nodes].sort((a, b) => (a.id === selected ? -1 : b.id === selected ? 1 : 0)).flatMap(n => {
        if (!visible.has(n.id) || !Number.isFinite(n.x)) return [];
        const camera = g.camera(); const delta = camera.position.clone().set(n.x, n.y, n.z).sub(camera.position);
        if (delta.dot(camera.getWorldDirection(camera.position.clone())) <= 0) return [];
        const p = g.graph2ScreenCoords(n.x, n.y, n.z);
        if (p.x < 55 || p.x > size.width - 55 || p.y < 50 || p.y > size.height - 70) return [];
        if (occupied.some(a => Math.abs(a.x - p.x) < 115 && Math.abs(a.y - p.y) < 37)) return [];
        occupied.push(p); return [{ ...p, id: n.id }];
      }); setLabels(points);
    }, 90); return () => clearInterval(timer);
  }, [graphData, selected, visible, size]);
  const searchResults = data.nodes.filter(n => allowed.has(n.id) && (n.en + n.hi).toLowerCase().includes(query.toLowerCase()));
  return <>

    <section className="explorer-card">
      <div className="explorer-toolbar"><div className="toolbar-title"><Network size={18}/><b>{t('Knowledge map')}</b><span className="live-badge">3D</span></div><div className="map-controls"><div className="search-control"><Search size={16}/><input aria-label="Search graph concepts" placeholder="Find a concept…" value={query} onChange={e => setQuery(e.target.value)}/>{query && <div className="search-results">{searchResults.length ? searchResults.map(n => <button key={n.id} onClick={() => choose(n.id)}>{name(n.id)}<small>{''} · {n.chapter}</small></button>) : <p>No matching concepts</p>}</div>}</div><button className={'subtle-button ' + (settings ? 'selected' : '')} onClick={() => setSettings(!settings)} aria-expanded={settings}><SlidersHorizontal size={16}/> Filters</button></div></div>
      {settings && <div className="filter-bar"><label>Chapter<select value={chapter} onChange={e => { const value = e.target.value; setChapter(value); if (value !== 'all' && nodes[selected]?.chapter !== value) choose(data.nodes.find(n => n.chapter === value).id); }}><option value="all">All chapters</option>{Object.entries(chapters).map(([id, c]) => <option key={id} value={id}>{id} · {uiLanguage==='hi'?c.hi:c.label}</option>)}</select></label></div>}
      <div className="map-workbench" aria-label="Map controls"><button onClick={()=>expand()}><Plus size={15}/> Expand connections</button><button onClick={()=>{setLocal(true);setExpanded(new Set([selected]));setHiddenNodes(new Set());}}><Minus size={15}/> Collapse to this idea</button><button onClick={pinSelected}><Pin size={15}/>{pinned.has(selected)?'Unpin node':'Pin node'}</button><button onClick={()=>setHiddenNodes(ids=>new Set([...ids,selected]))}><EyeOff size={15}/> Hide node</button><button onClick={()=>{setLocal(false);setHiddenNodes(new Set());setChapter('all');}}>{t('Show all')}</button><button onClick={saveLayout}><Save size={15}/> Save layout</button><button onClick={resetMap}><RotateCcw size={15}/> Reset layout</button><button onClick={fullscreen}><Expand size={15}/> Full screen</button></div>{notice&&<div className="map-workspace-notice" role="status">{notice}</div>}
      <div className="explorer-body"><div className="map-column"><div className="graph-canvas" ref={graphBox}>
        <div className="canvas-top"><span><span className="status-dot"/> {local ? 'YOUR EXPLORATION SPACE' : 'ALL CONNECTED IDEAS'}</span><button onClick={() => setLocal(!local)} className="canvas-toggle"><span className={'switch ' + (local ? 'on' : '')}/> Focus mode</button></div>
        <GraphBoundary><Suspense fallback={<div className="graph-loading"><LoaderCircle className="spin"/> Preparing your atlas</div>}><ForceGraph ref={graph} graphData={graphData} width={size.width} height={size.height} backgroundColor="#0e1b30" controlType="orbit" showNavInfo={false} nodeRelSize={6} nodeOpacity={1} nodeVal={n => n.id === selected ? 3 : 1} nodeColor={n => chapters[n.chapter]?.color || '#a7b6d1'} nodeVisibility={n => visible.has(n.id)} linkVisibility={e => visible.has(endpoint(e.source)) && visible.has(endpoint(e.target))} linkColor={e => e.id === edge?.id ? '#ffffff' : e.cycle ? '#db7d87' : '#7c9cb3'} linkOpacity={0.48} linkWidth={e => e.id === edge?.id ? 2.5 : 0.8} linkDirectionalArrowLength={3} linkDirectionalArrowRelPos={0.85} linkHoverPrecision={10} nodeLabel={n => escape(name(n.id))} onNodeClick={n => choose(n.id)} onLinkClick={e => setEdge(data.links.find(a => a.id === e.id))} enableNodeDrag={true} onNodeDragEnd={n=>{n.fx=n.x;n.fy=n.y;n.fz=n.z;setPinned(ids=>new Set([...ids,n.id]));setNotice('Node moved and pinned. Use Unpin if you want it to move with the layout.');}} onNodeRightClick={n=>{choose(n.id);expand(n.id);}} warmupTicks={70} cooldownTicks={70} onEngineStop={() => { if (!ready) { for (const n of graphData.nodes) { n.fx = n.x; n.fy = n.y; n.fz = n.z; } setReady(true); } }}/></Suspense></GraphBoundary>
        <div className="graph-labels">{labels.map(p => <button key={p.id} className={'graph-label ' + (p.id === selected ? 'current' : '')} style={{ left: p.x, top: p.y }} onClick={() => choose(p.id)} onDoubleClick={()=>expand(p.id)} title={name(p.id)+" - double-click to expand connections"}>{name(p.id)}{language === 'bilingual' && <small>{nodes[p.id]?.hi}</small>}</button>)}</div>
        <div className="canvas-tools"><button aria-label="Go back to previous concept" disabled={!trail.length} onClick={() => { const previous = trail.at(-1); setTrail(t => t.slice(0, -1)); choose(previous, false); }}><ArrowLeft size={17}/></button><button aria-label="Fit graph to view" onClick={fit}><Maximize2 size={17}/></button><button aria-label="Reset graph" onClick={resetMap}><RotateCcw size={17}/></button></div>
        <div className="canvas-bottom"><div className="chapter-legend">{Object.entries(chapters).map(([id, c]) => <span key={id}><i style={{ background: c.color }}/>{id}</span>)}</div><span>{visible.size} concepts <span className="legend-divider">/</span> {visibleLinks.length} connections</span></div>
      </div><div className="map-help"><Compass size={14}/><span>Drag to orbit <i>·</i> Scroll to zoom <i>·</i> Right-drag to pan</span><span>Double-click a label to expand</span></div>
      <div className="walk-bar"><div><span className="eyebrow">FOLLOW A CONNECTION</span><div className="walk-name">{activeEdge ? <>{name(activeEdge.source)}<ArrowRight size={15}/>{name(activeEdge.target)}</> : 'No connections in this chapter selection'}</div></div><div className="walk-actions"><span>{activeEdge ? `${walk % adjacent.length + 1} / ${adjacent.length}` : '0 / 0'}</span><button className="icon-button" aria-label="Previous connection" disabled={!activeEdge} onClick={() => setWalk(w => (w - 1 + adjacent.length) % adjacent.length)}><ChevronLeft size={18}/></button><button className="icon-button" aria-label="Next connection" disabled={!activeEdge} onClick={() => setWalk(w => (w + 1) % adjacent.length)}><ChevronRight size={18}/></button><button className="primary-button compact" disabled={!activeEdge} onClick={() => choose(activeEdge.source === selected ? activeEdge.target : activeEdge.source)}>{t('Explore')} <ArrowRight size={15}/></button></div></div>
      </div><aside className="inspector"><div className="inspector-heading"><span className="eyebrow">{edge ? 'HOW THESE IDEAS CONNECT' : 'EXPLORE THIS IDEA'}</span>{edge && <button className="icon-button" aria-label="Close relationship details" onClick={() => setEdge(null)}><X size={16}/></button>}</div>
      {edge ? <><h2>{name(edge.source)}</h2><div className="edge-direction"><ArrowRight size={16}/>{uiLanguage==='hi'?mapHindi['prerequisite_direction']:' is a prerequisite for'}</div><h2>{name(edge.target)}</h2><h4>{t('Why this connection?')}</h4><p className="body-copy">{uiLanguage==='hi'?mapHindi['pending_relation']:(edge.reasoning || 'No reasoning provided.')}</p><h4>{t('Supporting passage IDs')}</h4><p className="reference-text">{edge.evidence || 'Not provided'}</p><div className="mini-info"><span>{t('Model-reported confidence')}</span><b>{edge.confidence || 'Not provided'}</b></div><Tag tone="amber">{edge.status}</Tag>{edge.cycle && <p className="body-copy">Cycle flagged for review.</p>}<button className="secondary-button full" onClick={() => choose(edge.target)}>{t('Open dependent concept')} <ArrowRight size={15}/></button></> : current ? <><Tag>{current.chapter}</Tag><h2>{name(current.id)}</h2>{(latestScore===0||latestScore===1)&&<p className="map-learning-status">
        {latestScore===1?(uiLanguage==='hi'?'पिछला जाँचा गया उत्तर सही':'Latest scored answer correct'):(uiLanguage==='hi'?'दोहराएँ':'Review suggested')}
      </p>}<div className="map-node-position"><span>Move this idea in 3D, or drag its sphere on the map.</span><div className="map-position-fields">{['x','y','z'].map(axis=><label key={axis}>{axis.toUpperCase()}<input type="number" step="10" aria-label={'Node '+axis+' position'} value={Math.round(graphData.nodes.find(n=>n.id===selected)?.[axis]||0)} onChange={e=>moveCoordinate(axis,e.target.value)}/></label>)}</div></div><div className="connection-tabs" role="tablist" aria-label="Connection direction"><button role="tab" aria-selected={tab === 'before'} className={tab === 'before' ? 'active' : ''} onClick={() => setTab('before')}>{t('Learn first')} <span>{incoming.length}</span></button><button role="tab" aria-selected={tab === 'after'} className={tab === 'after' ? 'active' : ''} onClick={() => setTab('after')}>{t('Leads to')} <span>{outgoing.length}</span></button></div><p className="inspector-hint">{uiLanguage==='hi'?(tab==='before'?mapHindi['foundation_hint']:mapHindi['dependent_hint']):(tab === 'before' ? 'Ideas that help build this concept.' : 'Ideas this concept helps you understand.')}</p><div className="connection-list">{connections.length ? connections.map(e => { const id = tab === 'before' ? e.source : e.target; return <div className="connection-row" key={e.id}><button onClick={() => choose(id)}><span className="connection-dot" style={{ background: chapters[nodes[id]?.chapter]?.color }}/><span><b>{name(id)}</b></span><ChevronRight size={16}/></button><button className="evidence-link" onClick={() => setEdge(e)}>{t('View evidence')} <ArrowUpRight size={11}/></button></div>; }) : <p className="body-copy">{t('No connections recorded in this view.')}</p>}</div><div className="diagnostic-cta"><ScanLine size={20}/><h4>{t('Check your foundations')}</h4><p>Try up to three short questions and find your next learning step.</p><button className="primary-button full" onClick={diagnose}>Try a quick check <ArrowUpRight size={15}/></button></div></> : <Empty title="Choose a concept">Search the map or select a node to see its connections.</Empty>}
      </aside></div>
      <div className="research-note"><CircleHelp size={15}/><span>Connections are proposed, not academically validated. Passage identifiers have not yet been checked against the textbook.</span></div>
    </section>
  </>;
}

function Stat({ icon: Icon, value, label, sub }) { return <div className="stat-card"><div className="stat-top"><span>{label}</span><Icon size={18}/></div><strong>{value}</strong><small>{sub}</small></div>; }

createRoot(document.getElementById('root')).render(<App/>);
