// Display-only translations. Widget names, option values and model prompts stay unchanged.
// Ordem das entradas: [português, english]; 中文 vem do mapa abaixo e cai no inglês quando falta.
// Entry order: [Portuguese, English]; Chinese comes from the map below and falls back to English.
export const LANGUAGES=['Português','English','中文'];
const CHINESE=new Map(Object.entries({
 'CÂMERA H3':'H3 摄像机','Frame congelado':'冻结帧','Frame em movimento':'运动帧','Animar imagem':'动画图像',
 'Duração':'时长','Azimute':'方位角','Elevação':'仰角','Distância':'距离','Altura':'升降','Lateral':'横移','Órbita':'环绕',
 'Keyframes':'关键帧','↺ Reiniciar':'↺ 重置','⟳ Órbita pura':'⟳ 纯环绕','⟲ Fechar volta':'⟲ 闭合环绕',
 '− Remover ponto':'− 删除关键帧','+ Keyframe agora':'+ 添加关键帧','Imagem / vídeo':'图像 / 视频',
 'Visão da câmera':'摄像机视角','◈ Depth Warp':'◈ 深度变形','Ampliar canvas':'放大画布','Restaurar vista':'重置视角',
 'Zoom da prévia':'预览缩放','Presets':'预设','Aplicar trajetória':'应用轨迹','Desfazer preset':'撤销预设',
 'Vista frontal':'正面','Frente ¾':'前四分之三','Vista lateral':'侧面','Traseira ¾':'后四分之三','Vista traseira':'背面',
 'Imagem de referência':'参考图像','Referência: nenhuma':'参考：无','Idioma / Language':'语言','Experimento':'实验',
 'Remover keyframe':'删除关键帧','Testes':'测试','Front View':'正面','Side View':'侧面','Back View':'背面',
}));
const pairs=[
 ['CAMERA H3','CÂMERA H3'],['Freeze Frame','Frame congelado'],['Motion Frame','Frame em movimento'],
 ['Duração','Duration'],['Azimuth','Azimute'],['Elevation','Elevação'],['Distance','Distância'],['Height','Altura'],['Lateral','Lateral'],
 ['↺ Reiniciar','↺ Reset'],['⟳ Órbita pura','⟳ Pure orbit'],['Fechar volta','Close orbit'],
 ['⟲ Fechar volta','⟲ Close orbit'],['− Remover ponto','− Remove point'],['Órbita','Orbit'],
 ['Imagem de referência','Reference image'],['Remover keyframe','Remove keyframe'],['Testes','Tests'],
 ['usar o node','use connected node'],['Front View','Vista frontal'],['Front ¾','Frente ¾'],
 ['Side View','Vista lateral'],['Rear ¾','Traseira ¾'],['Back View','Vista traseira'],
 ['Referência: arquivo local','Reference: local file'],['Referência: node conectado','Reference: connected node'],
 ['Referência: nenhuma · conecte uma imagem em reference_image','Reference: none · connect an image to reference_image'],
 ['Não foi possível abrir a imagem.','Could not open the image.'],
 ['Trajetória inválida. Corrija o JSON ou use Reset. O primeiro ponto deve ser 0, 0°, 0°, distância 1.','Invalid path. Fix the JSON or reset. The first point must be 0, 0°, 0°, distance 1.'],
 ['Keyframe 1: imagem original · posição inicial fixa','Keyframe 1: source image · fixed starting pose'],
 ['Arraste a câmera na horizontal para orbitar, na vertical para elevar · o eixo trava no primeiro movimento · role para distância · arraste o fundo para olhar ao redor','Drag the camera horizontally to orbit, vertically to raise/lower · first movement locks the axis · scroll for distance · drag the background to orbit the view'],
 ['loop closure elegível / eligible · 360°','loop closure eligible · 360°'],
 ['loop closure OFF · volta aberta / open path','loop closure OFF · open path'],
 ['Motion Frame · loop closure OFF · ação continua / action continues','Motion Frame · loop closure OFF · action continues'],
 ['Keyframes','Keyframes'],['Referência: nenhuma','Reference: none'],
 ['Azimuth degrees','Graus de azimute'],['Elevation degrees','Graus de elevação'],
 ['Elevation slider','Controle de elevação'],['Camera distance','Distância da câmera'],['Camera height','Altura da câmera'],['Height slider','Controle de altura'],['Camera lateral','Travelling lateral'],['Lateral slider','Controle de travelling'],
 ['Distance slider','Controle de distância'],['Remove selected keyframe','Remover keyframe selecionado'],
 ['Modo de referência / Reference mode','Reference mode'],
];
// Some originals above were English already; define their Portuguese/English order explicitly.
const englishFirst=new Set(['CAMERA H3','Freeze Frame','Motion Frame','Azimuth','Elevation','Distance','Height','Camera height','Height slider','Front View','Front ¾','Side View','Rear ¾','Back View','Azimuth degrees','Elevation degrees','Elevation slider','Camera distance','Distance slider','Remove selected keyframe']);
const dictionary=new Map();
for(const [a,b] of pairs){const pair=englishFirst.has(a)?[b,a]:[a,b];dictionary.set(a,pair);dictionary.set(b,pair);}
dictionary.set('loop closure elegível / eligible · 360°',['loop closure elegível · 360°','loop closure eligible · 360°']);
dictionary.set('loop closure OFF · volta aberta / open path',['loop closure OFF · volta aberta','loop closure OFF · open path']);
dictionary.set('Motion Frame · loop closure OFF · ação continua / action continues',['Frame em movimento · loop closure OFF · ação continua','Motion Frame · loop closure OFF · action continues']);
export function translate(text,language){
  const zh=language==='中文',en=language==='English'||zh;
  if(zh){const direct=CHINESE.get(text);if(direct)return direct;}
  if(dictionary.has(text)){const pair=dictionary.get(text);return (zh&&CHINESE.get(pair[0]))||pair[en?1:0];}
  if(text.trimStart().startsWith('PT: ')&&text.includes('EN: ')){
    const raw=text.trimStart().slice(4),boundary=raw.indexOf('EN: ');
    const english=raw.slice(boundary+4),chinese=english.indexOf('ZH: ');
    if(!en)return raw.slice(0,boundary).trim();
    if(zh&&chinese>=0)return english.slice(chinese+4).trim();
    return (chinese>=0?english.slice(0,chinese):english).trim();
  }
  let m=text.match(/^Keyframe (\d+): mova a câmera para alterar · (.+)$/);
  if(m)return en?`Keyframe ${m[1]}: move the camera to edit · ${m[2]}`:text;
  m=text.match(/^Keyframe (\d+) at (.+)$/);if(m)return en?text:`Keyframe ${m[1]} em ${m[2]}`;
  if(text.startsWith('Elevação de ')){
    const angle=text.match(/Elevação de ([\d.]+)°/)?.[1];
    return en?`Elevation ${angle}°: large elevation changes can reveal an overhead view.`:`Elevação ${angle}°: grandes mudanças podem revelar uma vista de cima.`;
  }
  if(text.startsWith('Contratos estendidos'))return en?text.replace('Contratos estendidos','Extended contracts'):text;
  if(text.startsWith('Ângulo único (imagem)'))return en?text.replace('Ângulo único (imagem)','Single angle (still)'):text;
  if(text.startsWith('Acrescenta separação de eixos'))return en?'Adds axis separation, direction checks, orbit completion and angular rates. Off uses the baseline prompt.':text;
  if(text.startsWith('Liga o preset de 39 frames'))return en?'Enables the H3 Edit 39-frame preset, returning a still image instead of video. Ignores profile.':text;
  const short={'Reset camera path':['Reiniciar trajetória','Reset camera path'],'Play camera preview':['Reproduzir prévia da câmera','Play camera preview'],'Pause camera preview':['Pausar prévia da câmera','Pause camera preview'],'Azimuth dial':['Disco de azimute','Azimuth dial'],'Camera animation playhead':['Cursor da animação da câmera','Camera animation playhead'],'Cena e trajetória da câmera':['Cena e trajetória da câmera','Camera scene and path'],'Video duration':['Duração do vídeo','Video duration'],'Keyframe count':['Quantidade de keyframes','Keyframe count']};
  return (zh&&CHINESE.get(text))||short[text]?.[en?1:0]||text;
}

