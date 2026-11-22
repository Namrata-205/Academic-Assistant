import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),{chromium}=require('../.dist/ui-test/node_modules/playwright');
const AxeBuilder=require('../.dist/ui-test/node_modules/@axe-core/playwright').default;
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();
const base='http://127.0.0.1:8785',checks=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
async function nav(name){await page.getByRole('navigation',{name:'Main navigation',exact:true}).getByRole('button',{name,exact:true}).click();}
async function post(path,data){const r=await page.request.post(base+'/api'+path,{data});assert.ok(r.ok(),await r.text());return r.json();}
async function scan(name){const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();const bad=axe.violations.filter(v=>['serious','critical'].includes(v.impact));assert.equal(bad.length,0,JSON.stringify(bad.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))));checks.push(name);}
try{
 await post('/auth/signup',{name:'Ten Chapter QA',email:`ten-${Date.now()}@example.test`,password:'ten-chapter-test-2026!'});
 const account=(await (await page.request.get(base+'/api/auth/session')).json()).account,learner=account.learner;
 const data=await (await page.request.get(base+'/api/bootstrap')).json();
 assert.equal(data.nodes.length,144);assert.equal(data.links.length,211);assert.equal(data.chapters.length,10);assert.ok(data.links.every(e=>e.confidence===null));assert.ok(data.bank.every(q=>!('answer' in q)));checks.push('v2 bootstrap, private keys, unscored graph confidence');
 await page.goto(base+'/#dashboard');await page.locator('.chapter-card').first().waitFor();assert.equal(await page.locator('.chapter-card').count(),10);await scan('ten-chapter dashboard');
 await page.screenshot({path:'reports/curriculum_v2/dashboard.png',fullPage:true});
 for(const chapter of data.chapters){
  await nav('Practice');await page.getByRole('combobox',{name:'Chapter',exact:true}).selectOption(chapter.id);
  assert.equal(await page.locator('.practice-topic-card').count(),data.nodes.filter(n=>n.chapter===chapter.id).length);
 }
 checks.push('all ten practice filters match graph concepts');
 await page.locator('.practice-topic-card').first().getByRole('button',{name:'Start practice',exact:true}).click();await page.locator('.practice-question-text').waitFor();
 await page.locator('.study-number input').fill('99999');await page.getByRole('button',{name:'Check answer',exact:true}).click();await page.getByRole('status').filter({hasText:'Let’s revisit this one'}).waitFor();checks.push('chapter ten practice grades');
 await nav('Revision');await page.getByRole('button',{name:'Try a similar question',exact:true}).first().waitFor();checks.push('new-chapter mistake reaches revision');
 await nav('Mock exams');await page.getByRole('group',{name:'Choose your chapters',exact:true}).waitFor();assert.equal(await page.locator('.exam-chapter-picker input[type=checkbox]').count(),10);
 for(const chapter of data.chapters){
  const exam=await post('/exams',{learner,mode:chapter.id,language:'en'});assert.equal(exam.questions.length,4);assert.ok(exam.questions.every(q=>data.nodes.find(n=>n.id===q.concept_id).chapter===chapter.id));assert.ok(exam.questions.every(q=>!('correct_answer' in q)));await post('/exams/'+exam.id+'/submit',{learner,language:'en'});
 }
 const mixed=await post('/exams',{learner,mode:'mixed',language:'hi'});assert.equal(mixed.questions.length,20);for(const ch of data.chapters)assert.equal(mixed.questions.filter(q=>data.nodes.find(n=>n.id===q.concept_id).chapter===ch.id).length,2);await post('/exams/'+mixed.id+'/submit',{learner,language:'hi'});checks.push('ten chapter exams and balanced mixed exam');
 await nav('Concept map');await page.getByLabel('Chapter',{exact:true}).selectOption('CH07');assert.equal(await page.locator('.concept-directory-list button').count(),14);await page.getByRole('combobox',{name:'Language',exact:true}).selectOption('hi');assert.ok(!/[A-Za-z]/.test(await page.locator('.concept-directory-detail h3').innerText()));
 await page.locator('.visual-map-disclosure summary').click();await page.locator('.inspector h2').waitFor();await scan('Hindi v2 concept graph');
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await scan('mobile v2 graph');assert.equal(errors.length,0);
}finally{await fs.writeFile('reports/curriculum_v2/browser.json',JSON.stringify({checks,errors},null,2));console.log(JSON.stringify({checks,errors}));await browser.close();}
