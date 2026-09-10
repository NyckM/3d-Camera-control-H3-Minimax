import { app } from '../../scripts/app.js';
import { api } from '../../scripts/api.js';
import { createCameraEditor } from './panel.js';
import { resolveLinkedImage } from './linked-image.js';

app.registerExtension({
  name: 'local.h3.camera_editor',
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if(nodeData.name!=='H3LocalCameraEditor')return;
    const created=nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated=function(){
      const result=created?.apply(this,arguments);
      const node=this,find=name=>node.widgets.find(w=>w.name===name),trajectory=find('camera_trajectory');
      const editor=createCameraEditor({
        read:()=>trajectory.value,
        write:value=>{trajectory.value=value;trajectory.callback?.(value);node.setDirtyCanvas(true,true);},
        duration:()=> (parseInt(find('profile').value,10)-1)/24,
        interpolation:()=>find('interpolation').value,
        setDuration:frames=>{const w=find('profile');w.value=w.options.values.find(v=>parseInt(v,10)===frames);w.callback?.(w.value);},
        linkedImage:()=>{try{return resolveLinkedImage(app.graph,node,q=>api.apiURL(q));}catch{return '';}},
        // Toggle buttons in the panel drive the real ComfyUI widgets, so a saved workflow
        // keeps whatever the person selected and the two never disagree.
        switches:()=>{
          const flip=(name,options,hint,label)=>{
            const w=find(name); if(!w) return null;
            const on=String(w.value)===options[1];
            return {label:label+(on?' ON':' OFF'),on,hint,
              toggle(){w.value=options[on?0:1];w.callback?.(w.value);node.setDirtyCanvas(true,true);}};
          };
          return [
            flip('prompt_detail',['v15 baseline','extended contracts'],
                 'Acrescenta separação de eixos, teste de direção por borda, completude do giro e graus por segundo. Desligado, o prompt sai idêntico ao v15.',
                 'Contratos estendidos'),
            flip('runtime_task',['scene coverage | camera path','directed | new camera angle'],
                 'Liga o preset de 39 frames do H3 Edit, que entrega uma imagem em vez de vídeo. O widget profile passa a ser ignorado.',
                 'Ângulo único (imagem)'),
          ].filter(Boolean);
        },
        elevationRange:()=>{const w=find('elevation_range');return w?Number(String(w.value).replace(/[^\d]/g,''))||30:30;},
      });
      const widget=node.addDOMWidget('camera_editor','H3_CAMERA_EDITOR',editor.element,{serialize:false});
      widget.computeSize=()=>[600,880];
      widget.computeLayoutSize=()=>({minHeight:880,maxHeight:880});
      for(const name of ['camera_trajectory','profile','interpolation','elevation_range','prompt_detail','runtime_task','subject_box']){
        const w=find(name);if(!w)continue;const callback=w.callback;
        w.callback=function(){const r=callback?.apply(this,arguments);editor.sync();return r;};
      }
      const configure=node.onConfigure;
      node.onConfigure=function(){const r=configure?.apply(this,arguments);editor.sync();return r;};
      const connections=node.onConnectionsChange;
      node.onConnectionsChange=function(){const r=connections?.apply(this,arguments);editor.sync();return r;};
      const removed=node.onRemoved;
      node.onRemoved=function(){editor.destroy();return removed?.apply(this,arguments);};
      node.setSize([650,Math.max(node.size[1],1200)]);
      return result;
    };
  }
});
