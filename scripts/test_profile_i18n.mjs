import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {build} from 'esbuild';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {profileText,profileTopic} from '../src/profileText.js';

await build({entryPoints:['src/ProfileOverviewLocalized.jsx'],bundle:true,platform:'node',format:'cjs',packages:'external',outfile:'.dist/profile-overview-ssr.cjs',logLevel:'silent'});
const require=createRequire(import.meta.url),Profile=require('../.dist/profile-overview-ssr.cjs').default;
const profile={display_name:'Aanya A. Mehta',overall_percentage:'45.9',answered:'74',strong_topics:['Squares, Cubes, etc'],weak_subjects:['Geometry and Measure','Number','Units of Measurement','Basic Arithmetic'],revision_topics:['Mental Multiplication and Division','Place Value','Time','Prime Numbers and Prime Factors'],subjects:[{name:'Number',percentage:48.3,trend:'stable'},{name:'Algebra',percentage:null,trend:'insufficient data'},{name:'Geometry & measurement',percentage:35.7,trend:'insufficient data'}]};
const hi=renderToStaticMarkup(React.createElement(Profile,{profile,language:'hi'}));
for(const label of ['आपकी सीखने की जगह','नमस्ते','आपकी ताकतें','वर्ग, घन आदि','ज्यामिति और मापन','प्रदर्शन स्थिर है','स्थानीय मान','45.9%','48.3%','Aanya'])assert.ok(hi.includes(label),label);
for(const label of ['Your strengths','Earlier learning snapshot','Holding steady','Not enough history','Squares, Cubes, etc','Practice suggestions'])assert.ok(!hi.includes(label),label);
const english=renderToStaticMarkup(React.createElement(Profile,{profile,language:'en'}));
assert.ok(english.includes('Your strengths'));assert.ok(english.includes('45.9%'));
for(const key of Object.keys(profileText('en')))assert.ok(profileText('hi')[key],key);
for(const topic of [...profile.revision_topics,...profile.weak_subjects,...profile.strong_topics])assert.notEqual(profileTopic(topic,'hi'),topic);
console.log('Hindi profile rendering, topic labels, English fallback and unchanged report values passed.');
