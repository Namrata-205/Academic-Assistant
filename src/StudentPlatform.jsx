import React,{useEffect,useState} from 'react';
import {Network,Home,LayoutDashboard,Target,TrendingUp,MessageCircle,LoaderCircle} from 'lucide-react';
import {studentApi,currentLearner} from './studentApi';
import LandingPage from './LandingPage';
import StudentDashboard from './StudentDashboard';
import TopicPractice from './TopicPractice';
import BookChat from './BookChat';
import './platform.css';

const pages=['home','dashboard','practice','progress','chat','explore'];
const fromHash=()=>pages.includes(location.hash.slice(1))?location.hash.slice(1):'home';

export default function StudentPlatform({Explorer}){
  const [page,setPage]=useState(fromHash),[data,setData]=useState(null),[error,setError]=useState(''),[learner,setLearner]=useState(currentLearner),[profile,setProfile]=useState(null),[summary,setSummary]=useState(null),[revision,setRevision]=useState(0),[selected,setSelected]=useState('MATH6_C0024');
  const [language,setLanguage]=useState(()=>localStorage.getItem('atlas-ui-language')==='hi'?'hi':'en');
  const hi=language==='hi';
  function go(next){location.hash=next;setPage(next);window.scrollTo({top:0,behavior:'smooth'});}
  useEffect(()=>{const handler=()=>setPage(fromHash());addEventListener('hashchange',handler);return()=>removeEventListener('hashchange',handler);},[]);
  useEffect(()=>{studentApi('/bootstrap').then(setData).catch(e=>setError(e.message));},[]);
  useEffect(()=>{let live=true;setSummary(null);studentApi('/practice/analytics?learner='+encodeURIComponent(learner)).then(r=>{if(live)setSummary(r);}).catch(e=>{if(live)setError(e.message);});studentApi('/profile?learner='+encodeURIComponent(learner)).then(r=>{if(live)setProfile(r.profile);}).catch(()=>{});return()=>{live=false;};},[learner,revision]);
  useEffect(()=>{localStorage.setItem('atlas-ui-language',language);localStorage.setItem('atlas-chat-language',language);},[language]);
  async function switchProfile(id){let code;
    if(id===null){code=localStorage.getItem('atlas-guest-learner')||'learner-'+crypto.randomUUID();localStorage.setItem('atlas-guest-learner',code);}
    else{if(!profile)localStorage.setItem('atlas-guest-learner',learner);code=(await studentApi('/profile/select',{learner,student_id:id})).learner;}
    localStorage.setItem('atlas-learner-code',code);setProfile(null);setLearner(code);setError('');
  }
  const links=[['home',Home,hi?'मुख्य पृष्ठ':'Home'],['dashboard',LayoutDashboard,hi?'मेरी जगह':'My space'],['practice',Target,hi?'अभ्यास':'Practice'],['progress',TrendingUp,hi?'मेरी प्रगति':'My progress'],['chat',MessageCircle,hi?'शिक्षक से पूछें':'Ask my book'],['explore',Network,hi?'विचारों का मानचित्र':'Concept map']];
  const titles={dashboard:[hi?'आपकी सीख, आपके लिए':'YOUR SPACE, YOUR PACE',profile?(hi?`नमस्ते, ${profile.display_name.split(' ')[0]}!`:`Welcome back, ${profile.display_name.split(' ')[0]}.`):(hi?'आज कुछ नया सीखें।':'Let’s make a little progress today.'),hi?'अपनी ताकतें पहचानें और सीखने का अगला कदम चुनें।':'Explore your strengths, revisit a foundation, and choose your next step.'],
    practice:[hi?'थोड़ा अभ्यास, अधिक आत्मविश्वास':'PRACTICE WITH PURPOSE',hi?'आपका अगला विषय कौन सा है?':'What will you work on today?',hi?'विषय और भाषा चुनें। हर प्रश्न का उत्तर उसी कार्ड में दें।':'Choose a topic and a language. Answer each question in its own card.'],
    progress:[hi?'हर प्रयास मायने रखता है':'EVERY ATTEMPT COUNTS',hi?'अपनी सीखने की यात्रा देखें।':'See your learning take shape.',hi?'आपके वास्तविक अभ्यासों के परिणाम, विषय और भाषा के अनुसार।':'Your saved practice results, across topics, languages, and time.'],
    chat:[hi?'सवाल पूछें, समझकर सीखें':'ASK. UNDERSTAND. TRY AGAIN.',hi?'चलो, साथ समझते हैं।':'Let’s work through it together.',hi?'जहाँ अटकें, पूछें। पहले बुनियाद जाँचें, फिर समझें और अभ्यास करें।':'Tell your tutor where you’re stuck. Check the foundations, understand, and practise.'],
    explore:[hi?'हर विचार जुड़ा है':'EVERY IDEA CONNECTS',hi?'देखें गणित के विचार कैसे जुड़ते हैं।':'Discover how maths fits together.',hi?'3D मानचित्र में विचार चुनें और संबंध देखें।':'Move through the 3D concept map and explore the connections.']};
  return <div className="learner-app student-platform"><header className="platform-header"><button className="platform-brand" onClick={()=>go('home')}><Network size={25}/><span>concept atlas<span>.</span></span></button><nav aria-label="Main navigation">{links.map(([id,Icon,label])=><button key={id} className={page===id?'active':''} onClick={()=>go(id)} aria-current={page===id?'page':undefined}><Icon size={16}/><span>{label}</span></button>)}</nav><div className="platform-header-tools"><select aria-label="Platform language" value={language} onChange={e=>setLanguage(e.target.value)}><option value="en">English</option><option value="hi">हिंदी</option></select><button className="profile-avatar" aria-label={profile?.display_name||'Open my profile'} title={profile?.display_name||'My profile'} onClick={()=>go('dashboard')}>{profile?.display_name?.slice(0,1)||'You'}</button></div></header>
    <main className={'platform-main '+(page==='explore'?'platform-map-main':'')}>{page!=='home'&&<div className="platform-page-heading"><span className="platform-eyebrow">{titles[page][0]}</span><h1>{titles[page][1]}</h1><p>{titles[page][2]}</p>{profile&&<span className="current-space-label">{profile.display_name} · {hi?'आपकी सीखने की जगह':'Your learning space'}</span>}</div>}
      {error&&<div className="alert danger" role="alert">{error}<button className="text-button" onClick={()=>setError('')}>Close</button></div>}
      {!data?<div className="loading"><LoaderCircle className="spin"/> {hi?'आपकी जगह तैयार हो रही है…':'Getting your learning space ready…'}</div>:<>
        {page==='home'&&<LandingPage language={language} onNavigate={go}/>}
        {(page==='dashboard'||page==='progress')&&<StudentDashboard key={learner+page} learner={learner} data={data} language={language} summary={summary} onSwitch={switchProfile} onNavigate={go} onRefresh={()=>setRevision(n=>n+1)} progressOnly={page==='progress'}/>}
        {page==='practice'&&<TopicPractice key={learner} data={data} learner={learner} language={language} summary={summary} onSaved={()=>setRevision(n=>n+1)} onNavigate={go}/>}
        {page==='chat'&&<BookChat key={learner} data={data} preferredLanguage={language}/>}
        {page==='explore'&&<Explorer data={data} selected={selected} setSelected={setSelected} diagnose={()=>go('chat')}/>}
      </>}
    </main><footer className="platform-footer"><span>Concept Atlas</span><p>{hi?'थोड़ा और समझें। हर दिन।':'A little more understanding. Every day.'}</p><small>{hi?'\u0915\u0915\u094d\u0937\u093e 6 | \u0905\u0902\u0917\u094d\u0930\u0947\u091c\u093c\u0940 \u0914\u0930 \u0939\u093f\u0902\u0926\u0940':'Class 6 | English & Hindi'}</small></footer>
  </div>;
}
