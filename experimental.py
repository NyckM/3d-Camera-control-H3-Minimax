from .guide_render import CameraGuideRender, CameraGuideVideo
"""PT: Node principal do Camera H3, com Depth Warp. EN: Main Camera H3 node, with Depth Warp."""
import json
import os
from .prompt_compose import camera_prompt, CameraPromptCompose
from .motion import H3CameraEditor as StableEditor, MotionReference
from . import depth_warp as dw

# PT: widgets escondidos atras do botao Advanced do node. EN: widgets tucked behind the node Advanced toggle.
ADVANCED={'subject_framing','minimax_format','elevation_range','orbit_direction','subject_box','runtime_task',
          'prompt_detail','loop_closure','freeze_index','warp_hfov','warp_depth_ratio','warp_invert_depth',
          'warp_smooth_depth','warp_aim','warp_pivot_depth','warp_direction','warp_long_side','warp_offset_azimuth',
          'warp_offset_elevation','warp_offset_distance','warp_hold_at','warp_hold_frames','warp_format'}


class H3Camera(StableEditor):
    DESCRIPTION=('PT: Planejador de câmera para o MiniMax H3. Arraste a câmera na esfera, marque keyframes e o node\n'
                 'compila a trajetória em prompts. Ele compila PROMPTS, não embeddings de câmera: nenhum adaptador\n'
                 'de câmera é carregado e nenhuma API é chamada, então a precisão angular ainda depende do modelo.\n'
                 'EN: Camera planner for MiniMax H3. Drag the camera on the sphere, mark keyframes and the node\n'
                 'compiles that trajectory into prompts. It compiles PROMPTS, not camera embeddings: no camera\n'
                 'adapter is loaded and no API is called, so angular accuracy still depends on the model.\n'
                 'Depth Warp: com depth_animation = Depth Warp e depth ou moge_geometry conectados, a saída depth_warp\n'
                 'reprojeta a referência seguindo os keyframes, no formato do <Video 2> do Viggle Meridian.\n'
                 'With depth_animation = Depth Warp and depth or moge_geometry connected, depth_warp reprojects the\n'
                 'reference along the keyframes, in Viggle Meridian <Video 2> format.')
    RETURN_TYPES=StableEditor.RETURN_TYPES+('STRING','IMAGE','MASK')
    RETURN_NAMES=StableEditor.RETURN_NAMES+('camera_prompt','depth_warp','warp_mask')
    OUTPUT_TOOLTIPS=StableEditor.OUTPUT_TOOLTIPS+('PT: Somente câmera, sem congelamento ou referências obrigatórias. Ligue ao Camera Prompt Compose. EN: Camera only, without freezing or mandatory reference tokens. Connect to Camera Prompt Compose.',
        'PT: Vídeo de controle do Depth Warp: a referência reprojetada pela profundidade seguindo os keyframes, cinza 128 onde a câmera original nunca viu. Ligue como <Video 2> no bruxosdovfx • Meridian Reference, ou use como vídeo-guia. Só existe com depth_animation = Depth Warp; em Off os nodes ligados aqui não executam.\n'
        'EN: Depth Warp control video: the reference reprojected through depth along the keyframes, grey 128 where the source camera never looked. Wire as <Video 2> into bruxosdovfx • Meridian Reference, or use it as a video guide. Only produced with depth_animation = Depth Warp; when Off, nodes wired here do not run.',
        'PT: Máscara dos buracos do warp: 1 onde é buraco (área a gerar), 0 onde há pixel reprojetado. EN: Warp hole mask: 1 on the holes (area to generate), 0 where a pixel was reprojected.')
    @classmethod
    def INPUT_TYPES(cls):
        data=super().INPUT_TYPES()
        # PT: v30 Depth Warp. Tudo ACRESCENTADO no fim: widget_values é posicional nos workflows salvos.
        # EN: v30 Depth Warp. Everything APPENDED: widget_values is positional in saved workflows.
        o=data['optional']
        o['depth_animation']=(dw.ANIMATIONS,{'default':'Off','tooltip':
            'PT: Depth Warp anima a sua referência pela profundidade seguindo os keyframes: sai um vídeo com a cena reprojetada e buracos cinza onde a câmera original não viu. É o <Video 2> do Viggle Meridian, o fine-tune do MiniMax-H3 guiado por geometria. Precisa de reference_image e de depth ou moge_geometry. Off não calcula nada e bloqueia os nodes ligados em depth_warp/warp_mask.\n'
            'EN: Depth Warp animates your reference through depth along the keyframes: it outputs the scene reprojected with grey holes where the source camera never looked. This is <Video 2> for Viggle Meridian, the geometry-guided MiniMax-H3 fine-tune. Needs reference_image plus depth or moge_geometry. Off computes nothing and blocks nodes wired to depth_warp/warp_mask.'})
        o['depth']=('IMAGE',{'tooltip':'PT: Mapa de profundidade relativo (Depth Anything V2 etc.) da mesma imagem/sequência: claro = perto. 1 mapa ou um por frame. EN: Relative depth map (Depth Anything V2 etc.) for the same image/sequence: bright = near. One map or one per frame.'})
        o['moge_geometry']=('MOGE_GEOMETRY',{'tooltip':'PT: Geometria métrica do Run MoGe Inference (nativo do ComfyUI). É o caminho recomendado: profundidade em metros, com máscara e intrinsics; depth_ratio, invert e smooth deixam de valer. EN: Metric geometry from Run MoGe Inference (ComfyUI built-in). The recommended path: metric depth with mask and intrinsics; depth_ratio, invert and smooth no longer apply.'})
        o['warp_hfov']=('FLOAT',{'default':50.0,'min':0.0,'max':120.0,'step':1.0,'tooltip':'PT: Campo de visão horizontal assumido da referência. ~50 é lente normal. 0 lê do moge_geometry (costuma ficar ~10% curto). Não é o FOV ilustrativo de 40° do painel. EN: Assumed horizontal field of view of the reference. ~50 is a normal lens. 0 reads it from moge_geometry (usually ~10% short). Not the panel illustrative 40° FOV.'})
        o['warp_depth_ratio']=('FLOAT',{'default':6.0,'min':1.5,'max':1000.0,'step':0.5,'tooltip':'PT: Só depth relativo (sem MoGe). Razão longe/perto da cena: menor = relevo achatado e warp limpo; maior = mais paralaxe e mais rasgos. Close de rosto 2.5–4, plano médio 4–8, cena ampla 8–16. EN: Relative depth only. Far/near ratio: lower = flatter and cleaner; higher = more parallax and more tearing. Face close-up 2.5–4, medium 4–8, wide 8–16.'})
        o['warp_invert_depth']=('BOOLEAN',{'default':False,'tooltip':'PT: Só depth relativo. Ligue se o warp parecer do avesso (fundo andando como frente). EN: Relative depth only. Turn on if the warp looks inside-out (background moving like foreground).'})
        o['warp_smooth_depth']=('BOOLEAN',{'default':False,'tooltip':'PT: Só depth relativo. Suavização guiada pela imagem: menos pontinhos magenta, borda um pouco mais macia. Usa opencv. EN: Relative depth only. Image-guided smoothing: fewer magenta speckles, slightly softer edges. Uses opencv.'})
        o['warp_aim']=(dw.AIMS,{'default':'source aim','tooltip':'PT: source aim: a câmera orbita o pivô mas mira onde a original mirava, então o keyframe 1 é exatamente a imagem. look at pivot: centraliza o pivô; com subject_box fora do centro, o primeiro frame já sai reenquadrado. EN: source aim: orbits the pivot but looks where the source looked, so keyframe 1 is exactly the image. look at pivot: centres the pivot; with an off-centre subject_box, frame 1 is already reframed.'})
        o['warp_pivot_depth']=('FLOAT',{'default':0.0,'min':0.0,'max':1000.0,'step':0.01,'tooltip':'PT: Profundidade do centro da órbita. 0 = automático: mediana 3D do subject_box; sem caixa, 1.05 no depth relativo (o sujeito mais próximo) ou a metade mais próxima do centro no MoGe (metros). O raio da órbita é distance × pivô. EN: Orbit centre depth. 0 = auto: 3D median of subject_box; without a box, 1.05 for relative depth (nearest subject) or the nearer half of the centre for MoGe (metres). Orbit radius is distance × pivot.'})
        o['warp_direction']=(dw.DIRECTIONS,{'default':'panel (geometric)','tooltip':'PT: panel segue exatamente o que o painel desenha (geometria real). model_path usa o caminho calibrado por orbit_direction, igual ao Camera Guide Render. EN: panel follows exactly what the panel draws (real geometry). model_path uses the path calibrated by orbit_direction, like Camera Guide Render.'})
        o['warp_length']=('INT',{'default':0,'min':0,'max':2000,'step':1,'tooltip':'PT: Frames do warp. 0 = length do perfil (124/243/362). O Meridian só aceita 73, 90, 107, 124, 141, 158, 175 e 243: a trajetória inteira é esticada sobre esse comprimento a 24 fps. EN: Warp frame count. 0 = profile length (124/243/362). Meridian only accepts 73, 90, 107, 124, 141, 158, 175 and 243: the whole path is stretched over it at 24 fps.'})
        o['warp_long_side']=('INT',{'default':0,'min':0,'max':4096,'step':16,'tooltip':'PT: Reduz o maior lado antes do warp. 0 = resolução da referência. O splat é de 2 px, então gere no tamanho que vai para o modelo (ex.: 960 ou 1280). EN: Downscales the longest side before warping. 0 = reference resolution. The splat is 2 px, so warp at the size the model receives (e.g. 960 or 1280).'})
        o['warp_offset_azimuth']=('FLOAT',{'default':0.0,'min':-180.0,'max':180.0,'step':0.5,'tooltip':'PT: Soma este azimute a TODA a trajetória, só no warp. O keyframe 1 do Camera H3 é sempre a fonte (0°); use isto quando quiser que o clipe já comece num ângulo novo no frame 1 (ex.: −25). Não muda o prompt. EN: Adds this azimuth to the WHOLE path, warp only. Camera H3 keyframe 1 is always the source (0°); use this when the clip should already start at a new angle on frame 1 (e.g. −25). Does not change the prompt.'})
        o['warp_offset_elevation']=('FLOAT',{'default':0.0,'min':-89.0,'max':89.0,'step':0.5,'tooltip':'PT: Soma esta elevação a toda a trajetória, só no warp. EN: Adds this elevation to the whole path, warp only.'})
        o['warp_offset_distance']=('FLOAT',{'default':1.0,'min':0.1,'max':4.0,'step':0.01,'tooltip':'PT: Multiplica a distância de toda a trajetória, só no warp. Aproximação e afastamento são o que os modelos seguem com menos confiança. EN: Multiplies the whole path distance, warp only. Dollying in and out is what these models follow least reliably.'})
        o['warp_hold_at']=('INT',{'default':0,'min':0,'max':100000,'step':1,'tooltip':'PT: Só Motion Frame. Frame da FONTE que congela quando warp_hold_frames > 0: a ação roda até ele, segura, e retoma do frame seguinte. A câmera não para. EN: Motion Frame only. SOURCE frame held when warp_hold_frames > 0: the action plays up to it, holds, then resumes from the next frame. The camera keeps moving.'})
        o['warp_hold_frames']=('INT',{'default':0,'min':0,'max':2000,'step':1,'tooltip':'PT: Quantos frames de SAÍDA o congelamento ocupa. 0 desliga. É o --freeze F:N do Meridian (bullet time). EN: How many OUTPUT frames the hold lasts. 0 disables it. This is Meridian --freeze F:N (bullet time).'})
        # PT: node compacto. O frontend do ComfyUI esconde estes widgets atras do botao Advanced.
        # EN: compact node. The ComfyUI frontend hides these widgets behind the Advanced toggle.
        o['warp_format']=(dw.FORMATS,{'default':'Meridian (H3)','tooltip':'PT: Formato do vídeo de controle: Meridian (H3) — cinza 128, z-buffer 3x3, poda de bordas de profundidade, canvas classe 480 (832x480 em 16:9) e só 73/90/107/124/141/158/175/243 frames, para o <Video 2> do Viggle Meridian. EN: Control video format: Meridian (H3) — grey 128, 3x3 z-buffer, depth-edge pruning, 480-class canvas (832x480 at 16:9) and only 73/90/107/124/141/158/175/243 frames, for Viggle Meridian <Video 2>.'})
        for group in ('required','optional'):
            for name,spec in data[group].items():
                if name in ADVANCED and isinstance(spec,tuple) and len(spec)>1 and isinstance(spec[1],dict):
                    spec[1]['advanced']=True
        return data
    @classmethod
    def VALIDATE_INPUTS(cls,subject_framing=None,minimax_format=None,elevation_range=None,orbit_direction=None,runtime_task=None,prompt_detail=None,depth_animation=None,warp_aim=None,warp_direction=None,warp_format=None):
        checked=StableEditor.VALIDATE_INPUTS.__func__(cls,subject_framing,minimax_format,elevation_range,orbit_direction,runtime_task,prompt_detail)
        if checked is not True:return checked
        for value,allowed in ((depth_animation,dw.ANIMATIONS),(warp_aim,dw.AIMS),(warp_direction,dw.DIRECTIONS),(warp_format,dw.ALL_FORMATS)):
            if value is None or (isinstance(value,str) and not value.strip()):continue
            if value not in allowed:return f'Unknown option {value!r}. Allowed: {", ".join(allowed)}.'
        return True
    # Explicit input names preserve ComfyUI input delivery and older widget layouts.
    def run(self,camera_trajectory,profile,interpolation,instruction,subject_framing=None,minimax_format=None,reference_image=None,elevation_range=None,orbit_direction=None,subject_box=None,runtime_task=None,prompt_detail=None,frame_mode='Freeze Frame',source_fps=24.,freeze_index=0,ui_language='Português',loop_closure='auto',depth_animation='Off',depth=None,moge_geometry=None,warp_hfov=50.0,warp_depth_ratio=6.0,warp_invert_depth=False,warp_smooth_depth=False,warp_aim='source aim',warp_pivot_depth=0.0,warp_direction='panel (geometric)',warp_length=0,warp_long_side=0,warp_offset_azimuth=0.0,warp_offset_elevation=0.0,warp_offset_distance=1.0,warp_hold_at=0,warp_hold_frames=0,warp_format='Meridian (H3)'):
        result=list(super().run(camera_trajectory,profile,interpolation,instruction,subject_framing,minimax_format,reference_image,elevation_range,orbit_direction,subject_box,runtime_task,prompt_detail,frame_mode,source_fps,freeze_index,ui_language,loop_closure))
        plan=json.loads(result[2])
        en=ui_language=='English'
        result.append(camera_prompt(plan))
        depth_animation=dw.ANIMATIONS[0] if depth_animation in (None,'') else depth_animation
        if depth_animation not in dw.ANIMATIONS:
            raise ValueError('PT: depth_animation desconhecido. EN: Unknown depth_animation.')
        if depth_animation=='Off':
            if depth is not None or moge_geometry is not None:
                result[3]+='\n'+('Depth Warp: depth is connected but depth_animation is Off, so nothing was warped.' if en else 'Depth Warp: há profundidade conectada, mas depth_animation está Off; nada foi reprojetado.')
            result.extend([_blocked(),_blocked()])
            return tuple(result)
        warp,holes,warp_info,preview=_run_depth_warp(plan,plan['frame_mode'],reference_image,depth,moge_geometry,source_fps,freeze_index,subject_box,
            warp_hfov,warp_depth_ratio,warp_invert_depth,warp_smooth_depth,warp_aim,warp_pivot_depth,warp_direction,warp_length,warp_long_side,en,
            (warp_offset_azimuth,warp_offset_elevation,warp_offset_distance),warp_format,warp_hold_at,warp_hold_frames)
        result[3]+='\n'+warp_info
        result.extend([warp,holes])
        if preview:
            return {'ui':{'h3_depth_warp':[json.dumps(preview)]},'result':tuple(result)}
        return tuple(result)


