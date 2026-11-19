import React from 'react';

export default function QuestionAnswer({question, value, onChange, disabled, language, id}) {
  const hi=language==='hi';
  const options=question.type==='mcq' ? [...question.text.matchAll(/(?:^|\s)([A-D]):\s*/g)] : [];
  if(options.length){
    return <fieldset className="study-options" disabled={disabled}>
      <legend>{hi?'एक उत्तर चुनें':'Choose one answer'}</legend>
      {options.map((option,index)=>{
        const letter=option[1];
        const label=question.text.slice(option.index+option[0].length,options[index+1]?.index)
          .trim().replace(/[;।.]$/,'');
        return <label key={letter} className={value===letter?'chosen':''}>
          <input type="radio" name={id} checked={value===letter} onChange={()=>onChange(letter)}/>
          <span><b>{letter}.</b> {label}</span>
        </label>;
      })}
    </fieldset>;
  }
  return <label className="study-number">{hi?'आपका उत्तर':'Your answer'}
    <input value={value} onChange={event=>onChange(event.target.value)} disabled={disabled}
      maxLength={500} inputMode="decimal" autoComplete="off"/>
  </label>;
}

export function questionPrompt(question){
  return question.type==='mcq' ? question.text.split(/\s+[A-D]:\s*/)[0] : question.text;
}
