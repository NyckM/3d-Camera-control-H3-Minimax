"""CPU RGB guide renderer: analytic ray intersections, no editor overlays."""
import json
import math
from .camera import validate_path
from .trajectory_math import interpolate_pose
from .prompt_compose import camera_prompt


def parse_plan(raw):
    try:
        plan=json.loads(raw)
        validate_path(json.dumps(plan['model_path']))
        duration=float(plan['duration_s']);fps=float(plan['fps'])
        last=float(plan['last_frame_s']);frames=round(last*fps)+1
        if plan['runtime_task']!='scene coverage | camera path':
            raise ValueError('Use a video camera path, not a still-image task.')
        if fps!=24 or not 0<duration<=last+1e-6 or not 5<=frames<=362 or (frames-5)%17 or abs(last-(frames-1)/fps)>1e-6:
            raise ValueError('Guide requires a 24 fps H3 video plan with 17n+5 frames.')
        if plan['interpolation'] not in ('linear','smooth') or plan['prompt_detail'] not in ('v15 baseline','extended contracts'):
            raise ValueError('Unknown interpolation contract.')
        return plan,frames,fps
    except (KeyError,TypeError,OverflowError,json.JSONDecodeError) as error:
        raise ValueError('Connect Camera H3 storyboard_json, not the raw path or camera_prompt.') from error


def render_frame(pose,width,height,shape='mannequin',floor_cues='markers'):
    import numpy as np
    a,e=math.radians(pose['azimuth']),math.radians(pose['elevation'])
    eye=np.array([math.sin(a)*math.cos(e),math.sin(e),math.cos(a)*math.cos(e)])*pose['distance']*1.8
    forward=-eye/np.linalg.norm(eye)
    right=np.cross(forward,[0.,1.,0.]);right/=np.linalg.norm(right)
    up=np.cross(right,forward)
    yy,xx=np.mgrid[0:height,0:width]
    tangent=math.tan(math.radians(20))
    rays=forward+right*((2*(xx+.5)/width-1)*tangent*width/height)[...,None]+up*((1-2*(yy+.5)/height)*tangent)[...,None]
    pixels=np.empty((height,width,3),dtype=np.float32);pixels[:]=[.075,.095,.13]
    depth=np.full((height,width),np.inf)
    def paint(t,mask,color):
        selected=mask&(t>.025)&(t<depth)
        depth[selected]=t[selected];pixels[selected]=color
    # Infinite floor with sparse colored tiles for reading parallax. No grid/axes.
    denom=rays[...,1]
    t=np.divide(-.7-eye[1],denom,out=np.full_like(denom,np.inf),where=np.abs(denom)>1e-10)
    paint(t,np.isfinite(t),[.23,.25,.28])
    if floor_cues=='markers':
        safe=np.where(np.isfinite(t),t,0)
        x=eye[0]+safe*rays[...,0];z=eye[2]+safe*rays[...,2]
        for cx,cz,color in [(-1,-1,[.7,.26,.2]),(1,-1,[.23,.45,.72]),(-1,1,[.75,.61,.2]),(1,1,[.32,.64,.43])]:
            mask=(np.abs(x-cx)<.18)&(np.abs(z-cz)<.18)&(t>.025)&np.isfinite(t)
            pixels[mask]=color
    def box(center,size,color):
        low=np.array(center)-np.array(size)/2;high=np.array(center)+np.array(size)/2
        near=np.full((height,width),-np.inf);far=np.full((height,width),np.inf)
        for axis in range(3):
            d=rays[...,axis];parallel=np.abs(d)<1e-10
            l=np.divide(low[axis]-eye[axis],d,out=np.zeros_like(d),where=~parallel)
            h=np.divide(high[axis]-eye[axis],d,out=np.zeros_like(d),where=~parallel)
            inside=low[axis]<=eye[axis]<=high[axis]
            entry=np.where(parallel,-np.inf if inside else np.inf,np.minimum(l,h))
            leave=np.where(parallel,np.inf if inside else -np.inf,np.maximum(l,h))
            near=np.maximum(near,entry);far=np.minimum(far,leave)
        t=np.where(near>.025,near,far)
        paint(t,(far>=near)&np.isfinite(t),color)
    if shape=='ball':
        center=np.array([0.,-.2,0.]);offset=eye-center
        aa=np.sum(rays*rays,axis=-1);bb=2*np.sum(rays*offset,axis=-1);cc=np.dot(offset,offset)-.5**2
        disc=bb*bb-4*aa*cc;root=np.sqrt(np.maximum(disc,0));near=(-bb-root)/(2*aa);far=(-bb+root)/(2*aa)
        paint(np.where(near>.025,near,far),disc>=0,[.3,.65,.65])
    else:
        for center,size,color in [([0,.05,0],[.38,.55,.23],[.2,.59,.56]),([0,.47,0],[.25,.25,.25],[.77,.66,.54]),([- .27,.03,0],[.13,.52,.16],[.16,.48,.5]),([.27,.03,0],[.13,.52,.16],[.16,.48,.5]),([-.11,-.45,0],[.15,.5,.19],[.22,.38,.6]),([.11,-.45,0],[.15,.5,.19],[.22,.38,.6]),([0,.48,.135],[.13,.06,.035],[.95,.94,.82])]:
            box(center,size,color)
    return pixels


