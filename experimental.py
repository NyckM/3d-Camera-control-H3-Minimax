from .guide_render import CameraGuideRender, CameraGuideVideo
"""Local prompt experiments, not the fal runtime / Experimentos locais de prompt."""
import json
from .prompt_compose import camera_prompt, CameraPromptCompose
from .motion import H3CameraEditor as StableEditor, MotionReference

EXPERIMENT_MODES = ['Off', 'Article compact', 'Article numbers only']

def numeric_payload(plan):
    """Only one calibrated path; never mix HUD and model direction in the prompt."""
    return {
        'schema': 'bruxosdovfx.camera-experiment.v1',
        'reference': '<Video 1>' if plan['frame_mode']=='Motion Frame' else '<Picture 1>',
        'frame_mode': plan['frame_mode'],
        'subject_box': plan['coordinate_anchor']['box'],
        'box_role': 'initial subject region' if plan['coordinate_anchor']['kind']=='user_subject' else 'initial image boundary, not subject detection',
        'camera_motion_duration_s': plan['duration_s'],
        'output_duration_s': plan['output_duration_s'],
        'time_unit': 'normalized 0..1 of camera_motion_duration_s',
        'angle_unit': 'degrees, signed unwrapped offsets relative to the first camera',
        'distance_unit': 'ratio to the first camera radius',
        'interpolation': plan['interpolation'],
        'smooth_curve': 'none (linear)' if plan['interpolation']=='linear' else 'monotone cubic per axis' if plan['prompt_detail']=='extended contracts' else 'smoothstep per segment',
        'roll_degrees': 0,
        'keyframes': [{k:p[k] for k in ('time','azimuth','elevation','distance')} for p in plan['model_path']],
    }

def experiment_text(plan, payload, mode, sections=False):
    motion=plan['frame_mode']=='Motion Frame'
    reference=payload['reference']
    source=('Preserve the identity, scene and action progression of <Video 1>. Camera holds do not freeze the source action.' if motion else
            'Use <Picture 1> as the exact initial image. Freeze the captured scene in world space while the camera moves; preserve identities, materials and lighting.')
    if plan['frame_mode']=='Action Frame':
        source=plan['reference']+' '+plan['preserve']+' Camera holds do not freeze subject action.'
    body=[]
    if plan['frame_mode']!='Freeze Frame' and plan.get('user_instruction','').strip():body.append('Scene and action: '+plan['user_instruction'].strip())
    body.extend([source, plan['coordinate_anchor']['instruction']])
    if mode=='Article compact':
        body.append('Move the camera around the same target; keep aiming at it with fixed focal length and zero roll. Positive orbit goes toward the moving camera RIGHT and negative toward its LEFT. Elevation is a physical rise or fall around the target. Distance is the camera radius ratio, not a digital zoom. Preserve signed full turns.')
        body.append(plan['motion'])
        # Short segment direction, no speculative background travel or redundant contracts.
        for a,b in zip(plan['model_path'],plan['model_path'][1:]):
            delta={k:b[k]-a[k] for k in ('azimuth','elevation','distance')}
            moves=[]
            if abs(delta['azimuth'])>1e-8:moves.append(f"orbit {abs(delta['azimuth']):g} degrees to camera {'RIGHT' if delta['azimuth']>0 else 'LEFT'}")
            if abs(delta['elevation'])>1e-8:moves.append(f"{'raise' if delta['elevation']>0 else 'lower'} camera to elevation offset {b['elevation']:g} degrees")
            if abs(delta['distance'])>1e-8:moves.append(f"{'move away' if delta['distance']>0 else 'move closer'} to radius {b['distance']:g}")
            body.append(f"{a['time']*plan['duration_s']:.3f}s–{b['time']*plan['duration_s']:.3f}s: "+('; '.join(moves) if moves else 'hold the camera viewpoint')+'.')
    body.extend(['Camera keyframes:',json.dumps(payload,ensure_ascii=False,separators=(',',':'))])
    if plan['loop_closure_enabled']:
        # Hold endpoint conditioning identical across recipes without rich orbit prose.
        body.append(f"<Picture 2> is the same reference image and anchors the frame at {plan['duration_s']:.6f}s.")
    if plan['runtime_task']=='directed | new camera angle':
        body.append(f"Reach the last camera pose by {plan['duration_s']:.6f}s and hold through {plan['output_duration_s']:.6f}s.")
    if plan['frame_mode']=='Freeze Frame' and plan.get('user_instruction','').strip():body.append('Additional direction: '+plan['user_instruction'].strip())
    body.append('One continuous shot. No cuts or visible coordinates. Silence.')
    text='\n'.join(body)
    if not sections:return text
    return (f'subject_definitions:\n{reference} is the source reference.\n\n'
            f'summary:\nOne continuous shot with the supplied camera timeline.\n\n'
            f'retention_analysis:\n{source}\n\ndetailed_description:\n{text}\n\n'
            'overall_soundscape:\nSilence.\n\nnon_diegetic_music:\nN/A')

