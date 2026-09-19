"""PT: Referência temporal para H3. EN: Temporal reference routing for H3."""
import json
import math
from . import camera as base
from .diagnostics import review_path, diagnostic_text

MODES = ['Freeze Frame', 'Motion Frame', 'Action Frame']
HELP = {
 'camera_trajectory': (
   'A trajetória da câmera em JSON, escrita pelo painel acima. Cada keyframe tem time de 0 a 1, azimuth e elevation '
   'em graus e distance como múltiplo do raio inicial. O primeiro keyframe é sempre a sua imagem: time 0, azimuth 0, '
   'elevation 0, distance 1. São poses de câmera, não frames do vídeo de entrada.',
   'The camera trajectory as JSON, written by the panel above. Each keyframe has time from 0 to 1, azimuth and '
   'elevation in degrees and distance as a multiple of the starting radius. The first keyframe is always your image: '
   'time 0, azimuth 0, elevation 0, distance 1. These are camera poses, not frames of the input video.'),
 'profile': (
   'Quantos frames a geração vai ter, a 24 fps. Todos os tempos escritos no prompt saem daqui, então ligue as saídas '
   'length e fps na sua geração em vez de digitar os números duas vezes. Não reamostra nem acelera o vídeo de '
   'referência: só define o comprimento da saída.',
   'How many frames the generation will have, at 24 fps. Every time written into the prompt comes from here, so wire '
   'the length and fps outputs into your generation instead of typing the numbers twice. It does not retime or speed '
   'up the reference video: it only sets the output length.'),
 'interpolation': (
   'Como a câmera se move entre dois keyframes. smooth acelera e desacelera nas pontas da tomada e mantém velocidade '
   'constante no meio, parando só onde o giro inverte de sentido. linear mantém uma única velocidade do primeiro ao '
   'último frame, o que é mais previsível para medir um teste.',
   'How the camera travels between two keyframes. smooth accelerates and decelerates at the ends of the take and '
   'holds a constant rate through the middle, stopping only where the rotation reverses. linear holds one single '
   'rate from the first frame to the last, which is more predictable when measuring a test.'),
 'subject_framing': (
   'O tipo de plano da sua imagem: close-up é rosto e ombros, medium shot é da cintura para cima, wide shot é o '
   'sujeito com o cenário em volta. Ele só registra essa informação no prompt; não aplica zoom, corte nem movimento. '
   'Para dizer ONDE o sujeito está no quadro, use o subject_box.',
   'The shot size of your image: close-up is face and shoulders, medium shot is waist up, wide shot is the subject '
   'with the surroundings. It only records that information in the prompt; it applies no zoom, crop or movement. To '
   'say WHERE the subject sits in the frame, use subject_box.'),
 'minimax_format': (
   'Como a saída minimax_prompt é escrita. coordinate only é o bloco de coordenadas em texto; coordinate + H3 '
   'sections é o mesmo dentro das seções do H3; as duas versões compact JSON entregam o plano como objeto JSON, com '
   'cerca de um terço das palavras. Prompt mais longo não é automaticamente melhor: compare na mesma trajetória.',
   'How the minimax_prompt output is written. coordinate only is the plain-text coordinate block; coordinate + H3 '
   'sections is the same inside the H3 sections; the two compact JSON variants deliver the plan as a JSON object at '
   'about a third of the word count. A longer prompt is not automatically better: compare on the same trajectory.'),
 'reference_image': (
   'A sua imagem, ou a sua sequência de frames. Ela aparece no painel como referência visual e a proporção real do '
   'quadro entra no prompt; sem ela tudo é normalizado para 16:9, o que erra a escala em imagens verticais. Motion '
   'Frame exige uma sequência de verdade, com 2 frames ou mais.',
   'Your image, or your sequence of frames. It shows in the panel as a visual reference and the real frame aspect '
   'goes into the prompt; without it everything is normalised to 16:9, which mis-scales vertical images. Motion '
   'Frame requires a real sequence, two frames or more.'),
 'elevation_range': (
   'O alcance do controle de elevação no painel, e com ele a sensibilidade do arraste vertical. Com o campo de visão '
   'assumido, o horizonte já sai do quadro por volta de 20 graus, então um alcance largo desperdiça quase todo o '
   'slider. Reduzir o alcance nunca reescreve um keyframe existente: o slider se abre para caber nele.',
   'The range of the elevation control in the panel, and with it the sensitivity of the vertical drag. With the '
   'assumed field of view the horizon already leaves the frame around 20 degrees, so a wide range wastes most of the '
   'slider. Narrowing it never rewrites an existing keyframe: the slider widens to hold it.'),
 'orbit_direction': (
   'Calibração do sentido de giro entre o painel e o H3. O painel desenha um sentido; se o vídeo gerado girar para o '
   'lado contrário, troque aqui. Isso inverte apenas o sinal enviado ao modelo: a sua trajetória salva continua '
   'exatamente igual.',
   'Calibrates the rotation sense between the panel and H3. The panel draws one direction; if the generated video '
   'turns the other way, flip this. It inverts only the sign sent to the model: your saved trajectory is untouched.'),
 'subject_box': (
   'A região onde o sujeito está NA SUA IMAGEM, no formato [L=0.5, T=0.1, W=0.2, H=0.6], em fração do quadro. Serve '
   'para o prompt identificar em torno de quem a câmera gira. Vazio, ele usa a imagem inteira de propósito, em vez '
   'de chutar uma caixa. Vale preencher quando o sujeito está longe do centro. É uma região no primeiro frame, não '
   'uma trajetória.',
   'The region where the subject sits IN YOUR IMAGE, as [L=0.5, T=0.1, W=0.2, H=0.6], in fractions of the frame. It '
   'lets the prompt identify who the camera orbits around. Left empty it uses the whole image on purpose, rather '
   'than guessing a box. Worth filling in when the subject is far from centre. It is a region in the first frame, '
   'not a trajectory.'),
 'frame_mode': (
   'Freeze Frame congela a cena e move só a câmera: é o contrato do H3 Edit e o modo que aceita os perfis longos. '
   'Motion Frame usa a ação da sua sequência e deixa ela continuar enquanto a câmera percorre os keyframes; nele a '
   'ancoragem do último frame é desligada, porque o fim deixa de ser igual ao começo.',
   'Freeze Frame holds the scene still and moves only the camera: that is the H3 Edit contract and the mode its long '
   'profiles accept. Motion Frame uses the action in your sequence and lets it carry on while the camera walks the '
   'keyframes; there the final-frame anchoring is switched off, because the end no longer matches the start.'),
 'source_fps': (
   'A taxa de quadros da sequência que você ligou. Em Motion Frame ela é usada para reamostrar a referência para 24 '
   'fps, então informar errado deixa a ação rápida ou lenta demais. Em Freeze Frame não tem efeito.',
   'The frame rate of the sequence you connected. In Motion Frame it is used to resample the reference to 24 fps, so '
   'a wrong value makes the action too fast or too slow. In Freeze Frame it has no effect.'),
 'ui_language': (
   'Idioma do painel e dos textos de diagnóstico. Os prompts enviados ao modelo continuam em inglês em qualquer '
   'opção, porque é a língua em que o H3 foi treinado.',
   'Language of the panel and the diagnostic text. The prompts sent to the model stay in English either way, because '
   'that is the language H3 was trained on.'),
 'loop_closure': (
   'Ancorar o último frame na imagem de origem. Em auto isso só acontece numa volta completa de 360 graus que termina '
   'na mesma altura e na mesma distância; aí o último frame é obrigado a bater com o primeiro, o que força o giro a '
   'se completar. off desliga para comparar testes lado a lado.',
   'Anchor the final frame to the source image. On auto that only happens for a full 360 degree turn ending at the '
   'same height and the same distance; the last frame is then forced to match the first, which makes the rotation '
   'complete. off disables it so you can compare tests side by side.'),
}

