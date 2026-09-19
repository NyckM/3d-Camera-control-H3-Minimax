"""v30 Depth Warp: paridade com o CrossViewWarp, integração no Camera H3 e fixture da prévia JS.

python -B tests/test_v30_depth.py            (NumPy + Pillow; não precisa de Torch nem ComfyUI)
python -B tests/test_v30_depth.py --fixture  (regrava tests/fixtures/depth_warp_js.json)
"""
import importlib, json, math, sys, tempfile, types, unittest
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
pkg = types.ModuleType('integration'); pkg.__path__ = [str(root)]; sys.modules['integration'] = pkg
dw = importlib.import_module('integration.depth_warp')
editor = importlib.import_module('integration.experimental')
FIXTURE = root / 'tests' / 'fixtures' / 'depth_warp_js.json'

rng = np.random.default_rng(7)


def scene(H, W, frames=1):
    yy, xx = np.mgrid[0:H, 0:W]
    out_rgb, out_depth = [], []
    for f in range(frames):
        base = 0.35 + 0.3 * np.sin((xx + 3 * f) / 17.0) * np.cos(yy / 11.0)
        blob = ((xx - W * 0.5 - f) ** 2 + (yy - H * 0.45) ** 2) < (min(H, W) * 0.22) ** 2
        d = np.where(blob, 0.95, base) + rng.normal(0, 0.004, (H, W))
        out_depth.append(np.repeat(d[..., None], 3, -1))
        out_rgb.append(rng.random((H, W, 3)))
    return np.stack(out_rgb).astype(np.float32), np.stack(out_depth).astype(np.float32)


def path(*poses):
    return json.dumps([dict(time=t, azimuth=a, elevation=e, distance=d) for t, a, e, d in poses])


ORBIT = path((0, 0, 0, 1), (0.5, 30, 10, 1), (1, 60, 0, 0.8))


class ParityTests(unittest.TestCase):
    def test_fast_renderer_matches_crossview_loop(self):
        for H, W in [(33, 47), (72, 128)]:
            rgb = (rng.random((H, W, 3)) * 255).astype(np.uint8)
            d = scene(H, W)[1][0, ..., 0]
            z = dw.depth_to_z(d, False, 6.0, np.percentile(d, 1), np.percentile(d, 99))
            fx = W / (2 * math.tan(math.radians(50) / 2))
            cloud = dw.PointCloud(rgb, z, fx)
            for az, el, dist in [(0, 0, 1), (35, 12, 1), (-60, -25, 0.7), (120, 40, 1.6), (360, 0, 1), (5, 89, 1)]:
                for pivot, aim in [((0, 0, 1.05), None), ((0.2, -0.1, 2.0), (0, 0, math.hypot(0.2, 0.1, 2.0)))]:
                    C = dw.orbit_pose(az, el, dist, pivot, aim)
                    for splat in (0, 2):
                        expected = dw.reference_warp_frame(rgb, z, np.eye(4), C, fx, splat, W / 2, H / 2)
                        got, holes = cloud.render(C, splat)
                        self.assertTrue(np.array_equal(expected, got), (H, W, az, el, dist, pivot, splat))
                        self.assertTrue(((got == [255, 0, 255]).all(-1) | ~holes).all())

    def test_source_aim_first_pose_is_identity(self):
        C = dw.orbit_pose(0, 0, 1, (0.4, -0.2, 3.0), (0, 0, math.hypot(0.4, 0.2, 3.0)))
        self.assertTrue(np.allclose(C, np.eye(4)))

    def test_sign_convention_matches_panel(self):
        # +azimuth leva a câmera para a direita (+x no frame OpenCV), +elevation para cima (-y).
        C = dw.orbit_pose(30, 0, 1, (0, 0, 2), (0, 0, 2))
        self.assertGreater(C[0, 3], 0)
        C = dw.orbit_pose(0, 30, 1, (0, 0, 2), (0, 0, 2))
        self.assertLess(C[1, 3], 0)


