// Original implementation inspired by the referenced camera editor layout.
// All drawing and state stay local; no external assets or API requests.
export function createCameraEditor({read, write, duration, interpolation, setDuration, linkedImage, elevationRange, switches}) {
  const root=document.createElement('section');root.className='h3cam';
  root.innerHTML=`<style>
  .h3cam{--purple:#8035ff;--muted:#a5a4ae;box-sizing:border-box;width:100%;height:860px;overflow:auto;padding:16px;background:#191919;color:#f4f4f5;font:14px system-ui,sans-serif;border-radius:12px;user-select:none}
  .h3cam *{box-sizing:border-box}.h3cam header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;font-size:20px}.h3cam header small{color:#929199;border:2px solid #777780;border-radius:50%;font-size:13px;padding:0 6px;margin-left:7px}
  .h3cam button,.h3cam select,.h3cam input{font:inherit;color:inherit}.h3cam button{cursor:pointer}.h3cam button:disabled{opacity:.3;cursor:default}.h3cam .icon{background:none;border:0;color:#aaa;font-size:23px;padding:2px 7px}.h3cam .icon:hover{color:white}.h3cam .stage{background:#212121;border-radius:12px;overflow:hidden}.h3cam .viewport{position:relative;height:360px}.h3cam .scene{display:block;width:100%;height:100%;touch-action:none}.h3cam .hint{position:absolute;bottom:12px;left:12px;right:12px;pointer-events:none;color:#aaa;background:#292929e0;border-radius:5px;padding:8px;font-size:11px;width:max-content;max-width:calc(100% - 24px)}
  .h3cam .transport{border-top:1px solid #2b2b2b;padding:18px 15px}.h3cam .track{position:relative;height:32px;touch-action:none;margin:8px 7px}.h3cam .rail{position:absolute;top:14px;left:0;right:0;height:5px;border-radius:4px;background:#47464b}.h3cam .marker{position:absolute;top:11px;width:12px;height:12px;background:#a6a5ac;transform:translateX(-50%) rotate(45deg);border:0;padding:0;touch-action:none}.h3cam .marker.active{background:var(--purple)}.h3cam .cursor{position:absolute;top:-1px;height:33px;width:1px;background:var(--purple);pointer-events:none}.h3cam .cursor:before{content:'';position:absolute;top:0;left:-4px;width:9px;height:9px;background:var(--purple);border-radius:50%}.h3cam .labels{display:flex;justify-content:space-between;color:#81808a;font:12px ui-monospace,monospace;margin-bottom:14px}.h3cam .bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.h3cam .play{background:#f5f5f5;color:#151515;border:0;border-radius:5px;width:40px;height:40px;font-size:21px}.h3cam .time{color:#adadb8;font:14px ui-monospace,monospace;margin-right:auto}.h3cam .bar label{color:var(--muted);font-size:12px;display:flex;align-items:center;gap:7px}.h3cam select{background:#222;border:1px solid #3c3c40;border-radius:5px;padding:7px 9px;max-width:100px}.h3cam .selected{color:#9657ff;margin-top:12px;font-size:13px}.h3cam .controls{display:grid;grid-template-columns:1fr 1.4fr 1.4fr;gap:18px;margin-top:17px}.h3cam .heading{display:flex;justify-content:space-between;color:var(--muted);gap:5px}.h3cam .number{width:61px;background:transparent;border:0;color:white;text-align:right;padding:0;appearance:textfield;-moz-appearance:textfield}.h3cam .number::-webkit-inner-spin-button{display:none}.h3cam .range{accent-color:var(--purple);width:100%;margin:17px 0;background:#292929}.h3cam .dial{display:block;width:90px;height:90px;margin-top:13px;touch-action:none;cursor:grab}.h3cam .viewlabel{font-size:11px;color:#aaa;margin-top:3px}.h3cam footer{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:13px;border-top:1px solid #303034;padding-top:10px;color:#96949e;font-size:11px}.h3cam .reference{border:1px solid #444;background:#222;color:#bbb;border-radius:5px;padding:6px 9px;font-size:11px}.h3cam .error{color:#ffb4a6;padding-top:6px;font-size:12px}.h3cam button:focus-visible,.h3cam input:focus-visible,.h3cam canvas:focus-visible{outline:2px solid #b992ff;outline-offset:3px}
  </style>
  <header><span>Camera motion <small title="Planeja a câmera e gera instruções para o H3. Bruxos do VFX.">i</small></span><button class="icon" data-action="reset" title="Reset camera path" aria-label="Reset camera path">◇</button></header>
  <div class="stage"><div class="viewport"><canvas class="scene" aria-label="Cena e trajetória da câmera"></canvas><div class="hint">Arraste a câmera na horizontal para orbitar, na vertical para elevar · o eixo trava no primeiro movimento · role para distância · arraste o fundo para olhar ao redor</div></div>
  <div class="transport"><div class="track" role="slider" tabindex="0" aria-label="Camera animation playhead" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div class="rail"></div><div class="markers"></div><div class="cursor"></div></div>
  <div class="labels"><span>0:00</span><span data-role="end"></span></div>
  <div class="bar"><button class="play" data-action="play" aria-label="Play camera preview">▶</button><span class="time"></span><label>Keyframes<select aria-label="Keyframe count" data-role="count"></select></label><label>Duração<select aria-label="Video duration" data-role="duration"><option value="124">5.17s</option><option value="243">10.13s</option><option value="362">15.08s</option></select></label><button class="icon" data-action="remove" aria-label="Remove selected keyframe" title="Remover keyframe">♜</button></div>
  <div class="selected"></div></div></div>
  <div class="controls"><div><div class="heading"><label for="">Azimuth</label><input class="number" aria-label="Azimuth degrees" type="number" data-field="azimuth" min="-11520" max="11520" step="1"></div><canvas class="dial" role="slider" tabindex="0" aria-label="Azimuth dial" aria-valuemin="-11520" aria-valuemax="11520"></canvas><div class="viewlabel"></div></div>
  <div><div class="heading"><span>Elevation</span><input class="number" aria-label="Elevation degrees" type="number" data-field="elevation" min="-89" max="89" step="1"></div><input class="range" aria-label="Elevation slider" data-field="elevation" type="range" min="-89" max="89" step="1"></div>
  <div><div class="heading"><span>Distance</span><input class="number" aria-label="Camera distance" type="number" data-field="distance" min="0.1" max="4" step="0.05"></div><input class="range" aria-label="Distance slider" data-field="distance" type="range" min="0.1" max="4" step="0.01"></div></div>
  <footer><span data-role="refsrc">Referência: nenhuma</span><button class="reference" data-action="image">Imagem de referência</button><input type="file" accept="image/*" hidden></footer><div class="error" role="status"></div><div class="note" role="status"></div>`;
  // Keep the same controls and handlers, with an independent studio layout.
  const extraStyle=document.createElement('style');
  extraStyle.textContent=`
  .h3cam{background:#17171c;border:1px solid #303039;border-radius:18px;padding:20px;--purple:#8c4cff}
  .h3cam header{margin-bottom:16px;gap:12px}.h3cam .brand{display:flex;align-items:center;gap:11px}.h3cam .brandmark{width:40px;height:40px;display:block;object-fit:contain;filter:drop-shadow(0 0 10px #8c4cff35)}.h3cam .brand b{font-size:18px;letter-spacing:3px;display:block}.h3cam .brand em{display:block;font-style:normal;color:#8c899b;font-size:11px;letter-spacing:1px;margin-top:2px}
  .h3cam .bar{padding:10px 12px;border:1px solid #34313f;border-radius:10px;margin-bottom:12px;background:#201e28;gap:18px}.h3cam .bar label{font-size:12px}.h3cam .bar .icon{margin-left:auto;font-size:12px;color:#b8afcb;border:1px solid #464052;border-radius:6px;padding:7px 10px}.h3cam select{background:#18171e;border-color:#494051;max-width:110px}.h3cam .reference{border-color:#315e55;color:#8cdfcd;background:#19302a;padding:9px 12px;border-radius:8px}
  .h3cam .stage{border:1px solid #34313e;border-radius:12px;background:#1d1d23}.h3cam .viewport{height:360px;background:radial-gradient(ellipse at 50% 50%,#26252e 0%,#1d1d23 70%)}.h3cam .previewbar{position:absolute;top:12px;right:12px;display:flex;align-items:center;gap:12px;padding:6px 7px 6px 12px;background:#17151fd9;border:1px solid #42354f;border-radius:30px}.h3cam .play{width:34px;height:34px;border-radius:50%;background:#8c4cff;color:white;font-size:17px;box-shadow:0 0 18px #8c4cff30}.h3cam .time{font-size:12px;color:#c1b6d4;margin:0}.h3cam .hint{background:transparent;color:#827e90;font-size:10px}
  .h3cam .transport{padding:14px 18px 11px;background:#19181f;border-top-color:#34303d}.h3cam .rail{height:3px;background:#3f394b}.h3cam .marker{width:11px;height:11px;border-radius:3px;background:#4a9d8d}.h3cam .marker.active{background:#a878ff;box-shadow:0 0 10px #8c4cff60}.h3cam .labels{margin-bottom:8px}.h3cam .selectionrow{display:flex;align-items:center;justify-content:space-between;gap:8px}.h3cam .selected{margin:0;color:#baa0ef;font-size:11px}.h3cam .selectionrow .icon{font-size:11px;color:#a59bab;border:1px solid #3a3340;border-radius:5px;padding:5px 8px}
  .h3cam .controls{grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:12px}.h3cam .controls>div{padding:12px;background:#211e29;border:1px solid #393142;border-radius:10px;min-width:0}.h3cam .controls>div:first-child{border-top:2px solid #19bda1}.h3cam .controls>div:nth-child(2){border-top:2px solid #6b66db}.h3cam .controls>div:last-child{border-top:2px solid #9958ff}.h3cam .heading{font-size:12px}.h3cam .number{width:48px}.h3cam .dial{width:74px;height:74px;margin:8px auto 0}.h3cam .viewlabel{text-align:center;font-size:10px}.h3cam .range{margin-top:26px}.h3cam .controls>div:first-child .range{accent-color:#19c7a7}.h3cam footer{margin-top:10px;border:0;padding-top:0;font-size:10px}.h3cam .note{color:#ffd48a;font-size:11px;padding-top:5px;min-height:14px}.h3cam .clearref{background:none;border:0;color:#8cdfcd;font:inherit;text-decoration:underline;padding:0 0 0 6px}.h3cam .pure{border:1px solid #464052;background:#221f2b;color:#c9bfe0;border-radius:6px;padding:7px 10px;font-size:12px}.h3cam .switches{display:flex;gap:8px;flex-wrap:wrap;padding:8px 12px;border:1px solid #34313f;border-radius:10px;margin-bottom:12px;background:#1c1a24;align-items:center}.h3cam .switches b{font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:#7d7590;font-weight:600;margin-right:2px}.h3cam .sw{border:1px solid #464052;background:#221f2b;color:#8d85a0;border-radius:6px;padding:6px 10px;font-size:12px;cursor:pointer}.h3cam .sw[data-on='1']{border-color:#8c4cff;background:#2e2340;color:#e6dcff}.h3cam .closure{margin-left:auto;font-size:11px;color:#7d7590}.h3cam .closure[data-on='1']{color:#19c7a7}
  `;
  root.append(extraStyle);
  const header=root.querySelector('header'),bar=root.querySelector('.bar'),viewport=root.querySelector('.viewport');
  const reset=root.querySelector('[data-action=reset]'),reference=root.querySelector('[data-action=image]');
  const brand=document.createElement('div');brand.className='brand';
  const mark=document.createElement('img');mark.className='brandmark';mark.alt='';mark.decoding='async';
  mark.src=new URL('./logo.png',import.meta.url).href;
  const wordmark=document.createElement('span');wordmark.innerHTML='<b>CAMERA H3</b><em>BRUXOS DO VFX</em>';
  brand.append(mark,wordmark);
  header.replaceChildren(brand,reference);
  reset.textContent='↺ Reiniciar';
  const pure=document.createElement('button');pure.className='pure';pure.dataset.action='pure';
  pure.textContent='⟳ Órbita pura';pure.title='Zera a elevação de todos os keyframes, mantendo o azimute.';
  bar.append(pure,reset);
  const previewbar=document.createElement('div');previewbar.className='previewbar';
  previewbar.append(root.querySelector('.time'),root.querySelector('.play'));viewport.append(previewbar);
  root.insertBefore(bar,root.querySelector('.stage'));
  const selectionrow=document.createElement('div');selectionrow.className='selectionrow';
  const remove=root.querySelector('[data-action=remove]');remove.textContent='− Remover ponto';
  selectionrow.append(root.querySelector('.selected'),remove);root.querySelector('.transport').append(selectionrow);
  const controls=root.querySelector('.controls'),cards=[...controls.children];controls.replaceChildren(cards[2],cards[1],cards[0]);
  cards[2].querySelector('.heading span').textContent='Distância';cards[1].querySelector('.heading span').textContent='Elevação';cards[0].querySelector('.heading label').textContent='Órbita';
  const $=s=>root.querySelector(s),canvas=$('.scene'),ctx=canvas.getContext('2d'),dial=$('.dial'),dc=dial.getContext('2d'),track=$('.track');
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)),rad=v=>v*Math.PI/180,snapTime=v=>Math.round(v*1000)/1000;
  // Never below what the current keyframe already holds, so a wide old path stays editable.
  const elevLimit=()=>Math.min(89,Math.max(elevationRange?.()||30,Math.abs(path[selected]?.elevation||0)));
  const defaults=()=>[{time:0,azimuth:0,elevation:0,distance:1},{time:.5,azimuth:45,elevation:10,distance:1},{time:1,azimuth:90,elevation:0,distance:.8}];
  let path=defaults(),selected=1,playhead=.5,lastRaw='',yaw=.55,pitch=.45,image=null,playing=false,raf=0,disposed=false,start=0;
  let manualImage=null,linkedImg=null,linkedSrc='',poll=0;
  let drag=null,dialAngle=0,markerDrag=null,cameraScreen=[0,0],hoverCamera=false;
  const format=t=>`${Math.floor(t/60)}:${(t%60).toFixed(1).padStart(4,'0')}`;
  for(let i=2;i<=24;i++){$('[data-role=count]').add(new Option(String(i),String(i)));}
  function poseAt(t) {
    if(t<=path[0].time)return path[0];
    const j=path.findIndex(p=>p.time>=t);if(j<0)return path.at(-1);
    const a=path[j-1],b=path[j];let u=(t-a.time)/(b.time-a.time);
    if(interpolation()==='smooth')u=u*u*(3-2*u);
    return Object.fromEntries(['azimuth','elevation','distance'].map(k=>[k,a[k]+(b[k]-a[k])*u]));
  }
  function save(rebuild=true) {lastRaw=JSON.stringify(path);write(lastRaw);update(rebuild);}
  function stop(){playing=false;cancelAnimationFrame(raf);$('.play').textContent='▶';$('.play').setAttribute('aria-label','Play camera preview');}
  function choose(i){stop();selected=i;playhead=path[i].time;update();}
  function update(rebuild=true) {
    selected=clamp(selected,0,path.length-1);
    if(rebuild){
      $('.markers').replaceChildren();
      path.forEach((p,i)=>{
        const b=document.createElement('button');b.className='marker'+(selected===i?' active':'');b.style.left=`${p.time*100}%`;
        b.setAttribute('aria-label',`Keyframe ${i+1} at ${format(p.time*duration())}`);b.dataset.index=i;b.title=`Keyframe ${i+1}`;
        b.addEventListener('pointerdown',e=>{e.stopPropagation();choose(i);markerDrag={i};track.setPointerCapture(e.pointerId);});
        b.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(i);}});
        $('.markers').append(b);
      });
    }else path.forEach((p,i)=>{const b=$(`.marker[data-index="${i}"]`);if(b)b.style.left=`${p.time*100}%`;});
    $('.cursor').style.left=`${playhead*100}%`;
    track.setAttribute('aria-valuenow',String(Math.round(playhead*100)));
    $('.time').textContent=`${format(playhead*duration())} / ${format(duration())}`;
    $('[data-role=end]').textContent=format(duration());
    $('[data-role=count]').value=path.length;
    $('[data-role=duration]').value=String(Math.round(duration()*24)+1);
    $('[data-action=remove]').disabled=selected===0||path.length<=2;
    $('.selected').textContent=selected===0?'Keyframe 1: imagem original · posição inicial fixa':`Keyframe ${selected+1}: mova a câmera para alterar · ${(path[selected].time*duration()).toFixed(2)}s`;
    const limit=elevLimit();
    for(const el of root.querySelectorAll('[data-field=elevation]')){el.min=String(-limit);el.max=String(limit);}
    for(const el of root.querySelectorAll('[data-field]')){const v=path[selected][el.dataset.field];el.value=Number(v.toFixed(3));el.disabled=selected===0;}
    const a=((path[selected].azimuth%360)+360)%360;
    $('.viewlabel').textContent=a<22.5||a>=337.5?'Front View':a<67.5?'Front ¾':a<112.5?'Side View':a<157.5?'Rear ¾':a<202.5?'Back View':a<247.5?'Rear ¾':a<292.5?'Side View':'Front ¾';
    $('.error').textContent='';
    const steep=Math.max(...path.map(k=>Math.abs(k.elevation)));
    $('.note').textContent=steep>=45?`Elevação de ${steep}° no plano: o vídeo tende a virar plongée. Use "Órbita pura" para uma volta na altura dos olhos.`
      :steep>=20?`Elevação de ${steep}°: acima de ~20° o horizonte já sai do quadro.`:'';
    draw(poseAt(playhead));drawDial();paintSwitches();
  }
  function setupCanvas(c,height){const w=c.clientWidth||500,dpr=devicePixelRatio||1;if(c.width!==Math.round(w*dpr)||c.height!==Math.round(height*dpr)){c.width=Math.round(w*dpr);c.height=Math.round(height*dpr);}const context=c.getContext('2d');context.setTransform(dpr,0,0,dpr,0,0);context.clearRect(0,0,w,height);return w;}
  function world(p){const a=rad(p.azimuth),e=rad(p.elevation),r=p.distance*1.8;return [Math.sin(a)*Math.cos(e)*r,Math.sin(e)*r,Math.cos(a)*Math.cos(e)*r];}
  function draw(p){
    const h=360,w=setupCanvas(canvas,h),scale=Math.min(w*.105,58);
    const project=([x,y,z])=>{const X=x*Math.cos(yaw)-z*Math.sin(yaw),Z=x*Math.sin(yaw)+z*Math.cos(yaw);return [w/2+X*scale,h*.54-(y*Math.cos(pitch)-Z*Math.sin(pitch))*scale];};
    function line(a,b,color,width=1){a=project(a);b=project(b);ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke();}
    for(let i=-4;i<=4;i++){line([i*.5,-1,-2],[i*.5,-1,2],'#303033');line([-2,-1,i*.5],[2,-1,i*.5],'#303033');}
    for(let i=0;i<96;i++){
      line(world({azimuth:i*360/96,elevation:0,distance:1}),world({azimuth:(i+1)*360/96,elevation:0,distance:1}),'#45454a');
      const a=i*Math.PI*2/96,b=(i+1)*Math.PI*2/96;line([0,1.8*Math.sin(a),1.8*Math.cos(a)],[0,1.8*Math.sin(b),1.8*Math.cos(b)],'#353539');
    }
    for(let i=0;i<8;i++){const q=project(world({azimuth:i*45,elevation:0,distance:1}));ctx.fillStyle='#64646e';ctx.beginPath();ctx.arc(...q,2,0,Math.PI*2);ctx.fill();}
    // Affine projection of a flat reference card into the scene.
    const ratio=image?clamp(image.naturalWidth/image.naturalHeight,.5,2):1.1,cw=1.3*ratio,ch=1.3;
    const A=project([-cw/2,ch/2,0]),B=project([cw/2,ch/2,0]),D=project([-cw/2,-ch/2,0]);
    ctx.save();ctx.transform((B[0]-A[0])/160,(B[1]-A[1])/160,(D[0]-A[0])/120,(D[1]-A[1])/120,A[0],A[1]);
    if(image)ctx.drawImage(image,0,0,160,120);
    else{const g=ctx.createLinearGradient(0,0,160,120);g.addColorStop(0,'#38505b');g.addColorStop(1,'#b29163');ctx.fillStyle=g;ctx.fillRect(0,0,160,120);ctx.fillStyle='#d3c1a7';ctx.beginPath();ctx.arc(80,40,15,0,Math.PI*2);ctx.fill();ctx.fillRect(62,58,36,48);ctx.fillStyle='#fff8';ctx.font='10px system-ui';ctx.fillText('REFERENCE',7,113);}
    ctx.restore();
    for(let i=1;i<=160;i++)line(world(poseAt((i-1)/160)),world(poseAt(i/160)),'#00a995',1.7);
    path.forEach((k,i)=>{const q=project(world(k));ctx.fillStyle=i===selected?'#8850ff':'#00ab97';ctx.beginPath();ctx.arc(...q,i===selected?3.5:2.5,0,Math.PI*2);ctx.fill();});
    const pos=world(p),q=project(pos);cameraScreen=q;line(pos,[0,0,0],'#7045a650',1);
    ctx.save();ctx.translate(...q);ctx.fillStyle='#6c21ce';ctx.beginPath();ctx.moveTo(-10,-5);ctx.lineTo(4,-10);ctx.lineTo(11,-6);ctx.lineTo(-3,0);ctx.closePath();ctx.fill();ctx.fillStyle=hoverCamera?'#ab78ff':'#8235ef';ctx.fillRect(-10,-5,13,12);ctx.fillStyle='#5e16b4';ctx.beginPath();ctx.moveTo(3,-5);ctx.lineTo(11,-9);ctx.lineTo(11,3);ctx.lineTo(3,7);ctx.fill();ctx.fillStyle='#9f62ff';ctx.beginPath();ctx.moveTo(-10,-2);ctx.lineTo(-17,-6);ctx.lineTo(-17,7);ctx.lineTo(-10,4);ctx.fill();ctx.restore();
  }
  function drawDial(){setupCanvas(dial,90);dc.lineWidth=1;dc.strokeStyle='#3b3b3f';dc.fillStyle='#222';dc.beginPath();dc.arc(45,45,38,0,Math.PI*2);dc.fill();dc.stroke();
    for(let i=0;i<8;i++){const a=i*Math.PI/4;dc.beginPath();dc.moveTo(45+Math.sin(a)*31,45+Math.cos(a)*31);dc.lineTo(45+Math.sin(a)*36,45+Math.cos(a)*36);dc.stroke();}
    dc.fillStyle='#9c9ba3';dc.beginPath();dc.arc(45,45,2.4,0,Math.PI*2);dc.fill();const a=rad(path[selected].azimuth);dc.fillStyle='#8644ff';dc.strokeStyle='#a67bff';dc.lineWidth=2;dc.beginPath();dc.arc(45+Math.sin(a)*38,45+Math.cos(a)*38,6,0,Math.PI*2);dc.fill();dc.stroke();dial.setAttribute('aria-valuenow',String(path[selected].azimuth));dial.setAttribute('aria-disabled',String(selected===0));}
  const snap={azimuth:v=>Math.round(v),elevation:v=>Math.round(v),distance:v=>Math.round(v*100)/100};
  function modify(field,value){if(selected===0||!Number.isFinite(value))return;stop();const e=elevLimit(),limits={azimuth:[-11520,11520],elevation:[-e,e],distance:[.1,4]};path[selected][field]=snap[field](clamp(value,...limits[field]));playhead=path[selected].time;save(false);}
  for(const el of root.querySelectorAll('[data-field]'))el.addEventListener('input',()=>modify(el.dataset.field,el.valueAsNumber));
  function pointerTime(e){const r=track.getBoundingClientRect();return clamp((e.clientX-r.left)/r.width,0,1);}
  track.addEventListener('pointerdown',e=>{if(e.target.classList.contains('marker'))return;stop();playhead=pointerTime(e);markerDrag={scrub:true};track.setPointerCapture(e.pointerId);update(false);});
  track.addEventListener('pointermove',e=>{if(!markerDrag)return;const t=pointerTime(e);if(markerDrag.scrub)playhead=t;else {const i=markerDrag.i;if(i===0)return;path[i].time=snapTime(clamp(t,path[i-1].time+.001,i<path.length-1?path[i+1].time-.001:1));playhead=path[i].time;save(false);}update(false);});
  track.addEventListener('pointerup',()=>{markerDrag=null;update();});track.addEventListener('pointercancel',()=>markerDrag=null);
  track.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();stop();playhead=clamp(playhead+(e.key==='ArrowRight'?.01:-.01),0,1);update(false);}});
  function dialValue(e){const r=dial.getBoundingClientRect();return Math.atan2(e.clientX-r.left-r.width/2,e.clientY-r.top-r.height/2)*180/Math.PI;}
  dial.addEventListener('pointerdown',e=>{dialAngle=dialValue(e);drag={dial:true,raw:path[selected].azimuth};dial.setPointerCapture(e.pointerId);});
  dial.addEventListener('pointermove',e=>{if(!drag?.dial)return;const next=dialValue(e),delta=((next-dialAngle+540)%360)-180;dialAngle=next;drag.raw=clamp(drag.raw+delta,-11520,11520);modify('azimuth',drag.raw);});
  dial.addEventListener('pointerup',()=>drag=null);dial.addEventListener('pointercancel',()=>drag=null);
  dial.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();modify('azimuth',path[selected].azimuth+(e.key==='ArrowRight'?5:-5));}});
  canvas.addEventListener('pointerdown',e=>{stop();const r=canvas.getBoundingClientRect();const onCamera=Math.hypot(e.clientX-r.left-cameraScreen[0],e.clientY-r.top-cameraScreen[1])<30;drag={x:e.clientX,y:e.clientY,camera:onCamera&&!e.shiftKey,tx:0,ty:0,axis:'',rawAz:path[selected].azimuth,rawEl:path[selected].elevation};canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointermove',e=>{const r=canvas.getBoundingClientRect();hoverCamera=Math.hypot(e.clientX-r.left-cameraScreen[0],e.clientY-r.top-cameraScreen[1])<30;canvas.style.cursor=hoverCamera?'grab':'move';if(!drag||drag.dial)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.x=e.clientX;drag.y=e.clientY;if(drag.camera){if(selected>0){
      drag.tx+=dx;drag.ty+=dy;
      if(!drag.axis&&Math.hypot(drag.tx,drag.ty)>5)drag.axis=Math.abs(drag.tx)>=Math.abs(drag.ty)?'orbit':'height';
      if(drag.axis==='orbit'){drag.rawAz=clamp(drag.rawAz+dx*.7,-11520,11520);path[selected].azimuth=Math.round(drag.rawAz);}
      else if(drag.axis==='height'){const e=elevLimit();drag.rawEl=clamp(drag.rawEl-dy*e/150,-e,e);path[selected].elevation=Math.round(drag.rawEl);}
      playhead=path[selected].time;save(false);}}else{yaw+=dx*.008;pitch=clamp(pitch+dy*.008,-1.25,1.25);draw(poseAt(playhead));}});
  canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);
  canvas.addEventListener('wheel',e=>{const r=canvas.getBoundingClientRect();if(Math.hypot(e.clientX-r.left-cameraScreen[0],e.clientY-r.top-cameraScreen[1])<40){e.preventDefault();modify('distance',path[selected].distance*Math.exp(e.deltaY*.001));}}, {passive:false});
  function tick(now){if(disposed||!playing)return;playhead=((now-start)/1000/duration())%1;update(false);raf=requestAnimationFrame(tick);}
  root.addEventListener('click',e=>{const action=e.target.dataset.action;if(!action)return;
    if(action==='play'){if(playing)stop();else{playing=true;start=performance.now()-playhead*duration()*1000;$('.play').textContent='❚❚';$('.play').setAttribute('aria-label','Pause camera preview');raf=requestAnimationFrame(tick);}return;}
    stop();if(action==='reset'){path=defaults();selected=1;playhead=.5;save();}
    if(action==='remove'&&selected>0&&path.length>2){path.splice(selected,1);selected=Math.min(selected,path.length-1);playhead=path[selected].time;save();}
    if(action==='image')$('input[type=file]').click();
    if(action==='clearref'){manualImage=null;linkedSrc='';refreshReference();}
    if(action==='pure'){let changed=false;for(const k of path){if(k.elevation!==0){k.elevation=0;changed=true;}}if(changed)save();}
  });
  $('[data-role=count]').addEventListener('change',e=>{stop();const n=Number(e.target.value),next=[];for(let i=0;i<n;i++){const t=snapTime(i/(n-1));next.push({time:t,...poseAt(t)});}path=next;selected=Math.min(selected,n-1);playhead=path[selected].time;save();});
  $('[data-role=duration]').disabled=!setDuration;
  $('[data-role=duration]').addEventListener('change',e=>{stop();setDuration?.(Number(e.target.value));update();});
  $('input[type=file]').addEventListener('change',e=>{const file=e.target.files[0];if(!file)return;const url=URL.createObjectURL(file),img=new Image();img.onload=()=>{manualImage=img;URL.revokeObjectURL(url);refreshReference();};img.onerror=()=>{URL.revokeObjectURL(url);$('.error').textContent='Não foi possível abrir a imagem.';};img.src=url;});
  function referenceLabel(){
    const box=$('[data-role=refsrc]');box.replaceChildren();
    const text=manualImage?'Referência: arquivo local':(image?'Referência: node conectado':'Referência: nenhuma · conecte uma imagem em reference_image');
    box.append(document.createTextNode(text));
    if(manualImage){const clear=document.createElement('button');clear.className='clearref';clear.dataset.action='clearref';clear.textContent='usar o node';box.append(clear);}
  }
  function refreshReference(){
    if(manualImage){if(image!==manualImage){image=manualImage;draw(poseAt(playhead));}referenceLabel();return;}
    const src=linkedImage?.()||'';
    if(src!==linkedSrc){
      linkedSrc=src;linkedImg=null;
      if(src){const img=new Image();img.onload=()=>{if(disposed||linkedSrc!==src)return;linkedImg=img;image=img;referenceLabel();draw(poseAt(playhead));};
        img.onerror=()=>{if(disposed||linkedSrc!==src)return;image=null;referenceLabel();draw(poseAt(playhead));};img.src=src;}
      else{image=null;referenceLabel();draw(poseAt(playhead));}
      return;
    }
    if(image!==linkedImg){image=linkedImg;draw(poseAt(playhead));}
    referenceLabel();
  }
  function sync(){const raw=read();if(raw!==lastRaw){try{const data=JSON.parse(raw);if(!Array.isArray(data)||data.length<2||data.length>24)throw Error();for(let i=0;i<data.length;i++){const p=data[i];if(!['time','azimuth','elevation','distance'].every(k=>typeof p[k]==='number'&&Number.isFinite(p[k]))||p.time<0||p.time>1||p.distance<.1||p.distance>4||Math.abs(p.elevation)>89||(i&&p.time<=data[i-1].time))throw Error();}const first=data[0];if(first.time!==0||first.azimuth!==0||first.elevation!==0||first.distance!==1)throw Error();path=data;lastRaw=raw;selected=Math.min(selected,path.length-1);playhead=path[selected].time;}catch{$('.error').textContent='Trajetória inválida. Corrija o JSON ou use Reset. O primeiro ponto deve ser 0, 0°, 0°, distância 1.';return;}}update();}
  const switchRow=document.createElement('div');switchRow.className='switches';
  function paintSwitches(){
    const list=switches?.()||[];
    if(!list.length){switchRow.style.display='none';return;}
    switchRow.style.display='';switchRow.replaceChildren();
    const title=document.createElement('b');title.textContent='Testes';switchRow.append(title);
    for(const item of list){
      const b=document.createElement('button');b.className='sw';b.type='button';
      b.dataset.on=item.on?'1':'0';b.textContent=item.label;b.title=item.hint||'';
      b.addEventListener('click',()=>{item.toggle();paintSwitches();});
      switchRow.append(b);
    }
    const tag=document.createElement('span');tag.className='closure';
    const net=path[path.length-1].azimuth-path[0].azimuth;
    const closes=Math.abs(net)>0.5&&Math.abs(Math.abs(net)%360)<1e-3
      &&Math.abs(path[0].elevation-path[path.length-1].elevation)<0.5
      &&Math.abs(path[0].distance-path[path.length-1].distance)<0.01;
    tag.dataset.on=closes?'1':'0';
    tag.textContent=closes?'loop closure ativa · volta fechada':'loop closure inativa · a volta não fecha';
    tag.title='Liga sozinha quando a trajetória fecha 360° na mesma altura e distância.';
    switchRow.append(tag);
  }
  root.insertBefore(switchRow,root.querySelector('.stage')||root.children[1]);
  const observer=new ResizeObserver(()=>{draw(poseAt(playhead));drawDial();});observer.observe(canvas);sync();
  refreshReference();poll=setInterval(refreshReference,1200);
  return {element:root,sync(){sync();refreshReference();paintSwitches();},destroy(){disposed=true;stop();clearInterval(poll);observer.disconnect();}};
}
