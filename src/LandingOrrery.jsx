import React from 'react';

const orbits = [
  {name: 'teal', size: '66%', tilt: '-24deg', pitch: '57deg', duration: '12s', delay: '-2s'},
  {name: 'amber', size: '80%', tilt: '31deg', pitch: '66deg', duration: '17s', delay: '-8s'},
  {name: 'blue', size: '93%', tilt: '83deg', pitch: '71deg', duration: '21s', delay: '-13s'},
];

export default function LandingOrrery() {
  return <div className="landing-visual landing-orrery" aria-hidden="true">
    <div className="orrery-shadow"/>
    <div className="orrery-stage">
      <div className="orrery-core"/>
      {orbits.map(({name, size, tilt, pitch, duration, delay}) =>
        <div className={`orrery-orbit ${name}`} key={name}
          style={{'--size':size, '--tilt':tilt, '--pitch':pitch, '--duration':duration, '--delay':delay}}>
          <div className="orrery-ring"/>
          <div className="orrery-carrier"><span className="orrery-bead"/></div>
        </div>
      )}
    </div>
  </div>;
}
