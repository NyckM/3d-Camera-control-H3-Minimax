import { installLanguage } from './language.js';
import { app } from '../../scripts/app.js';
import { migrateGraph, packValues, applyValues, VALUES_KEY } from './legacy-workflow.js';
const NODE_ID='BruxosH3Camera';
const CAMERA_WIDGETS=[];
const CAMERA_SPEC={};
import { api } from '../../scripts/api.js';
import { createCameraEditor } from './panel.js';
import { resolveLinkedImage } from './linked-image.js';

app.registerExtension({
  name: 'bruxosdovfx.h3.camera_experimental',
  // PT: conserta workflows salvos antes da v32 antes do grafo ser montado (valores e fios).
  // EN: repairs pre-v32 workflows before the graph is built (values and wires).
  beforeConfigureGraph(graphData){
    try{
      const report=migrateGraph(graphData,CAMERA_WIDGETS,CAMERA_SPEC);
      if(report.nodes)console.info(`[Camera H3] workflow anterior à v32 migrado: ${report.nodes} node(s), ${report.links} ligação(ões) realinhada(s)`+(report.dropped?`, ${report.dropped} removida(s)`:''));
      for(const text of report.texts)console.info('[Camera H3] o widget instruction saiu na v32. O texto era:',text);
    }catch(error){console.warn('[Camera H3] migração do workflow falhou',error);}
  },
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if(!['BruxosH3Camera','BruxosH3CameraExperimental','H3LocalCameraEditor'].includes(nodeData.name))return;
    const created=nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated=function(){
      const result=created?.apply(this,arguments);
      const node=this,find=name=>node.widgets.find(w=>w.name===name),trajectory=find('camera_trajectory');
      const editor=createCameraEditor({
        frameMode:()=>find('frame_mode')?.value||'Freeze Frame',
        setFrameMode:value=>{const w=find('frame_mode');if(w){w.value=value;w.callback?.(value);node.setDirtyCanvas(true,true);}},
        read:()=>trajectory.value,
        write:value=>{trajectory.value=value;trajectory.callback?.(value);node.setDirtyCanvas(true,true);},
        duration:()=>(parseInt(find('profile').value,10)-1)/24,
        interpolation:()=>find('interpolation').value,
        setInterpolation:value=>{const w=find('interpolation');w.value=value;w.callback?.(value);},
        loopClosure:()=>find('loop_closure')?.value||'auto',
        setLoopClosure:value=>{const w=find('loop_closure');if(w){w.value=value;w.callback?.(value);node.setDirtyCanvas(true,true);}},
        ...(find('experiment_mode')?{
          experimentMode:()=>find('experiment_mode').value,
          setExperimentMode:value=>{const w=find('experiment_mode');w.value=value;w.callback?.(value);node.setDirtyCanvas(true,true);},
        }:{}),
        setDuration:frames=>{const w=find('profile');w.value=w.options.values.find(v=>parseInt(v,10)===frames);w.callback?.(w.value);},
        linkedImage:()=>{try{return resolveLinkedImage(app.graph,node,q=>api.apiURL(q));}catch{return '';}},
        elevationRange:()=>{const w=find('elevation_range');return w?Number(String(w.value).replace(/[^\d]/g,''))||30:30;},
        ...(find('depth_animation')?{
          depthWarp:()=>find('depth_animation').value==='Depth Warp',
          setDepthWarp:value=>{const w=find('depth_animation');w.value=value;w.callback?.(value);node.setDirtyCanvas(true,true);},
          depthOffset:()=>({azimuth:Number(find('warp_offset_azimuth')?.value)||0,elevation:Number(find('warp_offset_elevation')?.value)||0,distance:Number(find('warp_offset_distance')?.value)||1}),
        }:{}),
      });
      node.__h3CameraEditor=editor;
      const language=installLanguage(editor.element,()=>find('ui_language')?.value||'Português',value=>{const w=find('ui_language');if(w){w.value=value;w.callback?.(value);node.setDirtyCanvas(true,true);}});
      const widget=node.addDOMWidget('camera_editor','H3_CAMERA_EDITOR',editor.element,{serialize:false});
      widget.computeSize=()=>[600,880];
      widget.computeLayoutSize=()=>({minHeight:880,maxHeight:880});
      for(const name of ['camera_trajectory','profile','interpolation','elevation_range','subject_box','frame_mode','ui_language','loop_closure','depth_animation','warp_offset_azimuth','warp_offset_elevation','warp_offset_distance']){
        const w=find(name);if(!w)continue;const callback=w.callback;
        w.callback=function(){const r=callback?.apply(this,arguments);editor.sync();language.sync();return r;};
      }
      const configure=node.onConfigure;
      node.onConfigure=function(){const r=configure?.apply(this,arguments);editor.sync();language.sync();return r;};
      const connections=node.onConnectionsChange;
      node.onConnectionsChange=function(){const r=connections?.apply(this,arguments);editor.sync();language.sync();return r;};
      const removed=node.onRemoved;
      node.onRemoved=function(){language.destroy();editor.destroy();return removed?.apply(this,arguments);};
      node.setSize([650,Math.max(node.size[1],1200)]);
      return result;
    };
    // PT: a execução devolve os PNGs da prévia do Depth Warp. EN: execution returns the Depth Warp preview PNGs.
    if(nodeData?.name===NODE_ID&&nodeData?.input){
      // PT: guarda o que cada widget aceita hoje; a migração usa isso para achar a leitura certa
      // dos valores antigos em vez de adivinhar a versão do workflow.
      CAMERA_WIDGETS.length=0;
      for(const group of ['required','optional']){
        for(const [name,spec] of Object.entries(nodeData.input?.[group]||{})){
          const type=spec?.[0];
          const options=spec?.[1]||{};
          if(Array.isArray(type)){CAMERA_WIDGETS.push(name);CAMERA_SPEC[name]={options:type,default:options.default};}
          else if(type==='INT'||type==='FLOAT'){CAMERA_WIDGETS.push(name);CAMERA_SPEC[name]={numeric:true,default:options.default};}
          else if(type==='BOOLEAN'){CAMERA_WIDGETS.push(name);CAMERA_SPEC[name]={boolean:true,default:options.default};}
          else if(type==='STRING'){CAMERA_WIDGETS.push(name);CAMERA_SPEC[name]={};}
        }
      }
    }
    // PT: grava e lê os valores por NOME, além da lista posicional do ComfyUI. Isto encerra a classe
    // de bug em que acrescentar ou remover um widget embaralhava workflows salvos.
    // EN: stores and reads values BY NAME besides ComfyUI's positional list, ending the class of bug
    // where adding or removing a widget scrambled saved workflows.
    const serialize=nodeType.prototype.onSerialize;
    nodeType.prototype.onSerialize=function(info){
      const r=serialize?.apply(this,arguments);
      try{(info.properties??(info.properties={}))[VALUES_KEY]=packValues(this.widgets);}catch(e){}
      return r;
    };
    const configured=nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure=function(info){
      const r=configured?.apply(this,arguments);
      try{
        const saved=info?.properties?.[VALUES_KEY];
        const restored=applyValues(this.widgets,saved);
        if(restored)this.setDirtyCanvas?.(true,true);
      }catch(error){console.warn('[Camera H3] valores por nome',error);}
      return r;
    };
    const executed=nodeType.prototype.onExecuted;
    nodeType.prototype.onExecuted=function(message){
      const r=executed?.apply(this,arguments);
      const raw=message?.h3_depth_warp?.[0];
      if(raw&&this.__h3CameraEditor){
        try{
          const meta=typeof raw==='string'?JSON.parse(raw):raw;
          this.__h3CameraEditor.setDepthPreview(meta,ref=>api.apiURL(`/view?filename=${encodeURIComponent(ref.filename)}&type=${encodeURIComponent(ref.type||'temp')}&subfolder=${encodeURIComponent(ref.subfolder||'')}`));
        }catch(error){console.warn('[Camera H3] depth warp preview',error);}
      }
      return r;
    };
  }
});
