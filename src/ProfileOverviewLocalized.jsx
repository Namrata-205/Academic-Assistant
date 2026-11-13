import React from 'react';
import {Sparkles,TrendingUp,TrendingDown,ArrowRight,Minus,BookOpen} from 'lucide-react';
import {profileText,profileTopic} from './profileText';

export default function ProfileOverviewLocalized({profile,language='en'}){
  if(!profile)return null;const ui=profileText(language),topic=value=>profileTopic(value,language);
  const strengths=profile.strong_subjects?.length?profile.strong_subjects:profile.strong_topics||[],practice=profile.weak_subjects?.length?profile.weak_subjects:profile.practice_topics||[];
  const trends={improving:{icon:TrendingUp,tone:'improving'},declining:{icon:TrendingDown,tone:'attention'},stable:{icon:Minus,tone:'steady'}};
  return <div className="student-home"><div className="student-welcome"><span className="student-avatar">{profile.display_name?.split(' ').filter(Boolean).map(n=>n[0]).filter((_,i)=>i!==1).join('')}</span><div><span className="student-home-kicker">{ui.kicker}</span><h2>{ui.hi}, {profile.display_name?.split(' ')[0]}!</h2><p>{ui.welcome}</p></div><Sparkles size={27}/></div>
    <div className="student-snapshot"><div><span>{ui.snapshot}</span><b>{profile.overall_percentage!=null&&profile.overall_percentage!==''?`${profile.overall_percentage}%`:ui.notRecorded}</b></div><div><span>{ui.answered}</span><b>{profile.answered!=null&&profile.answered!==''?profile.answered:ui.notRecorded}</b></div><div><span>{ui.suggestions}</span><b>{profile.revision_topics?.length||0}</b></div></div>
    <div className="student-focus-grid"><section><h3><Sparkles size={17}/>{ui.strengths}</h3>{strengths.length?<div className="subject-chips">{strengths.slice(0,5).map(s=><span key={s}>{topic(s)}</span>)}</div>:<p>{ui.noStrengths}</p>}</section><section><h3><BookOpen size={17}/>{ui.work}</h3>{practice.length?<div className="subject-chips practice">{practice.slice(0,5).map(s=><span key={s}>{topic(s)}</span>)}</div>:<p>{ui.noPractice}</p>}</section></div>
    <section className="student-progress"><div className="student-section-title"><h3>{ui.bySubject}</h3><span>{ui.earlier}</span></div><div className="subject-progress-grid">{(profile.subjects||[]).map(subject=>{const trend=trends[subject.trend]||{icon:Minus,tone:'unknown'},Icon=trend.icon;return <article key={subject.name}><b>{topic(subject.name)}</b><div className="subject-progress-score">{subject.percentage==null?'—':`${subject.percentage}%`}</div><div className="subject-progress-bar"><span style={{width:`${Math.max(0,Math.min(100,subject.percentage||0))}%`}}/></div><span className={'subject-trend '+trend.tone}><Icon size={13}/>{ui[subject.trend]||ui.unknown}</span></article>;})}</div><p className="student-snapshot-note">{ui.snapshotNote}</p></section>
    {profile.revision_topics?.length>0&&<details className="student-revision"><summary>{ui.practiceTopics}</summary><ol>{profile.revision_topics.map(value=><li key={value}><ArrowRight size={12}/><span>{topic(value)}</span></li>)}</ol></details>}
  </div>;
}