class NodeTests(unittest.TestCase):
    def run_node(self, **kw):
        args = dict(camera_trajectory=ORBIT, profile='124 frames (~5.17s)', interpolation='linear', instruction='',
                    depth_animation='Depth Warp', warp_format=dw.LEGACY_FORMAT)
        args.update(kw)
        out = editor.H3Camera().run(**args)
        return out['result'] if isinstance(out, dict) else out

    def test_off_blocks_outputs_and_keeps_contract(self):
        img, depth = scene(24, 40)
        r = self.run_node(depth_animation='Off', reference_image=img, depth=depth)
        self.assertEqual(len(r), 10)
        self.assertEqual(editor.H3Camera.RETURN_NAMES[-3:], ('camera_prompt', 'depth_warp', 'warp_mask'))
        self.assertIn('Off', r[3])

    def test_freeze_warp_follows_profile(self):
        img, depth = scene(36, 64)
        r = self.run_node(reference_image=img, depth=depth, frame_mode='Freeze Frame')
        warp, holes = r[8], r[9]
        self.assertEqual(warp.shape, (124, 36, 64, 3))
        self.assertEqual(holes.shape, (124, 36, 64))
        self.assertEqual(warp.dtype, np.float32)
        self.assertLessEqual(float(warp.max()), 1.0)
        # Keyframe 1 é a imagem: sem buracos além das bordas do splat/corte de 0,5% mais distante.
        self.assertLess(float(holes[0].mean()), 0.02)
        self.assertGreater(float(holes[-1].mean()), float(holes[0].mean()))
        self.assertIn('Depth Warp (v30): 124 frames', r[3])

    def test_custom_length_stretches_path_and_downscales(self):
        img, depth = scene(40, 80)
        r = self.run_node(reference_image=img, depth=depth, warp_length=25, warp_long_side=40)
        self.assertEqual(r[8].shape, (25, 20, 40, 3))
        plan = json.loads(r[2])
        poses, _, n, _ = dw.frame_schedule(plan, 25, 1, 'Freeze Frame', 24.0, 0, dw.DIRECTIONS[0])
        self.assertEqual(n, 25)
        self.assertAlmostEqual(poses[-1]['azimuth'], 60.0)
        self.assertAlmostEqual(poses[12]['azimuth'], 30.0)

    def test_direction_option_uses_calibrated_path(self):
        plan = json.loads(self.run_node(depth_animation='Off')[2])
        panel, _, _, _ = dw.frame_schedule(plan, 0, 1, 'Freeze Frame', 24, 0, dw.DIRECTIONS[0])
        model, _, _, _ = dw.frame_schedule(plan, 0, 1, 'Freeze Frame', 24, 0, dw.DIRECTIONS[1])
        self.assertAlmostEqual(panel[-1]['azimuth'], 60.0)
        self.assertAlmostEqual(model[-1]['azimuth'], -60.0)

    def test_motion_uses_one_depth_per_source_frame(self):
        img, depth = scene(16, 24, frames=60)
        r = self.run_node(reference_image=img, depth=depth, frame_mode='Motion Frame', source_fps=12.0,
                          warp_length=0)
        self.assertEqual(r[8].shape[0], 124)
        plan = json.loads(r[2])
        _, sources, _, _ = dw.frame_schedule(plan, 0, 60, 'Motion Frame', 12.0, 0, dw.DIRECTIONS[0])
        self.assertEqual(sources[:4], [0, 0, 1, 1])
        self.assertEqual(sources[-1], 59)
        with self.assertRaises(ValueError):
            self.run_node(reference_image=img, depth=depth[:7], frame_mode='Motion Frame', source_fps=12.0)

    def test_moge_geometry_metric_path_and_intrinsics(self):
        img, depth = scene(30, 50)
        metric = 2.0 + 3.0 * (1.0 - depth[..., 0])
        mask = np.ones_like(metric, dtype=bool); mask[:, :5, :5] = False
        K = np.array([[[0.9, 0, 0.5], [0, 1.5, 0.5], [0, 0, 1]]], dtype=np.float32)
        geo = {'depth': metric, 'mask': mask, 'intrinsics': K}
        warp, holes, info, _ = dw.build_depth_warp(json.loads(self.run_node(depth_animation='Off')[2]),
                                                   'Freeze Frame', img, None, geo, hfov=0.0, length=5,
                                                   warp_format=dw.LEGACY_FORMAT)
        self.assertEqual(warp.shape, (5, 30, 50, 3))
        self.assertIn('MoGe', info)
        self.assertTrue(holes[0][:3, :3].all())  # splat 2 cobre ate 2 px do mascarado
        src = dw.DepthSource(img, None, geo, (50, 30), 0.0, 6, False, False, [0])
        self.assertAlmostEqual(src.fx, 45.0, places=4)

    def test_subject_box_pivot(self):
        z = np.full((40, 80), 4.0); z[10:30, 50:70] = 2.0
        fx = 80 / (2 * math.tan(math.radians(50) / 2))
        pivot, how = dw.estimate_pivot(z, fx, (50 / 80, 10 / 40, 20 / 80, 20 / 40), True, 0.0)
        self.assertEqual(how, 'subject_box')
        self.assertAlmostEqual(pivot[2], 2.0)
        self.assertGreater(pivot[0], 0)
        pivot2, how2 = dw.estimate_pivot(z, fx, None, False, 0.0)
        self.assertEqual(list(pivot2), [0.0, 0.0, 1.05])
        pivot3, _ = dw.estimate_pivot(z, fx, (50 / 80, 10 / 40, 20 / 80, 20 / 40), True, 3.0)
        self.assertAlmostEqual(pivot3[2], 3.0)
        self.assertAlmostEqual(pivot3[0] / pivot3[2], pivot[0] / pivot[2])

    def test_errors_are_explicit(self):
        img, depth = scene(20, 30)
        with self.assertRaises(ValueError):
            self.run_node(reference_image=img)
        with self.assertRaises(ValueError):
            self.run_node(depth=depth)
        old = dw.PIXEL_BUDGET
        try:
            dw.PIXEL_BUDGET = 1000
            with self.assertRaises(ValueError):
                self.run_node(reference_image=img, depth=depth)
        finally:
            dw.PIXEL_BUDGET = old

    def test_offset_applies_to_whole_warp(self):
        img, depth = scene(30, 50)
        plain = self.run_node(reference_image=img, depth=depth, warp_length=9)
        moved = self.run_node(reference_image=img, depth=depth, warp_length=9, warp_offset_azimuth=-25.0)
        self.assertLess(float(plain[9][0].mean()), float(moved[9][0].mean()))
        self.assertIn('offset (-25°', moved[3])
        plan = json.loads(plain[2])
        pivot = np.array([0.0, 0.0, 1.05])
        warp, _, _, _ = dw.build_depth_warp(plan, 'Freeze Frame', img, depth, None, length=2, offset_azimuth=-25.0,
                                            warp_format=dw.LEGACY_FORMAT)
        source = dw.DepthSource(img, depth, None, (50, 30), 50.0, 6.0, False, False, [0])
        rgb = dw._frame_rgb(img, 0)
        expected, _ = dw.PointCloud(rgb, source.z(0, rgb), source.fx).render(dw.orbit_pose(-25.0, 0, 1, pivot, (0, 0, 1.05)))
        self.assertTrue(np.array_equal((warp[0] * 255).round().astype(np.uint8), expected))

    def test_near_source_hint(self):
        img, depth = scene(20, 30)
        r = self.run_node(reference_image=img, depth=depth, warp_length=3,
                          camera_trajectory=path((0, 0, 0, 1), (1, 4, 0, 1)))
        self.assertIn('warp_offset_azimuth', r[3])

    def test_validate_inputs_accepts_old_empty_values(self):
        self.assertIs(editor.H3Camera.VALIDATE_INPUTS(depth_animation='', warp_aim=None), True)
        self.assertIsInstance(editor.H3Camera.VALIDATE_INPUTS(depth_animation='Nope'), str)

    def test_preview_files_and_fixture(self):
        img, depth = scene(48, 80)
        plan = json.loads(self.run_node(depth_animation='Off')[2])
        with tempfile.TemporaryDirectory() as tmp:
            _, _, _, meta = dw.build_depth_warp(plan, 'Freeze Frame', img, depth, None, temp_dir=tmp, length=3,
                                                    warp_format=dw.LEGACY_FORMAT)
            self.assertEqual(len(meta['samples']), 1)
            self.assertTrue((Path(tmp) / meta['samples'][0]['z']['filename']).is_file())
            self.assertEqual(meta['aim'], 'source')
        fixture = make_fixture()
        if FIXTURE.is_file():
            self.assertEqual(json.loads(FIXTURE.read_text()), fixture,
                             'Fixture JS desatualizada: rode python -B tests/test_v30_depth.py --fixture')