def _blocked():
    """PT: Em Off, bloqueia só quem está ligado nas saídas do warp. EN: When Off, blocks only nodes wired to the warp outputs."""
    try:
        from comfy_execution.graph import ExecutionBlocker
        return ExecutionBlocker(None)
    except Exception:
        return None


def _run_depth_warp(plan,frame_mode,reference_image,depth,moge_geometry,source_fps,freeze_index,subject_box,hfov,ratio,invert,smooth,aim,pivot_depth,direction,length,long_side,english,offset=(0.0,0.0,1.0),warp_format='Meridian (H3)',hold_at=0,hold_frames=0):
    progress=allocate=None;temp_dir=None
    try:
        import torch
        allocate=lambda rgb_shape,mask_shape:(torch.empty(rgb_shape,dtype=torch.float32),torch.empty(mask_shape,dtype=torch.float32))
    except ImportError:
        pass
    try:
        from comfy.utils import ProgressBar
        from comfy.model_management import throw_exception_if_processing_interrupted
        bar=[None]
        def progress(i,total):
            throw_exception_if_processing_interrupted()
            if bar[0] is None:bar[0]=ProgressBar(max(1,total))
            bar[0].update_absolute(i,total)
    except Exception:
        progress=None
    try:
        import folder_paths
        temp_dir=folder_paths.get_temp_directory();os.makedirs(temp_dir,exist_ok=True)
    except Exception:
        temp_dir=None
    return dw.build_depth_warp(plan,frame_mode,reference_image,depth,moge_geometry,source_fps,freeze_index,subject_box,
        hfov,ratio,invert,smooth,aim,pivot_depth,direction,length,long_side,english,progress,temp_dir,allocate,*offset,warp_format=warp_format,hold_at=hold_at,hold_frames=hold_frames)

