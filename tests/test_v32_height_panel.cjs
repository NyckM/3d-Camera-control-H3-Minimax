// node tests/test_v32_height_panel.cjs — altura no painel: card próprio, edição, JSON e prévia do warp.
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
  const page=await browser.newPage({viewport:{width:1050,height:1400}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/preview.html`);
  await page.waitForTimeout(200);
  // quatro cards: o que gira em cima, o que desloca embaixo
  const cards=await page.$$eval('.controls > div',els=>els.map(e=>e.querySelector('.heading').textContent.trim()));
  assert.deepEqual(cards,['Órbita','Elevação','Distância','Altura']);
  // o disco de órbita cabe inteiro no card (a alça fica na borda)
  assert.ok(await page.$eval('.dial',d=>{const r=d.getBoundingClientRect(),c=d.closest('div').getBoundingClientRect();return r.bottom<=c.bottom+.5&&r.top>=c.top-.5;}),'dial clipped');
  // keyframe 1 é a fonte: altura travada
  await page.locator('.marker[data-index="0"]').click();await page.waitForTimeout(80);
  assert.equal(await page.locator('input.number[data-field=height]').isDisabled(),true);
  await page.locator('.marker[data-index="1"]').click();await page.waitForTimeout(80);
  await page.locator('input.number[data-field=height]').fill('-0.6');
  await page.waitForTimeout(120);
  const traj=JSON.parse(await page.locator('#trajectory').inputValue());
  assert.equal(traj[1].height,-0.6);
  assert.equal(traj[0].height,0,'source keyframe stays at zero');
  // fora de alcance é limitado, não aceito
  await page.locator('input.number[data-field=height]').fill('9');
  await page.waitForTimeout(120);
  assert.equal(JSON.parse(await page.locator('#trajectory').inputValue())[1].height,3);
  await page.locator('input.number[data-field=height]').fill('-0.6');await page.waitForTimeout(120);
  // altura muda a prévia do warp sem nova execução
  await page.locator('[data-action=depth-warp]').click();
  await page.evaluate(async()=>{const meta=await (await fetch('/tests/fixtures/depth_preview/meta.json')).json();await window.h3Editor.setDepthPreview(meta,ref=>'/tests/fixtures/depth_preview/'+ref.filename);});
  await page.waitForTimeout(200);
  const shot=()=>page.locator('.camera-view canvas').evaluate(c=>c.toDataURL());
  const low=await shot();
  await page.locator('input.number[data-field=height]').fill('0.6');await page.waitForTimeout(150);
  assert.notEqual(await shot(),low,'boom must reproject the preview');
  // idioma chinês traduz o painel
  await page.locator('select[aria-label="Idioma / Language"]').selectOption('中文');
  await page.waitForTimeout(120);
  const zh=await page.$$eval('.controls > div',els=>els.map(e=>e.querySelector('.heading').textContent.trim()));
  assert.deepEqual(zh,['环绕','仰角','距离','升降']);
  await page.screenshot({path:path.join(os.tmpdir(),'h3_v32_height.png')});
  assert.deepEqual(errors,[]);
  console.log('v32 height panel: ok');
}finally{await browser?.close();server.close();}
})().catch(e=>{console.error(e);process.exit(1);});