class H3Camera(StableEditor):
    DESCRIPTION=('PT: Planejador de câmera para o MiniMax H3. Arraste a câmera na esfera, marque keyframes e o node\n'
                 'compila a trajetória em prompts. Ele compila PROMPTS, não embeddings de câmera: nenhum adaptador\n'
                 'de câmera é carregado e nenhuma API é chamada, então a precisão angular ainda depende do modelo.\n'
                 'EN: Camera planner for MiniMax H3. Drag the camera on the sphere, mark keyframes and the node\n'
                 'compiles that trajectory into prompts. It compiles PROMPTS, not camera embeddings: no camera\n'
                 'adapter is loaded and no API is called, so angular accuracy still depends on the model.')
    RETURN_TYPES=StableEditor.RETURN_TYPES+('STRING',)
    RETURN_NAMES=StableEditor.RETURN_NAMES+('camera_prompt',)
    OUTPUT_TOOLTIPS=StableEditor.OUTPUT_TOOLTIPS+('PT: Somente câmera, sem congelamento ou referências obrigatórias. Ligue ao Camera Prompt Compose. EN: Camera only, without freezing or mandatory reference tokens. Connect to Camera Prompt Compose.',)
    @classmethod
    def INPUT_TYPES(cls):
        data=super().INPUT_TYPES()
        data['optional']['experiment_mode']=(EXPERIMENT_MODES,{'default':'Off','tooltip':
            'PT: Off usa v29. Article compact combina texto curto e keyframes; Article numbers only testa números sem direção verbal por trecho. Mantenha seed, loop closure e instruction iguais; instruction vazio isola melhor a comparação. São hipóteses de prompt locais.\n'
            'EN: Off uses v29. Article compact combines short text and keyframes; Article numbers only tests numbers without per-segment verbal direction. Keep seed, loop closure and instruction identical; an empty instruction isolates the comparison. These are local prompt hypotheses.'})
        return data
    # Explicit input names preserve ComfyUI input delivery and older widget layouts.
    def run(self,camera_trajectory,profile,interpolation,instruction,subject_framing=None,minimax_format=None,reference_image=None,elevation_range=None,orbit_direction=None,subject_box=None,runtime_task=None,prompt_detail=None,frame_mode='Freeze Frame',source_fps=24.,freeze_index=0,ui_language='Português',loop_closure='auto',experiment_mode='Off'):
        if experiment_mode not in EXPERIMENT_MODES:
            raise ValueError('PT: Experimento desconhecido. EN: Unknown experiment mode.')
        result=list(super().run(camera_trajectory,profile,interpolation,instruction,subject_framing,minimax_format,reference_image,elevation_range,orbit_direction,subject_box,runtime_task,prompt_detail,frame_mode,source_fps,freeze_index,ui_language,loop_closure))
        plan=json.loads(result[2]);payload=numeric_payload(plan)
        if experiment_mode!='Off':
            # Apply AFTER Motion Frame conversion so temporal reference semantics survive.
            result[0]=experiment_text(plan,payload,experiment_mode,True)
            result[4]=experiment_text(plan,payload,experiment_mode,minimax_format=='coordinate + H3 sections')
            plan['experiment']={'mode':experiment_mode,'payload':payload,'control':'local text prompt hypothesis, no native numerical camera conditioning'}
            result[2]=json.dumps(plan,ensure_ascii=False,indent=2)
        en=ui_language=='English'
        result[3]+='\nExperimental: '+experiment_mode+'. '+('Off uses v29. Active experiments override minimax_format with compact text plus data (H3 sections still apply). No camera adapter or fal API is used.' if en else 'Off usa v29. Experimentos ativos substituem minimax_format por texto compacto com dados (as seções H3 continuam disponíveis). Não usa adaptador de câmera nem API fal.')
        if experiment_mode!='Off' and plan['loop_closure_enabled']:
            result[3]+='\n'+('End-frame anchoring remains ON in this test. Keep it identical in A/B comparisons.' if en else 'A ancoragem do último frame permanece ON neste teste. Mantenha igual na comparação A/B.')
        result.append(camera_prompt(plan))
        return tuple(result)

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
