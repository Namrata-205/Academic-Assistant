import React from 'react';

export default function AngleDiagram({diagram,language='en'}){
  if(diagram?.kind!=='angle')return null;
  const hi=language==='hi',degrees=Number(diagram.degrees),rotation=Number(diagram.rotation)||0;
  if(![90,180].includes(degrees))return null;
  // Geometry is numeric data, never executable markup returned by a model.
  const point=a=>[100+68*Math.cos(a*Math.PI/180),100-68*Math.sin(a*Math.PI/180)];
  const a=point(rotation),b=point(rotation+degrees);
  const label=hi?'चित्र में दिखाया गया कोण पहचानें।':'Identify the angle shown by the rays.';
  return <svg viewBox="0 0 200 200" role="img" aria-label={label} style={{width:220,maxWidth:'100%',display:'block',color:'currentColor'}}>
    <title>{label}</title>
    <g stroke="currentColor" strokeWidth="3" fill="none"><path d={`M ${a[0]} ${a[1]} L 100 100 L ${b[0]} ${b[1]}`}/>
      {degrees===90&&<path transform={`rotate(${-rotation} 100 100)`} d="M 116 100 L 116 84 L 100 84" strokeWidth="2"/>}
    </g><circle cx="100" cy="100" r="3" fill="currentColor"/>
    <text x="90" y="120" fill="currentColor" fontSize="14">O</text>
  </svg>;
}
