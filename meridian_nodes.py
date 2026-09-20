# -*- coding: utf-8 -*-
"""Nodes do Viggle Meridian para o ComfyUI / Viggle Meridian nodes for ComfyUI.

PT: O Meridian é um fine-tune completo do transformer ref2va do MiniMax-H3 (Viggle AI). Ele recebe
    duas referências de vídeo — <Video 1> o clipe original, <Video 2> o render da nuvem de pontos
    da câmera nova, com buracos cinza 128 — e gera o clipe dessa câmera. O texto é um embedding
    congelado, então não existe text encoder nem prompt: a câmera vem inteira do <Video 2>, que é a
    saída depth_warp do Camera H3 com warp_format = Meridian (H3).
EN: Meridian is a full finetune of MiniMax-H3's ref2va transformer (Viggle AI). It takes two video
    references — <Video 1> the source clip, <Video 2> the point-cloud render of the new camera with
    grey 128 holes — and generates that camera's clip. Text is a frozen embedding, so there is no
    text encoder and no prompt: the camera comes entirely from <Video 2>, which is Camera H3's
    depth_warp output with warp_format = Meridian (H3).

Os pesos, a LoRA DMD e os embeddings não são redistribuídos aqui; converta os seus com
meridian_convert.py. Os pesos do Meridian seguem a MiniMax H3 Community License.
"""
from __future__ import annotations

import math
import os

from . import depth_warp as dw

try:
    import torch
    import folder_paths
    import comfy.model_management
    import comfy.nested_tensor
    from comfy_extras import nodes_minimax_h3 as core_h3
except Exception:  # permite importar o módulo fora do ComfyUI (testes)
    torch = folder_paths = comfy = core_h3 = None

TEXT_COND_FOLDER = 'text_cond'


def _register_folder():
    if folder_paths is None:
        return
    try:
        paths, extensions = folder_paths.folder_names_and_paths.get(TEXT_COND_FOLDER, ([], set()))
        directory = os.path.join(folder_paths.models_dir, TEXT_COND_FOLDER)
        if directory not in paths:
            folder_paths.folder_names_and_paths[TEXT_COND_FOLDER] = (list(paths) + [directory],
                                                                     set(extensions) | {'.safetensors'})
        os.makedirs(directory, exist_ok=True)
    except Exception:
        pass


_register_folder()


def _text_cond_files():
    try:
        return folder_paths.get_filename_list(TEXT_COND_FOLDER) or ['(vazio / empty)']
    except Exception:
        return ['(vazio / empty)']


