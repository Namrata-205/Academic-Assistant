import React, {useState} from 'react';
import {RotateCw} from 'lucide-react';

const solids = [
  {mark: '∠', color: 'teal', position: 'angles'},
  {mark: '1²', color: 'amber', position: 'patterns'},
  {mark: '½', color: 'blue', position: 'numbers'}
];

export default function LandingSolids({language}) {
  const [angle, setAngle] = useState(-24);
  const hi = language === 'hi';
  const control = hi ? 'आकृतियाँ घुमाएँ' : 'Rotate the shapes';

  return <div className="landing-visual solid-visual">
    <div className="solid-stage" aria-hidden="true">
      <div className="solid-orbit"/>
      {solids.map(({mark, color, position}) =>
        <div key={mark} className={`solid-position ${position}`}>
          <div className={`math-solid ${color}`} style={{'--turn': angle + 'deg'}}>
            {['front', 'right', 'back', 'left', 'top', 'bottom'].map(face =>
              <span key={face} className={'solid-face ' + face}>{['front', 'back'].includes(face) ? mark : ''}</span>
            )}
          </div>
        </div>
      )}
    </div>
    <label className="solid-control">
      <RotateCw size={17}/><span>{control}</span>
      <input type="range" min="-180" max="180" value={angle} onChange={event => setAngle(Number(event.target.value))}/>
    </label>
  </div>;
}
