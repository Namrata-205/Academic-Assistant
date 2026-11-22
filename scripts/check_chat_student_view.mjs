import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require('../.dist/ui-test/node_modules/playwright');
const AxeBuilder=require('../.dist/ui-test/node_modules/@axe-core/playwright').default;
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000}});
const page=await context.newPage(),checks=[],errors=[];const base='http://127.0.0.1:8782';
page.on('pageerror',e=>errors.push(e.message));
async function ask(text){
  const pending=page.waitForResponse(r=>r.url()===base+'/api/chat/message',{timeout:120000});
  await page.locator('#book-chat-input').fill(text);await page.locator('.book-chat-composer button').click();
  const response=await pending;assert.equal(response.status(),200);await page.locator('.chat-thinking').waitFor({state:'hidden'});
  return (await response.json()).message;
}
async function layout(){
  const card=page.locator('.chat-book-message').last();
  assert.equal(await card.locator('.chat-tutor-summary,.chat-terms,.chat-teaching-heading,.inline-source-links').count(),0);
  const text=await card.innerText();assert.ok(!/Foundations included|No saved answer evidence|Imported reports|Graph relationships await|Original worked example:/.test(text));
  assert.ok(await card.evaluate(el=>{
    const explanation=el.querySelector('.chat-explanation'),disclaimer=el.querySelector('.chat-answer-disclaimer'),actions=el.lastElementChild;
    return explanation&&disclaimer&&actions.getAttribute('aria-label')&&Boolean(explanation.compareDocumentPosition(disclaimer)&Node.DOCUMENT_POSITION_FOLLOWING)&&Boolean(disclaimer.compareDocumentPosition(actions)&Node.DOCUMENT_POSITION_FOLLOWING);
  }));
  assert.ok((await card.locator('.chat-answer-disclaimer').innerText()).length<400);
}
try{
  const signup=await page.request.post(base+'/api/auth/signup',{data:{name:'Student View QA',email:`view-${Date.now()}@example.test`,password:'student-view-test-2026!'}});assert.equal(signup.status(),201);
  await page.goto(base+'/#chat');
  const response=await ask('What is a vertex?');assert.equal(response.mode,'guided_local');
  assert.ok(response.paragraphs.some(p=>p.text.includes('finger')));await layout();checks.push('hands-on vertex explanation and compact footer');
  const card=page.locator('.chat-book-message').last();await card.locator('details summary').click();assert.ok(await card.locator('details a').count()>0);await card.locator('details summary').click();checks.push('references remain available');
  await card.getByRole('button',{name:'Simpler explanation',exact:true}).click();await page.locator('.chat-thinking').waitFor({state:'hidden',timeout:120000});await layout();checks.push('feedback works at end of answer');
  await page.screenshot({path:'reports/chat_student_explanations_v3/desktop.png',fullPage:true});
  await page.getByRole('button',{name:'New chat',exact:true}).click();await page.getByRole('combobox',{name:'Language',exact:true}).selectOption('hi');
  await ask('शीर्ष क्या है?');await layout();checks.push('Hindi student answer');
  await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));checks.push('mobile wrapping');
  const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();assert.equal(axe.violations.filter(v=>['serious','critical'].includes(v.impact)).length,0);checks.push('no serious accessibility violations');
  await page.screenshot({path:'reports/chat_student_explanations_v3/mobile.png',fullPage:true});assert.equal(errors.length,0);
}finally{
  await fs.writeFile('reports/chat_student_explanations_v3/browser.json',JSON.stringify({checks,errors},null,2));console.log(JSON.stringify({checks,errors}));await browser.close();
}
