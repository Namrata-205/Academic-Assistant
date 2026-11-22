import React,{useRef,useState} from 'react';
import {ArrowRight,BookOpen,Check,Eye,EyeOff,ShieldCheck} from 'lucide-react';
import {studentApi} from './studentApi';

export default function StudentAuth({mode,language,onNavigate,onSuccess}){
  const signup=mode==='signup',hi=language==='hi',formRef=useRef(null);
  const [error,setError]=useState(''),[fields,setFields]=useState({}),[busy,setBusy]=useState(false),[visible,setVisible]=useState(false);
  const action=signup?(hi?'खाता बनाएँ':'Create account'):(hi?'साइन इन करें':'Sign in');
  async function submit(event){
    event.preventDefault();setError('');
    const values=Object.fromEntries(new FormData(event.currentTarget)),issues={};
    if(signup){
      if(!values.name?.trim())issues.name=hi?'अपना नाम लिखें।':'Enter your name.';
      if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email?.trim()||''))issues.email=hi?'सही ईमेल पता लिखें।':'Enter a valid email address.';
    }else if(!values.identifier?.trim())issues.identifier=hi?'ईमेल या स्कूल का उपयोगकर्ता नाम लिखें।':'Enter your email or school username.';
    if(!values.password||signup&&values.password.length<12)issues.password=hi?(signup?'पासवर्ड कम से कम 12 अक्षरों का रखें।':'पासवर्ड लिखें।'):signup?'Use at least 12 characters for your password.':'Enter your password.';
    setFields(issues);
    if(Object.keys(issues).length){formRef.current.elements.namedItem(Object.keys(issues)[0])?.focus();return;}
    setBusy(true);
    try{const {account}=await studentApi('/auth/'+mode,values);onSuccess(account);}
    catch(err){setError(err.message);}
    finally{setBusy(false);}
  }
  function field(name,label,props={}){
    return <div className="auth-field"><label htmlFor={'auth-'+name}>{label}</label>
      <input id={'auth-'+name} name={name} required disabled={busy} aria-invalid={!!fields[name]}
        aria-describedby={fields[name]?'auth-'+name+'-error':undefined} {...props}/>
      {fields[name]&&<p id={'auth-'+name+'-error'} className="field-error">{fields[name]}</p>}
    </div>;
  }
  return <div className="auth-layout"><aside className="auth-intro">
    <span className="auth-intro-icon"><BookOpen size={30} aria-hidden="true"/></span>
    <span className="platform-eyebrow">{hi?'अपनी गति से सीखें':'A LITTLE PROGRESS, EVERY DAY'}</span>
    <h2>{hi?'गणित समझने की अपनी जगह।':'Your space to make sense of maths.'}</h2>
    <p>{hi?'सवाल पूछें, एक छोटा अभ्यास करें और अगला कदम साफ़ देखें।':'Ask a question, try a little practice, and find a clear next step.'}</p>
    <ul>{[hi?'कक्षा 6 के तीन NCERT अध्याय':'Three Class 6 NCERT chapters',hi?'अंग्रेज़ी और हिंदी में सहायता':'Support in English and Hindi',hi?'आपका अभ्यास और प्रगति साथ रहें':'Your practice and progress, saved'].map(t=><li key={t}><Check size={18} aria-hidden="true"/>{t}</li>)}</ul>
    <div className="auth-intro-note"><ShieldCheck size={22} aria-hidden="true"/><span>{hi?'अपने खाते से अपनी सीख जारी रखें।':'Pick up where you left off with your own account.'}</span></div>
  </aside><section className="student-auth" aria-labelledby="auth-heading">
    <span className="platform-eyebrow">{signup?(hi?'एक नई शुरुआत':'LET’S GET STARTED'):(hi?'फिर से स्वागत है':'WELCOME BACK')}</span>
    <h1 id="auth-heading">{signup?(hi?'अपना खाता बनाएँ':'Create your account'):(hi?'अपनी सीख जारी रखें':'Continue your learning')}</h1>
    <p>{signup?(hi?'शुरू करने के लिए बस ये तीन बातें।':'Just three details to get started.'):(hi?'अपने ईमेल या स्कूल से मिले उपयोगकर्ता नाम से साइन इन करें।':'Sign in with your email or school-issued username.')}</p>
    {error&&<div className="alert danger" role="alert">{error}</div>}
    {Object.keys(fields).length>0&&<p role="alert" className="auth-error-summary">{hi?'नीचे बताए गए विवरण सही करें।':'Please check the highlighted fields below.'}</p>}
    <form ref={formRef} onSubmit={submit} noValidate aria-busy={busy}>
      {signup? <>{field('name',hi?'पूरा नाम':'Full name',{autoComplete:'name',maxLength:80,placeholder:hi?'आपका पूरा नाम':'Your full name'})}
        {field('email',hi?'ईमेल पता':'Email address',{type:'email',autoComplete:'email',maxLength:254,spellCheck:false,autoCapitalize:'none',placeholder:'you@example.com'})}</>:
        field('identifier',hi?'ईमेल या स्कूल का उपयोगकर्ता नाम':'Email or school username',{autoComplete:'username',maxLength:254,spellCheck:false,autoCapitalize:'none',placeholder:hi?'ईमेल या उपयोगकर्ता नाम':'you@example.com or school username'})}
      <div className="auth-field"><label htmlFor="auth-password">{hi?'पासवर्ड':'Password'}</label>
        <div className="password-field"><input id="auth-password" name="password" type={visible?'text':'password'} required disabled={busy}
          autoComplete={signup?'new-password':'current-password'} minLength={signup?12:undefined} maxLength={128}
          aria-invalid={!!fields.password} aria-describedby={fields.password?'auth-password-error':signup?'password-hint':undefined}/>
          <button type="button" disabled={busy} className="password-toggle" aria-label={visible?(hi?'पासवर्ड छिपाएँ':'Hide password'):(hi?'पासवर्ड दिखाएँ':'Show password')}
            aria-pressed={visible} onClick={()=>setVisible(v=>!v)}>{visible?<EyeOff size={20} aria-hidden="true"/>:<Eye size={20} aria-hidden="true"/>}</button></div>
        {fields.password?<p className="field-error" id="auth-password-error">{fields.password}</p>:signup&&<p className="field-hint" id="password-hint">{hi?'कम से कम 12 अक्षर रखें।':'Use at least 12 characters.'}</p>}
      </div>
      <button className="primary-button auth-submit" disabled={busy}>{busy?(hi?'कृपया प्रतीक्षा करें…':'Please wait…'):action}<ArrowRight size={18} aria-hidden="true"/></button>
      <span role="status" className="sr-only">{busy?(hi?'आपका अनुरोध भेजा जा रहा है।':'Submitting your details.'):''}</span>
    </form>
    <p className="auth-switch">{signup?(hi?'पहले से खाता है?':'Already have an account?'):(hi?'पहली बार आए हैं?':'New here?')} <button className="text-button" onClick={()=>onNavigate(signup?'login':'signup')}>{signup?(hi?'साइन इन करें':'Sign in'):(hi?'खाता बनाएँ':'Create account')}</button></p>
  </section></div>;
}
