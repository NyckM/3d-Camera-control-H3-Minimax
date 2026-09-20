"""v31 Meridian Reference: ordem das referências, canvas 480/768 e validações, com dublês do ComfyUI.

python -B tests/test_v31_reference.py   (NumPy; os dublês substituem torch/comfy)
"""
import importlib, sys, types, unittest
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
pkg = types.ModuleType('integration'); pkg.__path__ = [str(root)]; sys.modules['integration'] = pkg
mn = importlib.import_module('integration.meridian_nodes')

RESIZES = []


class FakeTorch:
    @staticmethod
    def cat(parts):
        return np.concatenate(parts, axis=0)

    @staticmethod
    def zeros(shape, device=None):
        return np.zeros(shape, dtype=np.float32)


class FakeCore:
    CANVAS_MULTIPLE = 32

    @staticmethod
    def temporal_shape(length):
        return length, (length - 5) // 17 + 1, round(length / 24 * 50)

    @staticmethod
    def _resize(image, width, height, crop):
        RESIZES.append((int(image.shape[2]), int(image.shape[1]), width, height))
        return np.zeros((image.shape[0], height, width, 3), dtype=np.float32)


class FakeVae:
    def encode(self, clip):
        frames, h, w = clip.shape[0], clip.shape[1], clip.shape[2]
        return np.zeros((1, 24, (frames - 5) // 17 + 1, h // 16, w // 16), dtype=np.float32)


def fake_comfy():
    module = types.ModuleType('comfy')
    module.model_management = types.SimpleNamespace(intermediate_device=lambda: 'cpu')
    module.nested_tensor = types.SimpleNamespace(NestedTensor=lambda pair: {'video': pair[0], 'audio': pair[1]})
    return module


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        RESIZES.clear()
        mn.torch, mn.core_h3, mn.comfy = FakeTorch, FakeCore, fake_comfy()
        self.text = {'prompt_embeds': np.zeros((1, 362, 8), dtype=np.float32),
                     'text_token_tags': np.zeros(362, dtype=np.int64), 'name': 'fixed_embed_124'}

    def clip(self, n, h=480, w=832):
        return np.zeros((n, h, w, 3), dtype=np.float32)

    def test_reference_order_and_canvas(self):
        source = self.clip(124, 1080, 1920)
        warp = self.clip(124)  # já sai 832x480 do Camera H3
        cond, latent, report = mn.MeridianReference().build(source, warp, FakeVae(), 124, text_cond=self.text)
        refs = cond[0][1]['minimax_refs']
        self.assertEqual(len(refs), 2)
        self.assertEqual([r['kind'] for r in refs], ['video', 'video'])
        self.assertEqual((refs[0]['latent_w'], refs[0]['latent_h']), (832 // 16, 480 // 16))
        self.assertEqual((refs[1]['latent_w'], refs[1]['latent_h']), (832 // 16, 480 // 16))
        self.assertIs(cond[0][0], self.text['prompt_embeds'])
        self.assertIs(cond[0][1]['minimax_token_tags'], self.text['text_token_tags'])
        # alvo: canvas classe 768 do aspecto 16:9
        self.assertEqual(latent['samples']['video'].shape[-2:], (768 // 16, 1344 // 16))
        self.assertEqual(latent['samples']['video'].shape[2], (124 - 5) // 17 + 1)
        # a fonte 1920x1080 é reduzida para a classe 480; o warp já está no tamanho
        self.assertEqual(RESIZES, [(1920, 1080, 832, 480)])
        self.assertIn('1344x768', report)

    def test_portrait_bucket(self):
        cond, latent, _ = mn.MeridianReference().build(self.clip(73, 1920, 1080), self.clip(73, 832, 480),
                                                       FakeVae(), 73, text_cond=self.text)
        self.assertEqual(cond[0][1]['minimax_refs'][0]['latent_w'], 480 // 16)
        self.assertEqual(latent['samples']['video'].shape[-2:], (1344 // 16, 768 // 16))

    def test_short_source_is_held(self):
        cond, _, report = mn.MeridianReference().build(self.clip(100), self.clip(124), FakeVae(), 124, text_cond=self.text)
        self.assertIn('último frame', report)
        self.assertEqual(cond[0][1]['minimax_refs'][0]['latent_t'], (124 - 5) // 17 + 1)

    def test_errors(self):
        with self.assertRaises(ValueError):  # duração sem embedding
            mn.MeridianReference().build(self.clip(121), self.clip(121), FakeVae(), 121, text_cond=self.text)
        with self.assertRaises(ValueError):  # warp com outro comprimento
            mn.MeridianReference().build(self.clip(124), self.clip(73), FakeVae(), 124, text_cond=self.text)

    def test_prompt_replaces_the_frozen_embedding(self):
        embeds = np.zeros((1, 88, 8), dtype=np.float32)
        tags = np.ones(88, dtype=np.int64)
        cond, _, report = mn.MeridianReference().build(self.clip(73), self.clip(73, 832, 480), FakeVae(), 73,
                                                       prompt=[[embeds, {'minimax_token_tags': tags}]])
        self.assertIs(cond[0][0], embeds)
        self.assertIs(cond[0][1]['minimax_token_tags'], tags)
        self.assertIn('prompt (1, 88, 8)', report)
        with self.assertRaises(ValueError):   # conditioning de outro modelo, sem token tags
            mn.MeridianReference().build(self.clip(73), self.clip(73, 832, 480), FakeVae(), 73,
                                         prompt=[[embeds, {}]])
        with self.assertRaises(ValueError):   # nem embedding nem prompt
            mn.MeridianReference().build(self.clip(73), self.clip(73, 832, 480), FakeVae(), 73)

    def test_image_references_come_first_and_warn_without_clip(self):
        """Ordem do H3: imagens antes dos vídeos. A numeração é por tipo, então o warp segue <Video 2>."""
        cond, _, report = mn.MeridianReference().build(self.clip(73), self.clip(73, 832, 480), FakeVae(), 73,
                                                       text_cond=self.text,
                                                       ref_image_1=np.zeros((1, 1024, 768, 3), dtype=np.float32),
                                                       ref_image_2=np.zeros((1, 512, 512, 3), dtype=np.float32))
        refs = cond[0][1]['minimax_refs']
        self.assertEqual([r['kind'] for r in refs], ['image', 'image', 'video', 'video'])
        self.assertIn('<Picture 1>', report)
        self.assertIn('<Picture 2>', report)
        self.assertIn('NÃO ao text encoder', report)   # sem clip, a etiqueta não aponta para nada

    def test_image_dimensions_are_patch_safe(self):
        """O H3 empacota em blocos 2x2: lado múltiplo de 32, latente par. Com 16 o patchify quebra."""
        for h, w in ((1024, 768), (1080, 1920), (713, 457), (37, 61), (2000, 1333)):
            cond, _, _ = mn.MeridianReference().build(self.clip(73), self.clip(73, 832, 480), FakeVae(), 73,
                                                      text_cond=self.text,
                                                      ref_image_1=np.zeros((1, h, w, 3), dtype=np.float32))
            block = cond[0][1]['minimax_refs'][0]
            self.assertEqual(block['kind'], 'image')
            for key in ('latent_h', 'latent_w'):
                self.assertEqual(block[key] % 2, 0, f'{key} ímpar para {w}x{h}: patchify_video vai falhar')
                self.assertGreaterEqual(block[key], 2)

    def test_clip_path_presents_every_reference(self):
        seen = {}

        class FakeClip:
            def tokenize(self, text, minimax_ref_items=None):
                seen['text'] = text; seen['items'] = minimax_ref_items
                return 'tokens'

            def encode_from_tokens_scheduled(self, tokens):
                seen['tokens'] = tokens
                return [[np.zeros((1, 12, 8), dtype=np.float32), {'minimax_token_tags': np.zeros(12)}]]

        cond, _, report = mn.MeridianReference().build(
            self.clip(73), self.clip(73, 832, 480), FakeVae(), 73, clip=FakeClip(),
            prompt_text='<Picture 1> is the subject', ref_image_1=np.zeros((1, 512, 512, 3), dtype=np.float32),
            ref_video_3=self.clip(73, 832, 480))
        self.assertEqual(seen['text'], '<Picture 1> is the subject')
        self.assertEqual([i['type'] for i in seen['items']], ['image', 'video', 'video', 'video'])
        self.assertEqual([r['kind'] for r in cond[0][1]['minimax_refs']], ['image', 'video', 'video', 'video'])
        self.assertIn('timestamps', seen['items'][1])                    # o vídeo vai a 2 fps
        self.assertEqual(len(seen['items'][1]['timestamps']), 7)         # 73 frames / 12
        self.assertIn('minimax_token_tags', cond[0][1])
        self.assertIn('experimental', report)

    def test_only_one_text_source(self):
        with self.assertRaises(ValueError):
            mn.MeridianReference().build(self.clip(73), self.clip(73, 832, 480), FakeVae(), 73,
                                         text_cond=self.text, prompt=[[np.zeros((1, 8, 8)), {'minimax_token_tags': 1}]])

    def test_manual_canvas_override(self):
        _, latent, _ = mn.MeridianReference().build(self.clip(73), self.clip(73), FakeVae(), 73, text_cond=self.text,
                                                    width=1024, height=576)
        self.assertEqual(latent['samples']['video'].shape[-2:], (576 // 16, 1024 // 16))


if __name__ == '__main__':
    unittest.main()