def make_fixture():
    """Cena pequena e poses fixas; o teste JS precisa reproduzir estes pixels com splat 0."""
    local = np.random.default_rng(3)
    H, W = 18, 32
    yy, xx = np.mgrid[0:H, 0:W]
    z = 1.0 + 3.0 * (0.5 + 0.5 * np.sin(xx / 5.0) * np.cos(yy / 4.0)) + local.random((H, W)) * 0.01
    z[4:12, 12:20] = 1.3 + local.random((8, 8)) * 0.01
    rgb = (local.random((H, W, 3)) * 255).astype(np.uint8)
    fx = W / (2 * math.tan(math.radians(50) / 2))
    cloud = dw.PointCloud(rgb, z, fx)
    cases = []
    for az, el, dist, aim in [(0, 0, 1, 'source'), (25, 10, 1, 'source'), (-40, -15, 0.8, 'pivot'), (70, 30, 1.3, 'source')]:
        pivot = [0.1, -0.05, 1.8]
        C = dw.orbit_pose(az, el, dist, pivot, (0, 0, math.hypot(*pivot)) if aim == 'source' else None)
        got, holes = cloud.render(C, 0)
        cases.append({'pose': {'azimuth': az, 'elevation': el, 'distance': dist}, 'aim': aim, 'pivot': pivot,
                      'C': np.round(C, 10).tolist(), 'rgb': got.reshape(-1).tolist(),
                      'holes': holes.reshape(-1).astype(int).tolist()})
    return {'w': W, 'h': H, 'fx_norm': fx / W, 'thr': cloud.thr, 'z': np.round(z, 12).reshape(-1).tolist(),
            'src': rgb.reshape(-1).tolist(), 'cases': cases}


if __name__ == '__main__':
    if '--fixture' in sys.argv:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(json.dumps(make_fixture()))
        print('fixture written', FIXTURE)
    else:
        unittest.main()
