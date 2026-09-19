"""v31 warp_format Meridian: paridade com recam/geometry.render_hw, canvas, poda de bordas e node.

python -B tests/test_v31_meridian.py   (NumPy + Pillow)
"""
import importlib, json, math, sys, types, unittest
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
pkg = types.ModuleType('integration'); pkg.__path__ = [str(root)]; sys.modules['integration'] = pkg
dw = importlib.import_module('integration.depth_warp')
editor = importlib.import_module('integration.experimental')
rng = np.random.default_rng(11)
ORBIT = json.dumps([dict(time=0, azimuth=0, elevation=0, distance=1), dict(time=1, azimuth=30, elevation=8, distance=0.9)])


class RenderParity(unittest.TestCase):
    def test_fast_render_matches_literal_render_hw(self):
        for trial in range(12):
            N = 4000 + 800 * trial
            H, W = [(48, 83), (60, 60), (83, 48)][trial % 3]
            P = np.column_stack([rng.normal(0, 1.2, N), rng.normal(0, 0.8, N), rng.uniform(-0.5, 6, N)])
            if trial % 4 == 0:  # empates de profundidade no mesmo pixel
                P[: N // 5, 2] = np.round(P[: N // 5, 2], 1)
            C = (rng.random((N, 3)) * 255).astype(np.uint8)
            az, el = rng.uniform(-40, 40), rng.uniform(-20, 20)
            c2w = dw.orbit_pose(az, el, rng.uniform(0.7, 1.3), (0.1, -0.1, 2.5), (0, 0, 2.5))
            extr = np.linalg.inv(c2w)[:3]
            K = np.array([[W * 0.9, 0, W / 2 + 0.3], [0, W * 0.9, H / 2 - 0.2], [0, 0, 1]])
            ref = dw.meridian_render_reference(P, C, extr, K, H, W)
            got = dw.meridian_render(P, C, extr, K, H, W)
            self.assertTrue(np.array_equal(ref[0], got[0]), trial)
            self.assertTrue(np.array_equal(ref[1], got[1]), trial)
            self.assertTrue((got[0][~got[1]] == 128).all())

    def test_bucket_and_canvas(self):
        self.assertEqual(dw.meridian_bucket(1920, 1080), ((1344, 768), (832, 480)))
        self.assertEqual(dw.meridian_bucket(1080, 1920), ((768, 1344), (480, 832)))
        self.assertEqual(dw.meridian_bucket(512, 512), ((1024, 1024), (640, 640)))
        g = dw.meridian_geometry(1920, 1080)
        self.assertEqual(g['point'], (1280, 720))
        x0, y0, bw, bh, f = g['box']
        self.assertEqual((x0, y0, bw, bh), (16, 0, 1248, 720))
        self.assertAlmostEqual(f, 832 / 1248)

    def test_scale_k_pixel_centre_convention(self):
        K = np.array([[100.0, 0, 31.5], [0, 100.0, 20.0], [0, 0, 1]])
        X = np.array([0.3, -0.2, 2.0])
        for f in (0.5, 0.65, 2.5):
            lo = K @ (X / X[2]); hi = dw.scale_k(K, f) @ (X / X[2])
            self.assertTrue(np.allclose(hi[:2], f * (lo[:2] + 0.5) - 0.5))

    def test_bilinear_matches_align_corners_false(self):
        out = dw._bilinear(np.array([[0.0, 1.0]], dtype=np.float32), 1, 4)
        self.assertTrue(np.allclose(out, [[0.0, 0.25, 0.75, 1.0]]))
        out = dw._bilinear(np.array([[0.0], [1.0]], dtype=np.float32), 4, 1)
        self.assertTrue(np.allclose(out[:, 0], [0.0, 0.25, 0.75, 1.0]))

    def test_edge_pruning(self):
        z = np.full((300, 400), 2.0); z[:, 200:] = 6.0; z[:40, :40] = np.nan
        keep = dw.meridian_keep(z)
        self.assertTrue(keep[150, 50] and keep[150, 350])
        self.assertFalse(keep[150, 199] or keep[150, 200])
        self.assertFalse(keep[10, 10] or keep[40, 20])
        self.assertTrue(keep[42, 20] and keep[0, 300])  # dilata 1 px na escala 512; a borda do quadro não poda
        z2 = np.linspace(2, 2.2, 400)[None].repeat(300, 0)  # rampa suave não é borda
        self.assertTrue(dw.meridian_keep(z2)[5:-5, 5:-5].all())


class NodeMeridian(unittest.TestCase):
    def run_node(self, **kw):
        args = dict(camera_trajectory=ORBIT, profile='124 frames (~5.17s)', interpolation='linear', instruction='',
                    depth_animation='Depth Warp', warp_format='Meridian (H3)')
        args.update(kw)
        out = editor.H3Camera().run(**args)
        return out['result'] if isinstance(out, dict) else out

    def scene(self, H=90, W=160):
        yy, xx = np.mgrid[0:H, 0:W]
        img = rng.random((1, H, W, 3)).astype(np.float32)
        d = 0.3 + 0.2 * yy / H
        d = np.where(((xx - W / 2) ** 2 / (W * .18) ** 2 + (yy - H / 2) ** 2 / (H * .3) ** 2) < 1, 0.9, d)
        return img, np.repeat(d[..., None], 3, -1)[None].astype(np.float32)

    def test_output_canvas_holes_and_first_frame(self):
        img, depth = self.scene()
        r = self.run_node(reference_image=img, depth=depth)
        warp, holes = r[8], r[9]
        self.assertEqual(warp.shape, (124, 480, 832, 3))
        self.assertLess(float(holes[0].mean()), 0.06)
        self.assertGreater(float(holes[-1].mean()), float(holes[0].mean()))
        grey = np.isclose(warp[-1], 128 / 255.0).all(-1)
        self.assertTrue(grey[holes[-1] > 0.5].all())
        self.assertIn('Depth Warp (Meridian)', r[3])
        self.assertIn('Meridian Reference', r[3])

    def test_lengths_and_portrait(self):
        img, depth = self.scene(160, 90)
        r = self.run_node(reference_image=img, depth=depth, warp_length=73)
        self.assertEqual(r[8].shape, (73, 832, 480, 3))
        with self.assertRaises(ValueError):
            self.run_node(reference_image=img, depth=depth, warp_length=121)
        with self.assertRaises(ValueError):
            self.run_node(reference_image=img, depth=depth, profile='362 frames (~15.08s)')

    def test_legacy_v30_format_still_runs(self):
        img, depth = self.scene()
        r = self.run_node(reference_image=img, depth=depth, warp_format=dw.LEGACY_FORMAT, warp_length=5)
        self.assertEqual(r[8].shape, (5, 90, 160, 3))

    def test_preview_meta(self):
        import tempfile
        img, depth = self.scene()
        plan = json.loads(self.run_node(depth_animation='Off')[2])
        with tempfile.TemporaryDirectory() as tmp:
            _, _, _, meta = dw.build_depth_warp(plan, 'Freeze Frame', img, depth, None, temp_dir=tmp, length=73,
                                                warp_format='Meridian (H3)')
        self.assertEqual(meta['format'], 'meridian')
        self.assertEqual(meta['hole'], [128, 128, 128])
        self.assertEqual((meta['source_w'], meta['source_h']), (832, 480))
        self.assertAlmostEqual(meta['w'] / meta['h'], 1248 / 720 * (90 / 90), delta=0.02)


class HoldTiming(unittest.TestCase):
    """--freeze F:N do Meridian: play -> segura -> retoma, com a câmera andando o tempo todo."""

    def plan(self):
        out = editor.H3Camera().run(camera_trajectory=ORBIT, profile='124 frames (~5.17s)', interpolation='linear',
                                    instruction='')
        return json.loads(out[2])

    def test_play_hold_resume(self):
        plan = self.plan()
        poses, sources, n, hold = dw.frame_schedule(plan, 73, 200, 'Motion Frame', 24.0, 0, dw.DIRECTIONS[0],
                                                    hold_at=24, hold_frames=25)
        self.assertEqual(n, 73)
        self.assertEqual(sources[:3], [0, 1, 2])
        self.assertEqual(sources[23:26], [23, 24, 24])
        self.assertEqual(sources[48], 24)          # 24 vivos + 25 segurando
        self.assertEqual(sources[49:52], [25, 26, 27])
        self.assertEqual(sources[-1], 24 + (73 - 49))
        self.assertEqual((hold['at'], hold['frames'], hold['live'], hold['tail']), (24, 25, 24, 24))
        # a câmera continua andando durante o congelamento
        self.assertGreater(poses[48]['azimuth'], poses[24]['azimuth'])

    def test_hold_beyond_source_end(self):
        plan = self.plan()
        _, sources, _, hold = dw.frame_schedule(plan, 73, 30, 'Motion Frame', 24.0, 0, dw.DIRECTIONS[0],
                                                hold_at=20, hold_frames=10)
        self.assertEqual(max(sources), 29)
        self.assertEqual(sources[-1], 29)
        self.assertTrue(hold['last'] >= 29)

    def test_hold_respects_source_fps_and_is_off_by_default(self):
        plan = self.plan()
        _, half, _, hold = dw.frame_schedule(plan, 73, 60, 'Motion Frame', 12.0, 0, dw.DIRECTIONS[0],
                                             hold_at=10, hold_frames=8)
        self.assertEqual(half[:4], [0, 0, 1, 1])
        self.assertEqual(half[20:28], [10] * 8)   # chega em 10 no frame 20 e segura 8 a partir dali
        self.assertEqual(half[28:32], [11, 11, 12, 12])
        _, plain, _, none = dw.frame_schedule(plan, 73, 60, 'Motion Frame', 12.0, 0, dw.DIRECTIONS[0])
        self.assertIsNone(none)
        self.assertEqual(plain[28], 14)

    def test_node_reports_hold(self):
        img, depth = NodeMeridian().scene(48, 84)
        frames = np.repeat(img, 60, axis=0)  # Motion Frame exige pelo menos 2 s
        depths = np.repeat(depth, 60, axis=0)
        out = editor.H3Camera().run(camera_trajectory=ORBIT, profile='124 frames (~5.17s)', interpolation='linear',
                                    instruction='', reference_image=frames, depth=depths, frame_mode='Motion Frame',
                                    source_fps=24.0, depth_animation='Depth Warp', warp_format='Meridian (H3)',
                                    warp_length=73, warp_hold_at=10, warp_hold_frames=20)
        r = out['result'] if isinstance(out, dict) else out
        self.assertEqual(r[8].shape[0], 73)
        self.assertIn('Congelamento', r[3])


if __name__ == '__main__':
    unittest.main()
