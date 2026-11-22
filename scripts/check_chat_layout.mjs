import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),{chromium}=require('../.dist/ui-test/node_modules/playwright');
const AxeBuilder=require('../.dist/ui-test/node_modules/@axe-core/playwright').default;
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:950}}),page=await context.newPage();
const base='http://127.0.0.1:8784',checks=[],errors=[];page.on('pageerror',e=>errors.push(e.message));
async function response(action){const pending=page.waitForResponse(r=>r.url()===base+'/api/chat/message',{timeout:120000});await action();const r=await pending;assert.equal(r.status(),200,await r.text());await page.locator('.chat-thinking').waitFor({state:'hidden'});return r.json();}
async function ask(text){await page.locator('#book-chat-input').fill(text);return response(()=>page.locator('.book-chat-composer button').click());}
async function dimensions(name){
 const card=page.locator('.chat-tutor-question').last();
 const field=card.locator('.study-number');
 if(await field.count()){
   const label=await field.locator('label').boundingBox(),input=await field.locator('input').boundingBox();
   assert.ok(input.y>=label.y+label.height+7,'answer box and focus ring clear the label');
   assert.ok(input.width>=100&&input.width<=132,'numeric answer has a compact usable width');
   checks.push(name+' numeric field spacing and width');
 }else{
   for(const label of await card.locator('.study-options label').all()){
     const box=await label.boundingBox(),radio=await label.locator('input').boundingBox(),text=await label.locator('span').boundingBox();
     assert.ok(radio.width<=22&&radio.width>=18);assert.ok(radio.x-box.x<22,'radio stays at the left');assert.ok(text.x>=radio.x+radio.width+8);
   }
   checks.push(name+' radio alignment');
 }
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
}
async function latestAtStart(){assert.ok(await page.locator('.chat-book-message').last().evaluate(el=>{const container=el.closest('.book-chat-messages'),area=container.getBoundingClientRect(),top=el.getBoundingClientRect().top;return top>=area.top-1&&top<area.bottom-65;}),'beginning of the new answer is visible');}
try{
 const signup=await page.request.post(base+'/api/auth/signup',{data:{name:'Layout QA',email:`layout-${Date.now()}@example.test`,password:'layout-test-2026!'}});assert.equal(signup.status(),201);await page.goto(base+'/#chat');
 let value=await ask('What is an acute angle?'),step=0;
 while(value.message.check_question){
   await latestAtStart();await dimensions('desktop question '+(++step));
   if(step===1)await page.screenshot({path:'reports/chat_layout_v5/numeric-desktop.png',fullPage:true});
   if(step===2){await page.screenshot({path:'reports/chat_layout_v5/options-desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});await dimensions('mobile');await page.screenshot({path:'reports/chat_layout_v5/options-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:950});}
   const card=page.locator('.chat-tutor-question').last(),radios=card.getByRole('radio');
   if(await radios.count())await radios.first().check();else await card.locator('.study-number input').fill('2');
   value=await response(()=>card.getByRole('button',{name:'Check answer',exact:true}).click());assert.ok(step<=3);
 }
 await latestAtStart();checks.push('explanation opens at its first paragraph');
 const card=page.locator('.chat-tutor-question').last(),radios=card.getByRole('radio');
 if(await radios.count())await radios.first().check();else await card.locator('.study-number input').fill('2');
 await card.getByRole('button',{name:'Check answer',exact:true}).scrollIntoViewIfNeeded();
 const top=await page.locator('.book-chat-messages').evaluate(el=>el.scrollTop);
 value=await response(()=>card.getByRole('button',{name:'Check answer',exact:true}).click());assert.equal(value.append_message,false);
 const after=await page.locator('.book-chat-messages').evaluate(el=>el.scrollTop);assert.ok(Math.abs(after-top)<60,'inline grading keeps reading position');checks.push('inline answer does not jump to footer');
 await ask('Just explain a vertex without questions');await latestAtStart();checks.push('new chat reply opens at its beginning');
 const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();assert.equal(axe.violations.filter(v=>['serious','critical'].includes(v.impact)).length,0);checks.push('accessibility');assert.equal(errors.length,0);
}finally{await fs.writeFile('reports/chat_layout_v5/browser.json',JSON.stringify({checks,errors},null,2));console.log(JSON.stringify({checks,errors}));await browser.close();}