export function installLanguage(root,getLanguage,setLanguage){
  const select=document.createElement('select');select.setAttribute('aria-label','Idioma / Language');
  for(const name of LANGUAGES){const option=document.createElement('option');option.value=name;option.textContent=name;select.append(option);}
  select.style.maxWidth='125px';root.querySelector('header').append(select);
  const records=new WeakMap();let disposed=false;
  function value(owner,key,current){
    const record=records.get(owner)||{};let entry=record[key];
    if(!entry||current!==entry.last)entry={raw:current,last:current};
    const next=translate(entry.raw,getLanguage());entry.last=next;record[key]=entry;records.set(owner,record);return next;
  }
  function apply(){
    if(disposed)return;
    select.value=getLanguage();
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let node;
    while(node=walker.nextNode()){
      if(['STYLE','SCRIPT','TEXTAREA'].includes(node.parentElement?.tagName)||select.contains(node))continue;
      const next=value(node,'text',node.nodeValue);if(next!==node.nodeValue)node.nodeValue=next;
    }
    for(const el of root.querySelectorAll('[title],[aria-label]'))for(const attr of ['title','aria-label']){
      if(!el.hasAttribute(attr))continue;const current=el.getAttribute(attr),next=value(el,attr,current);if(next!==current)el.setAttribute(attr,next);
    }
  }
  const observer=new MutationObserver(apply);observer.observe(root,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['title','aria-label']});
  select.addEventListener('change',()=>{setLanguage(select.value);apply();});apply();
  return {sync:apply,destroy(){disposed=true;observer.disconnect();}};
}

dictionary.set('Action Frame',['Animar imagem','Action Frame']);