HELP['frame_mode'] = ('Freeze Frame congela a cena. Motion Frame preserva a ação de um vídeo com Ref2VA. Action Frame anima uma imagem: descreva a ação no Camera Prompt Compose e use um workflow nativo de imagem para vídeo. Freeze continua o padrão.', 'Freeze Frame freezes the scene. Motion Frame preserves video action with Ref2VA. Action Frame animates an image: describe the action in Camera Prompt Compose and use a native image-to-video workflow. Freeze remains the default.')


def help_text(name):
    pt,en=HELP[name]
    return 'PT: '+pt+'\nEN: '+en

def prepare_frames(images, mode, source_fps, freeze_index):
    if images is None:
        if mode=='Motion Frame':
            raise ValueError('PT: Conecte uma sequência IMAGE. EN: Connect an IMAGE sequence.')
        return None,None,0
    if len(images.shape)!=4 or images.shape[0]<1 or images.shape[-1]!=3:
        raise ValueError('PT: Use frames RGB [N,H,W,3]. EN: Use RGB frames [N,H,W,3].')
    count=int(images.shape[0])
    if mode in ('Freeze Frame', 'Action Frame'):
        if not 0<=freeze_index<count:
            raise ValueError('PT: freeze_index fora do lote. EN: freeze_index outside the batch.')
        first=images[freeze_index:freeze_index+1]
        return first,first,count
    if not math.isfinite(source_fps) or source_fps<=0:
        raise ValueError('PT: source_fps deve ser positivo. EN: source_fps must be positive.')
    target=int(round(count*24/source_fps))
    if count<2 or not 48<=target<=360:
        raise ValueError('PT: Motion Frame aceita 2 a 15 segundos; recorte o vídeo antes. EN: Motion Frame accepts 2–15 seconds; trim the source first.')
    indices=[min(count-1,int(i*source_fps/24)) for i in range(target)]
    frames=images[indices]
    # Native H3 video references truncate to 17k+5; make that visible in our own output.
    aligned=5+17*((target-5)//17)
    frames=frames[:aligned]
    return frames[:1],frames,count

def motion_plan(plan):
    """Apply temporal semantics only to generated fields; user prose stays untouched."""
    action = plan['frame_mode'] == 'Action Frame'
    reference = '<Picture 1>' if action else '<Video 1>'
    plan['reference'] = (f'Use {reference} as the initial scene and identity reference. Animate the action described by the user while the camera follows its timeline.' if action else
        'Use <Video 1> as the temporal reference. Preserve its action order and natural progression while changing the camera viewpoint. Do not compress or repeat the action to match camera keyframes.')
    plan['preserve'] = ('Preserve character identity, appearance and scene coherence while allowing poses, expressions, contacts and positions to evolve with the action. Environmental motion continues naturally.' if action else
        'Preserve identities, appearance and scene coherence, and continue the source actions of <Video 1>, including moving people and environmental elements.')
    plan['forbid'] = 'One continuous shot. No cuts, temporal freezing, digital zoom or visible planning annotations. Camera rotation must not substitute for the requested subject action.'
    plan['final'] = plan['final'].replace('final pose', 'final camera pose') + ' Camera holds and camera keyframes constrain only the viewpoint; the subject action continues through them.'
    plan['instruction'] = plan['user_instruction'].strip()
    for key in ('camera_choreography', 'coordinate_convention', 'rotation_direction'):
        if key in plan:
            plan[key] = plan[key].replace('the subject itself stays stationary', 'the subject continues its action independently').replace('fixed target', 'subject target').replace('do not rotate the subject instead', 'do not substitute subject rotation for camera motion; allow rotations required by the action')
    for segment in plan['segments']:
        segment['camera_mode'] = segment['camera_mode'].replace('the subject itself stays stationary', 'the subject continues its action independently').replace('fixed target', 'subject target')
    plan['coordinate_anchor']['instruction'] = plan['coordinate_anchor']['instruction'].replace('fixed orbit target', 'initial subject target')
    plan['coordinate_convention'] += ' The subject region identifies the initial target only; it does not lock body pose or world position. Follow the same subject as it moves.'
    return plan


def motion_payload(plan):
    # Send one calibrated path, never the raw HUD path or diagnostic metadata.
    return {key: plan[key] for key in ('frame_mode', 'reference', 'instruction', 'preserve',
        'coordinate_anchor', 'coordinate_convention', 'duration_s', 'fps', 'interpolation',
        'model_path', 'motion', 'final', 'forbid')}


def motion_text(plan, sections=False):
    reference = '<Picture 1>' if plan['frame_mode']=='Action Frame' else '<Video 1>'
    lines = ([f"Scene and action: {plan['instruction']}"] if plan['instruction'].strip() else []) + [plan['reference'], plan['preserve'],
        plan['coordinate_anchor']['instruction'], plan['coordinate_convention'],
        'Camera interpolation: '+plan['motion']]
    for segment in plan['segments']:
        lines.append(f"{segment['start_s']:.3f}s–{segment['end_s']:.3f}s: {segment['camera_mode']}.")
    lines.extend([plan['final'], plan['forbid'], 'Silence.'])
    text = '\n'.join(lines)
    if not sections:
        return text
    return (f'subject_definitions:\n{reference} is the source reference.\n\n'
        f'summary:\nContinuous subject action with a camera timeline.\n\n'
        f'retention_analysis:\nPreserve identity and scene coherence while action progresses.\n\n'
        f'detailed_description:\n{text}\n\noverall_soundscape:\nSilence.\n\nnon_diegetic_music:\nN/A')

class H3CameraEditor(base.H3CameraEditor):
    CATEGORY='bruxosdovfx/Camera H3'
    DESCRIPTION='PT: Planejador de câmera com Freeze Frame e Motion Frame. Movimento por prompt; vídeo de referência exige Ref2VA.\nEN: Camera planner with Freeze Frame and Motion Frame. Prompt-based motion; video reference requires Ref2VA.'
    RETURN_TYPES=base.H3CameraEditor.RETURN_TYPES
    RETURN_NAMES=base.H3CameraEditor.RETURN_NAMES
    OUTPUT_TOOLTIPS=tuple('PT: '+pt+'\nEN: '+en for pt,en in [
        ('Prompt completo nas seções do H3 (subject_definitions, summary, retention_analysis, detailed_description). '
         'Vai no compiled_prompt do Text Encode H3 Edit. Use este OU minimax_prompt, nunca os dois na mesma entrada.',
         'The full prompt in the H3 sections (subject_definitions, summary, retention_analysis, '
         'detailed_description). Goes into compiled_prompt on Text Encode H3 Edit. Use this OR minimax_prompt, never '
         'both into the same input.'),
        ('Dicionário de opções do H3 Edit, com as 13 chaves que o encoder dele lê. É obrigatório junto do prompt: '
         'chave que falta faz o encoder usar valores antigos guardados no workflow. Só vale em Freeze Frame; em '
         'Motion Frame ele sai marcado como incompatível, porque os perfis longos exigem cena congelada.',
         'The H3 Edit options dictionary, with the 13 keys its encoder reads. Required alongside the prompt: a '
         'missing key makes the encoder fall back to stale values saved in the workflow. Only meaningful in Freeze '
         'Frame; in Motion Frame it is marked incompatible, because the long profiles require a frozen scene.'),
        ('O plano inteiro em JSON: trajetória crua, poses por trecho, duração, caixa do sujeito, modo de frame e os '
         'diagnósticos. Serve para conferir o que o node entendeu, alimentar script próprio ou montar storyboard.',
         'The whole plan as JSON: raw trajectory, per-segment poses, duration, subject box, frame mode and the '
         'diagnostics. Use it to check what the node understood, to feed your own script or to build a storyboard.'),
        ('Texto de diagnóstico para ligar num PreviewText. Diz a versão, o modo de frame, a contagem de frames, como '
         'ligar o resto do workflow, se a loop closure ficou ligada e por quê, e os avisos sobre a trajetória.',
         'Diagnostic text to wire into a PreviewText. It reports the version, the frame mode, the frame count, how '
         'to wire the rest of the workflow, whether loop closure ended up on and why, and trajectory warnings.'),
        ('A mesma trajetória escrita no formato escolhido em minimax_format. É o prompt para o caminho nativo do H3. '
         'Alternativa ao compiled_prompt, não um complemento dele.',
         'The same trajectory written in the format chosen by minimax_format. This is the prompt for the native H3 '
         'path. An alternative to compiled_prompt, not a companion to it.'),
        ('Contagem de frames com que o plano foi cronometrado. Ligue na contagem de frames da geração: se a geração '
         'rodar com outro valor, os tempos escritos no prompt descrevem uma cena que não existe.',
         'The frame count the plan was timed against. Wire it into the frame count of your generation: if the '
         'generation runs at another value, the times written in the prompt describe a scene that does not exist.'),
        ('Taxa de quadros de saída, 24. Ligue no fps do node de vídeo. Sai como FLOAT porque é o tipo que o '
         'CreateVideo do ComfyUI aceita.',
         'Output frame rate, 24. Wire it into the fps of your video node. It is a FLOAT because that is the type '
         "ComfyUI's CreateVideo accepts.")])
    @classmethod
    def INPUT_TYPES(cls):
        data=super().INPUT_TYPES()
        data['optional'].update(frame_mode=(MODES,{'default':'Freeze Frame'}),source_fps=('FLOAT',{'default':24.,'min':1.,'max':240.}),ui_language=(['Português','English','中文'],{'default':'Português'}),loop_closure=(['auto','off'],{'default':'auto'}))
        for group in data.values():
            for key,value in group.items():
                group[key]=(value[0],dict(value[1] if len(value)>1 else {},tooltip=help_text(key)))
        return data
    def run(self,camera_trajectory,profile,interpolation,instruction,subject_framing=None,minimax_format=None,reference_image=None,elevation_range=None,orbit_direction=None,subject_box=None,runtime_task=None,prompt_detail=None,frame_mode='Freeze Frame',source_fps=24.,freeze_index=0,ui_language='Português',loop_closure='auto'):
        loop_closure=base._choice(loop_closure,['auto','off'],'auto')
        frame_mode=base._choice(frame_mode,MODES,'Freeze Frame')
        if frame_mode!='Freeze Frame' and runtime_task and runtime_task!='scene coverage | camera path':
            raise ValueError('PT: Action/Motion Frame exige runtime_task camera path. EN: Action/Motion Frame requires camera path runtime_task.')
        if frame_mode=='Action Frame' and (reference_image is None or not instruction.strip()):
            raise ValueError('PT: Action Frame exige uma imagem e a ação em instruction. EN: Action Frame requires an image and an action in instruction.')
        first,frames,count=prepare_frames(reference_image,frame_mode,source_fps,freeze_index)
        result=list(base.compile_camera(camera_trajectory,profile,interpolation,instruction,subject_framing,minimax_format,first,elevation_range,orbit_direction,subject_box,runtime_task,prompt_detail,allow_closure=frame_mode=='Freeze Frame' and loop_closure=='auto'))
        plan=json.loads(result[2])
        plan['frame_mode']=frame_mode
        plan['loop_closure_request']=loop_closure
        plan['loop_closure_enabled']=bool(result[1].get('coverage_loop_closure'))
        plan['user_instruction']=instruction or ''
        plan['source']={'input_frames':count,'source_fps':source_fps,'reference_frames':int(frames.shape[0]) if frames is not None else 0,'freeze_index':freeze_index if frame_mode!='Motion Frame' else None}
        if frame_mode!='Freeze Frame':
            plan=motion_plan(plan)
            result[0]=motion_text(plan,True)
            result[4]=json.dumps(motion_payload(plan),ensure_ascii=False,indent=2) if minimax_format in ('compact JSON','compact JSON (no boxes)') else motion_text(plan,minimax_format=='coordinate + H3 sections')
            # Prevent a frozen scene-coverage encoder from silently taking over a motion request.
            result[1]={'coverage_loop_closure':False,'bruxosdovfx_requires_ref2va':frame_mode=='Motion Frame','bruxosdovfx_requires_native_video':True}
        en=ui_language=='English'
        source_count=int(frames.shape[0]) if frames is not None else 0
        closure=bool(result[1].get('coverage_loop_closure'))
        route=('Motion: feed your frame sequence and this minimax_prompt and length to bruxosdovfx H3 Motion Reference; use H3 Ref2VA. Do not use H3 Edit options.' if en else 'Motion: leve a sua sequência de frames junto com este minimax_prompt e length ao bruxosdovfx H3 Motion Reference; use H3 Ref2VA. Não use options do H3 Edit.') if frame_mode=='Motion Frame' else ('Freeze: feed the same image you connected here as the source image. Loop closure requires H3 Edit options and source wiring; native H3 needs separate end-frame wiring.' if en else 'Freeze: use a mesma imagem que você ligou aqui como imagem de origem. Loop closure exige options e imagem no H3 Edit; H3 nativo precisa de ligação separada do último frame.')
        if frame_mode=='Action Frame':
            route=('Action: connect the source image to your native image-to-video workflow and use minimax_prompt, length and fps. Do not connect H3 Edit options or reuse the initial image as the end frame.' if en else 'Action: conecte a imagem ao workflow nativo de imagem para vídeo e use minimax_prompt, length e fps. Não conecte options do H3 Edit nem repita a imagem inicial como frame final.')
        raw_path=plan['path'];net=abs(raw_path[-1]['azimuth']-raw_path[0]['azimuth'])
        reasons=[]
        if loop_closure=='off':reasons.append('disabled by user' if en else 'desativado pelo usuário')
        if frame_mode!='Freeze Frame':reasons.append('action continues' if en else 'a ação continua')
        if first is None:reasons.append('no reference image' if en else 'sem imagem de referência')
        if abs(net-360)>1e-6:reasons.append(f'orbit {net:g}°; requires 360°' if en else f'giro {net:g}°; exige 360°')
        for key,pt in [('elevation','elevação'),('distance','distância')]:
            if abs(raw_path[-1][key]-raw_path[0][key])>1e-6:reasons.append(f"{key if en else pt}: {raw_path[-1][key]:g} → {raw_path[0][key]:g}")
        if runtime_task and runtime_task!='scene coverage | camera path':reasons.append('still-image task' if en else 'tarefa de imagem')
        result[3]=f"bruxosdovfx v30 | {frame_mode} | {result[5]} frames / 24 fps\n"+route+'\nLoop closure '+('ON' if closure else 'OFF')+(': '+', '.join(reasons) if reasons else '')+f"\n{'Source / reference frames' if en else 'Frames da fonte / referência'}: {count} / {source_count}. "+('Reference is resampled to 24 fps and trimmed to 17k+5; up to 16 trailing frames may be omitted. Camera following remains prompt-based.' if en else 'Referência reamostrada para 24 fps e cortada para 17k+5; até 16 frames finais podem ser omitidos. A câmera continua guiada por prompt.')
        warnings=review_path(plan['path'],plan['duration_s'],base.ELEVATION_RANGES.get(elevation_range,30))
        plan['diagnostics']=warnings
        result[2]=json.dumps(plan,ensure_ascii=False,indent=2)
        result[3]+='\n'+diagnostic_text(warnings,en)
        if frame_mode=='Freeze Frame':
            result[3]+='\n'+('Frame batch resampling applies only to Motion Frame; Freeze uses just the selected frame.' if en else 'A reamostragem do lote só se aplica a Motion Frame; Freeze usa apenas o frame selecionado.')
        if frame_mode!='Freeze Frame':
            result[3]+='\n'+('Action and camera adherence require validation in generated video; the preview does not predict the result.' if en else 'Continuidade da ação e aderência da câmera precisam ser validadas no vídeo gerado; a prévia não prevê o resultado.')
        return tuple(result)

class MotionReference:
    CATEGORY='bruxosdovfx/Camera H3'
    FUNCTION='encode'
    RETURN_TYPES=('CONDITIONING','LATENT')
    RETURN_NAMES=('positive','latent')
    DESCRIPTION='PT: Codifica a sequência como <Video 1> no H3 nativo. Exige modelo Ref2VA; não congela frames de saída. EN: Encodes the sequence as <Video 1> in native H3. Requires Ref2VA; does not pin output frames.'
    @classmethod
    def INPUT_TYPES(cls):
        return {'required':{
          'clip':('CLIP',{'tooltip':'PT: Encoder Qwen H3. EN: H3 Qwen encoder.'}),
          'vae':('VAE',{'tooltip':'PT: VAE de vídeo H3. EN: H3 video VAE.'}),
          'reference_frames':('IMAGE',{'tooltip':'PT: Saída Motion Frame do editor. EN: Editor Motion Frame output.'}),
          'prompt':('STRING',{'multiline':True,'forceInput':True,'tooltip':'PT: Conecte minimax_prompt. EN: Connect minimax_prompt.'}),
          'width':('INT',{'default':960,'min':32,'step':32,'tooltip':'PT: Largura gerada. EN: Output width.'}),
          'height':('INT',{'default':544,'min':32,'step':32,'tooltip':'PT: Altura gerada. EN: Output height.'}),
          'length':('INT',{'default':124,'min':5,'step':17,'tooltip':'PT: Conecte length do editor. EN: Connect editor length.'})}}
    def encode(self,clip,vae,reference_frames,prompt,width,height,length):
        if int(reference_frames.shape[0])<5:
            raise ValueError('PT: Use Motion Frame com sequência. EN: Use Motion Frame with a sequence.')
        from comfy_extras.nodes_minimax_h3 import MiniMaxH3ReferenceToVideo
        result=MiniMaxH3ReferenceToVideo.execute(clip=clip,vae=vae,prompt=prompt,width=width,height=height,length=length,ref_videos={'ref_video_1':reference_frames})
        return tuple(result.result)

NODE_CLASS_MAPPINGS={'H3LocalCameraEditor':H3CameraEditor,'BruxosH3MotionReference':MotionReference}
NODE_DISPLAY_NAME_MAPPINGS={'H3LocalCameraEditor':'bruxosdovfx • Camera H3','BruxosH3MotionReference':'bruxosdovfx • H3 Motion Reference'}
