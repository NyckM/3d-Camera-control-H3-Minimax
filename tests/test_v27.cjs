const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const http=require('http'),fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..');
(async()=>{
const server=http.createServer((req,res)=>{const file=path.join(root,decodeURIComponent(req.url.split('?')[0]));if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}fs.readFile(file,(err,data)=>{if(err){res.writeHead(404).end();return;}res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.html')?'text/html':'application/octet-stream');res.end(data);});}).listen(0,'127.0.0.1');
await new Promise(r=>server.once('listening',r));
let browser;
try{
browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'msedge',headless:true});
const page=await browser.newPage({viewport:{width:1050,height:1300}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(`http://127.0.0.1:${server.address().port}/preview.html`);
const bytes=await page.evaluate(async()=>{const c=document.createElement('canvas');c.width=160;c.height=90;const ctx=c.getContext('2d');const stream=c.captureStream(24);const rec=new MediaRecorder(stream,{mimeType:'video/webm'});const chunks=[];rec.ondataavailable=e=>chunks.push(e.data);const done=new Promise(r=>rec.onstop=r);rec.start();let n=0;await new Promise(resolve=>{const timer=setInterval(()=>{ctx.fillStyle=n%2?'#206040':'#602040';ctx.fillRect(0,0,160,90);ctx.fillStyle='white';ctx.fillRect(n*3,20,15,20);if(++n>=36){clearInterval(timer);resolve();}},42);});rec.stop();await done;stream.getTracks().forEach(t=>t.stop());return Array.from(new Uint8Array(await new Blob(chunks,{type:'video/webm'}).arrayBuffer()));});
// MediaRecorder WebM has an indefinite duration until the browser seeks the end.
await page.locator('input[type=file]').setInputFiles({name:'reference.webm',mimeType:'video/webm',buffer:Buffer.from(bytes)});
await page.waitForTimeout(700);
assert.ok(await page.locator('video').evaluate(v=>Number.isFinite(v.duration)&&v.readyState>=2));
await page.locator('[data-action=play]').click();await page.waitForTimeout(450);
const before=await page.locator('video').evaluate(v=>v.currentTime);
await page.locator('input.number[data-field=azimuth]').fill('72');
await page.waitForTimeout(200);
assert.equal(await page.locator('video').evaluate(v=>v.paused),false,'editing stopped playback');
assert.ok(await page.locator('video').evaluate(v=>v.currentTime)>before);
assert.equal(JSON.parse(await page.locator('#trajectory').inputValue())[1].azimuth,72);
await page.locator('[data-action=add]').click();
assert.equal(JSON.parse(await page.locator('#trajectory').inputValue()).length,4);
assert.equal(await page.locator('video').evaluate(v=>v.paused),false);
await page.locator('[data-action=play]').click();
assert.equal(await page.locator('video').evaluate(v=>v.paused),true);
const track=await page.locator('.track').boundingBox();await page.mouse.click(track.x+track.width*.25,track.y+3);await page.waitForTimeout(200);
const progress=await page.locator('video').evaluate(v=>v.currentTime/v.duration);assert.ok(Math.abs(progress-.25)<.03,'scrub sync');
await page.locator('[data-role=duration]').selectOption('243');
await page.locator('[data-action=play]').click();await page.waitForTimeout(150);
assert.ok(await page.locator('video').evaluate(v=>Math.abs(v.playbackRate-v.duration/((243-1)/24)))<.001);
await page.locator('[data-action=play]').click();
// UI regression: view changes must not change the generated camera path.
const saved=await page.locator('#trajectory').inputValue();
assert.equal(await page.locator('.camera-view').isVisible(),true);
const imageBefore=await page.locator('.camera-view canvas').evaluate(c=>c.toDataURL());
await page.locator('[data-action=camera-view]').click();assert.equal(await page.locator('.camera-view').isVisible(),false);
await page.locator('[data-action=camera-view]').click();assert.equal(await page.locator('.camera-view').isVisible(),true);
const oldLeft=await page.locator('.spatial-key[data-index="1"]').evaluate(el=>el.style.left);
await page.locator('[data-action=zoom-in]').click();
assert.notEqual(await page.locator('.spatial-key[data-index="1"]').evaluate(el=>el.style.left),oldLeft);
assert.equal(await page.locator('#trajectory').inputValue(),saved);
await page.locator('[data-action=expand]').click();
assert.equal(await page.locator('.viewport').evaluate(el=>el.clientHeight),560);
await page.locator('[data-action=view-reset]').click();
const key=page.locator('.spatial-key[data-index="1"]');
await key.scrollIntoViewIfNeeded();const box=await key.boundingBox();
await page.mouse.move(box.x+12,box.y+12);await page.mouse.down();await page.mouse.move(box.x+62,box.y-18,{steps:8});await page.mouse.up();
const changed=JSON.parse(await page.locator('#trajectory').inputValue());const previous=JSON.parse(saved);
assert.notEqual(changed[1].azimuth,previous[1].azimuth);assert.notEqual(changed[1].elevation,previous[1].elevation);
assert.equal(changed[1].time,previous[1].time);assert.deepEqual(changed[0],previous[0]);
assert.notEqual(await page.locator('.camera-view canvas').evaluate(c=>c.toDataURL()),imageBefore);
assert.equal(changed[1].distance,previous[1].distance);
const first=await page.locator('.spatial-key[data-index="0"]').boundingBox();
await page.mouse.move(first.x+12,first.y+12);await page.mouse.down();await page.mouse.move(first.x+45,first.y+30);await page.mouse.up();
assert.deepEqual(JSON.parse(await page.locator('#trajectory').inputValue())[0],previous[0]);
await page.locator('.spatial-key[data-index="1"]').focus();await page.keyboard.press('ArrowRight');
assert.equal(JSON.parse(await page.locator('#trajectory').inputValue())[1].azimuth,Math.round(changed[1].azimuth+1));
await page.locator('[data-action=expand]').click();
await page.locator('[data-action=play]').click();
await page.locator('[data-action=zoom-out]').click();
assert.equal(await page.locator('video').evaluate(v=>v.paused),false);
await page.locator('[data-action=play]').click();
console.log('PASS: zoom does not mutate path, expanded canvas, direct keyframe drag, first frame protection, keyboard controls, zoom during playback');
await page.screenshot({path:path.join(require('os').tmpdir(),'h3-v27-tested.png'),fullPage:true});
await page.locator('[data-action=clearref]').click();
assert.equal(await page.locator('.video-reference').isVisible(),false);
assert.equal(await page.locator('video').getAttribute('src'),null);
assert.equal(await page.locator('[aria-label="Modo de referência / Reference mode"]').inputValue(),'Freeze Frame');
assert.deepEqual(errors,[]);
console.log('PASS: video decode, play/pause, live edit, keyframe insertion, scrub synchronization, duration mapping, clear reference, Freeze default.');
console.log('errors',errors);
}finally{await browser?.close();server.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});


