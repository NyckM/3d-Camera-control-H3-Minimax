"""v31 meridian_convert: nomes, QKV fundido, troca do SwiGLU e escala da LoRA, tudo numérico.

python -B tests/test_v31_convert.py   (NumPy + safetensors; não precisa de Torch)
"""
import importlib, json, math, sys, tempfile, types, unittest
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
pkg = types.ModuleType('integration'); pkg.__path__ = [str(root)]; sys.modules['integration'] = pkg
mc = importlib.import_module('integration.meridian_convert')
rng = np.random.default_rng(3)

HID, HEADS, HEAD, FFN, RANK = 8, 2, 4, 12, 4
INNER = HEADS * HEAD


def f32(*shape):
    return (rng.standard_normal(shape) * 0.1).astype(np.float32)


def write(path, tensors, metadata=None):
    items = []
    for name, (array, dtype) in tensors.items():
        if dtype == 'BF16':
            items.append((name, 'BF16', array.shape, lambda a=array: mc.encode_bf16(a)))
        else:
            items.append((name, 'F32', array.shape, lambda a=array: np.ascontiguousarray(a, dtype=np.float32)))
    mc.write_safetensors(str(path), items, metadata)


def read(path):
    src = mc.SafeSet(str(path))
    return {k: mc.decode_float(src.raw(k), src.dtype(k)).reshape(src.shape(k)) for k in src.keys()}, src


class NamesAndTransformer(unittest.TestCase):
    def diffusers_model(self, dtype='BF16'):
        t = {}
        for key, shape in [('proj_in.weight', (HID, 16)), ('proj_in.bias', (HID,)),
                           ('audio_proj_in.weight', (HID, 4)), ('context_embedder.weight', (HID, 6)),
                           ('time_embedder.linear_1.weight', (HID, 4)), ('time_embedder.linear_1.bias', (HID,)),
                           ('time_embedder.linear_2.weight', (HID, HID)), ('time_embedder.linear_2.bias', (HID,)),
                           ('norm_out.norm.weight', (HID,)), ('norm_out.linear.weight', (2 * HID, HID)),
                           ('proj_out.weight', (16, HID)), ('audio_proj_out.weight', (4, HID)),
                           ('token_refiner.final_norm.weight', (HID,))]:
            t[key] = (f32(*shape), 'F32')
        for prefix in ('transformer_blocks.0', 'transformer_blocks.1', 'token_refiner.refiner_blocks.0'):
            for name, shape in [('norm1.weight', (HID,)), ('norm2.weight', (HID,)),
                                ('attn.to_q.weight', (INNER, HID)), ('attn.to_k.weight', (INNER, HID)),
                                ('attn.to_v.weight', (INNER, HID)), ('attn.to_out.0.weight', (HID, INNER)),
                                ('attn.norm_q.weight', (HEAD,)), ('attn.norm_k.weight', (HEAD,)),
                                ('ff.net.0.proj.weight', (2 * FFN, HID)), ('ff.net.2.weight', (HID, FFN))]:
                t[f'{prefix}.{name}'] = (f32(*shape), dtype)
            if 'refiner' not in prefix:
                t[f'{prefix}.adaln_proj.linear.weight'] = (f32(18 * HID, HID), dtype)
        return t

    def test_transformer_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / 'diffusers.safetensors', Path(tmp) / 'comfy.safetensors'
            tensors = self.diffusers_model()
            write(src, tensors)
            mc.convert_transformer(str(src), str(dst), report=lambda *a: None)
            out, handle = read(dst)
            # nomes que o ComfyUI usa para detectar o H3
            for key in ('video_patch_proj.weight', 'audio_patch_proj.weight', 'condition_proj.weight',
                        'time_embedder.proj_in.weight', 'time_embedder.proj_out.weight',
                        'final_layer.norm.weight', 'final_layer.adaln_proj.linear.weight',
                        'final_layer.video_out.weight', 'final_layer.audio_out.weight',
                        'blocks.0.attn.q_norm.weight', 'blocks.1.attn.out_proj.weight',
                        'token_refiner.blocks.0.mlp.fc2.weight', 'rope.inv_freq'):
                self.assertIn(key, out, key)
            self.assertNotIn('transformer_blocks.0.attn.to_q.weight', out)
            # QKV fundido na ordem q, k, v
            qkv = out['blocks.0.attn.qkv_proj.weight']
            self.assertEqual(qkv.shape, (3 * INNER, HID))
            for i, name in enumerate(('to_q', 'to_k', 'to_v')):
                self.assertTrue(np.allclose(qkv[i * INNER:(i + 1) * INNER],
                                            mc.decode_float(mc.encode_bf16(tensors[f'transformer_blocks.0.attn.{name}.weight'][0]).view(np.uint8), 'BF16').reshape(INNER, HID)))
            # fc1: [valor; porta] -> [porta; valor]
            src_ff = tensors['transformer_blocks.0.ff.net.0.proj.weight'][0]
            got = out['blocks.0.mlp.fc1.weight']
            expect = np.concatenate([src_ff[FFN:], src_ff[:FFN]])
            self.assertTrue(np.allclose(got, mc.decode_float(mc.encode_bf16(expect).view(np.uint8), 'BF16').reshape(2 * FFN, HID)))
            # dtypes preservados: as ilhas fp32 continuam fp32
            self.assertEqual(handle.dtype('video_patch_proj.weight'), 'F32')
            self.assertEqual(handle.dtype('blocks.0.mlp.fc1.weight'), 'BF16')
            self.assertTrue(np.allclose(out['rope.inv_freq'], 1.0 / (10000.0 ** (np.arange(0, 32, 2) / 32))))
            # e o arquivo abre na biblioteca oficial
            from safetensors import safe_open
            with safe_open(str(dst), framework='np') as f:
                self.assertIn('blocks.0.attn.qkv_proj.weight', f.keys())
                self.assertTrue(np.allclose(f.get_tensor('rope.inv_freq'), out['rope.inv_freq']))

    def test_unknown_key_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / 'a.safetensors', Path(tmp) / 'b.safetensors'
            tensors = self.diffusers_model()
            tensors['mystery.weight'] = (f32(4, 4), 'F32')
            write(src, tensors)
            with self.assertRaises(ValueError):
                mc.convert_transformer(str(src), str(dst), report=lambda *a: None)


