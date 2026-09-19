// Browser: node tests/test_v30_depth_panel.cjs  (Playwright; BROWSER_CHANNEL=msedge|chrome, vazio = chromium do Playwright)
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const http=require('http'),fs=require('fs'),path=require('path'),os=require('os'),assert=require('assert');
const root=path.resolve(__dirname,'..');
(async()=>{
const types={'.js':'text/javascript','.html':'text/html','.png':'image/png','.json':'application/json'};
const server=http.createServer((req,res)=>{const file=path.join(root,decodeURIComponent(req.url.split('?')[0]));if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}fs.readFile(file,(err,data)=>{if(err){res.writeHead(404).end();return;}res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');res.end(data);});}).listen(0,'127.0.0.1');
await new Promise(r=>server.once('listening',r));
let browser;
try{
  const channel=process.env.BROWSER_CHANNEL;
  browser=await chromium.launch(channel?{channel,headless:true}:{headless:true});
  const page=await browser.newPage({viewport:{width:1050,height:1300}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/preview.html`);
  const toggle=page.locator('[data-action=depth-warp]');
  assert.equal(await toggle.getAttribute('data-on'),'0');
  const saved=await page.locator('#trajectory').inputValue();
  await toggle.click();
  assert.equal(await toggle.getAttribute('data-on'),'1');
  assert.match(await page.locator('.camera-view-label').textContent(),/rode o node/);
  assert.equal(await page.locator('#trajectory').inputValue(),saved,'toggle must not change the path');
  // Mesmo formato que o onExecuted entrega.
  await page.evaluate(async()=>{const meta=await (await fetch('/tests/fixtures/depth_preview/meta.json')).json();await window.h3Editor.setDepthPreview(meta,ref=>'/tests/fixtures/depth_preview/'+ref.filename);});
  await page.waitForTimeout(150);
  assert.match(await page.locator('.camera-view-label').textContent(),/última execução/);
  const stats=()=>page.locator('.camera-view canvas').evaluate(c=>{const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let magenta=0,yellow=0;for(let i=0;i<d.length;i+=4){if(d[i]===255&&d[i+1]===0&&d[i+2]===255)magenta++;if(d[i]>200&&d[i+1]>160&&d[i+2]<90)yellow++;}return {magenta,yellow,url:c.toDataURL()};});
  // Keyframe 1: pose inicial, praticamente sem buracos.
  await page.locator('.marker[data-index="0"]').click();await page.waitForTimeout(80);
  const first=await stats();
  assert.ok(first.yellow>500,'subject visible in warp');
  // Keyframe 3 (90° no preview.html): muito buraco magenta.
  await page.locator('.marker[data-index="2"]').click();await page.waitForTimeout(80);
  const last=await stats();
  assert.ok(last.magenta>first.magenta*3&&last.magenta>2000,`holes grow with orbit ${first.magenta} -> ${last.magenta}`);
  // Editar a órbita reprojeta na hora, sem nova execução.
  await page.locator('input.number[data-field=azimuth]').fill('20');await page.waitForTimeout(80);
  const edited=await stats();
  assert.notEqual(edited.url,last.url);assert.ok(edited.magenta<last.magenta);
  await page.screenshot({path:path.join(os.tmpdir(),'h3_v30_depth_panel.png')});
  // Desligar volta ao manequim; a prévia fica guardada para religar.
  await toggle.click();
  assert.match(await page.locator('.camera-view-label').textContent(),/manequim/);
  assert.equal((await stats()).magenta,0);
  await toggle.click();await page.waitForTimeout(50);
  assert.ok((await stats()).magenta>0);
  await page.locator('select[aria-label="Idioma / Language"]').selectOption('English');
  assert.match(await page.locator('.camera-view-label').textContent(),/geometry from last run/);
  assert.deepEqual(errors,[]);
  console.log('v30 depth panel: ok',{first:first.magenta,last:last.magenta,edited:edited.magenta});
}finally{await browser?.close();server.close();}
})().catch(e=>{console.error(e);process.exit(1);});
