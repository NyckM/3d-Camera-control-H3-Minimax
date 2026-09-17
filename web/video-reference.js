// Local preview media only. The selected file is never uploaded or serialized.
export function createVideoReference(host, {duration, onReady, onError}) {
  const video=document.createElement('video');
  video.muted=true;video.playsInline=true;video.preload='auto';video.loop=false;
  video.setAttribute('aria-label','Reference video');video.style.cssText='width:100%;max-height:220px;display:block;background:#101015';
  host.append(video);host.hidden=true;
  let url='',disposed=false;
  const ready=()=>!disposed&&!!url&&Number.isFinite(video.duration)&&video.duration>0&&video.readyState>=2;
  video.addEventListener('loadeddata',()=>{if(!disposed&&url)onReady();});
  video.addEventListener('durationchange',()=>{if(ready())onReady();});
  video.addEventListener('error',()=>{if(!disposed&&url)onError('PT: Não foi possível decodificar o vídeo. Tente MP4 H.264 ou WebM. EN: Cannot decode video. Try H.264 MP4 or WebM.');});
  function clear(){video.pause();video.removeAttribute('src');video.load();if(url)URL.revokeObjectURL(url);url='';host.hidden=true;}
  return {
    video,ready,
    load(file){clear();url=URL.createObjectURL(file);host.hidden=false;video.src=url;video.load();},
    clear,
    seek(progress){if(ready()&&!video.seeking){const target=Math.min(Math.max(0,progress)*video.duration,Math.max(0,video.duration-.001));if(Math.abs(video.currentTime-target)>.025)video.currentTime=target;}},
    async play(progress){if(!ready())throw Error('PT: Aguarde o vídeo carregar. EN: Wait for the video to load.');this.seek(progress);video.playbackRate=video.duration/duration();await video.play();},
    pause(){video.pause();},
    progress(){return ready()?Math.min(1,video.currentTime/video.duration):0;},
    rate(){return ready()?video.duration/duration():1;},
    active(){return !!url;},
    destroy(){disposed=true;clear();}
  };
}