class LoraNumerics(unittest.TestCase):
    def build(self, path, metadata=None, drop=(), ranks=(RANK, RANK, RANK), dtype='BF16'):
        """LoRA no formato que o diffusers salva, com prefixo `transformer.`."""
        tensors, truth = {}, {}
        for name, rank, out_dim in (('to_q', ranks[0], INNER), ('to_k', ranks[1], INNER), ('to_v', ranks[2], INNER)):
            if name in drop:
                continue
            A, B = f32(rank, HID), f32(out_dim, rank)
            tensors[f'transformer.transformer_blocks.0.attn.{name}.lora_A.weight'] = (A, dtype)
            tensors[f'transformer.transformer_blocks.0.attn.{name}.lora_B.weight'] = (B, dtype)
            truth[f'attn.{name}'] = (A, B)
        for module, (rank, out_dim, in_dim) in {
                'ff.net.0.proj': (RANK, 2 * FFN, HID), 'adaln_proj.linear': (2, 18 * HID, HID)}.items():
            A, B = f32(rank, in_dim), f32(out_dim, rank)
            tensors[f'transformer.transformer_blocks.0.{module}.lora_A.weight'] = (A, dtype)
            tensors[f'transformer.transformer_blocks.0.{module}.lora_B.weight'] = (B, dtype)
            truth[module] = (A, B)
        A, B = f32(RANK, 6), f32(HID, RANK)
        tensors['transformer.context_embedder.lora_A.weight'] = (A, dtype)
        tensors['transformer.context_embedder.lora_B.weight'] = (B, dtype)
        truth['context_embedder'] = (A, B)
        write(path, tensors, metadata)
        return truth

    def bf(self, a):
        return mc.decode_float(mc.encode_bf16(a).view(np.uint8), 'BF16').reshape(a.shape)

    def test_effective_update_is_preserved(self):
        meta = {'lora_adapter_metadata': json.dumps({'transformer.r': 4, 'transformer.lora_alpha': 8})}
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / 'lora.safetensors', Path(tmp) / 'comfy_lora.safetensors'
            truth = self.build(src, meta)
            mc.convert_lora(str(src), str(dst), report=lambda *a: None)
            out, _ = read(dst)
            scale = 8 / 4
            # QKV: bloco diagonal em B e A concatenado devem reproduzir cada projeção separada
            A = out['diffusion_model.blocks.0.attn.qkv_proj.lora_A.weight']
            B = out['diffusion_model.blocks.0.attn.qkv_proj.lora_B.weight']
            self.assertEqual(A.shape, (3 * RANK, HID))
            self.assertEqual(B.shape, (3 * INNER, 3 * RANK))
            delta = B @ A
            for i, name in enumerate(('to_q', 'to_k', 'to_v')):
                a, b = truth[f'attn.{name}']
                expect = scale * (self.bf(b) @ self.bf(a))
                self.assertTrue(np.allclose(delta[i * INNER:(i + 1) * INNER], expect, atol=1e-5), name)
            # fc1: a troca das metades aplicada ao delta efetivo
            a, b = truth['ff.net.0.proj']
            delta_ff = out['diffusion_model.blocks.0.mlp.fc1.lora_B.weight'] @ out['diffusion_model.blocks.0.mlp.fc1.lora_A.weight']
            expect = scale * (self.bf(b) @ self.bf(a))
            self.assertTrue(np.allclose(delta_ff, np.concatenate([expect[FFN:], expect[:FFN]]), atol=1e-5))
            # renomeado
            a, b = truth['context_embedder']
            delta_c = out['diffusion_model.condition_proj.lora_B.weight'] @ out['diffusion_model.condition_proj.lora_A.weight']
            self.assertTrue(np.allclose(delta_c, scale * (self.bf(b) @ self.bf(a)), atol=1e-5))

    def test_swiglu_forward_matches_after_swap(self):
        """O ponto da troca: fc2(silu(porta)*valor) no ComfyUI = valor*silu(porta) no diffusers."""
        x = f32(5, HID)
        W = f32(2 * FFN, HID)              # diffusers: [valor; porta]
        comfy_W = np.concatenate([W[FFN:], W[:FFN]])
        h = x @ W.T
        value, gate = h[:, :FFN], h[:, FFN:]
        diffusers_out = value * (gate / (1 + np.exp(-gate)))
        h2 = x @ comfy_W.T
        gate2, value2 = h2[:, :FFN], h2[:, FFN:]
        comfy_out = (gate2 / (1 + np.exp(-gate2))) * value2
        self.assertTrue(np.allclose(diffusers_out, comfy_out, atol=1e-6))

    def test_alpha_sources_and_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            # tensor .alpha por módulo vence tudo
            src, dst = Path(tmp) / 'a.safetensors', Path(tmp) / 'b.safetensors'
            truth = self.build(src, {'alpha': '16'})
            mc.convert_lora(str(src), str(dst), report=lambda *a: None)
            out, _ = read(dst)
            a, b = truth['context_embedder']
            delta = out['diffusion_model.condition_proj.lora_B.weight'] @ out['diffusion_model.condition_proj.lora_A.weight']
            self.assertTrue(np.allclose(delta, (16 / RANK) * (self.bf(b) @ self.bf(a)), atol=1e-5))
            # alpha_pattern e rslora
            src2, dst2 = Path(tmp) / 'c.safetensors', Path(tmp) / 'd.safetensors'
            meta = {'lora_adapter_metadata': json.dumps({'r': 4, 'lora_alpha': 4,
                                                         'alpha_pattern': {'context_embedder': 12}, 'use_rslora': True})}
            truth2 = self.build(src2, meta)
            mc.convert_lora(str(src2), str(dst2), report=lambda *a: None)
            out2, _ = read(dst2)
            a, b = truth2['context_embedder']
            delta2 = out2['diffusion_model.condition_proj.lora_B.weight'] @ out2['diffusion_model.condition_proj.lora_A.weight']
            self.assertTrue(np.allclose(delta2, (12 / math.sqrt(4)) * (self.bf(b) @ self.bf(a)), atol=1e-5))

    def test_scale_one_keeps_bytes_and_dtype(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / 'a.safetensors', Path(tmp) / 'b.safetensors'
            self.build(src)  # sem metadados: escala 1
            mc.convert_lora(str(src), str(dst), report=lambda *a: None)
            handle = mc.SafeSet(str(dst))
            self.assertEqual(handle.dtype('diffusion_model.condition_proj.lora_B.weight'), 'BF16')
            self.assertEqual(handle.dtype('diffusion_model.blocks.0.attn.qkv_proj.lora_B.weight'), 'BF16')

    def test_missing_projection_becomes_zero_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / 'a.safetensors', Path(tmp) / 'b.safetensors'
            truth = self.build(src, drop=('to_k',), ranks=(RANK, 0, 2))
            mc.convert_lora(str(src), str(dst), report=lambda *a: None)
            out, _ = read(dst)
            B = out['diffusion_model.blocks.0.attn.qkv_proj.lora_B.weight']
            A = out['diffusion_model.blocks.0.attn.qkv_proj.lora_A.weight']
            self.assertEqual(A.shape, (RANK + 2, HID))
            delta = B @ A
            self.assertTrue(np.allclose(delta[INNER:2 * INNER], 0))
            a, b = truth['attn.to_v']
            self.assertTrue(np.allclose(delta[2 * INNER:], self.bf(b) @ self.bf(a), atol=1e-5))

    def test_pruned_drops_adaln(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / 'a.safetensors', Path(tmp) / 'b.safetensors'
            self.build(src)
            mc.convert_lora(str(src), str(dst), pruned=True, report=lambda *a: None)
            keys = mc.SafeSet(str(dst)).keys()
            self.assertFalse(any('adaln' in k for k in keys))
            self.assertTrue(any('qkv_proj' in k for k in keys))


class Fp8Codec(unittest.TestCase):
    def representable(self):
        codes = np.arange(256, dtype=np.uint8)
        values = mc.decode_fp8_e4m3fn(codes)
        finite = codes[(codes & 0x7F) != 0x7F]
        return np.unique(mc.decode_fp8_e4m3fn(finite))

    def test_known_values(self):
        self.assertTrue(np.allclose(mc.decode_fp8_e4m3fn(np.array([0x38, 0x40, 0x3C, 0xB8, 0x7E, 0x00], np.uint8)),
                                    [1.0, 2.0, 1.5, -1.0, 448.0, 0.0]))
        self.assertTrue(np.array_equal(mc.encode_fp8_e4m3fn(np.float32([1.0, 2.0, 1.5, -1.0, 448.0, 0.0])),
                                       [0x38, 0x40, 0x3C, 0xB8, 0x7E, 0x00]))

    def test_rounds_to_nearest_representable(self):
        grid = self.representable()
        values = np.concatenate([rng.standard_normal(4000).astype(np.float32) * 3,
                                 np.float32([1e-9, 2 ** -9, 2 ** -7, 0.1, 300.0, 1000.0, -1000.0])])
        got = mc.decode_fp8_e4m3fn(mc.encode_fp8_e4m3fn(values))
        clipped = np.clip(values, -mc.FP8_MAX, mc.FP8_MAX)
        nearest = grid[np.abs(clipped[:, None] - grid[None]).argmin(1)]
        self.assertTrue(np.array_equal(got, nearest.astype(np.float32)))

    def test_never_emits_nan_code(self):
        codes = mc.encode_fp8_e4m3fn(np.float32([np.nan, np.inf, -np.inf, 1e9, -1e9, 447.9, 448.1]))
        self.assertFalse(np.any((codes & 0x7F) == 0x7F))


class AdalnCurve(unittest.TestCase):
    """A poda do AdaLN: a curva do tempo cabe numa base pequena, e a camada projetada dá o mesmo resultado."""

    def curve_weights(self):
        freq, hidden, out = 32, 48, 64
        return (f32(hidden, freq) * 3, f32(hidden) * 0.1, f32(out, hidden) * 3, f32(out) * 0.1)

    def test_curve_matches_comfy_formula_and_low_rank(self):
        w1, b1, w2, b2 = self.curve_weights()
        curve = mc.time_embedding_curve(w1, b1, w2, b2, grid=256)
        # mesma fórmula do TimeEmbedder do ComfyUI, conferida em t = 0.37
        silu = lambda v: v / (1 + np.exp(-v))
        half = w1.shape[1] // 2
        t = np.float32(94 / 255)
        freqs = np.exp(-math.log(10000.0) * np.arange(half, dtype=np.float32) / half)
        emb = np.concatenate([np.cos(t * freqs), np.sin(t * freqs)])
        expect = silu(silu(emb @ w1.T + b1) @ w2.T + b2)
        self.assertTrue(np.allclose(curve[94], expect, atol=1e-5))
        base, table, error = mc.adaln_basis(curve, rank=8)
        self.assertEqual(base.shape, (64, 8))
        self.assertEqual(table.shape, (256, 8))
        self.assertLess(error, 0.02)
        self.assertTrue(np.allclose(base.T @ base, np.eye(8), atol=1e-4))

    def test_projected_layer_reproduces_full_layer(self):
        w1, b1, w2, b2 = self.curve_weights()
        grid = 512
        curve = mc.time_embedding_curve(w1, b1, w2, b2, grid)
        base, table, _ = mc.adaln_basis(curve, rank=8)
        W = f32(96, 64)          # camada AdaLN completa: [saída, time_embed_dim]
        Wp = W @ base            # o que o conversor grava
        for t in (0.0, 0.13, 0.5, 0.77, 1.0):
            full = W @ mc.time_embedding_curve(w1, b1, w2, b2, grid)[min(grid - 1, int(round(t * (grid - 1))))]
            position = t * (grid - 1)
            low = min(int(np.floor(position)), grid - 2)
            coefficients = table[low] + (position - low) * (table[low + 1] - table[low])
            pruned = Wp @ coefficients
            self.assertLess(np.linalg.norm(full - pruned) / np.linalg.norm(full), 0.03, t)


class TransformerCompression(unittest.TestCase):
    def test_fp8_and_pruned_output(self):
        case = NamesAndTransformer()
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'diffusers.safetensors'
            tensors = case.diffusers_model()
            # camadas grandes o bastante para o corte de 1M elementos do fp8
            tensors['transformer_blocks.0.ff.net.0.proj.weight'] = (f32(2 * 1024, 640), 'BF16')
            tensors['transformer_blocks.0.ff.net.2.weight'] = (f32(640, 1024), 'BF16')
            write(src, tensors)
            quant = Path(tmp) / 'fp8.safetensors'
            mc.convert_transformer(str(src), str(quant), report=lambda *a: None, fp8=True)
            handle = mc.SafeSet(str(quant))
            self.assertEqual(handle.dtype('blocks.0.mlp.fc1.weight'), 'F8_E4M3')
            self.assertNotEqual(handle.dtype('blocks.0.attn.q_norm.weight'), 'F8_E4M3')  # normas ficam intactas
            # marcador do formato escalado + escala por camada (o ComfyUI lê isso como comfy_quant)
            self.assertEqual(handle.dtype('scaled_fp8'), 'F8_E4M3')
            scale = mc.decode_float(handle.raw('blocks.0.mlp.fc1.scale_weight'), 'F32')[0]
            source_ff = tensors['transformer_blocks.0.ff.net.0.proj.weight'][0]
            expect = np.concatenate([source_ff[1024:], source_ff[:1024]])
            stored = mc.decode_float(mc.encode_bf16(expect).view(np.uint8), 'BF16').reshape(2048, 640)  # o arquivo de origem é bf16
            self.assertAlmostEqual(scale, np.abs(stored).max() / mc.FP8_MAX, places=6)
            got = mc.decode_fp8_e4m3fn(handle.raw('blocks.0.mlp.fc1.weight')).reshape(2048, 640) * scale
            # com escala, o erro relativo do e4m3 fica na casa de 1/16
            self.assertLess(np.abs(got - stored).max(), np.abs(stored).max() * 0.05)
            self.assertLess(np.abs(got - stored).mean(), np.abs(stored).mean() * 0.05)
            codes = mc.decode_fp8_e4m3fn(handle.raw('blocks.0.mlp.fc1.weight')).reshape(2048, 640)
            self.assertTrue(np.array_equal(codes, mc.decode_fp8_e4m3fn(mc.encode_fp8_e4m3fn(stored / scale)).reshape(2048, 640)))

            pruned = Path(tmp) / 'pruned.safetensors'
            mc.convert_transformer(str(src), str(pruned), report=lambda *a: None, prune_adaln=True, adaln_grid=256)
            out = mc.SafeSet(str(pruned))
            self.assertIn('adaln_t_table', out.keys())
            self.assertFalse(any(k.startswith('time_embedder.') for k in out.keys()))
            self.assertEqual(out.shape('blocks.0.adaln_proj.linear.weight'), (18 * HID, 8))
            self.assertEqual(out.dtype('blocks.0.adaln_proj.linear.weight'), 'F32')
            self.assertEqual(out.shape('adaln_t_table'), (256, 8))
            basis = mc.SafeSet(str(pruned) + '.adaln_basis.safetensors')
            self.assertEqual(basis.shape('adaln_basis'), (HID, 8))

    def test_lora_adaln_projection(self):
        lora = LoraNumerics()
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'model.safetensors'
            write(src, NamesAndTransformer().diffusers_model())
            model = Path(tmp) / 'pruned.safetensors'
            mc.convert_transformer(str(src), str(model), report=lambda *a: None, prune_adaln=True, adaln_grid=256)
            lora_src, lora_dst = Path(tmp) / 'lora.safetensors', Path(tmp) / 'lora_comfy.safetensors'
            truth = lora.build(lora_src)
            mc.convert_lora(str(lora_src), str(lora_dst), pruned=True, report=lambda *a: None,
                            adaln_basis_path=str(model) + '.adaln_basis.safetensors')
            out, handle = read(lora_dst)
            key = 'diffusion_model.blocks.0.adaln_proj.linear.lora_A.weight'
            self.assertIn(key, out)                      # projetado, não descartado
            self.assertEqual(out[key].shape, (2, 8))
            basis = mc.decode_float(mc.SafeSet(str(model) + '.adaln_basis.safetensors').raw('adaln_basis'), 'F32').reshape(HID, 8)
            a, _ = truth['adaln_proj.linear']
            self.assertTrue(np.allclose(out[key], lora.bf(a) @ basis, atol=1e-5))


class Spectrum(unittest.TestCase):
    """A medição que decide se vale extrair uma LoRA: delta de posto baixo tem que aparecer como tal."""

    def files(self, tmp, delta):
        base = f32(96, 64)
        write(Path(tmp) / 'base.safetensors', {'blocks.0.attn.qkv_proj.weight': (base, 'BF16')})
        write(Path(tmp) / 'tuned.safetensors', {'blocks.0.attn.qkv_proj.weight': (base + delta, 'BF16')})
        return str(Path(tmp) / 'base.safetensors'), str(Path(tmp) / 'tuned.safetensors')

    def test_low_rank_delta_is_recognised(self):
        with tempfile.TemporaryDirectory() as tmp:
            delta = (f32(96, 8) @ f32(8, 64)) * 3          # posto 8 exato
            base, tuned = self.files(tmp, delta)
            out = mc.spectrum(base, tuned, keys=['blocks.0.attn.qkv_proj.weight'], ranks=(8, 32),
                              report=lambda *a: None)
            self.assertGreater(out[8], 0.98)
            self.assertGreater(out[32], 0.99)

    def test_full_rank_delta_is_recognised(self):
        with tempfile.TemporaryDirectory() as tmp:
            base, tuned = self.files(tmp, f32(96, 64) * 3)  # ruído: posto cheio
            out = mc.spectrum(base, tuned, keys=['blocks.0.attn.qkv_proj.weight'], ranks=(8, 32),
                              report=lambda *a: None)
            self.assertLess(out[8], 0.45)
            self.assertLess(out[32], 0.95)

    def test_randomised_svd_matches_exact_values(self):
        # Matriz gaussiana é o pior caso (espectro achatado); o que usamos é a energia acumulada.
        matrix = f32(120, 80)
        exact = np.linalg.svd(matrix, compute_uv=False)
        approx = mc.top_singular_values(matrix, 16)
        self.assertTrue(np.allclose(exact[:5], approx[:5], rtol=0.02), (exact[:3], approx[:3]))
        energy = lambda v: float((v[:16].astype(np.float64) ** 2).sum())
        self.assertAlmostEqual(energy(approx) / energy(exact), 1.0, delta=0.03)
        # num delta de posto baixo, a aproximação é praticamente exata
        low = f32(120, 6) @ f32(6, 80)
        self.assertTrue(np.allclose(np.linalg.svd(low, compute_uv=False)[:6],
                                    mc.top_singular_values(low, 6)[:6], rtol=1e-3))

    def test_refuses_incompatible_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            write(Path(tmp) / 'a.safetensors', {'blocks.0.attn.qkv_proj.weight': (f32(96, 64), 'BF16')})
            write(Path(tmp) / 'b.safetensors', {'outra.weight': (f32(96, 64), 'BF16')})
            with self.assertRaises(ValueError):
                mc.spectrum(str(Path(tmp) / 'a.safetensors'), str(Path(tmp) / 'b.safetensors'),
                            keys=['blocks.0.attn.qkv_proj.weight'], report=lambda *a: None)


class Bf16Codec(unittest.TestCase):
    def test_known_bit_patterns(self):
        bits = np.array([0x3F80, 0x4000, 0xBF80, 0x3FC0, 0x0000, 0xC120], dtype=np.uint16)
        values = mc.decode_float(bits.view(np.uint8), 'BF16')
        self.assertTrue(np.allclose(values, [1.0, 2.0, -1.0, 1.5, 0.0, -10.0]))
        self.assertTrue(np.array_equal(mc.encode_bf16(values), bits))

    def test_round_trip_is_nearest_even(self):
        values = (rng.standard_normal(2000) * 5).astype(np.float32)
        back = mc.decode_float(mc.encode_bf16(values).view(np.uint8), 'BF16')
        self.assertTrue(np.all(np.abs(back - values) <= np.abs(values) * 2 ** -8 + 1e-30))
        exact = np.array([1.5, -2.0, 0.0078125], dtype=np.float32)
        self.assertTrue(np.array_equal(mc.decode_float(mc.encode_bf16(exact).view(np.uint8), 'BF16'), exact))


if __name__ == '__main__':
    unittest.main()
