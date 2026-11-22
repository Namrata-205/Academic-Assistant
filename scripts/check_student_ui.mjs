import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {chromium}=require('../.dist/ui-test/node_modules/playwright');
const AxeBuilder=require('../.dist/ui-test/node_modules/@axe-core/playwright').default;
const output=process.env.UI_OUTPUT||'.dist/ui-qa';await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless:true});
const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
const page=await context.newPage(),checks=[],errors=[];page.on('pageerror',error=>errors.push(error.message));
const base=process.env.UI_BASE||'http://127.0.0.1:8765',email=`ui-${Date.now()}@example.test`,password='UI-test-password-2026!';
async function scan(name){
  await page.evaluate(()=>document.fonts.ready);
  const results=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']).analyze();
  checks.push({name,violations:results.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),name+' has horizontal page overflow');
}
async function nav(name){await page.getByRole('navigation',{name:'Main navigation',exact:true}).getByRole('button',{name,exact:true}).click();await page.getByRole('heading',{level:1,name:name==='Dashboard'?'Welcome back, Aanya.':name,exact:true}).waitFor();}
try{
  await page.goto(base+'/#signup');await page.getByLabel('Full name',{exact:true}).waitFor();
  await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.className),'skip-link');
  await page.evaluate(()=>document.activeElement.blur());
  await page.screenshot({path:output+'/registration-desktop.png',fullPage:true});await scan('registration desktop');
  await page.setViewportSize({width:390,height:844});await scan('registration mobile');await page.screenshot({path:output+'/registration-mobile.png',fullPage:true});await page.setViewportSize({width:1440,height:1000});
  await page.locator('form').getByRole('button',{name:'Create account',exact:true}).click();
  await page.getByText('Enter your name.',{exact:true}).waitFor();assert.equal(await page.evaluate(()=>document.activeElement.id),'auth-name');
  await page.getByLabel('Full name',{exact:true}).fill('Aanya Test');await page.getByLabel('Email address',{exact:true}).fill(email);
  await page.getByLabel('Password',{exact:true}).fill(password);
  await page.getByRole('button',{name:'Show password',exact:true}).click();assert.equal(await page.locator('#auth-password').getAttribute('type'),'text');
  await page.getByRole('button',{name:'Hide password',exact:true}).click();
  await page.locator('form').getByRole('button',{name:'Create account',exact:true}).click();
  await page.getByRole('heading',{name:'Welcome back, Aanya.',exact:true}).waitFor();await page.locator('.chapter-card').first().waitFor();
  await page.waitForFunction(()=>document.querySelector('.student-stat strong')?.textContent==='0');
  await page.screenshot({path:output+'/dashboard-desktop.png',fullPage:true});await scan('dashboard desktop');
  await page.locator('.chapter-card').filter({hasText:'Lines and Angles'}).click();
  assert.equal(await page.getByLabel('Chapter',{exact:true}).inputValue(),'CH02');await scan('practice chapter');
  const {account}=await (await page.request.get(base+'/api/auth/session')).json();
  let practice=await (await page.request.post(base+'/api/practice/sessions',{data:{learner:account.learner,concept_id:'MATH6_C0025',language:'en'}})).json();
  for(let i=0;i<8&&practice.question;i++)practice=await (await page.request.post(base+'/api/practice/sessions/'+practice.id+'/answer',{data:{learner:account.learner,ordinal:practice.question.ordinal,response:practice.question.type==='mcq'?'A':'2'}})).json();
  assert.ok(practice.completed);await page.reload();
  await nav('My progress');await page.getByRole('combobox',{name:/View an attempt/}).waitFor();
  await page.getByText('View scores as a table',{exact:true}).click();await scan('populated progress chart and table');
  for(const name of ['My progress','Revision','Mock exams','Concept map']){await nav(name);await page.waitForTimeout(150);await scan(name+' desktop');}
  assert.ok(await page.getByRole('button',{name:/right angle Lines and Angles/i}).count()>0);
  await page.getByLabel('Find a concept',{exact:true}).fill('acute');await page.locator('.concept-directory-list').getByRole('button',{name:'acute angle Lines and Angles',exact:true}).click();
  await page.getByRole('heading',{name:'acute angle',exact:true}).waitFor();
  await nav('Ask my book');await page.getByLabel('Ask your textbook a question',{exact:true}).fill('I am confused about acute angles.');
  await page.getByRole('button',{name:'Ask',exact:true}).click();await page.getByRole('button',{name:'Check answer',exact:true}).waitFor({timeout:60000});
  await scan('chat diagnostic question');
  await page.getByLabel('Your answer',{exact:true}).fill('2');await page.getByRole('button',{name:'Check answer',exact:true}).click();
  await page.getByRole('radio').first().waitFor();assert.ok(await page.getByRole('radio').count()>=2);
  await page.getByRole('button',{name:'Explain now',exact:true}).last().click();
  await page.getByRole('button',{name:'Simpler explanation',exact:true}).last().waitFor({timeout:60000});await scan('chat explanation');
  await page.screenshot({path:output+'/chat-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.getByRole('button',{name:'Open navigation',exact:true}).click();assert.equal(await page.getByRole('button',{name:'Close navigation',exact:true}).getAttribute('aria-expanded'),'true');
  await page.keyboard.press('Escape');assert.equal(await page.getByRole('button',{name:'Open navigation',exact:true}).getAttribute('aria-expanded'),'false');
  await page.getByRole('button',{name:'Open navigation',exact:true}).click();await nav('Dashboard');
  await page.screenshot({path:output+'/dashboard-mobile.png',fullPage:true});await scan('dashboard mobile');
  for(const name of ['Practice','My progress','Ask my book','Revision','Mock exams','Concept map']){
    await page.getByRole('button',{name:'Open navigation',exact:true}).click();await nav(name);await page.waitForTimeout(100);await scan(name+' mobile');
  }
  await page.getByRole('button',{name:'Open navigation',exact:true}).click();
  await page.getByLabel('Language',{exact:true}).selectOption('hi');await page.getByRole('navigation').getByRole('button',{name:'मेरी जगह',exact:true}).click();
  await page.getByRole('heading',{name:'नमस्ते, Aanya!',exact:true}).waitFor();await scan('dashboard Hindi mobile');
  await page.screenshot({path:output+'/dashboard-hindi-mobile.png',fullPage:true});
  await page.setViewportSize({width:320,height:800});await scan('dashboard Hindi 320px');await page.setViewportSize({width:390,height:844});
  await page.getByRole('button',{name:'मेनू खोलें',exact:true}).click();await page.getByRole('button',{name:'साइन आउट',exact:true}).click();
  await page.locator('.student-landing').waitFor();
  await page.goto(base+'/#login');await page.getByLabel('ईमेल या स्कूल का उपयोगकर्ता नाम',{exact:true}).fill(email);await page.getByLabel('पासवर्ड',{exact:true}).fill(password);
  await page.locator('form').getByRole('button',{name:'साइन इन करें',exact:true}).click();await page.getByRole('heading',{name:'नमस्ते, Aanya!',exact:true}).waitFor();
  await page.getByLabel('भाषा',{exact:true}).selectOption('en');
  await page.route('**/api/bootstrap',route=>route.fulfill({status:503,contentType:'application/json',body:'{"error":"Test connection failure"}'}));
  await page.reload();await page.getByRole('button',{name:'Try again',exact:true}).waitFor();await scan('bootstrap failure recovery');
  await page.unroute('**/api/bootstrap');await page.getByRole('button',{name:'Try again',exact:true}).click();await page.locator('.chapter-card').first().waitFor();
  assert.equal(errors.length,0,errors.join('\n'));
}finally{
  const report={checks,consoleErrors:errors,seriousOrCritical:checks.flatMap(c=>c.violations).filter(v=>['serious','critical'].includes(v.impact)).length};
  await fs.writeFile(process.env.UI_REPORT||'reports/ui_accessibility_results.json',JSON.stringify(report,null,2));
  console.log(JSON.stringify({screensChecked:checks.length,seriousOrCritical:report.seriousOrCritical,consoleErrors:errors}));
  await browser.close();
}
assert.equal(checks.flatMap(c=>c.violations).filter(v=>['serious','critical'].includes(v.impact)).length,0,'Accessibility violations: see reports/ui_accessibility_results.json');
