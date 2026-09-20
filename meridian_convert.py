"""Conversor Viggle Meridian (diffusers) -> ComfyUI / Meridian to ComfyUI converter.

PT: Converte o transformer, a LoRA DMD e os embeddings de texto congelados do
    huggingface.co/Viggle/Meridian para o formato que o ComfyUI carrega nativamente.
EN: Converts the transformer, the DMD LoRA and the frozen text embeddings of
    huggingface.co/Viggle/Meridian into the layout ComfyUI loads natively.

O que muda entre os dois formatos (o mesmo mapeamento do script oficial
diffusers/scripts/convert_minimax_h3_to_diffusers.py, ao contrário):

  diffusers                                    ComfyUI (nomes do checkpoint original)
  transformer_blocks.N.attn.to_q/to_k/to_v  -> blocks.N.attn.qkv_proj      (fundidos, [q;k;v])
  transformer_blocks.N.attn.to_out.0        -> blocks.N.attn.out_proj
  transformer_blocks.N.attn.norm_q/norm_k   -> blocks.N.attn.q_norm/k_norm
  transformer_blocks.N.ff.net.0.proj        -> blocks.N.mlp.fc1            (metades trocadas)
  transformer_blocks.N.ff.net.2             -> blocks.N.mlp.fc2
  token_refiner.refiner_blocks.N            -> token_refiner.blocks.N
  proj_in / audio_proj_in / context_embedder-> video_patch_proj / audio_patch_proj / condition_proj
  time_embedder.linear_1/linear_2           -> time_embedder.proj_in/proj_out
  norm_out.norm / norm_out.linear           -> final_layer.norm / final_layer.adaln_proj.linear
  proj_out / audio_proj_out                 -> final_layer.video_out / final_layer.audio_out
  (ausente)                                 -> rope.inv_freq               (recalculado; o ComfyUI detecta o H3 por ela)

A troca das metades do fc1 existe porque o SwiGLU do diffusers lê [valor; porta] e o
ComfyUI calcula fc2(silu(porta) * valor) a partir de [porta; valor]. Numa LoRA a troca vale
só para lora_B: é uma permutação das linhas de saída.

Os tensores são copiados byte a byte (bf16, fp16, fp32 e fp8 passam sem conversão) e lidos por
memmap, então nada disso precisa de Torch nem de memória para o modelo inteiro. Só a conversão
dos embeddings de texto (.pt) precisa de Torch, porque é um pickle do PyTorch.

Uso:
  python meridian_convert.py lora        <Meridian>/lora/pytorch_lora_weights.safetensors  saida.safetensors [--pruned]
  python meridian_convert.py transformer <Meridian>/transformer                            saida.safetensors
  python meridian_convert.py text        <Meridian>/assets/fixed_embed_124.pt              saida.safetensors
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import struct

import numpy as np

DTYPE_SIZE = {'F64': 8, 'F32': 4, 'F16': 2, 'BF16': 2, 'F8_E4M3': 1, 'F8_E5M2': 1,
              'I64': 8, 'I32': 4, 'I16': 2, 'I8': 1, 'U8': 1, 'BOOL': 1,
              'U64': 8, 'U32': 4, 'U16': 2}
ROPE_FREQ_DIM, ROPE_THETA = 16, 10000.0
LORA_SUFFIXES = (('.lora_A.weight', 'A'), ('.lora_B.weight', 'B'),
                 ('.lora_A.default.weight', 'A'), ('.lora_B.default.weight', 'B'),
                 ('.lora_down.weight', 'A'), ('.lora_up.weight', 'B'), ('.alpha', 'alpha'))
LORA_PREFIXES = ('transformer.', 'transformer_ref.', 'base_model.model.', 'diffusion_model.', 'lora_unet_')
# Prefixos do diffusers -> nomes do checkpoint original. Os mais longos primeiro.
STANDALONE = (('audio_proj_in.', 'audio_patch_proj.'),
              ('audio_proj_out.', 'final_layer.audio_out.'),
              ('proj_in.', 'video_patch_proj.'),
              ('proj_out.', 'final_layer.video_out.'),
              ('context_embedder.', 'condition_proj.'),
              ('time_embedder.linear_1.', 'time_embedder.proj_in.'),
              ('time_embedder.linear_2.', 'time_embedder.proj_out.'),
              ('norm_out.norm.', 'final_layer.norm.'),
              ('norm_out.linear.', 'final_layer.adaln_proj.linear.'),
              ('token_refiner.final_norm.', 'token_refiner.final_norm.'))


# =============================================================================
# safetensors em bytes
# =============================================================================

class SafeSet:
    """Um .safetensors ou uma pasta de shards com índice; devolve bytes crus por memmap."""

    def __init__(self, path):
        self.metadata = {}
        self.files = {}
        self.info = {}
        path = os.path.abspath(path)
        shards = []
        if os.path.isdir(path):
            index = [p for p in os.listdir(path) if p.endswith('.safetensors.index.json')]
            if index:
                with open(os.path.join(path, index[0]), encoding='utf-8') as f:
                    shards = sorted(set(json.load(f)['weight_map'].values()))
                shards = [os.path.join(path, s) for s in shards]
            else:
                shards = sorted(os.path.join(path, p) for p in os.listdir(path) if p.endswith('.safetensors'))
            if not shards:
                raise FileNotFoundError(f'Nenhum .safetensors em {path} / no .safetensors in {path}')
        else:
            shards = [path]
        for shard in shards:
            with open(shard, 'rb') as f:
                length = struct.unpack('<Q', f.read(8))[0]
                header = json.loads(f.read(length))
            start = 8 + length
            meta = header.pop('__metadata__', None) or {}
            self.metadata.update(meta)
            for name, info in header.items():
                self.info[name] = info
                self.files[name] = (shard, start)

    def keys(self):
        return list(self.info)

    def dtype(self, name):
        return self.info[name]['dtype']

    def shape(self, name):
        return tuple(self.info[name]['shape'])

    def raw(self, name):
        """uint8 [linhas, resto*elemento] — as operações são recortes e concatenações de linhas."""
        info = self.info[name]
        shard, start = self.files[name]
        begin, end = info['data_offsets']
        flat = np.memmap(shard, dtype=np.uint8, mode='r', offset=start + begin, shape=(end - begin,))
        shape = tuple(info['shape'])
        rows = shape[0] if shape else 1
        return flat.reshape(rows, -1) if rows else flat.reshape(0, 0)


def write_safetensors(path, items, metadata=None, progress=None):
    """items: [(nome, dtype, shape, produtor)] — o produtor devolve uint8 do tamanho exato."""
    header, offset = {}, 0
    for name, dtype, shape, _ in items:
        size = DTYPE_SIZE[dtype] * int(np.prod(shape)) if shape else DTYPE_SIZE[dtype]
        header[name] = {'dtype': dtype, 'shape': list(shape), 'data_offsets': [offset, offset + size]}
        offset += size
    if metadata:
        header['__metadata__'] = {str(k): str(v) for k, v in metadata.items()}
    blob = json.dumps(header, separators=(',', ':')).encode('utf-8')
    blob += b' ' * ((8 - len(blob) % 8) % 8)
    tmp = path + '.part'
    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    with open(tmp, 'wb') as f:
        f.write(struct.pack('<Q', len(blob)))
        f.write(blob)
        for i, (name, dtype, shape, produce) in enumerate(items):
            data = np.ascontiguousarray(produce()).view(np.uint8).reshape(-1)
            expected = header[name]['data_offsets'][1] - header[name]['data_offsets'][0]
            if data.size != expected:
                raise ValueError(f'{name}: {data.size} bytes, esperado {expected} / expected {expected}')
            data.tofile(f)
            if progress:
                progress(i + 1, len(items), name)
    os.replace(tmp, path)
    return offset


def decode_float(raw, dtype):
    """bytes -> float32 (bf16 decodificado na mão; float32 representa bf16 exatamente)."""
    if dtype == 'F32':
        return raw.reshape(-1).view('<f4')
    if dtype == 'F16':
        return raw.reshape(-1).view('<f2').astype(np.float32)
    if dtype == 'BF16':
        bits = raw.reshape(-1).view('<u2').astype(np.uint32)
        return (bits << 16).view(np.float32) if bits.size else np.zeros(0, np.float32)
    if dtype == 'F64':
        return raw.reshape(-1).view('<f8').astype(np.float32)
    raise ValueError(f'dtype {dtype} não é float / is not float')


FP8_MAX = 448.0          # maior finito do e4m3fn (0x7E); 0x7F é NaN
FP8_MIN_NORMAL = 2.0 ** -6
ADALN_RANK, ADALN_GRID = 8, 1024


def _round_half_even(x):
    floor = np.floor(x)
    frac = x - floor
    out = np.where(frac > 0.5, floor + 1, np.where(frac < 0.5, floor, floor + (floor % 2)))
    return out


def encode_fp8_e4m3fn(values):
    """float32 -> fp8 e4m3fn, arredondando para o par mais próximo, por manipulação de bits.

    Normais: o expoente do float32 (viés 127) vira o do fp8 (viés 7) subtraindo 0x3C0 depois de
    arredondar a mantissa para 3 bits; o carry do arredondamento sobe para o expoente sozinho.
    Abaixo de 2^-6 o valor é subnormal (passo 2^-9) e vai pelo caminho aritmético.
    """
    x = np.ascontiguousarray(values, dtype=np.float32)
    bits = x.view(np.uint32)
    sign = ((bits >> 24) & 0x80).astype(np.uint8)
    mag = bits & 0x7FFFFFFF
    lsb = (mag >> 20) & 1
    code = ((mag + 0x7FFFF + lsb) >> 20).astype(np.int64) - 0x3C0
    subnormal = mag < 0x3C800000  # 2^-6
    if subnormal.any():
        magnitude = np.abs(x[subnormal]).astype(np.float64)
        code[subnormal] = _round_half_even(magnitude * 512.0).astype(np.int64)
    np.clip(code, 0, 0x7E, out=code)
    return (sign | code.astype(np.uint8)).astype(np.uint8)


def decode_fp8_e4m3fn(raw):
    code = np.asarray(raw, dtype=np.uint8).reshape(-1)
    sign = np.where(code & 0x80, -1.0, 1.0)
    exponent = ((code >> 3) & 0x0F).astype(np.int32)
    mantissa = (code & 0x07).astype(np.float32)
    normal = exponent > 0
    value = np.where(normal, np.ldexp(1.0 + mantissa / 8.0, exponent - 7), np.ldexp(mantissa / 8.0, -6))
    return (sign * value).astype(np.float32)


def time_embedding_curve(proj_in_w, proj_in_b, proj_out_w, proj_out_b, grid=ADALN_GRID):
    """silu(time_embedder(t)) para t = i/(grid-1) — exatamente o que as camadas AdaLN consomem."""
    silu = lambda v: v / (1.0 + np.exp(-v))
    freq_dim = proj_in_w.shape[1]
    half = freq_dim // 2
    t = (np.arange(grid, dtype=np.float32) / (grid - 1))[:, None]
    freqs = np.exp(-math.log(10000.0) * np.arange(half, dtype=np.float32) / half)[None]
    emb = np.concatenate([np.cos(t * freqs), np.sin(t * freqs)], axis=-1).astype(np.float32)
    hidden = silu(emb @ proj_in_w.T + proj_in_b)
    return silu(hidden @ proj_out_w.T + proj_out_b).astype(np.float32)


def adaln_basis(curve, rank=ADALN_RANK):
    """Base ortonormal da curva do tempo: E ~= tabela @ base.T. Devolve (base [2688, k], tabela [grid, k], erro)."""
    _, _, vh = np.linalg.svd(curve, full_matrices=False)
    base = np.ascontiguousarray(vh[:rank].T.astype(np.float32))
    table = (curve @ base).astype(np.float32)
    error = float(np.linalg.norm(curve - table @ base.T) / max(np.linalg.norm(curve), 1e-9))
    return base, table, error


def encode_bf16(values):
    """float32 -> bf16 com arredondamento para o par mais próximo (igual ao PyTorch)."""
    bits = np.ascontiguousarray(values, dtype=np.float32).view(np.uint32)
    rounded = (bits + 0x7FFF + ((bits >> 16) & 1)) >> 16
    nan = np.isnan(values)
    out = rounded.astype(np.uint16)
    out[nan] = (bits[nan] >> 16).astype(np.uint16) | 0x0040
    return out


# =============================================================================
# nomes
# =============================================================================

def _block_tail(tail):
    tail = tail.replace('attn.norm_q.', 'attn.q_norm.').replace('attn.norm_k.', 'attn.k_norm.')
    tail = tail.replace('attn.to_out.0.', 'attn.out_proj.')
    tail = tail.replace('ff.net.0.proj.', 'mlp.fc1.').replace('ff.net.2.', 'mlp.fc2.')
    return tail


def comfy_key(key):
    """Chave diffusers -> chave ComfyUI, ou None se não for um módulo conhecido do H3."""
    for source, target in STANDALONE:
        if key.startswith(source):
            return target + key[len(source):]
    match = re.match(r'transformer_blocks\.(\d+)\.(.+)$', key)
    if match:
        return f'blocks.{match.group(1)}.{_block_tail(match.group(2))}'
    match = re.match(r'token_refiner\.refiner_blocks\.(\d+)\.(.+)$', key)
    if match:
        return f'token_refiner.blocks.{match.group(1)}.{_block_tail(match.group(2))}'
    return None


def rope_inv_freq(freq_dim=ROPE_FREQ_DIM, theta=ROPE_THETA):
    return (1.0 / (theta ** (np.arange(0, 2 * freq_dim, 2, dtype=np.float32) / (2 * freq_dim)))).astype(np.float32)


# =============================================================================
# transformer
# =============================================================================

def convert_transformer(source, destination, report=print, progress=None, fp8=False,
                        prune_adaln=False, adaln_rank=ADALN_RANK, adaln_grid=ADALN_GRID):
    src = SafeSet(source)
    config = {}
    config_path = os.path.join(source, 'config.json') if os.path.isdir(source) else ''
    if config_path and os.path.isfile(config_path):
        with open(config_path, encoding='utf-8') as f:
            config = json.load(f)
    freq_dim = int(config.get('rope_freq_dim', ROPE_FREQ_DIM))
    theta = float(config.get('rope_theta', ROPE_THETA))

    basis = table = None
    if prune_adaln:
        needed = ['time_embedder.linear_1.weight', 'time_embedder.linear_1.bias',
                  'time_embedder.linear_2.weight', 'time_embedder.linear_2.bias']
        if any(k not in src.info for k in needed):
            raise ValueError('PT: sem time_embedder no checkpoint; ele já está podado? '
                             'EN: no time_embedder in the checkpoint; is it already pruned?')
        weights = [decode_float(src.raw(k), src.dtype(k)).reshape(src.shape(k)) for k in needed]
        curve = time_embedding_curve(weights[0], weights[1], weights[2], weights[3], adaln_grid)
        basis, table, error = adaln_basis(curve, adaln_rank)
        report(f'adaln: curva do tempo aproximada por {adaln_rank} componentes, erro relativo {100 * error:.3f}% '
               f'/ time curve approximated with {adaln_rank} components, relative error {100 * error:.3f}%')

    scales = {}

    def _chunks(key):
        shape = src.shape(key)
        raw = src.raw(key)
        columns = max(1, int(np.prod(shape[1:])))
        step = max(1, 2 ** 22 // columns)
        for start in range(0, shape[0], step):
            stop = min(shape[0], start + step)
            yield stop - start, columns, decode_float(raw[start:stop], src.dtype(key))

    def scale_for(target, keys):
        """Escala por camada: o maior valor absoluto vira 448, o topo do fp8 e4m3fn."""
        if target not in scales:
            peak = 0.0
            for key in keys:
                for _, _, block in _chunks(key):
                    peak = max(peak, float(np.abs(block).max(initial=0.0)))
            scales[target] = max(peak / FP8_MAX, 1e-12) if peak > 0 else 1.0
        return scales[target]

    def quantize(key, target, keys):
        """Peso grande -> fp8 e4m3fn escalado, em blocos de linhas."""
        scale = np.float32(scale_for(target, keys))
        shape = src.shape(key)
        out = np.empty((shape[0], max(1, int(np.prod(shape[1:])))), dtype=np.uint8)
        row = 0
        for rows, columns, block in _chunks(key):
            out[row:row + rows] = encode_fp8_e4m3fn(block / scale).reshape(rows, columns)
            row += rows
        return out

    def project_adaln(key):
        """W [saída, 2688] -> W @ base [saída, k], em blocos."""
        shape = src.shape(key)
        raw = src.raw(key)
        out = np.empty((shape[0], basis.shape[1]), dtype=np.float32)
        step = max(1, 2 ** 22 // max(1, shape[1]))
        for start in range(0, shape[0], step):
            stop = min(shape[0], start + step)
            block = decode_float(raw[start:stop], src.dtype(key)).reshape(stop - start, shape[1])
            out[start:stop] = block @ basis
        return out

    def as_f32(key):
        return decode_float(src.raw(key), src.dtype(key)).astype(np.float32)

    big = lambda key: len(src.shape(key)) == 2 and int(np.prod(src.shape(key))) >= 2 ** 20

    items, handled, fused, swapped, unknown = [], set(), 0, 0, []
    quantized = projected = 0
    for key in sorted(src.keys()):
        if key in handled:
            continue
        if key.endswith('.attn.to_q.weight'):
            base = key[: -len('to_q.weight')]
            parts = [base + name + '.weight' for name in ('to_q', 'to_k', 'to_v')]
            missing = [p for p in parts if p not in src.info]
            if missing:
                raise ValueError(f'QKV incompleto / incomplete QKV: falta {missing[0]}')
            dtypes = {src.dtype(p) for p in parts}
            if len(dtypes) != 1:
                raise ValueError(f'{base}: q/k/v com dtypes diferentes / different dtypes {dtypes}')
            cols = {src.shape(p)[1:] for p in parts}
            if len(cols) != 1:
                raise ValueError(f'{base}: q/k/v com formas incompatíveis / incompatible shapes')
            rows = sum(src.shape(p)[0] for p in parts)
            target = comfy_key(base + 'qkv_proj.weight')
            if fp8:
                items.append((target, 'F8_E4M3', (rows,) + src.shape(key)[1:],
                              lambda parts=parts, target=target: np.concatenate([quantize(p, target, parts) for p in parts], axis=0)))
                items.append((target[: -len('.weight')] + '.scale_weight', 'F32', (),
                              lambda parts=parts, target=target: np.float32([scale_for(target, parts)])))
                quantized += 1
            else:
                items.append((target, src.dtype(key), (rows,) + src.shape(key)[1:],
                              lambda parts=parts: np.concatenate([src.raw(p) for p in parts], axis=0)))
            handled.update(parts)
            fused += 1
            continue
        if key.endswith(('.attn.to_k.weight', '.attn.to_v.weight')):
            continue
        target = comfy_key(key)
        if target is None:
            unknown.append(key)
            continue
        if prune_adaln and key.startswith('time_embedder.'):
            continue  # a curva substitui o time embedder
        if prune_adaln and target.endswith('adaln_proj.linear.weight'):
            items.append((target, 'F32', (src.shape(key)[0], basis.shape[1]), lambda key=key: project_adaln(key)))
            projected += 1
            continue
        if prune_adaln and target.endswith('adaln_proj.linear.bias'):
            items.append((target, 'F32', src.shape(key), lambda key=key: as_f32(key)))
            continue
        if key.endswith('ff.net.0.proj.weight'):
            rows = src.shape(key)[0]
            if rows % 2:
                raise ValueError(f'{key}: {rows} linhas, o SwiGLU precisa de um número par / needs an even row count')
            if fp8:
                def swap_quantized(key=key, rows=rows, target=target):
                    codes = quantize(key, target, [key])
                    return np.concatenate([codes[rows // 2:], codes[: rows // 2]], axis=0)
                items.append((target, 'F8_E4M3', src.shape(key), swap_quantized))
                items.append((target[: -len('.weight')] + '.scale_weight', 'F32', (),
                              lambda key=key, target=target: np.float32([scale_for(target, [key])])))
                quantized += 1
            else:
                items.append((target, src.dtype(key), src.shape(key),
                              lambda key=key, rows=rows: np.concatenate([src.raw(key)[rows // 2:], src.raw(key)[: rows // 2]], axis=0)))
            swapped += 1
            continue
        if fp8 and big(key) and key.endswith('.weight'):
            items.append((target, 'F8_E4M3', src.shape(key), lambda key=key, target=target: quantize(key, target, [key])))
            items.append((target[: -len('.weight')] + '.scale_weight', 'F32', (),
                          lambda key=key, target=target: np.float32([scale_for(target, [key])])))
            quantized += 1
            continue
        items.append((target, src.dtype(key), src.shape(key), lambda key=key: src.raw(key)))
    if unknown:
        raise ValueError(f'{len(unknown)} chaves fora do H3 / keys outside H3, e.g. {unknown[:3]}')
    items.append(('rope.inv_freq', 'F32', (freq_dim,), lambda: rope_inv_freq(freq_dim, theta)))
    if prune_adaln:
        items.append(('adaln_t_table', 'F32', table.shape, lambda: np.ascontiguousarray(table)))
    if fp8:
        # marcador do formato fp8 escalado; o ComfyUI o converte em metadados comfy_quant por camada
        items.append(('scaled_fp8', 'F8_E4M3', (1,), lambda: np.zeros(1, dtype=np.uint8)))
    items.sort(key=lambda item: item[0])

    required = ('video_patch_proj.weight', 'audio_patch_proj.weight', 'condition_proj.weight',
                'blocks.0.attn.qkv_proj.weight', 'blocks.0.attn.q_norm.weight', 'blocks.0.mlp.fc1.weight',
                'final_layer.video_out.weight', 'final_layer.audio_out.weight', 'rope.inv_freq')
    names = {item[0] for item in items}
    missing = [r for r in required if r not in names]
    if missing:
        raise ValueError(f'Faltam chaves que o ComfyUI usa para detectar o H3 / missing keys ComfyUI detects H3 by: {missing}')
    blocks = len({int(re.match(r'blocks\.(\d+)\.', n).group(1)) for n in names if n.startswith('blocks.')})
    size = write_safetensors(destination, items, {
        'format': 'pt', 'converted_by': 'bruxosdovfx meridian_convert',
        'meridian_adaln_pruned': str(bool(prune_adaln)), 'meridian_fp8': str(bool(fp8))}, progress)
    report(f'transformer: {len(items)} tensores, {blocks} blocos, {fused} QKV fundidos, {swapped} fc1 trocados, '
           f'{quantized} pesos em fp8, {projected} AdaLN projetados, {size / 2**30:.1f} GiB -> {destination}')
    if prune_adaln:
        basis_path = destination + '.adaln_basis.safetensors'
        write_safetensors(basis_path, [
            ('adaln_basis', 'F32', basis.shape, lambda: np.ascontiguousarray(basis)),
            ('adaln_t_table', 'F32', table.shape, lambda: np.ascontiguousarray(table))],
            {'format': 'pt', 'converted_by': 'bruxosdovfx meridian_convert'})
        report(f'base da curva salva em {basis_path} — use-a em --adaln-basis ao converter a LoRA / '
               f'curve basis saved to {basis_path} — pass it to --adaln-basis when converting the LoRA')
    return destination


# =============================================================================
# LoRA
# =============================================================================

def _split_lora_key(key):
    for prefix in LORA_PREFIXES:
        if key.startswith(prefix):
            key = key[len(prefix):]
            break
    for suffix, kind in sorted(LORA_SUFFIXES, key=lambda s: -len(s[0])):
        if key.endswith(suffix):
            return key[: -len(suffix)], kind
    return None, None


def _peft_config(metadata):
    raw = metadata.get('lora_adapter_metadata')
    if not raw:
        return None
    try:
        config = json.loads(raw)
    except ValueError:
        return None
    if isinstance(config.get('transformer'), dict):
        config = config['transformer']
    return {k.split('.', 1)[1] if k.startswith(('transformer.', 'transformer_ref.')) else k: v
            for k, v in config.items()}


def _pattern_value(patterns, module, default):
    """Casamento do PEFT: o padrão casa o fim do caminho do módulo."""
    if isinstance(patterns, dict):
        for pattern, value in patterns.items():
            if re.match(rf'(.*\.)?({pattern})$', module):
                return value
    return default


def module_scale(module, rank, metadata, config, alpha_tensor):
    """Escala efetiva da LoRA (alpha/rank do PEFT), e de onde ela veio."""
    if alpha_tensor is not None:
        return float(alpha_tensor) / rank, 'tensor .alpha'
    if 'alpha' in metadata:
        try:
            return float(metadata['alpha']) / rank, '__metadata__ alpha'
        except ValueError:
            pass
    if config:
        r = float(_pattern_value(config.get('rank_pattern'), module, config.get('r', rank)) or rank)
        alpha = float(_pattern_value(config.get('alpha_pattern'), module, config.get('lora_alpha', r)) or r)
        scale = alpha / math.sqrt(r) if config.get('use_rslora') else alpha / r
        return scale, 'lora_adapter_metadata'
    return 1.0, 'sem alpha (escala 1) / no alpha (scale 1)'


def _scaled_rows(src, key, scale):
    """Linhas de lora_B multiplicadas pela escala, em F32 (só quando a escala não é 1)."""
    return (decode_float(src.raw(key), src.dtype(key)).astype(np.float32) * np.float32(scale))


def convert_lora(source, destination, pruned=False, report=print, progress=None, adaln_basis_path=None):
    src = SafeSet(source)
    basis = None
    if adaln_basis_path:
        basis = decode_float(SafeSet(adaln_basis_path).raw('adaln_basis'), 'F32').reshape(
            SafeSet(adaln_basis_path).shape('adaln_basis'))
    config = _peft_config(src.metadata)
    modules = {}
    for key in src.keys():
        module, kind = _split_lora_key(key)
        if module is None:
            report(f'ignorando chave desconhecida / skipping unknown key: {key}')
            continue
        modules.setdefault(module, {})[kind] = key
    if not modules:
        raise ValueError('Nenhum adaptador LoRA encontrado / no LoRA adapters found')

    groups, singles = {}, {}
    for module, keys in modules.items():
        match = re.match(r'(.*\.attn\.)to_([qkv])$', module)
        if match:
            groups.setdefault(match.group(1), {})[match.group(2)] = (module, keys)
        else:
            singles[module] = keys

    items, dropped, projected, scales = [], [], [], set()

    def add(name, dtype, shape, produce):
        items.append((name, dtype, shape, produce))

    def target_of(module):
        return comfy_key(module + '.weight')[: -len('.weight')]

    def skip(target):
        if not pruned:
            return False
        if target.startswith('time_embedder.'):
            return True
        return target.endswith('adaln_proj.linear') and basis is None

    for module in sorted(singles):
        keys = singles[module]
        if 'A' not in keys or 'B' not in keys:
            report(f'par incompleto, ignorado / incomplete pair, skipped: {module}')
            continue
        target = target_of(module)
        if target is None:
            raise ValueError(f'Módulo fora do H3 / module outside H3: {module}')
        if skip(target):
            dropped.append(target)
            continue
        rank = src.shape(keys['A'])[0]
        alpha = None
        if 'alpha' in keys:
            alpha = float(decode_float(src.raw(keys['alpha']), src.dtype(keys['alpha']))[0])
        scale, origin = module_scale(module, rank, src.metadata, config, alpha)
        scales.add(origin)
        project = pruned and basis is not None and target.endswith('adaln_proj.linear')
        if project and src.shape(keys['A'])[1] != basis.shape[0]:
            raise ValueError(f'{module}: lora_A tem {src.shape(keys["A"])[1]} entradas e a base tem {basis.shape[0]} / '
                             f'lora_A has {src.shape(keys["A"])[1]} inputs, the basis has {basis.shape[0]}')
        swap = target.endswith('mlp.fc1')
        rows = src.shape(keys['B'])[0]
        if swap and rows % 2:
            raise ValueError(f'{module}: lora_B com {rows} linhas ímpares / odd row count')

        def produce_b(key=keys['B'], swap=swap, scale=scale, rows=rows):
            if scale == 1.0:
                raw = src.raw(key)
                return np.concatenate([raw[rows // 2:], raw[: rows // 2]], axis=0) if swap else raw
            values = _scaled_rows(src, key, scale).reshape(rows, -1)
            return np.concatenate([values[rows // 2:], values[: rows // 2]], axis=0) if swap else values

        b_dtype = src.dtype(keys['B']) if scale == 1.0 else 'F32'
        if project:
            # A vira A @ base: o delta passa a atuar sobre as 8 coordenadas da curva, igual aos pesos podados.
            add(f'diffusion_model.{target}.lora_A.weight', 'F32', (src.shape(keys['A'])[0], basis.shape[1]),
                lambda key=keys['A']: (decode_float(src.raw(key), src.dtype(key)).reshape(src.shape(key)) @ basis).astype(np.float32))
            projected.append(target)
        else:
            add(f'diffusion_model.{target}.lora_A.weight', src.dtype(keys['A']), src.shape(keys['A']),
                lambda key=keys['A']: src.raw(key))
        add(f'diffusion_model.{target}.lora_B.weight', b_dtype, src.shape(keys['B']), produce_b)

    for base in sorted(groups):
        present = groups[base]
        target = target_of(base + 'qkv_proj')
        order = [present.get(name) for name in ('q', 'k', 'v')]
        ranks, out_rows, dtypes = [], [], set()
        for entry in order:
            if entry is None:
                ranks.append(0)
                continue
            module, keys = entry
            if 'A' not in keys or 'B' not in keys:
                raise ValueError(f'{module}: par lora_A/lora_B incompleto / incomplete pair')
            ranks.append(src.shape(keys['A'])[0])
            out_rows.append(src.shape(keys['B'])[0])
            dtypes.add(src.dtype(keys['B']))
        if not out_rows:
            continue
        if len(set(out_rows)) != 1:
            raise ValueError(f'{base}: q/k/v com saídas diferentes / different output sizes {out_rows}')
        rows_each = out_rows[0]
        in_dim = src.shape(order[[i for i, e in enumerate(order) if e][0]][1]['A'])[1]
        scale_list, needs_float = [], False
        for entry, rank in zip(order, ranks):
            if entry is None:
                scale_list.append(1.0)
                continue
            module, keys = entry
            alpha = float(decode_float(src.raw(keys['alpha']), src.dtype(keys['alpha']))[0]) if 'alpha' in keys else None
            scale, origin = module_scale(module, rank, src.metadata, config, alpha)
            scales.add(origin)
            scale_list.append(scale)
            needs_float = needs_float or scale != 1.0
        total_rank = sum(ranks)
        a_dtype = src.dtype(order[[i for i, e in enumerate(order) if e][0]][1]['A'])

        def produce_a(order=order, a_dtype=a_dtype, in_dim=in_dim):
            parts = [src.raw(entry[1]['A']) for entry in order if entry is not None]
            return np.concatenate(parts, axis=0)

        def produce_b(order=order, ranks=ranks, rows_each=rows_each, total_rank=total_rank,
                      scale_list=scale_list, needs_float=needs_float, dtype=None):
            element = 4 if needs_float else DTYPE_SIZE[list(dtypes)[0]]
            out = np.zeros((3 * rows_each, total_rank * element), dtype=np.uint8)
            column = 0
            for index, (entry, rank) in enumerate(zip(order, ranks)):
                if entry is not None:
                    if needs_float:
                        block = (_scaled_rows(src, entry[1]['B'], scale_list[index])
                                 .reshape(rows_each, rank).view(np.uint8).reshape(rows_each, rank * element))
                    else:
                        block = src.raw(entry[1]['B'])
                    out[index * rows_each:(index + 1) * rows_each, column * element:(column + rank) * element] = block
                column += rank
            return out

        if skip(target):
            dropped.append(target)
            continue
        add(f'diffusion_model.{target}.lora_A.weight', a_dtype, (total_rank, in_dim), produce_a)
        add(f'diffusion_model.{target}.lora_B.weight',
            'F32' if needs_float else list(dtypes)[0], (3 * rows_each, total_rank), produce_b)

    items.sort(key=lambda item: item[0])
    size = write_safetensors(destination, items, {
        'format': 'pt', 'converted_by': 'bruxosdovfx meridian_convert',
        'meridian_pruned_base': str(bool(pruned))}, progress)
    report(f'lora: {len(items) // 2} adaptadores ({len(groups)} QKV fundidos), escala de {", ".join(sorted(scales))}, '
           f'{size / 2**20:.0f} MiB -> {destination}')
    if projected:
        report(f'pruned: {len(projected)} adaptadores AdaLN projetados na base da curva / '
               f'{len(projected)} AdaLN adapters projected onto the curve basis')
    if dropped:
        report(f'pruned: {len(dropped)} adaptadores AdaLN/time_embedder removidos (não existem na base podada) / '
               f'{len(dropped)} AdaLN/time_embedder adapters removed (absent from a pruned base)')
    return destination


# =============================================================================
# embeddings de texto congelados (.pt -> safetensors)
# =============================================================================

def convert_text_embeds(source, destination, report=print):
    try:
        import torch
    except ImportError:
        raise RuntimeError('PT: os embeddings são um pickle do PyTorch; rode isto com o Python do ComfyUI. '
                           'EN: the embeddings are a PyTorch pickle; run this with ComfyUI\'s Python.')
    from safetensors.torch import save_file

    blob = torch.load(source, map_location='cpu', weights_only=True)
    embeds = tags = None
    if torch.is_tensor(blob):
        embeds = blob
    elif isinstance(blob, dict):
        for name in ('prompt_embeds', 'encoder_hidden_states', 'text_embeds', 'embeds'):
            if name in blob:
                embeds = blob[name]
                break
        for name in ('text_token_tags', 'token_tags', 'tags'):
            if name in blob:
                tags = blob[name]
                break
        if embeds is None:
            floats = [v for v in blob.values() if torch.is_tensor(v) and v.is_floating_point() and v.dim() >= 2]
            embeds = floats[0] if len(floats) == 1 else None
        if tags is None:
            ints = [v for v in blob.values() if torch.is_tensor(v) and not v.is_floating_point() and v.dim() == 1]
            tags = ints[0] if len(ints) == 1 else None
    elif isinstance(blob, (tuple, list)) and len(blob) == 2:
        embeds, tags = blob
    if embeds is None:
        keys = list(blob) if isinstance(blob, dict) else type(blob).__name__
        raise ValueError(f'PT: não achei prompt_embeds em {source} (conteúdo: {keys}). '
                         f'EN: no prompt_embeds found in {source} (content: {keys}).')
    if embeds.dim() == 2:
        embeds = embeds[None]
    out = {'prompt_embeds': embeds.contiguous()}
    if tags is not None:
        out['text_token_tags'] = tags.reshape(-1).to(torch.int64).contiguous()
    else:
        report('AVISO: sem text_token_tags; o Meridian Reference vai precisar deles. / '
               'WARNING: no text_token_tags; Meridian Reference needs them.')
    save_file(out, destination, metadata={'format': 'pt', 'converted_by': 'bruxosdovfx meridian_convert'})
    report(f'text: prompt_embeds {tuple(embeds.shape)}'
           + (f', text_token_tags {tuple(out["text_token_tags"].shape)}' if tags is not None else '')
           + f' -> {destination}')
    return destination


# =============================================================================
# Espectro do delta: uma LoRA de posto r consegue carregar este fine-tune?
# =============================================================================

DEFAULT_PROBE = ('blocks.0.attn.qkv_proj.weight', 'blocks.0.mlp.fc1.weight', 'blocks.0.attn.out_proj.weight',
                 'blocks.25.attn.qkv_proj.weight', 'blocks.25.mlp.fc1.weight',
                 'blocks.49.attn.qkv_proj.weight', 'blocks.49.mlp.fc1.weight')
DEFAULT_RANKS = (32, 64, 128, 256)


def top_singular_values(matrix, rank, oversample=16, iterations=2, seed=0):
    """Maiores valores singulares por SVD aleatorizada: o SVD completo dessas matrizes levaria horas."""
    rows, cols = matrix.shape
    size = min(rank + oversample, cols, rows)
    sketch = np.random.default_rng(seed).standard_normal((cols, size)).astype(np.float32)
    basis = matrix @ sketch
    for _ in range(iterations):          # iterações de potência: separam melhor os valores próximos
        basis = matrix @ (matrix.T @ basis)
    basis, _ = np.linalg.qr(basis)
    return np.linalg.svd(basis.T @ matrix, compute_uv=False)


def spectrum(base, tuned, keys=None, ranks=DEFAULT_RANKS, report=print):
    """Quanta energia do delta (tuned - base) cabe nos primeiros valores singulares.

    Energia alta em posto baixo => uma LoRA desse posto reproduz quase todo o fine-tune.
    Energia baixa => o fine-tune é de posto alto e a LoRA vai perder comportamento.
    """
    a, b = SafeSet(base), SafeSet(tuned)
    probe = [k for k in (keys or DEFAULT_PROBE) if k in a.info and k in b.info and a.shape(k) == b.shape(k)]
    missing = [k for k in (keys or DEFAULT_PROBE) if k not in probe]
    if missing:
        report(f'ignoradas {len(missing)} chaves ausentes ou de forma diferente / skipped: {missing[:3]}')
    if not probe:
        raise ValueError('PT: nenhuma camada em comum. Os dois arquivos estão no formato do ComfyUI? '
                         'EN: no layer in common. Are both files in ComfyUI layout?')
    totals = {r: [] for r in ranks}
    report(f"{'camada':34} {'|Δ|/|W|':>8} " + ' '.join(f'r={r:<6}' for r in ranks))
    for key in probe:
        base_w = decode_float(a.raw(key), a.dtype(key)).reshape(a.shape(key)).astype(np.float32)
        delta = decode_float(b.raw(key), b.dtype(key)).reshape(b.shape(key)).astype(np.float32) - base_w
        energy = float((delta.astype(np.float64) ** 2).sum())
        relative = math.sqrt(energy) / max(math.sqrt(float((base_w.astype(np.float64) ** 2).sum())), 1e-12)
        values = top_singular_values(delta, max(ranks))
        line = f'{key[:34]:34} {relative:8.3f} '
        for r in ranks:
            captured = float((values[:r].astype(np.float64) ** 2).sum()) / max(energy, 1e-12)
            totals[r].append(captured)
            line += f'{100 * captured:6.1f}% '
        report(line)
    report('')
    for r in ranks:
        mean = 100 * sum(totals[r]) / len(totals[r])
        verdict = ('uma LoRA desse posto carrega o fine-tune / a LoRA of this rank carries the finetune' if mean >= 90 else
                   'perde comportamento; considere posto maior / loses behaviour; consider a higher rank' if mean >= 70 else
                   'posto alto demais para LoRA / the finetune is too high-rank for a LoRA')
        report(f'posto {r:4}: {mean:5.1f}% da energia — {verdict}')
    return {r: sum(v) / len(v) for r, v in totals.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('mode', choices=('lora', 'transformer', 'text', 'spectrum'))
    parser.add_argument('source')
    parser.add_argument('destination', help='no modo spectrum: o segundo modelo (o fine-tune) / in spectrum mode: the second model (the finetune)')
    parser.add_argument('--pruned', action='store_true',
                        help='LoRA para uma base podada (curve-form)')
    parser.add_argument('--adaln-basis', default=None,
                        help='LoRA + --pruned: arquivo .adaln_basis.safetensors gerado ao podar o transformer; '
                             'projeta os adaptadores AdaLN em vez de descartá-los')
    parser.add_argument('--fp8', action='store_true', help='transformer: grava os pesos grandes em fp8 e4m3fn (metade do tamanho)')
    parser.add_argument('--prune-adaln', action='store_true',
                        help='transformer: substitui o time embedder e as camadas AdaLN pela curva do tempo (~13 dos 33 bilhões de parâmetros)')
    parser.add_argument('--adaln-rank', type=int, default=ADALN_RANK)
    parser.add_argument('--adaln-grid', type=int, default=ADALN_GRID)
    args = parser.parse_args(argv)
    if args.mode == 'spectrum':
        spectrum(args.source, args.destination)
        return
    if args.mode == 'lora':
        convert_lora(args.source, args.destination, pruned=args.pruned, adaln_basis_path=args.adaln_basis)
    elif args.mode == 'transformer':
        convert_transformer(args.source, args.destination, fp8=args.fp8, prune_adaln=args.prune_adaln,
                            adaln_rank=args.adaln_rank, adaln_grid=args.adaln_grid)
    else:
        convert_text_embeds(args.source, args.destination)


if __name__ == '__main__':
    main()
