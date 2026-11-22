import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require('../.dist/ui-test/node_modules/playwright');
const AxeBuilder=require('../.dist/ui-test/node_modules/@axe-core/playwright').default;
const base=process.env.UI_BASE||'http://127.0.0.1:8781';
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000}});
const page=await context.newPage(),checks=[],transcript=[],errors=[];
page.on('pageerror',e=>errors.push(e.message));
async function ask(text){
  const pending=page.waitForResponse(r=>r.url()===base+'/api/chat/message',{timeout:120000});
  await page.locator('#book-chat-input').fill(text);
  await page.locator('.book-chat-composer button').click();
  const response=await pending,data=await response.json();assert.equal(response.status(),200,JSON.stringify(data));
  await page.locator('.book-chat-composer button').waitFor({state:'visible'});
  await page.waitForFunction(()=>!document.querySelector('.book-chat-composer button').disabled||!document.querySelector('#book-chat-input').value);
  transcript.push({question:text,answer:data.message});return data.message;
}
try{
  const signup=await page.request.post(base+'/api/auth/signup',{data:{name:'Chat QA',email:`chat-qa-${Date.now()}@example.test`,password:'chat-quality-test-2026!'}});
  assert.equal(signup.status(),201);await page.goto(base+'/#chat');
  const first=await ask('What is an acute angle?');assert.equal(first.mode,'guided_local');checks.push('authored explanation instead of excerpt dump');
  const repair=await ask("I didn't understand");assert.equal(repair.concept.id,first.concept.id);assert.equal(repair.feedback_action,'still_confused');checks.push('natural confusion retains topic');
  const again=await ask("I still don't understand");assert.notDeepEqual(repair.paragraphs,again.paragraphs);assert.notEqual(again.mode,'practice_feedback');checks.push('fresh example, no prose grading');
  const topic=await ask('What is a square number?');assert.equal(topic.concept.id,'MATH6_C0009');checks.push('explicit topic change');
  await page.getByRole('button',{name:'New chat',exact:true}).click();
  const check=await ask('I am confused about acute angles');assert.equal(check.mode,'learning_check');
  await page.locator('#book-chat-input').waitFor();
  const interrupt=await ask('Explain a square number');assert.equal(interrupt.concept.id,'MATH6_C0009');checks.push('composer interrupts check');
  await page.getByRole('button',{name:'New chat',exact:true}).click();
  await page.getByRole('combobox',{name:'Language',exact:true}).selectOption('hi');
  const hindi=await ask('न्यून कोण क्या है?');const hindiRepair=await ask('समझ नहीं आया');
  assert.equal(hindiRepair.concept.id,hindi.concept.id);assert.equal(hindiRepair.feedback_action,'still_confused');
  assert.ok(hindiRepair.paragraphs.every(p=>/[\u0900-\u097f]/.test(p.text)));checks.push('Hindi contextual repair');
  const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
  assert.equal(axe.violations.filter(v=>['serious','critical'].includes(v.impact)).length,0);checks.push('chat accessibility');
  await page.screenshot({path:'reports/chat_quality_v2/chat-hindi.png',fullPage:true});
  assert.equal(errors.length,0);checks.push('no browser errors');
}finally{
  await fs.writeFile('reports/chat_quality_v2/browser.json',JSON.stringify({checks,errors,transcript},null,2));
  console.log(JSON.stringify({checks,errors}));await browser.close();
}
