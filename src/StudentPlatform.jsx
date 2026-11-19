import React,{useEffect,useState} from 'react';
import {Network,Home,LayoutDashboard,Target,TrendingUp,MessageCircle,LoaderCircle,CalendarDays,ClipboardList} from 'lucide-react';
import {studentApi} from './studentApi';
import StudentAuth from './StudentAuth';
import LandingPage from './LandingPage';
import StudentDashboard from './StudentDashboard';
import TopicPractice from './TopicPractice';
import BookChat from './BookChat';
import StudentRevision from './StudentRevision';
import StudentExams from './StudentExams';
import './platform.css';

const titlesForStudents=['dashboard','practice','progress','chat','explore','revision','notebook','exams'];
const pages=['home','login','signup',...titlesForStudents];
const fromHash=()=>pages.includes(location.hash.slice(1))?location.hash.slice(1):'home';

export default function StudentPlatform({Explorer}){
  const [page,setPage]=useState(fromHash),[data,setData]=useState(null),[error,setError]=useState(''),[account,setAccount]=useState(undefined),[profile,setProfile]=useState(null),[summary,setSummary]=useState(null),[revision,setRevision]=useState(0),[selected,setSelected]=useState('MATH6_C0024');
  const [language,setLanguage]=useState(()=>localStorage.getItem('atlas-ui-language')==='hi'?'hi':'en');
  const hi=language==='hi',learner=account?.learner;
  const [practiceTopic,setPracticeTopic]=useState(null);
  const [afterLogin,setAfterLogin]=useState(null);
  const protectedPage=titlesForStudents.includes(page);
  const activePage=protectedPage&&!account?'login':page;
  const navPage=page==='notebook'?'revision':page;
  function navigate(next){
    setPracticeTopic(null);
    if(titlesForStudents.includes(next)&&!account){setAfterLogin(next);go('login');}
    else go(next);
  }
  function signIn(next){
    setError('');setProfile(null);setSummary(null);setPracticeTopic(null);setAccount(next);
    go(afterLogin||(protectedPage?page:'dashboard'));
    setAfterLogin(null);
  }
  function openPractice(id){
    setPracticeTopic(id);
    go('practice');
  }
  async function signOut(){
    try{await studentApi('/auth/logout',{});setAccount(null);setProfile(null);setSummary(null);setPracticeTopic(null);go('home');}
    catch(e){setError(e.message);}
  }
  function go(next){location.hash=next;setPage(next);window.scrollTo({top:0,behavior:'smooth'});}
  useEffect(()=>{const handler=()=>setPage(fromHash());addEventListener('hashchange',handler);return()=>removeEventListener('hashchange',handler);},[]);
  useEffect(()=>{studentApi('/auth/session').then(r=>setAccount(r.account)).catch(e=>{setAccount(null);setError(e.message);});},[]);
  useEffect(()=>{studentApi('/bootstrap').then(setData).catch(e=>setError(e.message));},[]);
  useEffect(()=>{let live=true;setSummary(null);setProfile(null);if(!learner)return;studentApi('/practice/analytics?learner='+encodeURIComponent(learner)).then(r=>{if(live)setSummary(r);}).catch(e=>{if(live)setError(e.message);});studentApi('/profile?learner='+encodeURIComponent(learner)).then(r=>{if(live)setProfile(r.profile);}).catch(()=>{});return()=>{live=false;};},[learner,revision]);
  useEffect(()=>{localStorage.setItem('atlas-ui-language',language);localStorage.setItem('atlas-chat-language',language);},[language]);
  const links=[['home',Home,hi?'मुख्य पृष्ठ':'Home'],['dashboard',LayoutDashboard,hi?'मेरी जगह':'My space'],['practice',Target,hi?'अभ्यास':'Practice'],['progress',TrendingUp,hi?'मेरी प्रगति':'My progress'],['chat',MessageCircle,hi?'शिक्षक से पूछें':'Ask my book'],['explore',Network,hi?'विचारों का मानचित्र':'Concept map'],['revision',CalendarDays,hi?'पुनरावृत्ति':'Revision'],['exams',ClipboardList,hi?'मॉक परीक्षा':'Mock exams']];
  const titles={dashboard:[hi?'आपकी सीख, आपके लिए':'YOUR SPACE, YOUR PACE',account?(hi?`नमस्ते, ${account.display_name.split(' ')[0]}!`:`Welcome, ${account.display_name.split(' ')[0]}.`):'',hi?'अपनी ताकतें पहचानें और सीखने का अगला कदम चुनें।':'Explore your strengths, revisit a foundation, and choose your next step.'],
    practice:[hi?'थोड़ा अभ्यास, अधिक आत्मविश्वास':'PRACTICE WITH PURPOSE',hi?'आपका अगला विषय कौन सा है?':'What will you work on today?',hi?'विषय और भाषा चुनें। हर प्रश्न का उत्तर उसी कार्ड में दें।':'Choose a topic and a language. Answer each question in its own card.'],
    progress:[hi?'हर प्रयास मायने रखता है':'EVERY ATTEMPT COUNTS',hi?'अपनी सीखने की यात्रा देखें।':'See your learning take shape.',hi?'आपके वास्तविक अभ्यासों के परिणाम, विषय और भाषा के अनुसार।':'Your saved practice results, across topics, languages, and time.'],
    chat:[hi?'सवाल पूछें, समझकर सीखें':'ASK. UNDERSTAND. TRY AGAIN.',hi?'चलो, साथ समझते हैं।':'Let’s work through it together.',hi?'जहाँ अटकें, पूछें। पहले बुनियाद जाँचें, फिर समझें और अभ्यास करें।':'Tell your tutor where you’re stuck. Check the foundations, understand, and practise.'],
    revision:['',hi?'आज क्या दोहराएँ?':'Today’s revision',hi?'तय समय पर छोटे सवाल हल करके अपनी समझ पक्की करें।':'Revisit the questions that are ready for another try.'],
    notebook:['',hi?'गलतियों की कॉपी':'Mistake notebook',hi?'अपने पिछले उत्तर और हल की तुलना करें, फिर एक नया प्रश्न हल करें।':'Compare your answer with the worked solution, then try a new question on the same concept.'],
    exams:['',hi?'मॉक परीक्षाएँ':'Mock exams',hi?'अंग्रेज़ी या हिंदी में समयबद्ध गणित परीक्षा दें।':'Take a timed Class 6 maths paper in English or Hindi.'],
    explore:[hi?'हर विचार जुड़ा है':'EVERY IDEA CONNECTS',hi?'देखें गणित के विचार कैसे जुड़ते हैं।':'Discover how maths fits together.',hi?'3D मानचित्र में विचार चुनें और संबंध देखें।':'Move through the 3D concept map and explore the connections.']};
  return <div className="learner-app student-platform"><header className="platform-header"><button className="platform-brand" onClick={()=>go('home')}><Network size={25}/><span>concept atlas<span>.</span></span></button><nav aria-label="Main navigation">{links.map(([id,Icon,label])=><button key={id} className={navPage===id?'active':''} onClick={()=>navigate(id)} aria-current={navPage===id?'page':undefined}><Icon size={16}/><span>{label}</span></button>)}</nav><div className="platform-header-tools"><select aria-label="Platform language" value={language} onChange={e=>setLanguage(e.target.value)}><option value="en">English</option><option value="hi">हिंदी</option></select>{account?<button className="secondary-button" onClick={signOut}>{hi?'साइन आउट':'Sign out'}</button>:<button className="secondary-button" onClick={()=>go('login')}>{hi?'साइन इन':'Sign in'}</button>}</div></header>
    <main className={'platform-main '+(activePage==='explore'?'platform-map-main':'')}>{account&&protectedPage&&<div className="platform-page-heading">{titles[page][0]&&<span className="platform-eyebrow">{titles[page][0]}</span>}<h1>{titles[page][1]}</h1><p>{titles[page][2]}</p>{profile&&<span className="current-space-label">{profile.display_name} · {hi?'आपकी सीखने की जगह':'Your learning space'}</span>}</div>}
      {error&&<div className="alert danger" role="alert">{error}<button className="text-button" onClick={()=>setError('')}>Close</button></div>}
      {activePage==='home'&&<LandingPage language={language} onNavigate={navigate} signedIn={!!account}/>}
      {account!==undefined&&['login','signup'].includes(activePage)&&<StudentAuth key={activePage} mode={activePage} language={language} onNavigate={go} onSuccess={signIn}/>}
      {protectedPage&&(account===undefined||account&&!data)&&<div className="loading"><LoaderCircle className="spin"/> {hi?'आपकी जगह तैयार हो रही है…':'Getting your learning space ready…'}</div>}
      {account&&data&&<>
        {(page==='dashboard'||page==='progress')&&<StudentDashboard key={learner+page} learner={learner} data={data} language={language} summary={summary} profile={profile} onPractice={openPractice} onNavigate={navigate} onRefresh={()=>setRevision(n=>n+1)} progressOnly={page==='progress'}/>}
        {page==='practice'&&<TopicPractice key={learner} initialTopic={practiceTopic} data={data} learner={learner} language={language} summary={summary} onSaved={()=>setRevision(n=>n+1)} onNavigate={go}/>}
        {(page==='revision'||page==='notebook')&&<StudentRevision key={learner+page} learner={learner} language={language}
          daily={page==='revision'} data={data} onNavigate={navigate} onPractice={openPractice}/>}
        {page==='exams'&&<StudentExams key={learner} learner={learner} language={language} onNavigate={navigate}/>}
        {page==='chat'&&<BookChat key={learner} learnerCode={learner} data={data} preferredLanguage={language}/>}
        {page==='explore'&&<Explorer data={data} selected={selected} setSelected={setSelected} diagnose={()=>go('chat')}/>}
      </>}
    </main><footer className="platform-footer"><span>Concept Atlas</span><p>{hi?'थोड़ा और समझें। हर दिन।':'A little more understanding. Every day.'}</p><small>{hi?'\u0915\u0915\u094d\u0937\u093e 6 | \u0905\u0902\u0917\u094d\u0930\u0947\u091c\u093c\u0940 \u0914\u0930 \u0939\u093f\u0902\u0926\u0940':'Class 6 | English & Hindi'}</small></footer>
  </div>;
}