def render_sequence(plan,width,height,frames,fps,shape,floor_cues,progress=None):
    import numpy as np
    if not 64<=width<=1024 or not 64<=height<=1024 or width%8 or height%8 or width*height*frames>32_000_000:
        raise ValueError('Use dimensions divisible by 8 (64–1024); maximum 32 million pixels per batch. Reduce resolution or duration.')
    if shape not in ('mannequin','ball') or floor_cues not in ('plain','markers'):
        raise ValueError('Unknown guide appearance.')
    images=np.empty((frames,height,width,3),dtype=np.float32)
    for index in range(frames):
        if progress:progress(index)
        pose=interpolate_pose(plan['model_path'],(index/fps)/plan['duration_s'],plan['interpolation'],plan['prompt_detail'])
        images[index]=render_frame(pose,width,height,shape,floor_cues)
    if progress:progress(frames)
    return images


class CameraGuideRender:
    CATEGORY='bruxosdovfx/Camera H3'
    FUNCTION='render'
    RETURN_TYPES=('IMAGE','FLOAT','INT','STRING','STRING')
    RETURN_NAMES=('rgb_frames','fps','length','guide_prompt','info')
    DESCRIPTION='PT: Render CPU do plano calibrado em um guia RGB. Não executa H3. EN: CPU render of the calibrated path into an RGB guide. Does not run H3.'
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{
            'storyboard_json':('STRING',{'forceInput':True}),
            'width':('INT',{'default':320,'min':64,'max':1024,'step':8}),
            'height':('INT',{'default':192,'min':64,'max':1024,'step':8}),
            'subject_shape':(['mannequin','ball'],{'default':'mannequin'}),
            'floor_cues':(['plain','markers'],{'default':'markers'}),
            'video_reference_index':('INT',{'default':1,'min':1,'max':8,'tooltip':'PT: Número do token Video correspondente ao guia no encoder. EN: Video token number corresponding to the guide in the encoder.'})}}
    def render(self,storyboard_json,width,height,subject_shape='mannequin',floor_cues='markers',video_reference_index=1):
        plan,frames,fps=parse_plan(storyboard_json)
        if not isinstance(video_reference_index,int) or not 1<=video_reference_index<=8:raise ValueError('Invalid video reference index.')
        import torch
        from comfy.utils import ProgressBar
        from comfy.model_management import throw_exception_if_processing_interrupted
        bar=ProgressBar(frames)
        def progress(n):
            throw_exception_if_processing_interrupted();bar.update_absolute(n)
        images=torch.from_numpy(render_sequence(plan,width,height,frames,fps,subject_shape,floor_cues,progress))
        prompt=(f'Use <Video {video_reference_index}> as a camera-motion guide only: viewpoint, framing and timing. '
            'Do not copy its proxy appearance, body pose, action, floor or colored landmarks. '
            'Character appearance comes from the identity references; character and environmental actions come from the scene prompt.\n\n'+camera_prompt(plan))
        info=f'{frames} RGB frames, {width}x{height}, {fps:g} fps. Calibrated model_path; FOV 40 degrees. Static proxy only; action preservation is not guaranteed. Match the guide token to encoder video wiring.'
        return images,float(fps),frames,prompt,info


class CameraGuideVideo:
    CATEGORY='bruxosdovfx/Camera H3'
    FUNCTION='convert'
    RETURN_TYPES=('VIDEO',)
    RETURN_NAMES=('video',)
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{'rgb_frames':('IMAGE',),'fps':('FLOAT',{'default':24.,'min':1.,'max':60.})}}
    def convert(self,rgb_frames,fps):
        from fractions import Fraction
        try:from comfy_api.latest import InputImpl,Types
        except ImportError as error:raise RuntimeError('Native VIDEO API unavailable. Use rgb_frames with your existing video-save node.') from error
        if not math.isfinite(fps) or not 1<=fps<=60:raise ValueError('Invalid fps.')
        return (InputImpl.VideoFromComponents(Types.VideoComponents(images=rgb_frames,frame_rate=Fraction(str(fps))),bit_depth=8),)
