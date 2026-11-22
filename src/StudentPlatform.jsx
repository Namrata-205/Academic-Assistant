import React,{useEffect,useRef,useState} from 'react';
import {Network,LayoutDashboard,Target,TrendingUp,MessageCircle,LoaderCircle,CalendarDays,ClipboardList,Menu,X,LogOut,ArrowLeft,RefreshCw} from 'lucide-react';
import {studentApi} from './studentApi';
import StudentAuth from './StudentAuth';
import LandingPage from './LandingPage';
import StudentDashboard from './StudentDashboard';
import TopicPractice from './TopicPractice';
import BookChat from './BookChat';
import StudentRevision from './StudentRevision';
import StudentExams from './StudentExams';
import AccessibleConcepts from './AccessibleConcepts';
import './platform.css';
import './accessible-platform.css';

const privatePages=['dashboard','practice','progress','chat','explore','revision','notebook','exams'];
const pages=['home','login','signup',...privatePages];
const fromHash=()=>pages.includes(location.hash.slice(1))?location.hash.slice(1):'home';

export default function StudentPlatform({Explorer}){
  const [page,setPage]=useState(fromHash),[data,setData]=useState(null),[dataState,setDataState]=useState('loading'),[error,setError]=useState('');
  const [account,setAccount]=useState(undefined),[profile,setProfile]=useState(null),[summary,setSummary]=useState(null),[summaryState,setSummaryState]=useState('loading');
  const [revision,setRevision]=useState(0),[selected,setSelected]=useState('MATH6_C0024'),[menuOpen,setMenuOpen]=useState(false),[showMap,setShowMap]=useState(false);
  const [language,setLanguage]=useState(()=>localStorage.getItem('atlas-ui-language')==='hi'?'hi':'en');
  const [practiceTopic,setPracticeTopic]=useState(null),[practiceChapter,setPracticeChapter]=useState('all'),[afterLogin,setAfterLogin]=useState(null);
  const main=useRef(null),menuButton=useRef(null),initialRoute=useRef(true),hi=language==='hi',learner=account?.learner;
  const protectedPage=privatePages.includes(page),workspace=!!account&&protectedPage;
  const activePage=protectedPage&&!account?'login':page,navPage=page==='notebook'?'revision':page;
  const labels=hi?{dashboard:'मेरी जगह',practice:'अभ्यास',progress:'मेरी प्रगति',chat:'मेरी किताब से पूछें',explore:'अवधारणा मानचित्र',revision:'पुनरावृत्ति',notebook:'गलतियों की कॉपी',exams:'मॉक परीक्षा'}:
    {dashboard:'Dashboard',practice:'Practice',progress:'My progress',chat:'Ask my book',explore:'Concept map',revision:'Revision',notebook:'Mistake notebook',exams:'Mock exams'};
  const links=[['dashboard',LayoutDashboard],['chat',MessageCircle],['practice',Target],['revision',CalendarDays],['exams',ClipboardList],['progress',TrendingUp],['explore',Network]];
  const descriptions=hi?{dashboard:'छोटा अभ्यास, एक साफ़ अगला कदम।',practice:'एक विषय चुनें और अपने उत्तरों पर प्रतिक्रिया पाएँ।',progress:'अपने सहेजे गए अभ्यास और परिणाम देखें।',chat:'सवाल पूछें। बुनियाद जाँचें। उदाहरण से समझें।',explore:'विषयों और उनकी बुनियादी अवधारणाओं के संबंध देखें।',revision:'पिछली गलतियों पर एक नई कोशिश करें।',notebook:'अपने उत्तरों और हल को साथ देखकर सीखें।',exams:'अंग्रेज़ी या हिंदी में समयबद्ध अभ्यास करें।'}:
    {dashboard:'A little practice. A clear next step.',practice:'Choose a topic and get feedback on each answer.',progress:'Your saved attempts and progress, in one place.',chat:'Ask a question. Check the foundations. Work through an example.',explore:'Discover how topics and their foundations connect.',revision:'Return to earlier mistakes with a fresh question.',notebook:'Learn from your answers and their worked solutions.',exams:'Build a practice paper in English or Hindi.'};
  const [nextStep,setNextStep]=useState(null),[chatStart,setChatStart]=useState(null);
  const [examStart,setExamStart]=useState(null);
  const [signingOut,setSigningOut]=useState(false);
  function openTutor(start){setChatStart(start);go('chat');}
  function openExam(id){setExamStart(id);go('exams');}
  function go(next){location.hash=next;setPage(next);setMenuOpen(false);window.scrollTo({top:0,behavior:'auto'});}
  function navigate(next){setChatStart(null);setExamStart(null);setPracticeTopic(null);setPracticeChapter('all');if(privatePages.includes(next)&&!account){setAfterLogin(next);go('login');}else go(next);}
  function signIn(next){setError('');setProfile(null);setSummary(null);setAccount(next);go(afterLogin||(protectedPage?page:'dashboard'));setAfterLogin(null);}
  function openPractice(id){setPracticeTopic(id);setPracticeChapter('all');go('practice');}
  function openChapter(id){setPracticeTopic(null);setPracticeChapter(id);go('practice');}
  async function signOut(){
    setSigningOut(true);setError('');
    try{
      await studentApi('/auth/logout',{});
      setAccount(null);setProfile(null);setSummary(null);setNextStep(null);setChatStart(null);setExamStart(null);
      go('home');
    }catch(e){setError(e.message);}
    finally{setSigningOut(false);}
  }
  async function loadData(){setDataState('loading');try{setData(await studentApi('/bootstrap'));setDataState('ready');}catch(e){setDataState('error');}}
  useEffect(()=>{const handler=()=>{setPage(fromHash());setMenuOpen(false);};addEventListener('hashchange',handler);return()=>removeEventListener('hashchange',handler);},[]);
  useEffect(()=>{studentApi('/auth/session').then(r=>setAccount(r.account)).catch(e=>{setAccount(null);setError(e.message);});loadData();},[]);
  useEffect(()=>{
    if(!learner||!['dashboard','progress','practice','explore'].includes(page))return;
    let live=true,requestId=0,expiryTimer;
    async function refreshProgress(){
      clearTimeout(expiryTimer);
      const id=++requestId;
      setSummaryState('loading');
      try{
        const result=await studentApi('/learning/progress?learner='+encodeURIComponent(learner));
        if(live&&id===requestId){
          setSummary(result);setSummaryState('ready');
          const delay=result.exams?.refresh_after_ms;
          if(Number.isFinite(delay)&&delay>=0)expiryTimer=setTimeout(refreshProgress,delay+250);
        }
      }catch{if(live&&id===requestId)setSummaryState('error');}
    }
    refreshProgress();
    function onVisibility(){if(document.visibilityState==='visible')refreshProgress();}
    window.addEventListener('focus',refreshProgress);
    document.addEventListener('visibilitychange',onVisibility);
    return()=>{
      live=false;clearTimeout(expiryTimer);
      window.removeEventListener('focus',refreshProgress);
      document.removeEventListener('visibilitychange',onVisibility);
    };
  },[learner,page,revision]);
  useEffect(()=>{
    if(!learner)return;
    let live=true;
    studentApi('/profile?learner='+encodeURIComponent(learner)).then(r=>{if(live)setProfile(r.profile);}).catch(()=>{});
    return()=>{live=false;};
  },[learner,revision]);
  useEffect(()=>{
    let live=true;
    setNextStep(null);
    if(learner&&page==='dashboard')studentApi('/learning/next?learner='+encodeURIComponent(learner))
      .then(value=>{if(live)setNextStep(value.next_step);}).catch(()=>{});
    return()=>{live=false;};
  },[learner,page,revision]);
  useEffect(()=>{localStorage.setItem('atlas-ui-language',language);localStorage.setItem('atlas-chat-language',language);document.documentElement.lang=language;},[language]);
  useEffect(()=>{document.title=(labels[page]||(page==='signup'?'Create account':page==='login'?'Sign in':'Class 6 maths'))+' · Concept Atlas';if(initialRoute.current)initialRoute.current=false;else main.current?.focus({preventScroll:true});},[page]);
  useEffect(()=>{if(!menuOpen)return;const close=e=>{if(e.key==='Escape'){setMenuOpen(false);menuButton.current?.focus();}};addEventListener('keydown',close);return()=>removeEventListener('keydown',close);},[menuOpen]);
  const name=account?.display_name?.trim().split(/\s+/)[0]||'',initials=account?.display_name?.trim().split(/\s+/).slice(0,2).map(n=>n[0]).join('')||'';
  return <div className={'learner-app student-platform '+(workspace?'workspace-mode':'public-mode')}>
    <a className="skip-link" href="#main-content" onClick={e=>{e.preventDefault();main.current?.focus();main.current?.scrollIntoView({behavior:'instant'});}}>{hi?'मुख्य सामग्री पर जाएँ':'Skip to main content'}</a>
    <header className="platform-header">
      {workspace?<div className="workspace-location"><button ref={menuButton} className="mobile-menu-button" type="button" aria-expanded={menuOpen} aria-controls="app-navigation" aria-label={menuOpen?(hi?'मेनू बंद करें':'Close navigation'):(hi?'मेनू खोलें':'Open navigation')} onClick={()=>setMenuOpen(v=>!v)}>{menuOpen?<X size={23}/>:<Menu size={23}/>}</button><span className="workspace-breadcrumb">{hi?'सीखने की जगह':'Your learning space'}<span aria-hidden="true">/</span><b>{labels[page]}</b></span></div>:
        <button className="platform-brand" onClick={()=>navigate('home')}><span className="brand-mark"><Network size={24} aria-hidden="true"/></span><span>Concept Atlas<small>{hi?'थोड़ा और समझें।':'Make room for understanding.'}</small></span></button>}
      <div className="platform-header-tools"><label className="platform-language"><span>{hi?'भाषा':'Language'}</span><select aria-label={hi?'भाषा':'Language'} value={language} onChange={e=>setLanguage(e.target.value)}><option value="en">English</option><option value="hi">हिन्दी</option></select></label>
        {workspace?<><span className="header-person"><span className="account-avatar" aria-hidden="true">{initials}</span><b>{name}</b></span>
          <button type="button" className="secondary-button header-logout" disabled={signingOut} onClick={signOut}>
            <LogOut size={17} aria-hidden="true"/>{hi?'लॉग आउट':'Log out'}
          </button></>:account?<button className="primary-button" onClick={()=>navigate('dashboard')}>{hi?'मेरी जगह':'My dashboard'}</button>:<div className="public-auth-actions"><button className="text-button" onClick={()=>go('login')}>{hi?'साइन इन':'Sign in'}</button><button className="primary-button" onClick={()=>go('signup')}>{hi?'खाता बनाएँ':'Create account'}</button></div>}
      </div>
    </header>
    {workspace&&<aside className={'app-sidebar '+(menuOpen?'menu-open':'')} id="app-navigation">
      <button className="platform-brand sidebar-brand" onClick={()=>navigate('dashboard')}><span className="brand-mark"><Network size={26} aria-hidden="true"/></span><span>Concept Atlas<small>{hi?'आपकी सीखने की जगह':'Your learning companion'}</small></span></button>
      <div className="sidebar-class"><span className="class-badge-dot" aria-hidden="true"/>{hi?'कक्षा 6 · गणित':'CLASS 6 · MATHEMATICS'}</div>
      <nav aria-label={hi?'मुख्य नेविगेशन':'Main navigation'}>{links.map(([id,Icon])=><button key={id} type="button" className={'workspace-nav-link '+(navPage===id?'active':'')} aria-current={navPage===id?'page':undefined} onClick={()=>navigate(id)}><Icon size={21} aria-hidden="true"/><span>{labels[id]}</span>{navPage===id&&<i aria-hidden="true"/>}</button>)}</nav>
      <div className="sidebar-bottom"><p>{hi?'एक छोटा कदम भी आगे ले जाता है।':'Small steps still move you forward.'}</p><button className="sidebar-home" onClick={()=>navigate('home')}><ArrowLeft size={17} aria-hidden="true"/>{hi?'मुख्य पृष्ठ':'Back to home'}</button><div className="sidebar-account"><span className="account-avatar" aria-hidden="true">{initials}</span><span><b>{account.display_name}</b><small>{hi?'विद्यार्थी खाता':'Student account'}</small></span></div><button className="secondary-button signout-button" disabled={signingOut} onClick={signOut}><LogOut size={18} aria-hidden="true"/>{hi?'साइन आउट':'Sign out'}</button></div>
    </aside>}
    <main ref={main} id="main-content" tabIndex={-1} className={'platform-main '+(activePage==='explore'?'platform-map-main':activePage==='chat'?'platform-chat-main':'')}>
      {workspace&&activePage==='chat'&&<h1 className="sr-only">{labels.chat}</h1>}{workspace&&activePage!=='chat'&&<div className="platform-page-heading"><span className="platform-eyebrow">{hi?'आपकी सीख, आपकी गति':'YOUR LEARNING, YOUR PACE'}</span><h1>{page==='dashboard'?(hi?`नमस्ते, ${name}!`:`Welcome back, ${name}.`):labels[page]}</h1><p>{descriptions[page]}</p></div>}
      {error&&<div className="alert danger" role="alert">{error}<button className="text-button" onClick={()=>setError('')}>{hi?'बंद करें':'Dismiss'}</button></div>}
      {activePage==='home'&&<LandingPage language={language} onNavigate={navigate} signedIn={!!account}/>}
      {account!==undefined&&['login','signup'].includes(activePage)&&<StudentAuth key={activePage} mode={activePage} language={language} onNavigate={go} onSuccess={signIn}/>}
      {protectedPage&&(account===undefined||account&&dataState==='loading')&&<div className="platform-loading" role="status"><LoaderCircle className="spin" aria-hidden="true"/>{hi?'आपकी जगह तैयार हो रही है…':'Getting your learning space ready…'}</div>}
      {workspace&&dataState==='error'&&<section className="platform-panel load-error" role="alert"><h2>{hi?'सामग्री लोड नहीं हो सकी':'We couldn’t load your learning space'}</h2><p>{hi?'कनेक्शन जाँचें और फिर कोशिश करें।':'Check your connection and try again.'}</p><button className="primary-button" onClick={loadData}><RefreshCw size={18} aria-hidden="true"/>{hi?'फिर कोशिश करें':'Try again'}</button></section>}
      {workspace&&data&&dataState==='ready'&&<>
        {(page==='dashboard'||page==='progress')&&<StudentDashboard key={learner+page} learner={learner} data={data} language={language} summary={summary} summaryState={summaryState} profile={profile} nextStep={nextStep} onTutor={openTutor} onPractice={openPractice} onChapter={openChapter} onNavigate={navigate} onExam={openExam} onRefresh={()=>setRevision(n=>n+1)} progressOnly={page==='progress'}/>}
        {page==='practice'&&<TopicPractice key={learner+String(practiceChapter)+String(practiceTopic)} initialTopic={practiceTopic} initialChapter={practiceChapter} data={data} learner={learner} language={language} summary={summary} onSaved={()=>setRevision(n=>n+1)} onNavigate={navigate}/>}
        {(page==='revision'||page==='notebook')&&<StudentRevision key={learner+page} learner={learner} language={language} daily={page==='revision'} data={data} onNavigate={navigate} onPractice={openPractice}/>}
        {page==='exams'&&<StudentExams key={learner} learner={learner} language={language} data={data} initialExam={examStart} onInitialExamConsumed={()=>setExamStart(null)}/>}
        {page==='chat'&&<BookChat key={learner} learnerCode={learner} data={data} preferredLanguage={language} start={chatStart} onStartConsumed={()=>setChatStart(null)}/>}
        {page==='explore'&&<><AccessibleConcepts data={data} language={language} selected={selected} onSelect={setSelected} onPractice={openPractice} activity={summary?.concept_activity} progressState={summaryState} onTutor={openTutor}/><details className="visual-map-disclosure" onToggle={e=>setShowMap(e.currentTarget.open)}><summary>{hi?'इंटरैक्टिव 3D मानचित्र खोलें':'Open the interactive 3D map'}</summary>{showMap&&<Explorer language={language} data={data} selected={selected} setSelected={setSelected} activity={summary?.concept_activity} diagnose={()=>openTutor({id:selected,text:data.nodes.find(node=>node.id===selected)?.[language]||selected,action:'check'})}/>}</details></>}
      </>}
    </main>{activePage!=='chat'&&<footer className="platform-footer"><span>Concept Atlas</span><p>{hi?'हर दिन, थोड़ी और समझ।':'A little more understanding. Every day.'}</p><small>{hi?'कक्षा 6 · अंग्रेज़ी और हिंदी':'Class 6 · English & Hindi'}</small></footer>}
  </div>;
}
