// node tests/test_v32_migrate.cjs — workflows salvos antes da v32: valores por nome e fios no soquete certo.
const assert=require('assert');const path=require('path');
(async()=>{
const {migrateGraph,LEGACY_WIDGETS,REMOVED,LAYOUTS,scoreLayout,packValues,applyValues,sanitizeWidgets,VALUES_KEY}=await import(path.join(__dirname,'..','web','legacy-workflow.js'));
// spec real do node hoje, lido do Python para o teste não repetir a lista à mão
const {execFileSync}=require('child_process');
const SPEC=JSON.parse(execFileSync('python3',['-c',`
import sys,types,importlib,json
p=types.ModuleType('bx');p.__path__=['${path.join(__dirname,'..').replace(/\\/g,'/')}'];sys.modules['bx']=p
ed=importlib.import_module('bx.experimental')
d=ed.H3Camera.INPUT_TYPES();out={}
for g in ('required','optional'):
    for k,v in d[g].items():
        t=v[0]
        if isinstance(t,list): out[k]={'options':t}
        elif t in ('INT','FLOAT'): out[k]={'numeric':True}
        elif t=='BOOLEAN': out[k]={'boolean':True}
        elif t=='STRING': out[k]={}
print(json.dumps(out))
`],{encoding:'utf8'}));
const CURRENT_WIDGETS=Object.keys(SPEC);
const CURRENT=CURRENT_WIDGETS;

// valores plausíveis por widget: a migração agora escolhe a leitura que encaixa nas opções reais,
// então a fixture precisa ter valores de verdade, não os nomes dos campos.
const VALUE={instruction:'a dancer spins',experiment_mode:'Off',runtime_task:'free',prompt_detail:'v15 baseline',
  freeze_index:0,frame_mode:'Motion Frame',warp_length:124,source_fps:24,subject_box:'',camera_trajectory:'[]'};

function legacyGraph(){
  // Camera H3 como a v31 salvava: 3 soquetes + entradas convertidas na ordem antiga.
  const inputs=[{name:'reference_image',link:43},{name:'depth',link:null},{name:'moge_geometry',link:4}];
  LEGACY_WIDGETS.forEach(name=>inputs.push({name,widget:{name},link:name==='subject_box'?33:name==='instruction'?77:null}));
  const values=LEGACY_WIDGETS.map(n=>VALUE[n]!==undefined?VALUE[n]:(SPEC[n]?.options?SPEC[n].options[0]:(SPEC[n]?.numeric?0:'')));
  return {nodes:[
    {id:5,type:'BruxosH3Camera',inputs,outputs:[{name:'depth_warp',links:[6]}],widgets_values:values},
    {id:33,type:'BruxosH3SubjectBox',inputs:[],outputs:[{name:'subject_box',links:[33]}]},
    {id:77,type:'PrimitiveString',inputs:[],outputs:[{name:'STRING',links:[77]}]}],
    links:[[43,44,0,5,0,'IMAGE'],[4,4,0,5,2,'MOGE_GEOMETRY'],
           [33,33,0,5,3+LEGACY_WIDGETS.indexOf('subject_box'),'STRING'],
           [77,77,0,5,3+LEGACY_WIDGETS.indexOf('instruction'),'STRING']]};
}

const graph=legacyGraph();
const report=migrateGraph(graph,CURRENT_WIDGETS,SPEC);
const node=graph.nodes[0];
const names=node.inputs.map(i=>i.widget?.name??i.name);

// os widgets que saíram não estão mais no node
for(const gone of REMOVED) assert.ok(!names.includes(gone),`${gone} ficou`);
// soquetes de verdade continuam nos índices 0..2
assert.deepEqual(names.slice(0,3),['reference_image','depth','moge_geometry']);
// cada link aponta para o nome certo, não para o índice antigo
const slotOf=id=>graph.links.find(l=>l[0]===id)?.[4];
assert.equal(names[slotOf(43)],'reference_image');
assert.equal(names[slotOf(4)],'moge_geometry');
assert.equal(names[slotOf(33)],'subject_box','o fio do subject_box tem que seguir o nome');
// o link que ia para instruction some, e a saída que o listava também é limpa
assert.equal(slotOf(77),undefined,'link órfão precisa sair');
assert.equal(report.dropped,1);
assert.deepEqual(graph.nodes[2].outputs[0].links,[]);
// valores realinhados por nome
const values=new Map(CURRENT.map((n,i)=>[n,node.widgets_values[i]]));
assert.equal(values.get('frame_mode'),'Motion Frame');
assert.equal(values.get('warp_length'),124);
assert.equal(values.get('warp_format'),SPEC['warp_format'].options[0]);
assert.equal(node.widgets_values.length,CURRENT.length);
assert.deepEqual(report.texts,['a dancer spins'],'o texto do instruction é avisado, não perdido');
// rodar de novo não estraga nada (idempotente)
const again=migrateGraph(graph,CURRENT_WIDGETS,SPEC);
assert.equal(again.nodes,0);
assert.deepEqual(node.inputs.map(i=>i.widget?.name??i.name),names);
// o mesmo node dentro de um subgraph também precisa ser migrado
const nested={definitions:{subgraphs:[legacyGraph()]},nodes:[],links:[]};
const deep=migrateGraph(nested,CURRENT_WIDGETS,SPEC);
const sub=nested.definitions.subgraphs[0], subNode=sub.nodes[0];
const subNames=subNode.inputs.map(i=>i.widget?.name??i.name);
assert.equal(deep.nodes,1,'subgraph precisa ser migrado');
for(const gone of REMOVED) assert.ok(!subNames.includes(gone),`${gone} ficou no subgraph`);
assert.equal(subNames[sub.links.find(l=>l[0]===33)[4]],'subject_box','fio do subgraph realinhado');
assert.equal(subNode.widgets_values.length,CURRENT.length);
assert.deepEqual(deep.texts,['a dancer spins']);
// v29: layout antigo com runtime_task, prompt_detail, freeze_index e experiment_mode
const V29=LAYOUTS.at(-1);
const v29Values=V29.map(n=>({camera_trajectory:'[]',profile:'124 frames (~5.17s)',interpolation:'smooth',
  instruction:'texto antigo',subject_framing:'close-up',minimax_format:'coordinate only',elevation_range:'+/-60',
  orbit_direction:'same as HUD',subject_box:'',runtime_task:'free',prompt_detail:'v15 baseline',
  frame_mode:'Motion Frame',source_fps:30,freeze_index:0,ui_language:'English',loop_closure:'off',
  experiment_mode:'Off'}[n]));
const old={nodes:[{id:7,type:'BruxosH3Camera',inputs:[{name:'reference_image',link:null}],outputs:[],widgets_values:v29Values}],links:[]};
const r29=migrateGraph(old,CURRENT_WIDGETS,SPEC);
const read=new Map(CURRENT_WIDGETS.map((n,i)=>[n,old.nodes[0].widgets_values[i]]));
assert.equal(read.get('frame_mode'),'Motion Frame','v29: frame_mode caiu no lugar certo');
assert.equal(read.get('source_fps'),30);
assert.equal(read.get('ui_language'),'English');
assert.equal(read.get('loop_closure'),'off');
assert.equal(read.get('elevation_range'),'+/-60');
assert.deepEqual(r29.texts,['texto antigo'],'o texto do instruction antigo é avisado');
// e a leitura certa pontua mais que a identidade, que é o que faz a escolha
assert.ok(scoreLayout(v29Values,V29,SPEC,CURRENT_WIDGETS)>scoreLayout(v29Values,CURRENT_WIDGETS,SPEC,CURRENT_WIDGETS));
// --- a trava definitiva: valores por nome sobrevivem a qualquer mudança de ordem ---
const widgets=CURRENT_WIDGETS.map(name=>({name,value:SPEC[name]?.options?SPEC[name].options[0]:(SPEC[name]?.numeric?7:'x')}));
widgets.find(w=>w.name==='frame_mode').value='Motion Frame';
widgets.find(w=>w.name==='warp_length').value=124;
const saved=packValues(widgets);
assert.equal(saved.frame_mode,'Motion Frame');
assert.equal(Object.keys(saved).length,CURRENT_WIDGETS.length);

// versão futura: dois widgets novos no MEIO e um removido — o pior caso posicional
const future=[{name:'camera_trajectory',value:''},{name:'novo_widget_1',value:'?'},
  ...CURRENT_WIDGETS.filter(n=>n!=='camera_trajectory'&&n!=='loop_closure').map(n=>({name:n,value:'errado'})),
  {name:'novo_widget_2',value:'?'}];
const restored=applyValues(future,saved);
assert.equal(restored,CURRENT_WIDGETS.length-1,'restaura todos que ainda existem');
assert.equal(future.find(w=>w.name==='frame_mode').value,'Motion Frame');
assert.equal(future.find(w=>w.name==='warp_length').value,124);
assert.equal(future.find(w=>w.name==='novo_widget_1').value,'?','widget novo mantém o padrão');
assert.equal(applyValues(future,undefined),0,'sem mapa salvo, não mexe em nada');
assert.equal(VALUES_KEY,'bruxos_widget_values');

// --- rede de segurança: arquivo já salvo embaralhado não pode travar a execução ---
const dirty=[{name:'frame_mode',value:'Português'},{name:'ui_language',value:'Depth Warp'},
  {name:'source_fps',value:'auto'},{name:'warp_invert_depth',value:'Meridian (H3)'},
  {name:'warp_length',value:124},{name:'profile',value:SPEC['profile'].options[0]}];
const fixed=sanitizeWidgets(dirty,SPEC);
assert.deepEqual(fixed.sort(),['frame_mode','source_fps','ui_language','warp_invert_depth'].sort());
assert.ok(SPEC['frame_mode'].options.includes(dirty[0].value),'frame_mode voltou para uma opção válida');
assert.equal(typeof dirty[2].value,'number','source_fps virou número');
assert.equal(typeof dirty[3].value,'boolean');
assert.equal(dirty[4].value,124,'valor já válido não é tocado');
assert.equal(dirty[5].value,SPEC['profile'].options[0]);

console.log('v32 migrate: ok',report,'| subgraph ok | v29 ok',r29.layout,'| por nome ok | saneamento ok');
})().catch(e=>{console.error(e);process.exit(1);});
