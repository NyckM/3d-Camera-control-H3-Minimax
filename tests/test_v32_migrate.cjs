// node tests/test_v32_migrate.cjs — workflows salvos antes da v32: valores por nome e fios no soquete certo.
const assert=require('assert');const path=require('path');
(async()=>{
const {migrateGraph,LEGACY_WIDGETS,REMOVED}=await import(path.join(__dirname,'..','web','legacy-workflow.js'));
const CURRENT=LEGACY_WIDGETS.filter(n=>!REMOVED.includes(n));

function legacyGraph(){
  // Camera H3 como a v31 salvava: 3 soquetes + entradas convertidas na ordem antiga.
  const inputs=[{name:'reference_image',link:43},{name:'depth',link:null},{name:'moge_geometry',link:4}];
  LEGACY_WIDGETS.forEach(name=>inputs.push({name,widget:{name},link:name==='subject_box'?33:name==='instruction'?77:null}));
  const values=LEGACY_WIDGETS.map(n=>n==='instruction'?'a dancer spins':n==='warp_length'?124:n==='frame_mode'?'Motion Frame':n);
  return {nodes:[
    {id:5,type:'BruxosH3Camera',inputs,outputs:[{name:'depth_warp',links:[6]}],widgets_values:values},
    {id:33,type:'BruxosH3SubjectBox',inputs:[],outputs:[{name:'subject_box',links:[33]}]},
    {id:77,type:'PrimitiveString',inputs:[],outputs:[{name:'STRING',links:[77]}]}],
    links:[[43,44,0,5,0,'IMAGE'],[4,4,0,5,2,'MOGE_GEOMETRY'],
           [33,33,0,5,3+LEGACY_WIDGETS.indexOf('subject_box'),'STRING'],
           [77,77,0,5,3+LEGACY_WIDGETS.indexOf('instruction'),'STRING']]};
}

const graph=legacyGraph();
const report=migrateGraph(graph);
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
assert.equal(values.get('warp_format'),'warp_format');
assert.equal(node.widgets_values.length,CURRENT.length);
assert.deepEqual(report.texts,['a dancer spins'],'o texto do instruction é avisado, não perdido');
// rodar de novo não estraga nada (idempotente)
const again=migrateGraph(graph);
assert.equal(again.nodes,0);
assert.deepEqual(node.inputs.map(i=>i.widget?.name??i.name),names);
console.log('v32 migrate: ok',report);
})().catch(e=>{console.error(e);process.exit(1);});
