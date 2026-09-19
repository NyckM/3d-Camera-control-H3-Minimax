import {SHOT_PRESETS,presetPath} from './shot-presets.js';
import {dragOrbit, frustum, drawCameraView} from './spatial-camera.js';
import {loadDepthPreview, drawDepthWarp} from './depth-warp.js';
// Original implementation inspired by the referenced camera editor layout.
// All drawing and state stay local; no external assets or API requests.
import { createVideoReference } from './video-reference.js';
import { interpolatePose } from './trajectory-math.js';
export function createCameraEditor({read, write, duration, interpolation, setInterpolation, setDuration, linkedImage, elevationRange, switches, frameMode, setFrameMode, promptDetail, runtimeTask, motionFraction, loopClosure, setLoopClosure, experimentMode, setExperimentMode, depthWarp, setDepthWarp, depthOffset}) {
  const root=document.createElement('section');root.className='h3cam';
  root.innerHTML=`<style>
  .h3cam{--purple:#8035ff;--muted:#a5a4ae;box-sizing:border-box;width:100%;height:860px;overflow:auto;padding:16px;background:#191919;color:#f4f4f5;font:14px system-ui,sans-serif;border-radius:12px;user-select:none}
  .h3cam *{box-sizing:border-box}.h3cam header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;font-size:20px}.h3cam header small{color:#929199;border:2px solid #777780;border-radius:50%;font-size:13px;padding:0 6px;margin-left:7px}
  .h3cam button,.h3cam select,.h3cam input{font:inherit;color:inherit}.h3cam button{cursor:pointer}.h3cam button:disabled{opacity:.3;cursor:default}.h3cam .icon{background:none;border:0;color:#aaa;font-size:23px;padding:2px 7px}.h3cam .icon:hover{color:white}.h3cam .stage{background:#212121;border-radius:12px;overflow:hidden}.h3cam .viewport{position:relative;height:360px}.h3cam .scene{display:block;width:100%;height:100%;touch-action:none}.h3cam .hint{position:absolute;bottom:12px;left:12px;right:12px;pointer-events:none;color:#aaa;background:#292929e0;border-radius:5px;padding:8px;font-size:11px;width:max-content;max-width:calc(100% - 24px)}
  .h3cam .transport{border-top:1px solid #2b2b2b;padding:18px 15px}.h3cam .track{position:relative;height:32px;touch-action:none;margin:8px 7px}.h3cam .rail{position:absolute;top:14px;left:0;right:0;height:5px;border-radius:4px;background:#47464b}.h3cam .marker{position:absolute;top:11px;width:12px;height:12px;background:#a6a5ac;transform:translateX(-50%) rotate(45deg);border:0;padding:0;touch-action:none}.h3cam .marker.active{background:var(--purple)}.h3cam .cursor{position:absolute;top:-1px;height:33px;width:1px;background:var(--purple);pointer-events:none}.h3cam .cursor:before{content:'';position:absolute;top:0;left:-4px;width:9px;height:9px;background:var(--purple);border-radius:50%}.h3cam .labels{display:flex;justify-content:space-between;color:#81808a;font:12px ui-monospace,monospace;margin-bottom:14px}.h3cam .bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.h3cam .play{background:#f5f5f5;color:#151515;border:0;border-radius:5px;width:40px;height:40px;font-size:21px}.h3cam .time{color:#adadb8;font:14px ui-monospace,monospace;margin-right:auto}.h3cam .bar label{color:var(--muted);font-size:12px;display:flex;align-items:center;gap:7px}.h3cam select{background:#222;border:1px solid #3c3c40;border-radius:5px;padding:7px 9px;max-width:100px}.h3cam .selected{color:#9657ff;margin-top:12px;font-size:13px}.h3cam .controls{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:17px}.h3cam .heading{display:flex;justify-content:space-between;color:var(--muted);gap:5px}.h3cam .number{width:61px;background:transparent;border:0;color:white;text-align:right;padding:0;appearance:textfield;-moz-appearance:textfield}.h3cam .number::-webkit-inner-spin-button{display:none}.h3cam .range{accent-color:var(--purple);width:100%;margin:17px 0;background:#292929}.h3cam .dial{display:block;width:92px;height:92px;margin-top:11px;touch-action:none;cursor:grab}.h3cam .viewlabel{font-size:11px;color:#aaa;margin-top:3px}.h3cam footer{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:13px;border-top:1px solid #303034;padding-top:10px;color:#96949e;font-size:11px}.h3cam .reference{border:1px solid #444;background:#222;color:#bbb;border-radius:5px;padding:6px 9px;font-size:11px}.h3cam .error{color:#ffb4a6;padding-top:6px;font-size:12px}.h3cam button:focus-visible,.h3cam input:focus-visible,.h3cam canvas:focus-visible{outline:2px solid #b992ff;outline-offset:3px}
  </style>
  <header><span>bruxosdovfx · Camera motion <small title="Planeja a câmera e gera instruções para o H3. Bruxos do VFX.">i</small></span><button class="icon" data-action="reset" title="Reset camera path" aria-label="Reset camera path">◇</button></header>
  <div class="stage"><div class="viewport"><canvas class="scene" aria-label="Cena e trajetória da câmera"></canvas><div class="hint">Arraste a câmera na horizontal para orbitar, na vertical para elevar · o eixo trava no primeiro movimento · role para distância · arraste o fundo para olhar ao redor</div></div>
  <div class="transport"><div class="track" role="slider" tabindex="0" aria-label="Camera animation playhead" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div class="rail"></div><div class="markers"></div><div class="cursor"></div></div>
  <div class="labels"><span>0:00</span><span data-role="end"></span></div>
  <div class="bar"><button class="play" data-action="play" aria-label="Play camera preview">▶</button><span class="time"></span><label>Keyframes<select aria-label="Keyframe count" data-role="count"></select></label><label>Duração<select aria-label="Video duration" data-role="duration"><option value="124">5.125s</option><option value="243">10.083s</option><option value="362">15.042s</option></select></label><button class="icon" data-action="remove" aria-label="Remove selected keyframe" title="Remover keyframe">♜</button></div>
  <div class="selected"></div></div></div>
  <div class="controls"><div><div class="heading"><label for="">Azimuth</label><input class="number" aria-label="Azimuth degrees" type="number" data-field="azimuth" min="-11520" max="11520" step="1"></div><canvas class="dial" role="slider" tabindex="0" aria-label="Azimuth dial" aria-valuemin="-11520" aria-valuemax="11520"></canvas><div class="viewlabel"></div></div>
  <div><div class="heading"><span>Elevation</span><input class="number" aria-label="Elevation degrees" type="number" data-field="elevation" min="-89" max="89" step="1"></div><input class="range" aria-label="Elevation slider" data-field="elevation" type="range" min="-89" max="89" step="1"></div>
  <div><div class="heading"><span>Distance</span><input class="number" aria-label="Camera distance" type="number" data-field="distance" min="0.1" max="4" step="0.05"></div><input class="range" aria-label="Distance slider" data-field="distance" type="range" min="0.1" max="4" step="0.01"></div>
  <div><div class="heading"><span>Height</span><input class="number" aria-label="Camera height" type="number" data-field="height" min="-3" max="3" step="0.05"></div><input class="range" aria-label="Height slider" data-field="height" type="range" min="-3" max="3" step="0.01"></div></div>
  <footer><span data-role="refsrc">Referência: nenhuma</span><button class="reference" data-action="image">Imagem de referência</button><input type="file" accept="image/*,video/*" hidden></footer><div class="error" role="status"></div><div class="note" role="status"></div>`;
  // Keep the same controls and handlers, with an independent studio layout.
  const extraStyle=document.createElement('style');
  extraStyle.textContent=`
  .h3cam{background:#17171c;border:1px solid #303039;border-radius:18px;padding:20px;--purple:#8c4cff}
  .h3cam header{margin-bottom:16px;gap:12px}.h3cam .brand{display:flex;align-items:center;gap:11px}.h3cam .brandmark{width:40px;height:40px;display:block;object-fit:contain;filter:drop-shadow(0 0 10px #8c4cff35)}.h3cam .brand b{font-size:18px;letter-spacing:3px;display:block}.h3cam .brand em{display:block;font-style:normal;color:#8c899b;font-size:11px;letter-spacing:1px;margin-top:2px}
  .h3cam .bar{padding:10px 12px;border:1px solid #34313f;border-radius:10px;margin-bottom:12px;background:#201e28;gap:18px}.h3cam .bar label{font-size:12px}.h3cam .bar .icon{margin-left:auto;font-size:12px;color:#b8afcb;border:1px solid #464052;border-radius:6px;padding:7px 10px}.h3cam select{background:#18171e;border-color:#494051;max-width:110px}.h3cam .reference{border-color:#315e55;color:#8cdfcd;background:#19302a;padding:9px 12px;border-radius:8px}
  .h3cam .stage{border:1px solid #34313e;border-radius:12px;background:#1d1d23}.h3cam .viewport{height:360px;background:radial-gradient(ellipse at 50% 50%,#26252e 0%,#1d1d23 70%)}.h3cam .previewbar{position:absolute;top:12px;right:12px;display:flex;align-items:center;gap:12px;padding:6px 7px 6px 12px;background:#17151fd9;border:1px solid #42354f;border-radius:30px}.h3cam .play{width:34px;height:34px;border-radius:50%;background:#8c4cff;color:white;font-size:17px;box-shadow:0 0 18px #8c4cff30}.h3cam .time{font-size:12px;color:#c1b6d4;margin:0}.h3cam .hint{background:transparent;color:#827e90;font-size:10px}
  .h3cam .transport{padding:14px 18px 11px;background:#19181f;border-top-color:#34303d}.h3cam .rail{height:3px;background:#3f394b}.h3cam .marker{width:11px;height:11px;border-radius:3px;background:#4a9d8d}.h3cam .marker.active{background:#a878ff;box-shadow:0 0 10px #8c4cff60}.h3cam .labels{margin-bottom:8px}.h3cam .selectionrow{display:flex;align-items:center;justify-content:space-between;gap:8px}.h3cam .selected{margin:0;color:#baa0ef;font-size:11px}.h3cam .selectionrow .icon{font-size:11px;color:#a59bab;border:1px solid #3a3340;border-radius:5px;padding:5px 8px}
  .h3cam .controls{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:12px}.h3cam .controls>div{padding:12px;background:#211e29;border:1px solid #393142;border-radius:10px;min-width:0;display:flex;flex-direction:column;min-height:104px}.h3cam .controls>div:nth-child(1){border-top:2px solid #9958ff}.h3cam .controls>div:nth-child(2){border-top:2px solid #6b66db}.h3cam .controls>div:nth-child(3){border-top:2px solid #19bda1}.h3cam .controls>div:nth-child(4){border-top:2px solid #dfaf61}.h3cam .heading{font-size:12px}.h3cam .number{width:52px}.h3cam .dial{width:86px;height:86px;margin:6px auto 0}.h3cam .viewlabel{text-align:center;font-size:10px;margin-top:5px}.h3cam .range{margin:auto 0 4px}.h3cam .controls>div:nth-child(3) .range{accent-color:#19c7a7}.h3cam .controls>div:nth-child(4) .range{accent-color:#dfaf61}.h3cam footer{margin-top:10px;border:0;padding-top:0;font-size:10px}.h3cam .note{color:#ffd48a;font-size:11px;padding-top:5px;min-height:14px}.h3cam .clearref{background:none;border:0;color:#8cdfcd;font:inherit;text-decoration:underline;padding:0 0 0 6px}.h3cam .pure{border:1px solid #464052;background:#221f2b;color:#c9bfe0;border-radius:6px;padding:7px 10px;font-size:12px}.h3cam .switches{display:flex;gap:8px;flex-wrap:wrap;padding:8px 12px;border:1px solid #34313f;border-radius:10px;margin-bottom:12px;background:#1c1a24;align-items:center}.h3cam .switches b{font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:#7d7590;font-weight:600;margin-right:2px}.h3cam .sw{border:1px solid #464052;background:#221f2b;color:#8d85a0;border-radius:6px;padding:6px 10px;font-size:12px;cursor:pointer}.h3cam .sw[data-on='1']{border-color:#8c4cff;background:#2e2340;color:#e6dcff}.h3cam .closure{margin-left:auto;font-size:11px;color:#7d7590}.h3cam .closure[data-on='1']{color:#19c7a7}
  `;
  extraStyle.textContent+=`.h3cam .stage:has(.video-reference:not([hidden])){display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.h3cam .stage:has(.video-reference:not([hidden])) .transport{grid-column:1 / -1}.h3cam .video-reference{align-self:center;min-width:0}.h3cam .video-reference[hidden]{display:none}.h3cam .stage:has(.video-reference:not([hidden])) .hint{font-size:9px}`;
  extraStyle.textContent+=`.h3cam .viewtools{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-bottom:10px}.h3cam .viewtools button{background:#25202f;border:1px solid #5b476b;border-radius:5px;padding:5px 9px}.h3cam .viewtools output{min-width:45px;text-align:center;font-size:12px}.h3cam .viewport.expanded{height:560px}.h3cam .stage:has(.viewport.expanded){grid-template-columns:minmax(0,1fr)}.h3cam .spatial-key{position:absolute;transform:translate(-50%,-50%);width:24px;height:24px;border-radius:50%;border:1px solid #7cf0d9;background:#144a42;color:white;font-size:11px;padding:0;touch-action:none;cursor:grab;z-index:2}.h3cam .spatial-key[data-selected="true"]{background:#7638c6;border-color:#dfb5ff;z-index:3}.h3cam .spatial-key[data-index="0"]{background:#38343c;cursor:default}.h3cam .previewbar{z-index:5}`;
  root.append(extraStyle);
  extraStyle.textContent+=`.h3cam header .depth-toggle{font-size:12px;padding:7px 11px}.h3cam header .depth-toggle[data-on='1']{border-color:#ff4fd8;background:#3a1a36;color:#ffd6f6;box-shadow:0 0 12px #ff4fd840}`;
  extraStyle.textContent+=`.h3cam header{flex-wrap:wrap}.h3cam .path-tools{border:1px solid #34313f;border-radius:10px;margin:0 0 12px;padding:10px;background:#1c1a24}.h3cam .path-tools summary{cursor:pointer;font-size:12px;color:#c6b3ec}.h3cam .toolrow{display:flex;gap:7px;flex-wrap:wrap;margin-top:9px;align-items:center}.h3cam .toolrow select{max-width:215px}.h3cam .toolrow button{border:1px solid #464052;background:#221f2b;color:#c9bfe0;border-radius:6px;padding:7px 9px;font-size:11px}.h3cam .toolrow label{display:flex;align-items:center;gap:6px;font-size:11px;color:#b8afcb}.h3cam .diagnostics{font-size:11px;color:#ffd48a;margin-top:9px;white-space:pre-wrap}.h3cam .experiment-note{font-size:10px;color:#bfa8e5;line-height:1.45;margin-top:8px}.h3cam .switches select{max-width:170px}.h3cam .closure{flex-basis:100%;margin:0}.h3cam .error{white-space:pre-wrap}`;
  const header=root.querySelector('header'),bar=root.querySelector('.bar'),viewport=root.querySelector('.viewport');
  const reset=root.querySelector('[data-action=reset]'),reference=root.querySelector('[data-action=image]');
  const brand=document.createElement('div');brand.className='brand';
  const mark=document.createElement('img');mark.className='brandmark';mark.alt='';mark.decoding='async';
  mark.src=new URL('./logo.png',import.meta.url).href;
  const wordmark=document.createElement('span');wordmark.innerHTML='<b>CAMERA H3</b><em>bruxosdovfx</em>';
  brand.append(mark,wordmark);
  header.replaceChildren(brand,reference);
  const modeSelect=document.createElement('select');
  modeSelect.setAttribute('aria-label','Modo de referência / Reference mode');
  modeSelect.style.maxWidth='200px';modeSelect.style.fontSize='12px';
  for(const name of ['Freeze Frame','Motion Frame','Action Frame']){const o=document.createElement('option');o.value=name;o.textContent=name;modeSelect.append(o);}
  modeSelect.title='PT: Freeze Frame congela um frame; Motion Frame mantém a ação da sequência com Ref2VA; Action Frame anima a imagem conforme instruction. EN: Freeze Frame freezes one frame; Motion Frame preserves sequence action with Ref2VA; Action Frame animates the image using instruction.';
  modeSelect.value=frameMode?.()||'Freeze Frame';
  modeSelect.addEventListener('change',()=>setFrameMode?.(modeSelect.value));
  header.append(modeSelect);
  // PT: v30 · botão Depth Warp, ligado ao widget depth_animation. EN: v30 · Depth Warp toggle bound to depth_animation.
  let depthButton=null;
  if(depthWarp&&setDepthWarp){
    depthButton=document.createElement('button');depthButton.className='sw depth-toggle';depthButton.dataset.action='depth-warp';
    depthButton.textContent='PT: ◈ Depth Warp EN: ◈ Depth Warp';
    depthButton.title='PT: Anima a referência pela profundidade seguindo os keyframes. Conecte depth ou moge_geometry; a saída depth_warp é o <Video 2> do Meridian Reference. EN: Animates the reference through depth along the keyframes. Connect depth or moge_geometry; the depth_warp output is <Video 2> for Meridian Reference.';
    header.append(depthButton);
  }
  const tips={reset:'PT: Reinicia a trajetória. EN: Resets the path.',play:'PT: Reproduz a câmera; não gera vídeo. EN: Plays camera preview; does not generate video.',remove:'PT: Remove o keyframe escolhido. EN: Removes selected keyframe.',image:'PT: Foto apenas para a prévia; conecte frames ao node para gerar. EN: Preview-only image; connect frames to the node for generation.'};
  for(const [action,tip] of Object.entries(tips)){const el=root.querySelector(`[data-action="${action}"]`);if(el)el.title=tip;}
  for(const [field,tip] of Object.entries({azimuth:'PT: Ângulo da órbita. EN: Orbit angle.',elevation:'PT: Elevação relativa à câmera inicial. EN: Elevation relative to the starting camera.',distance:'PT: Raio relativo; 1 mantém distância inicial. EN: Relative radius; 1 preserves starting distance.',height:'PT: Grua: sobe e desce a câmera sem girar, em múltiplos do raio inicial. Negativo desce. A lente mantém a direção, então o sujeito se desloca no quadro — é diferente da elevação, que gira em torno do alvo. EN: Boom: raises and lowers the camera without orbiting, in units of the starting radius. Negative lowers it. The lens keeps its direction, so the subject shifts in frame — unlike elevation, which orbits the target.'}))for(const el of root.querySelectorAll(`[data-field="${field}"]`))el.title=tip;
  root.querySelector('.track').title='PT: Selecione o tempo e arraste keyframes. EN: Select time and drag keyframes.';
  root.querySelector('[data-role="count"]').title='PT: Número de keyframes. EN: Number of camera keyframes.';
  root.querySelector('[data-role="duration"]').title='PT: Duração de saída a 24 fps. EN: Output duration at 24 fps.';
  const stillDuration=document.createElement('option');stillDuration.value='39';stillDuration.textContent='PT: Imagem · 1,625 s EN: Still · 1.625 s';stillDuration.disabled=true;root.querySelector('[data-role=duration]').append(stillDuration);
  reset.textContent='↺ Reiniciar';
  const pure=document.createElement('button');pure.className='pure';pure.dataset.action='pure';
  pure.textContent='⟳ Órbita pura';pure.title='PT: Zera a elevação mantendo azimute e distância. EN: Resets elevation, keeping azimuth and distance.';
  const shut=document.createElement('button');shut.className='pure';shut.dataset.action='close';
  shut.textContent='⟲ Fechar volta';
  shut.title='PT: Fecha o último ponto e restaura altura/raio. Loop closure só em Freeze Frame. EN: Closes the last pose and restores height/radius. Loop closure only in Freeze Frame.';
  bar.append(pure,shut,reset);
  reference.textContent='PT: Imagem / vídeo EN: Image / video';
  reference.title='PT: Arquivo local para prévia; conecte a referência ao workflow para gerar. EN: Local preview file; connect the reference to the workflow for generation.';
  const viewtools=document.createElement('div');viewtools.className='viewtools';
  viewtools.innerHTML='<span>PT: Zoom da prévia EN: Preview zoom</span><button data-action="zoom-out" aria-label="Zoom out">−</button><output class="zoom-value">160%</output><button data-action="zoom-in" aria-label="Zoom in">+</button><button data-action="view-reset">PT: Restaurar vista EN: Reset view</button><button data-action="expand" aria-pressed="false">PT: Ampliar canvas EN: Expand canvas</button>';
  root.insertBefore(viewtools,root.querySelector('.stage'));
  root.querySelector('.hint').textContent='PT: Role para zoom · arraste os pontos numerados sobre a esfera 3D · Shift + arraste o fundo para girar a vista · Alt + roda ajusta distância EN: Scroll to zoom · drag numbered points on the 3D sphere · Shift + drag background to rotate view · Alt + wheel adjusts distance';
  const cameraView=document.createElement('div');cameraView.className='camera-view';cameraView.style.cssText='grid-column:1 / -1;padding:10px;border-top:1px solid #39414f';
  cameraView.innerHTML='<div class="camera-view-label" style="font-size:11px;color:#b7c9db;margin-bottom:6px">PT: Visão da câmera · manequim 3D · FOV ilustrativo 40° EN: Camera view · 3D mannequin · illustrative FOV 40°</div><canvas aria-label="Camera view" style="display:block;width:100%;height:230px"></canvas>';
  root.querySelector('.stage').append(cameraView);
  const toggleView=document.createElement('button');toggleView.dataset.action='camera-view';toggleView.setAttribute('aria-pressed','true');toggleView.textContent='PT: Visão da câmera EN: Camera view';viewtools.append(toggleView);
  const presetsBox=document.createElement('div');presetsBox.className='path-tools';
  presetsBox.innerHTML='<div class="toolrow"><label>Presets <select aria-label="Camera preset"></select></label><button data-action="preset-apply">PT: Aplicar trajetória EN: Apply path</button><button data-action="preset-undo" disabled>PT: Desfazer preset EN: Undo preset</button></div><div class="preset-note" style="font-size:11px;line-height:1.5;padding:8px" role="status"></div>';
  const presetSelect=presetsBox.querySelector('select'),presetNote=presetsBox.querySelector('.preset-note');
  for(const preset of SHOT_PRESETS){const option=document.createElement('option');option.value=preset.id;const tag=preset.status==='approx'?' ≈':preset.status==='unsupported'?' —':' ';option.textContent=`PT: ${preset.id} · ${preset.pt}${tag} EN: ${preset.id} · ${preset.en}${tag}`;presetSelect.append(option);}
  let presetUndo=null;
  function presetDescription(){const preset=SHOT_PRESETS.find(p=>p.id===presetSelect.value);presetNote.textContent=`PT: ${preset.notePt} ${preset.path?'Aplicar substitui a trajetória e ajusta a interpolação.':'Sem conversão disponível.'} EN: ${preset.noteEn} ${preset.path?'Apply replaces the path and sets interpolation.':'No conversion available.'}`;presetsBox.querySelector('[data-action=preset-apply]').disabled=!preset.path;}
  presetSelect.addEventListener('change',presetDescription);presetDescription();root.insertBefore(presetsBox,root.querySelector('.stage'));
  const videoHost=document.createElement('div');videoHost.className='video-reference';
  root.querySelector('.stage').prepend(videoHost);
  const videoNote=document.createElement('div');videoNote.className='video-note';videoNote.style.cssText='font-size:11px;padding:8px;color:#bfb2cf';videoHost.append(videoNote);
  const add=document.createElement('button');add.className='pure';add.dataset.action='add';add.textContent='PT: + Keyframe agora EN: + Keyframe now';bar.append(add);
  const previewbar=document.createElement('div');previewbar.className='previewbar';
  previewbar.append(root.querySelector('.time'),root.querySelector('.play'));viewport.append(previewbar);
  root.insertBefore(bar,root.querySelector('.stage'));
  let experimentSelect=null;
  if(experimentMode&&setExperimentMode){
    // PT: container proprio; o bloco de ferramentas que o continha foi removido.
    // EN: its own container; the tools block that used to hold it was removed.
    const experimentBox=document.createElement('div');experimentBox.className='path-tools';
    const row=document.createElement('div');row.className='toolrow';const label=document.createElement('label');const text=document.createElement('span');text.textContent='PT: Experimento EN: Experiment';experimentSelect=document.createElement('select');experimentSelect.dataset.role='experiment';experimentSelect.setAttribute('aria-label','PT: Receita experimental EN: Experimental recipe');
    for(const [value,title] of [['Off','PT: Desligado EN: Off'],['Article compact','PT: Artigo · compacto EN: Article · compact'],['Article numbers only','PT: Artigo · só números EN: Article · numbers only']]){const option=document.createElement('option');option.value=value;option.textContent=title;experimentSelect.append(option);}
    experimentSelect.title='PT: Hipótese de prompt para H3 local. Não ativa o endpoint do fal nem condicionamento geométrico. Compare mesma imagem, trajetória, seed e loop closure. EN: A prompt hypothesis for local H3. Does not enable the fal endpoint or geometric conditioning. Compare the same image, path, seed and loop closure.';
    experimentSelect.addEventListener('change',()=>setExperimentMode(experimentSelect.value));label.append(text,experimentSelect);row.append(label);experimentBox.append(row);
    const note=document.createElement('div');note.className='experiment-note';note.textContent='PT: Experimental: compara formas de escrever o prompt. A câmera ainda depende da interpretação do H3. EN: Experimental: compares prompt formats. Camera motion still depends on H3 interpretation.';experimentBox.append(note);root.insertBefore(experimentBox,root.querySelector('.stage'));
  }
  const selectionrow=document.createElement('div');selectionrow.className='selectionrow';
  const remove=root.querySelector('[data-action=remove]');remove.textContent='− Remover ponto';
  selectionrow.append(root.querySelector('.selected'),remove);root.querySelector('.transport').append(selectionrow);
  // Em cima o que gira (órbita, elevação); embaixo o que desloca (distância, altura).
  const cards=[...root.querySelector('.controls').children];
  cards[0].querySelector('.heading label').textContent='Órbita';cards[1].querySelector('.heading span').textContent='Elevação';
  cards[2].querySelector('.heading span').textContent='Distância';cards[3].querySelector('.heading span').textContent='Altura';
  const $=s=>root.querySelector(s),canvas=$('.scene'),ctx=canvas.getContext('2d'),dial=$('.dial'),dc=dial.getContext('2d'),track=$('.track');
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)),rad=v=>v*Math.PI/180,snapTime=v=>Math.round(v*1000)/1000;
  // Never below what the current keyframe already holds, so a wide old path stays editable.
  const elevLimit=()=>Math.min(89,Math.max(elevationRange?.()||30,Math.abs(path[selected]?.elevation||0)));
  const defaults=()=>[{time:0,azimuth:0,elevation:0,distance:1},{time:.5,azimuth:45,elevation:10,distance:1},{time:1,azimuth:90,elevation:0,distance:.8}];
  let viewZoom=1.6;const spatialKeys=[];
  let path=defaults(),selected=1,playhead=.5,lastRaw='',yaw=.55,pitch=.45,image=null,playing=false,raf=0,disposed=false,start=0;
  let manualImage=null,linkedImg=null,linkedSrc='',poll=0,toolError='';
  let depthPreview=null,depthLabel='',depthGeneration=0;
  let drag=null,dialAngle=0,markerDrag=null,cameraScreen=[0,0],hoverCamera=false;
  const media=createVideoReference(videoHost,{duration,onReady(){media.seek(playhead);refreshReference();update(false);},onError(message){stop();toolError=message;update(false);}});
  media.video.addEventListener('seeked',()=>{if(!disposed){if(!playing)media.seek(playhead);draw(poseAt(playhead));}});
  const format=t=>`${Math.floor(t/60)}:${(t%60).toFixed(1).padStart(4,'0')}`;
  for(let i=2;i<=24;i++){$('[data-role=count]').add(new Option(String(i),String(i)));}
  const activeFraction=()=>clamp(motionFraction?.()||1,.001,1);
  let previousFraction=activeFraction();
  const pathPoseAt=t=>interpolatePose(path,t,interpolation(),promptDetail?.()||'v15 baseline');
  function poseAt(t) {return pathPoseAt(t/activeFraction());}
  function save(rebuild=true) {toolError='';lastRaw=JSON.stringify(path);write(lastRaw);update(rebuild);}
  function stop(){media.pause();playing=false;cancelAnimationFrame(raf);$('.play').textContent='▶';$('.play').setAttribute('aria-label','Play camera preview');}
  function choose(i){stop();selected=i;playhead=path[i].time*activeFraction();update();}
  function update(rebuild=true) {
    selected=clamp(selected,0,path.length-1);
    if(!playing)media.seek(playhead);
    if(media.active())videoNote.textContent=`PT: Referência original · prévia ${media.rate().toFixed(2)}× · não é o resultado H3 EN: Original reference · preview ${media.rate().toFixed(2)}× · not the H3 result`;
    add.disabled=path.length>=24;
    if(rebuild){
      $('.markers').replaceChildren();
      path.forEach((p,i)=>{
        const b=document.createElement('button');b.className='marker'+(selected===i?' active':'');b.style.left=`${p.time*activeFraction()*100}%`;
        b.setAttribute('aria-label',`Keyframe ${i+1} at ${format(p.time*activeFraction()*duration())}`);b.dataset.index=i;b.title=`Keyframe ${i+1}`;
        b.addEventListener('pointerdown',e=>{e.stopPropagation();choose(i);markerDrag={i};track.setPointerCapture(e.pointerId);});
        b.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(i);}});
        $('.markers').append(b);
      });
    }else path.forEach((p,i)=>{const b=$(`.marker[data-index="${i}"]`);if(b)b.style.left=`${p.time*activeFraction()*100}%`;});
    $('.cursor').style.left=`${playhead*100}%`;
    track.setAttribute('aria-valuenow',String(Math.round(playhead*100)));
    $('.time').textContent=`${format(playhead*duration())} / ${format(duration())}`;
    $('[data-role=end]').textContent=format(duration());
    $('[data-role=count]').value=path.length;
    const directed=runtimeTask?.()==='directed | new camera angle';
    $('[data-role=duration]').disabled=!setDuration||directed;
    $('[data-role=duration]').value=directed?'39':String(Math.round(duration()*24)+1);
    modeSelect.value=frameMode?.()||'Freeze Frame';
    const depthOn=!!depthWarp?.();
    if(depthButton){depthButton.dataset.on=depthOn?'1':'0';depthButton.setAttribute('aria-pressed',String(depthOn));}
    const label=depthOn?(depthPreview?'PT: Depth Warp · geometria da última execução, pose ao vivo · mudou profundidade, hfov ou subject_box? rode de novo EN: Depth Warp · geometry from last run, live pose · changed depth, hfov or subject_box? run again'
      :'PT: Depth Warp ligado · rode o node uma vez para ver a cena reprojetada aqui EN: Depth Warp on · run the node once to see the reprojected scene here')
      :'PT: Visão da câmera · manequim 3D · FOV ilustrativo 40° EN: Camera view · 3D mannequin · illustrative FOV 40°';
    if(label!==depthLabel){depthLabel=label;cameraView.querySelector('.camera-view-label').textContent=label;}
    if(experimentSelect)experimentSelect.value=experimentMode();
    $('[data-action=remove]').disabled=selected===0||path.length<=2;
    $('.selected').textContent=selected===0?'Keyframe 1: imagem original · posição inicial fixa':`Keyframe ${selected+1}: mova a câmera para alterar · ${(path[selected].time*activeFraction()*duration()).toFixed(2)}s`;
    const limit=elevLimit();
    for(const el of root.querySelectorAll('[data-field=elevation]')){el.min=String(-limit);el.max=String(limit);}
    for(const el of root.querySelectorAll('[data-field]')){const v=path[selected][el.dataset.field]??0;if(document.activeElement!==el)el.value=Number(v.toFixed(3));el.disabled=selected===0;}
    const a=((path[selected].azimuth%360)+360)%360;
    $('.viewlabel').textContent=a<22.5||a>=337.5?'Front View':a<67.5?'Front ¾':a<112.5?'Side View':a<157.5?'Rear ¾':a<202.5?'Back View':a<247.5?'Rear ¾':a<292.5?'Side View':'Front ¾';
    $('.error').textContent=toolError;
    const steep=Math.max(...path.map(k=>Math.abs(k.elevation)));
    $('.note').textContent=steep>=45?`Elevação de ${steep}° no plano: o vídeo tende a virar plongée. Use "Órbita pura" para uma volta na altura dos olhos.`
      :steep>=20?`Elevação de ${steep}°: acima de ~20° o horizonte já sai do quadro.`:'';
    draw(poseAt(playhead));drawDial();
  }
  function setupCanvas(c,height){const w=c.clientWidth||500,dpr=devicePixelRatio||1;if(c.width!==Math.round(w*dpr)||c.height!==Math.round(height*dpr)){c.width=Math.round(w*dpr);c.height=Math.round(height*dpr);}const context=c.getContext('2d');context.setTransform(dpr,0,0,dpr,0,0);context.clearRect(0,0,w,height);return w;}
  function world(p){const a=rad(p.azimuth),e=rad(p.elevation),r=p.distance*1.8;return [Math.sin(a)*Math.cos(e)*r,Math.sin(e)*r,Math.cos(a)*Math.cos(e)*r];}
  function draw(p){
    const h=viewport.clientHeight||360,w=setupCanvas(canvas,h),scale=Math.min(w*.105,58)*viewZoom;
    const project=([x,y,z])=>{const X=x*Math.cos(yaw)-z*Math.sin(yaw),Z=x*Math.sin(yaw)+z*Math.cos(yaw);return [w/2+X*scale,h*.54-(y*Math.cos(pitch)-Z*Math.sin(pitch))*scale];};
    function line(a,b,color,width=1){a=project(a);b=project(b);ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke();}
    for(let i=-4;i<=4;i++){line([i*.5,-1,-2],[i*.5,-1,2],'#303033');line([-2,-1,i*.5],[2,-1,i*.5],'#303033');}
    for(let i=0;i<96;i++){
      line(world({azimuth:i*360/96,elevation:0,distance:1}),world({azimuth:(i+1)*360/96,elevation:0,distance:1}),'#45454a');
      const a=i*Math.PI*2/96,b=(i+1)*Math.PI*2/96;line([0,1.8*Math.sin(a),1.8*Math.cos(a)],[0,1.8*Math.sin(b),1.8*Math.cos(b)],'#353539');
    }
    for(let i=0;i<8;i++){const q=project(world({azimuth:i*45,elevation:0,distance:1}));ctx.fillStyle='#64646e';ctx.beginPath();ctx.arc(...q,2,0,Math.PI*2);ctx.fill();}
    // Affine projection of a flat reference card into the scene.
    const ratio=image?clamp((image.videoWidth||image.naturalWidth)/(image.videoHeight||image.naturalHeight),.5,2):1.1,cw=1.3*ratio,ch=1.3;
    const A=project([-cw/2,ch/2,0]),B=project([cw/2,ch/2,0]),D=project([-cw/2,-ch/2,0]);
    ctx.save();ctx.transform((B[0]-A[0])/160,(B[1]-A[1])/160,(D[0]-A[0])/120,(D[1]-A[1])/120,A[0],A[1]);
    if(image)ctx.drawImage(image,0,0,160,120);
    else{const g=ctx.createLinearGradient(0,0,160,120);g.addColorStop(0,'#38505b');g.addColorStop(1,'#b29163');ctx.fillStyle=g;ctx.fillRect(0,0,160,120);ctx.fillStyle='#d3c1a7';ctx.beginPath();ctx.arc(80,40,15,0,Math.PI*2);ctx.fill();ctx.fillRect(62,58,36,48);ctx.fillStyle='#fff8';ctx.font='10px system-ui';ctx.fillText('REFERENCE',7,113);}
    ctx.restore();
    for(let i=1;i<=160;i++)line(world(poseAt((i-1)/160)),world(poseAt(i/160)),'#00a995',1.7);
    while(spatialKeys.length>path.length)spatialKeys.pop().remove();
    const placed=[];
    path.forEach((k,i)=>{
      let button=spatialKeys[i];
      if(!button){
        button=document.createElement('button');button.className='spatial-key';button.dataset.index=i;
        button.textContent=String(i+1);viewport.append(button);spatialKeys.push(button);
        let move=null;
        button.addEventListener('pointerdown',e=>{
          e.stopPropagation();e.preventDefault();selected=i;if(!playing)playhead=path[i].time*activeFraction();update(false);
          move={x:e.clientX,y:e.clientY,pose:{...path[i]},scale:Math.min((canvas.clientWidth||500)*.105,58)*viewZoom,yaw,pitch};button.setPointerCapture(e.pointerId);
        });
        button.addEventListener('pointermove',e=>{
          if(!move||i===0)return;e.stopPropagation();
          const limit=Math.min(89,Math.max(elevationRange?.()||30,Math.abs(move.pose.elevation)));
          const next=dragOrbit(move.pose,e.clientX-move.x,e.clientY-move.y,move.scale,move.yaw,move.pitch,limit);
          path[i].azimuth=next.azimuth;path[i].elevation=next.elevation;
          save(false);
        });
        for(const event of ['pointerup','pointercancel','lostpointercapture'])button.addEventListener(event,()=>move=null);
        button.addEventListener('keydown',e=>{
          if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;
          e.preventDefault();selected=i;modify(e.key==='ArrowLeft'||e.key==='ArrowRight'?'azimuth':'elevation',
            (e.key==='ArrowLeft'||e.key==='ArrowRight'?path[i].azimuth:path[i].elevation)+(e.key==='ArrowLeft'||e.key==='ArrowDown'?-1:1));
        });
      }
      const point=project(world(k));let q=[...point];
      for(let attempt=0;attempt<96;attempt++){
        q=[clamp(q[0],14,w-14),clamp(q[1],65,h-42)];
        if(placed.every(other=>Math.hypot(q[0]-other[0],q[1]-other[1])>=27))break;
        const angle=attempt*2.4,radius=28+Math.floor(attempt/8)*15;
        q=[point[0]+Math.cos(angle)*radius,point[1]+Math.sin(angle)*radius];
      }
      placed.push(q);
      ctx.beginPath();ctx.moveTo(...point);ctx.lineTo(...q);ctx.strokeStyle='#62bda7';ctx.lineWidth=1;ctx.stroke();
      ctx.beginPath();ctx.arc(...point,2.5,0,Math.PI*2);ctx.fillStyle='#62bda7';ctx.fill();
      button.style.left=`${q[0]}px`;button.style.top=`${q[1]}px`;
      button.dataset.selected=String(i===selected);button.setAttribute('aria-label',`Keyframe ${i+1}`);
      button.title=i===0?'PT: Primeiro frame fixo EN: Fixed first frame':'PT: Arraste sobre a esfera 3D; raio e tempo preservados. EN: Drag on the 3D sphere; radius and time stay unchanged.';
    });
    const aspect=image?(image.videoWidth||image.naturalWidth)/(image.videoHeight||image.naturalHeight):16/9;
    const lens=frustum(p,aspect);lens.corners.forEach((corner,i)=>{line(lens.eye,corner,'#dfaf61',1);line(corner,lens.corners[(i+1)%4],'#dfaf61',1);});
    if(!cameraView.hidden){const view=cameraView.querySelector('canvas');if(depthWarp?.()&&depthPreview)drawDepthWarp(view,p,depthPreview,playhead,depthOffset?.());else drawCameraView(view,p,aspect);}
    const pos=world(p),q=project(pos);cameraScreen=q;line(pos,[0,0,0],'#7045a650',1);
    ctx.save();ctx.translate(...q);ctx.fillStyle='#6c21ce';ctx.beginPath();ctx.moveTo(-10,-5);ctx.lineTo(4,-10);ctx.lineTo(11,-6);ctx.lineTo(-3,0);ctx.closePath();ctx.fill();ctx.fillStyle=hoverCamera?'#ab78ff':'#8235ef';ctx.fillRect(-10,-5,13,12);ctx.fillStyle='#5e16b4';ctx.beginPath();ctx.moveTo(3,-5);ctx.lineTo(11,-9);ctx.lineTo(11,3);ctx.lineTo(3,7);ctx.fill();ctx.fillStyle='#9f62ff';ctx.beginPath();ctx.moveTo(-10,-2);ctx.lineTo(-17,-6);ctx.lineTo(-17,7);ctx.lineTo(-10,4);ctx.fill();ctx.restore();
  }
  function drawDial(){
    // A alça vive na borda: o raio deixa folga para ela, senão o disco sai cortado.
    const box=dial.clientHeight||86,size=setupCanvas(dial,box),cx=size/2,cy=box/2,handle=Math.max(4.5,box*.07),r=Math.min(cx,cy)-handle-1;
    dc.lineWidth=1;dc.strokeStyle='#3b3b3f';dc.fillStyle='#222';dc.beginPath();dc.arc(cx,cy,r,0,Math.PI*2);dc.fill();dc.stroke();
    for(let i=0;i<8;i++){const a=i*Math.PI/4;dc.beginPath();dc.moveTo(cx+Math.sin(a)*r*.82,cy+Math.cos(a)*r*.82);dc.lineTo(cx+Math.sin(a)*r*.95,cy+Math.cos(a)*r*.95);dc.stroke();}
    dc.fillStyle='#9c9ba3';dc.beginPath();dc.arc(cx,cy,2.4,0,Math.PI*2);dc.fill();
    const a=rad(path[selected].azimuth);dc.fillStyle='#8644ff';dc.strokeStyle='#a67bff';dc.lineWidth=2;
    dc.beginPath();dc.arc(cx+Math.sin(a)*r,cy+Math.cos(a)*r,handle,0,Math.PI*2);dc.fill();dc.stroke();
    dial.setAttribute('aria-valuenow',String(path[selected].azimuth));dial.setAttribute('aria-disabled',String(selected===0));}
  const snap={azimuth:v=>Math.round(v),elevation:v=>Math.round(v),distance:v=>Math.round(v*100)/100,height:v=>Math.round(v*100)/100};
  function modify(field,value){if(selected===0||!Number.isFinite(value))return;const e=elevLimit(),limits={azimuth:[-11520,11520],elevation:[-e,e],distance:[.1,4],height:[-3,3]};path[selected][field]=snap[field](clamp(value,...limits[field]));if(!playing)playhead=path[selected].time*activeFraction();save(false);}
  for(const el of root.querySelectorAll('[data-field]'))el.addEventListener('input',()=>modify(el.dataset.field,el.valueAsNumber));
  function pointerTime(e){const r=track.getBoundingClientRect();return clamp((e.clientX-r.left)/r.width,0,1);}
  track.addEventListener('pointerdown',e=>{if(e.target.classList.contains('marker'))return;stop();playhead=pointerTime(e);markerDrag={scrub:true};track.setPointerCapture(e.pointerId);update(false);});
  track.addEventListener('pointermove',e=>{if(!markerDrag)return;const t=pointerTime(e);if(markerDrag.scrub)playhead=t;else {const i=markerDrag.i;if(i===0)return;path[i].time=snapTime(clamp(t/activeFraction(),path[i-1].time+.001,i<path.length-1?path[i+1].time-.001:1));playhead=path[i].time*activeFraction();save(false);}update(false);});
  track.addEventListener('pointerup',()=>{markerDrag=null;update();});track.addEventListener('pointercancel',()=>markerDrag=null);
  track.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();stop();playhead=clamp(playhead+(e.key==='ArrowRight'?.01:-.01),0,1);update(false);}});
  function dialValue(e){const r=dial.getBoundingClientRect();return Math.atan2(e.clientX-r.left-r.width/2,e.clientY-r.top-r.height/2)*180/Math.PI;}
  dial.addEventListener('pointerdown',e=>{dialAngle=dialValue(e);drag={dial:true,raw:path[selected].azimuth};dial.setPointerCapture(e.pointerId);});
  dial.addEventListener('pointermove',e=>{if(!drag?.dial)return;const next=dialValue(e),delta=((next-dialAngle+540)%360)-180;dialAngle=next;drag.raw=clamp(drag.raw+delta,-11520,11520);modify('azimuth',drag.raw);});
  dial.addEventListener('pointerup',()=>drag=null);dial.addEventListener('pointercancel',()=>drag=null);
  dial.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();modify('azimuth',path[selected].azimuth+(e.key==='ArrowRight'?5:-5));}});
  canvas.addEventListener('pointerdown',e=>{const r=canvas.getBoundingClientRect();const onCamera=Math.hypot(e.clientX-r.left-cameraScreen[0],e.clientY-r.top-cameraScreen[1])<30;drag={x:e.clientX,y:e.clientY,camera:onCamera&&!e.shiftKey,tx:0,ty:0,axis:'',rawAz:path[selected].azimuth,rawEl:path[selected].elevation,pose:{...path[selected]},scale:Math.min((canvas.clientWidth||500)*.105,58)*viewZoom,observerYaw:yaw,observerPitch:pitch};canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointermove',e=>{const r=canvas.getBoundingClientRect();hoverCamera=Math.hypot(e.clientX-r.left-cameraScreen[0],e.clientY-r.top-cameraScreen[1])<30;canvas.style.cursor=hoverCamera?'grab':'move';if(!drag||drag.dial)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.x=e.clientX;drag.y=e.clientY;if(drag.camera){if(selected>0){
      drag.tx+=dx;drag.ty+=dy;
      const limit=Math.min(89,Math.max(elevationRange?.()||30,Math.abs(drag.pose.elevation)));
      const next=dragOrbit(drag.pose,drag.tx,drag.ty,drag.scale,drag.observerYaw,drag.observerPitch,limit);
      path[selected].azimuth=next.azimuth;path[selected].elevation=next.elevation;
      if(!playing)playhead=path[selected].time*activeFraction();save(false);}}else{yaw+=dx*.008;pitch=clamp(pitch+dy*.008,-1.25,1.25);draw(poseAt(playhead));}});
  canvas.addEventListener('pointerup',()=>drag=null);canvas.addEventListener('pointercancel',()=>drag=null);
  viewport.addEventListener('wheel',e=>{
    e.preventDefault();e.stopPropagation();
    if(e.altKey)modify('distance',path[selected].distance*Math.exp(e.deltaY*.001));
    else{viewZoom=clamp(viewZoom*Math.exp(-e.deltaY*.0015),.5,4);$('.zoom-value').textContent=`${Math.round(viewZoom*100)}%`;draw(poseAt(playhead));}
  },{passive:false});
  function tick(now){if(disposed||!playing)return;playhead=media.ready()?media.progress():Math.min(1,(now-start)/1000/duration());if(playhead>=1||media.ready()&&media.video.ended){playhead=1;stop();update(false);return;}update(false);raf=requestAnimationFrame(tick);}
  root.addEventListener('click',async e=>{const action=e.target.dataset.action;if(!action)return;
    if(action==='preset-apply'){
      const preset=SHOT_PRESETS.find(p=>p.id===presetSelect.value);if(!preset?.path)return;stop();
      presetUndo={path:path.map(p=>({...p})),interpolation:interpolation()};
      path=presetPath(preset.id);selected=1;playhead=0;save();setInterpolation?.(preset.interpolation);
      presetsBox.querySelector('[data-action=preset-undo]').disabled=false;return;
    }
    if(action==='preset-undo'&&presetUndo){stop();const previous=presetUndo;presetUndo=null;path=previous.path;selected=Math.min(selected,path.length-1);playhead=0;save();setInterpolation?.(previous.interpolation);presetsBox.querySelector('[data-action=preset-undo]').disabled=true;return;}
    if(action==='depth-warp'){setDepthWarp?.(depthWarp?.()?'Off':'Depth Warp');if(depthWarp?.()&&cameraView.hidden){cameraView.hidden=false;root.querySelector('[data-action=camera-view]')?.setAttribute('aria-pressed','true');}update(false);return;}
    if(action==='camera-view'){cameraView.hidden=!cameraView.hidden;e.target.setAttribute('aria-pressed',String(!cameraView.hidden));draw(poseAt(playhead));return;}
    if(['zoom-in','zoom-out','view-reset','expand'].includes(action)){
      if(action==='expand'){viewport.classList.toggle('expanded');e.target.setAttribute('aria-pressed',String(viewport.classList.contains('expanded')));}
      else if(action==='view-reset'){viewZoom=1.6;yaw=.55;pitch=.45;}
      else viewZoom=clamp(viewZoom*(action==='zoom-in'?1.2:1/1.2),.5,4);
      $('.zoom-value').textContent=`${Math.round(viewZoom*100)}%`;draw(poseAt(playhead));return;
    }
    if(action==='play'){
      if(playing){stop();return;}
      if(playhead>=.999)playhead=0;
      playing=true;start=performance.now()-playhead*duration()*1000;
      try{if(media.active())await media.play(playhead);}catch(error){stop();toolError=error.message;update(false);return;}
      if(disposed||!playing){media.pause();return;}
      $('.play').textContent='❚❚';$('.play').setAttribute('aria-label','Pause camera preview');raf=requestAnimationFrame(tick);return;
    }
    if(action==='add'){
      const t=snapTime(clamp(playhead/activeFraction(),0,1));
      const existing=path.findIndex(k=>Math.abs(k.time-t)<.001);
      if(existing>=0){selected=existing;update();return;}
      if(path.length>=24)return;
      const key={time:t,...pathPoseAt(t)};path.push(key);path.sort((a,b)=>a.time-b.time);selected=path.indexOf(key);save();return;
    }
    stop();
    if(action==='reset'){path=defaults();selected=1;playhead=.5*activeFraction();save();}
    if(action==='remove'&&selected>0&&path.length>2){path.splice(selected,1);selected=Math.min(selected,path.length-1);playhead=path[selected].time*activeFraction();save();}
    if(action==='image')$('input[type=file]').click();
    if(action==='clearref'){++loadGeneration;media.clear();manualImage=null;linkedSrc='';refreshReference();}
    if(action==='close'){
      const last=path[path.length-1],first=path[0];
      // O upstream so ativa a closure com 360 exatos; arredonda para a volta inteira mais
      // proxima, sem nunca cair em zero, e devolve altura e raio ao valor inicial.
      const voltas=Math.round(last.azimuth/360)||(last.azimuth>=0?1:-1);
      last.azimuth=voltas*360;last.elevation=first.elevation;last.distance=first.distance;
      save();
    }
    if(action==='pure'){let changed=false;for(const k of path){if(k.elevation!==0){k.elevation=0;changed=true;}}if(changed)save();}
  });
  $('[data-role=count]').addEventListener('change',e=>{stop();const n=Number(e.target.value),next=[];for(let i=0;i<n;i++){const t=snapTime(i/(n-1));next.push({time:t,...pathPoseAt(t)});}path=next;selected=Math.min(selected,n-1);playhead=path[selected].time*activeFraction();save();});
  $('[data-role=duration]').disabled=!setDuration;
  $('[data-role=duration]').addEventListener('change',e=>{stop();setDuration?.(Number(e.target.value));update();});
  let loadGeneration=0;
  $('input[type=file]').addEventListener('change',e=>{
    const file=e.target.files[0];if(!file)return;e.target.value='';stop();const generation=++loadGeneration;
    if(file.type.startsWith('video/')||/\.(mp4|webm|mov|m4v|ogv)$/i.test(file.name)){manualImage=null;image=null;media.load(file);referenceLabel();return;}
    media.clear();const url=URL.createObjectURL(file),img=new Image();
    img.onload=()=>{URL.revokeObjectURL(url);if(disposed||generation!==loadGeneration)return;manualImage=img;refreshReference();};
    img.onerror=()=>{URL.revokeObjectURL(url);if(disposed||generation!==loadGeneration)return;toolError='Não foi possível abrir a imagem.';update(false);};img.src=url;
  });
  function referenceLabel(){
    const box=$('[data-role=refsrc]');box.replaceChildren();
    const text=media.active()?'PT: Vídeo local · somente prévia EN: Local video · preview only':manualImage?'Referência: arquivo local':(image?'Referência: node conectado':'Referência: nenhuma · conecte uma imagem em reference_image');
    box.append(document.createTextNode(text));
    if(manualImage||media.active()){const clear=document.createElement('button');clear.className='clearref';clear.dataset.action='clearref';clear.textContent='usar o node';box.append(clear);}
  }
  function refreshReference(){
    if(media.active()){image=media.ready()?media.video:null;referenceLabel();draw(poseAt(playhead));return;}
    if(manualImage){if(image!==manualImage){image=manualImage;draw(poseAt(playhead));}referenceLabel();return;}
    const src=linkedImage?.()||'';
    if(src!==linkedSrc){
      linkedSrc=src;linkedImg=null;
      if(src){const img=new Image();img.onload=()=>{if(disposed||linkedSrc!==src||media.active()||manualImage)return;linkedImg=img;image=img;referenceLabel();draw(poseAt(playhead));};
        img.onerror=()=>{if(disposed||linkedSrc!==src||media.active()||manualImage)return;image=null;referenceLabel();draw(poseAt(playhead));};img.src=src;}
      else{image=null;referenceLabel();draw(poseAt(playhead));}
      return;
    }
    if(image!==linkedImg){image=linkedImg;draw(poseAt(playhead));}
    referenceLabel();
  }
  function sync(){const fraction=activeFraction();if(fraction!==previousFraction){stop();playhead=clamp(playhead/previousFraction*fraction,0,1);previousFraction=fraction;}const raw=read();if(raw!==lastRaw){try{const data=JSON.parse(raw);if(!Array.isArray(data)||data.length<2||data.length>24)throw Error();for(let i=0;i<data.length;i++){const p=data[i];if(p.height==null)p.height=0;if(!['time','azimuth','elevation','distance','height'].every(k=>typeof p[k]==='number'&&Number.isFinite(p[k]))||p.time<0||p.time>1||p.distance<.1||p.distance>4||Math.abs(p.elevation)>89||Math.abs(p.height)>3||(i&&p.time<=data[i-1].time))throw Error();}const first=data[0];if(first.time!==0||first.azimuth!==0||first.elevation!==0||first.distance!==1||first.height!==0)throw Error();path=data;lastRaw=raw;toolError='';selected=Math.min(selected,path.length-1);playhead=path[selected].time*activeFraction();}catch{$('.error').textContent='Trajetória inválida. Corrija o JSON ou use Reset. O primeiro ponto deve ser 0, 0°, 0°, distância 1.';return;}}update();}
  const observer=new ResizeObserver(()=>{draw(poseAt(playhead));drawDial();});observer.observe(canvas);sync();
  refreshReference();poll=setInterval(refreshReference,1200);
  async function setDepthPreview(meta,urlFor){
    const generation=++depthGeneration;
    try{const state=await loadDepthPreview(meta,urlFor);if(disposed||generation!==depthGeneration)return;depthPreview=state;toolError='';}
    catch(error){if(disposed||generation!==depthGeneration)return;depthPreview=null;toolError='PT: Não foi possível carregar a prévia do Depth Warp. EN: Could not load the Depth Warp preview.';console.warn('[Camera H3] depth preview',error);}
    update(false);
  }
  return {element:root,setDepthPreview,sync(){modeSelect.value=frameMode?.()||'Freeze Frame';sync();refreshReference();},destroy(){disposed=true;++depthGeneration;stop();media.destroy();clearInterval(poll);observer.disconnect();}};
}