class MeridianTextCond:
    """Carrega o embedding de texto congelado do Meridian (um por duração)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'text_cond': (_text_cond_files(), {'tooltip':
            'PT: Arquivo em models/text_cond convertido de assets/fixed_embed_<frames>.pt com meridian_convert.py. '
            'O Meridian tem um por duração: use o que bate com length. '
            'EN: File in models/text_cond converted from assets/fixed_embed_<frames>.pt with meridian_convert.py. '
            'Meridian ships one per length: use the one matching length.'})}}

    RETURN_TYPES = ('MERIDIAN_TEXT',)
    RETURN_NAMES = ('text_cond',)
    FUNCTION = 'load'
    CATEGORY = 'Bruxos do VFX/Meridian'
    DESCRIPTION = 'PT: Embedding de texto congelado; substitui o text encoder do H3. EN: Frozen text embedding; replaces the H3 text encoder.'

    def load(self, text_cond):
        from safetensors.torch import load_file
        path = folder_paths.get_full_path_or_raise(TEXT_COND_FOLDER, text_cond)
        blob = load_file(path)
        if 'prompt_embeds' not in blob:
            raise ValueError('PT: arquivo sem prompt_embeds; converta com meridian_convert.py text. '
                             'EN: file has no prompt_embeds; convert it with meridian_convert.py text.')
        embeds = blob['prompt_embeds']
        if embeds.dim() == 2:
            embeds = embeds[None]
        tags = blob.get('text_token_tags')
        if tags is None:
            raise ValueError('PT: arquivo sem text_token_tags; o H3 precisa deles para montar a sequência. '
                             'EN: file has no text_token_tags; H3 needs them to build the packed sequence.')
        return ({'prompt_embeds': embeds, 'text_token_tags': tags.reshape(-1), 'name': text_cond},)


class MeridianReference:
    """Conditioning do Meridian: embedding congelado + <Video 1> (fonte) e <Video 2> (render)."""

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'source_video': ('IMAGE', {'tooltip': 'PT: <Video 1>, o clipe original a 24 fps, os mesmos frames que você ligou em reference_image no Camera H3. EN: <Video 1>, the source clip at 24 fps, the same frames wired into the Camera H3 reference_image.'}),
            'warp_video': ('IMAGE', {'tooltip': 'PT: <Video 2>, a saída depth_warp do Camera H3 com warp_format = Meridian (H3). Cinza 128 = buraco. EN: <Video 2>, Camera H3 depth_warp with warp_format = Meridian (H3). Grey 128 = hole.'}),
            'vae': ('VAE', {'tooltip': 'PT: VAE de vídeo do MiniMax-H3. EN: MiniMax-H3 video VAE.'}),
            'length': ('INT', {'default': 124, 'min': 73, 'max': 243, 'step': 1, 'tooltip':
                'PT: Frames gerados. O Meridian só tem embedding para 73, 90, 107, 124, 141, 158, 175 e 243, e precisa ser o mesmo número de frames do warp. '
                'EN: Generated frames. Meridian only ships embeddings for 73, 90, 107, 124, 141, 158, 175 and 243, and it must match the warp frame count.'}),
        }, 'optional': {
            'text_cond': ('MERIDIAN_TEXT', {'tooltip': 'PT: Embedding congelado, do node Meridian Text Cond. É o que o Meridian viu no treino. EN: Frozen embedding from the Meridian Text Cond node. It is what Meridian saw in training.'}),
            'clip': ('CLIP', {'tooltip': 'PT: Text encoder do H3 (qwen3vl). Ligue junto com prompt_text para escrever o seu próprio texto: aí as referências são APRESENTADAS ao text encoder e as etiquetas <Picture 1>, <Video 1>, <Video 2> passam a significar algo. Sem clip, as referências extras chegam só ao transformer, como latentes. EN: H3 text encoder (qwen3vl). Connect it with prompt_text to write your own text: the references are then PRESENTED to the text encoder and the <Picture 1>, <Video 1>, <Video 2> tags mean something. Without clip, extra references reach only the transformer, as latents.'}),
            'prompt_text': ('STRING', {'default': '', 'multiline': True, 'tooltip': 'PT: Só com clip ligado. Comece pelo texto da tarefa em assets/prompt.txt do Meridian — é ele que ensina o modelo a ler o <Video 2> como render com buracos cinza — e acrescente as suas frases, citando <Picture 1>, <Picture 2>... EN: Only with clip connected. Start from the task text in Meridian assets/prompt.txt — it teaches the model to read <Video 2> as a grey-hole render — and add your own sentences, naming <Picture 1>, <Picture 2>...'}),
            'ref_image_1': ('IMAGE', {'tooltip': 'PT: <Picture 1>. Sujeito, ambiente, o que você quiser citar no texto. EN: <Picture 1>. Subject, environment, whatever you name in the text.'}),
            'ref_image_2': ('IMAGE', {'tooltip': 'PT: <Picture 2>. EN: <Picture 2>.'}),
            'ref_image_3': ('IMAGE', {'tooltip': 'PT: <Picture 3>. EN: <Picture 3>.'}),
            'ref_image_4': ('IMAGE', {'tooltip': 'PT: <Picture 4>. EN: <Picture 4>.'}),
            'ref_image_5': ('IMAGE', {'tooltip': 'PT: <Picture 5>. EN: <Picture 5>.'}),
            'ref_image_6': ('IMAGE', {'tooltip': 'PT: <Picture 6>. EN: <Picture 6>.'}),
            'ref_image_7': ('IMAGE', {'tooltip': 'PT: <Picture 7>. EN: <Picture 7>.'}),
            'ref_image_8': ('IMAGE', {'tooltip': 'PT: <Picture 8>. EN: <Picture 8>.'}),
            'ref_image_9': ('IMAGE', {'tooltip': 'PT: <Picture 9>. EN: <Picture 9>.'}),
            'ref_video_3': ('IMAGE', {'tooltip': 'PT: <Video 3>, o terceiro e último slot de vídeo do H3 (1 e 2 são a fonte e o warp). Frames a 24 fps. EN: <Video 3>, the third and last H3 video slot (1 and 2 are the source and the warp). Frames at 24 fps.'}),
            'prompt': ('CONDITIONING', {'tooltip': 'PT: EXPERIMENTAL. Conditioning de um CLIP Text Encode com o text encoder do H3, no lugar do embedding congelado. O Meridian foi treinado com um texto fixo, então ele pode simplesmente ignorar o que você escrever — vale testar na sua cena. EN: EXPERIMENTAL. Conditioning from a CLIP Text Encode with the H3 text encoder, replacing the frozen embedding. Meridian was trained with one fixed prompt, so it may simply ignore your text — worth testing on your own scene.'}),
            'extra_reference': ('IMAGE', {'tooltip': 'PT: EXPERIMENTAL. Uma imagem a mais como referência (sujeito ou ambiente), no formato de referência de imagem do H3. O Meridian nunca viu uma terceira referência no treino. EN: EXPERIMENTAL. One extra reference image (subject or environment), in the H3 image-reference format. Meridian never saw a third reference in training.'}),
            'width': ('INT', {'default': 0, 'min': 0, 'max': 4096, 'step': 32, 'tooltip': 'PT: 0 = canvas classe 768 do aspecto da fonte (1344x768 em 16:9). EN: 0 = the 768-class canvas of the source aspect (1344x768 at 16:9).'}),
            'height': ('INT', {'default': 0, 'min': 0, 'max': 4096, 'step': 32}),
        }}

    RETURN_TYPES = ('CONDITIONING', 'LATENT', 'STRING')
    RETURN_NAMES = ('positive', 'latent', 'relatorio')
    FUNCTION = 'build'
    CATEGORY = 'Bruxos do VFX/Meridian'
    DESCRIPTION = ('PT: Monta o ref2va do Meridian: texto congelado, <Video 1> = fonte e <Video 2> = warp, ambos na classe 480, '
                   'alvo na classe 768. Use com o transformer do Meridian convertido (não com o H3 base) e a LoRA DMD dele. '
                   'EN: Builds Meridian ref2va: frozen text, <Video 1> = source and <Video 2> = warp, both at the 480 class, '
                   'target at the 768 class. Use the converted Meridian transformer (not stock H3) with its DMD LoRA.')

    def build(self, source_video, warp_video, vae, length, text_cond=None, prompt=None, clip=None, prompt_text='',
              ref_video_3=None, extra_reference=None, width=0, height=0, **refs):
        chosen = [name for name, value in (('text_cond', text_cond), ('prompt', prompt), ('clip', clip)) if value is not None]
        if not chosen:
            raise ValueError('PT: Ligue text_cond (embedding congelado), prompt (conditioning pronto) ou clip + prompt_text. '
                             'EN: Connect text_cond (frozen embedding), prompt (ready conditioning) or clip + prompt_text.')
        if len(chosen) > 1:
            raise ValueError(f'PT: Escolha UMA fonte de texto; estão ligadas: {", ".join(chosen)}. '
                             f'EN: Pick ONE text source; connected: {", ".join(chosen)}.')
        images = [refs[key] for key in sorted(refs) if key.startswith('ref_image_') and refs[key] is not None]
        if extra_reference is not None:
            images.append(extra_reference)   # entrada antiga, mantida para workflows salvos

        frames, source_h, source_w = int(source_video.shape[0]), int(source_video.shape[1]), int(source_video.shape[2])
        target, cond_canvas = dw.meridian_bucket(source_w, source_h)
        tw, th = (int(width) or target[0]), (int(height) or target[1])
        cw, ch = cond_canvas
        if int(length) not in dw.MERIDIAN_LENGTHS:
            raise ValueError(f'PT: length {length} não tem embedding no Meridian; use {", ".join(map(str, dw.MERIDIAN_LENGTHS))}. '
                             f'EN: length {length} has no Meridian embedding; use {", ".join(map(str, dw.MERIDIAN_LENGTHS))}.')
        if int(warp_video.shape[0]) != int(length):
            raise ValueError(f'PT: o warp tem {int(warp_video.shape[0])} frames e length é {length}; ajuste warp_length no Camera H3. '
                             f'EN: the warp has {int(warp_video.shape[0])} frames and length is {length}; set warp_length in Camera H3.')
        frame_count, latent_t, audio_t = core_h3.temporal_shape(int(length))
        if frame_count != int(length):
            raise ValueError(f'PT: {length} não cai na grade 17k+5 do H3. EN: {length} is off the H3 17k+5 grid.')

        # Ordem de apresentação do H3: imagens primeiro, depois vídeos. A numeração é por tipo,
        # então o clipe continua sendo <Video 1> e o warp <Video 2> mesmo com imagens ligadas.
        blocks, items, report = [], [], []
        # O H3 empacota o latente em blocos 2x2, entao o lado da imagem tem que ser multiplo de 32:
        # com multiplo de 16 o latente sai com dimensao impar e o patchify_video quebra.
        multiple = getattr(core_h3, 'CANVAS_MULTIPLE', 32)
        for index, image in enumerate(images, 1):
            h, w = int(image.shape[1]), int(image.shape[2])
            scale = min(1.0, math.sqrt((tw * th) / max(1, w * h)))
            iw = max(multiple, round(w * scale / multiple) * multiple)
            ih = max(multiple, round(h * scale / multiple) * multiple)
            resized = core_h3._resize(image[:1], iw, ih, 'disabled')
            items.append({'type': 'image', 'data': resized})
            blocks.append({'kind': 'image', 'latent_h': ih // 16, 'latent_w': iw // 16, 'latent': vae.encode(resized)})
            report.append(f'<Picture {index}> {iw}x{ih}')

        videos = [('<Video 1> fonte/source', source_video), ('<Video 2> warp', warp_video)]
        if ref_video_3 is not None:
            videos.append(('<Video 3> extra', ref_video_3))
        for name, video in videos:
            block = video[:frame_count]
            if int(block.shape[0]) < frame_count:
                block = torch.cat([block] + [block[-1:]] * (frame_count - int(block.shape[0])))
                report.append(f'{name}: repetindo o último frame até {frame_count} / holding the last frame to {frame_count}')
            if (int(block.shape[1]), int(block.shape[2])) != (ch, cw):
                block = core_h3._resize(block, cw, ch, 'disabled')
            # O text encoder vê o vídeo a 2 fps, com marcas de tempo, como no node nativo do H3.
            sample = list(range(0, int(block.shape[0]), 12))
            items.append({'type': 'video', 'data': block[sample], 'timestamps': [i / 2.0 for i in range(len(sample))]})
            latent = vae.encode(block)
            blocks.append({'kind': 'video', 'latent_t': int(latent.shape[2]), 'latent_h': ch // 16, 'latent_w': cw // 16,
                           'ref_audio_t': 0, 'latent': latent, 'audio_latent': None})

        if clip is not None:
            # Caminho do H3 nativo: as referências são apresentadas ao text encoder, então as
            # etiquetas <Picture i> e <Video k> do seu texto apontam para algo de verdade.
            cond = clip.encode_from_tokens_scheduled(clip.tokenize(prompt_text, minimax_ref_items=items))
            cond = [[entry[0], dict(entry[1] if len(entry) > 1 else {}, minimax_refs=blocks)] for entry in cond]
            origem = f'prompt_text pelo text encoder, {len(items)} referência(s) apresentada(s)'
            report.append('Texto próprio com as referências apresentadas ao text encoder (experimental: o Meridian foi '
                          'treinado com texto fixo e duas referências) / Own text with the references presented to the '
                          'text encoder (experimental: Meridian was trained with fixed text and two references).')
        else:
            if prompt is not None:
                embeds, options = prompt[0][0], (prompt[0][1] if len(prompt[0]) > 1 else {})
                tags = options.get('minimax_token_tags')
                if tags is None:
                    raise ValueError('PT: esse conditioning não veio do text encoder do H3 (faltam os token tags). '
                                     'EN: this conditioning did not come from the H3 text encoder (no token tags).')
                origem = f'prompt {tuple(embeds.shape)}'
            else:
                embeds, tags = text_cond['prompt_embeds'], text_cond['text_token_tags']
                origem = f'texto congelado {tuple(embeds.shape)} ({text_cond.get("name", "?")})'
            if len(blocks) > 2:
                report.append('As referências extras chegam ao transformer, mas NÃO ao text encoder: sem clip ligado, '
                              'citar <Picture 1> no texto não aponta para nada / The extra references reach the '
                              'transformer but NOT the text encoder: without clip, naming <Picture 1> points at nothing.')
            cond = [[embeds, {'minimax_refs': blocks, 'minimax_token_tags': tags}]]

        device = comfy.model_management.intermediate_device()
        latent = {'samples': comfy.nested_tensor.NestedTensor((
            torch.zeros([1, 24, latent_t, th // 16, tw // 16], device=device),
            torch.zeros([1, 32, 2, audio_t], device=device)))}
        report.insert(0, f'Meridian: {frame_count} frames · vídeos {cw}x{ch} · alvo {tw}x{th} · {origem} · '
                         f'fonte com {frames} frames.')
        report.append('Sampler: Euler, CFG 1.0 (BasicGuider), ModelSamplingMiniMaxH3 3.0/3.0; o turbo do Meridian usa '
                      '4 pontos de sigma (3 passos): 1.0, 0.8571428571428571, 0.6, 0.0.')
        return cond, latent, '\n'.join(report)


NODE_CLASS_MAPPINGS = {
    'BruxosMeridianTextCond': MeridianTextCond,
    'BruxosMeridianReference': MeridianReference,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    'BruxosMeridianTextCond': 'bruxosdovfx • Meridian Text Cond',
    'BruxosMeridianReference': 'bruxosdovfx • Meridian Reference',
}