from .subject_box import SubjectBoxPicker
from .image_path import ImagePath

# PT: BruxosH3Camera e BruxosH3MotionReference sao os ids atuais. Os ids antigos continuam
# registrados para que workflows ja salvos abram, mas via subclasses marcadas com
# DEPRECATED: o ComfyUI esconde node depreciado da busca e mantem ele carregavel, entao o
# menu mostra uma entrada so por node em vez de uma por alias.
# EN: BruxosH3Camera and BruxosH3MotionReference are the current ids. The old ids stay
# registered so already saved workflows open, but through subclasses flagged DEPRECATED:
# ComfyUI hides a deprecated node from search while keeping it loadable, so the menu shows
# one entry per node instead of one per alias.
class _LegacyCamera(H3Camera):
    DEPRECATED = True


class _LegacyMotion(MotionReference):
    DEPRECATED = True


NODE_CLASS_MAPPINGS = {
    'BruxosH3CameraGuideRender': CameraGuideRender,
    'BruxosH3CameraGuideVideo': CameraGuideVideo,
    'BruxosH3Camera': H3Camera,
    'BruxosH3CameraPromptCompose': CameraPromptCompose,
    'BruxosH3MotionReference': MotionReference,
    'BruxosH3SubjectBox': SubjectBoxPicker,
    'BruxosH3ImagePath': ImagePath,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    'BruxosH3CameraGuideRender': 'bruxosdovfx • Camera Guide Render',
    'BruxosH3CameraGuideVideo': 'bruxosdovfx • Camera Guide Video',
    'BruxosH3CameraPromptCompose': 'bruxosdovfx • Camera Prompt Compose',
    'BruxosH3Camera': 'bruxosdovfx \u2022 Camera H3',
    'BruxosH3MotionReference': 'bruxosdovfx \u2022 H3 Motion Reference',
    'BruxosH3SubjectBox': 'bruxosdovfx \u2022 H3 Subject Box',
    'BruxosH3ImagePath': 'bruxosdovfx \u2022 H3 Image Path',
}
for _id in ('BruxosH3CameraExperimental', 'H3LocalCameraEditor'):
    NODE_CLASS_MAPPINGS[_id] = _LegacyCamera
    NODE_DISPLAY_NAME_MAPPINGS[_id] = 'bruxosdovfx \u2022 Camera H3 (id antigo \u00b7 legacy)'
NODE_CLASS_MAPPINGS['BruxosH3MotionReferenceExperimental'] = _LegacyMotion
NODE_DISPLAY_NAME_MAPPINGS['BruxosH3MotionReferenceExperimental'] = (
    'bruxosdovfx \u2022 H3 Motion Reference (id antigo \u00b7 legacy)')
