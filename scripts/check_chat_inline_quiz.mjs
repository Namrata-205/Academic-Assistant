import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require('../.dist/ui-test/node_modules/playwright');
const AxeBuilder=require('../.dist/ui-test/node_modules/@axe-core/playwright').default;
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();
const base='http://127.0.0.1:8783',checks=[],errors=[];
page.on('pageerror',e=>errors.push(e.message));
async function clickResponse(action){const pending=page.waitForResponse(r=>r.url()===base+'/api/chat/message',{timeout:120000});await action();const r=await pending;assert.equal(r.status(),200,await r.text());await page.locator('.chat-thinking').waitFor({state:'hidden'});return r.json();}
async function ask(text){await page.locator('#book-chat-input').fill(text);return clickResponse(()=>page.locator('.book-chat-composer button').click());}
async function answer(){
 const card=page.locator('.chat-tutor-question').last();
 const radios=card.getByRole('radio');if(await radios.count())await radios.first().check();else await card.locator('input').fill('99999');
 return clickResponse(()=>card.getByRole('button',{name:/^(Check answer|उत्तर भेजें)$/}).click());
}
try{
 const signup=await page.request.post(base+'/api/auth/signup',{data:{name:'Quiz View QA',email:`quiz-${Date.now()}@example.test`,password:'inline-quiz-test-2026!'}});assert.equal(signup.status(),201);await page.goto(base+'/#chat');
 let value=await ask('What is an acute angle?');assert.equal(value.message.mode,'learning_check');checks.push('new topic asks an understanding question before explaining');
 let count=0;while(value.message.check_question){value=await answer();assert.ok(++count<=3);assert.equal(await page.locator('.chat-user-message').count(),1);}
 assert.ok(value.message.paragraphs.length);assert.ok(await page.locator('.chat-quiz-feedback').count()>0);checks.push('initial answers and grading stay in their cards');
 const messages=await page.locator('.chat-book-message').count();assert.ok(value.message.practice_question);value=await answer();assert.equal(value.append_message,false);assert.equal(await page.locator('.chat-book-message').count(),messages);assert.equal(await page.locator('.chat-user-message').count(),1);checks.push('practice answer adds no user or assistant chat bubble');
 await page.reload();await page.getByRole('button',{name:'Saved chats',exact:true}).click();await page.locator('.book-chat-history button').first().click();await page.locator('.chat-quiz-feedback').last().waitFor();assert.equal(await page.locator('.chat-user-message').count(),1);checks.push('inline results survive reopening');
 value=await clickResponse(()=>page.locator('.chat-book-message').last().getByRole('button',{name:'I still don’t understand',exact:true}).click());assert.equal(value.message.mode,'guided_local');assert.equal(value.message.practice_question,undefined);assert.ok(!value.message.paragraphs.some(p=>p.kind==='textbook_excerpt'));checks.push('confusion with a foundation focus gives teaching instead of excerpts');
 await page.screenshot({path:'reports/chat_inline_quiz_v4/desktop.png',fullPage:true});
 await page.getByRole('button',{name:'New chat',exact:true}).click();await page.getByRole('combobox',{name:'Language',exact:true}).selectOption('hi');value=await ask('न्यून कोण क्या है?');assert.equal(value.message.mode,'learning_check');
 value=await clickResponse(()=>page.getByRole('button',{name:'अभी समझाइए',exact:true}).click());assert.ok(value.message.paragraphs.length);checks.push('Hindi check-first and skip-to-explanation');
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 const axe=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();assert.equal(axe.violations.filter(v=>['serious','critical'].includes(v.impact)).length,0);checks.push('mobile layout and accessibility');assert.equal(errors.length,0);
}finally{await fs.writeFile('reports/chat_inline_quiz_v4/browser.json',JSON.stringify({checks,errors},null,2));console.log(JSON.stringify({checks,errors}));await browser.close();}
