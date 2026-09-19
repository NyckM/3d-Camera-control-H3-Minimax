import { installLanguage } from './language.js';
import { app } from '../../scripts/app.js';
import { api } from '../../scripts/api.js';
import { createCameraEditor } from './panel.js';
import { resolveLinkedImage } from './linked-image.js';

app.registerExtension({
  name: 'bruxosdovfx.h3.camera_experimental',
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
    // PT: v32 tirou instruction e experiment_mode. widgets_values é posicional, então workflows
    // salvos antes disso precisam ser remapeados por nome na hora de carregar.
    // EN: v32 dropped instruction and experiment_mode. widgets_values is positional, so workflows saved
    // before that are remapped by name on load.
    const LEGACY_ORDER=['camera_trajectory','profile','interpolation','instruction','subject_framing','minimax_format',
      'elevation_range','orbit_direction','subject_box','runtime_task','prompt_detail','frame_mode','source_fps',
      'freeze_index','ui_language','loop_closure','experiment_mode','depth_animation','warp_hfov','warp_depth_ratio',
      'warp_invert_depth','warp_smooth_depth','warp_aim','warp_pivot_depth','warp_direction','warp_length',
      'warp_long_side','warp_offset_azimuth','warp_offset_elevation','warp_offset_distance','warp_hold_at',
      'warp_hold_frames','warp_format'];
    const configure=nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure=function(info){
      const values=info?.widgets_values;
      if(Array.isArray(values)&&typeof values[3]==='string'&&LEGACY_ORDER.length-values.length<=2){
        const legacy=new Map(LEGACY_ORDER.slice(0,values.length).map((name,i)=>[name,values[i]]));
        if(legacy.has('instruction')&&legacy.has('ui_language')){
          const names=(this.widgets||[]).map(w=>w.name);
          if(!names.includes('instruction')){
            info.widgets_values=names.map((name,i)=>legacy.has(name)?legacy.get(name):this.widgets[i]?.value);
            const text=String(legacy.get('instruction')||'').trim();
            if(text)console.info('[Camera H3] v32 removeu o widget instruction. O texto estava:',text);
          }
        }
      }
      return configure?.apply(this,arguments);
    };
    // PT: a execução devolve os PNGs da prévia do Depth Warp. EN: execution returns the Depth Warp preview PNGs.
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
