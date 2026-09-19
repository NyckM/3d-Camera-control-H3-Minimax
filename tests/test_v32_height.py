"""v32 altura (grua): eixo novo, separado da elevação.

python -B tests/test_v32_height.py
"""
import importlib, json, math, sys, types, unittest
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
pkg = types.ModuleType('integration'); pkg.__path__ = [str(root)]; sys.modules['integration'] = pkg
dw = importlib.import_module('integration.depth_warp')
tm = importlib.import_module('integration.trajectory_math')
editor = importlib.import_module('integration.experimental')


def path(*poses):
    return json.dumps([dict(zip(('time', 'azimuth', 'elevation', 'distance', 'height'), p)) for p in poses])


class Interpolation(unittest.TestCase):
    def test_legacy_paths_without_height(self):
        legacy = [dict(time=0, azimuth=0, elevation=0, distance=1), dict(time=1, azimuth=40, elevation=0, distance=1)]
        pose = tm.interpolate_pose(legacy, 0.5, 'linear')
        self.assertEqual(pose['height'], 0.0)
        self.assertAlmostEqual(pose['azimuth'], 20.0)

    def test_height_interpolates_on_every_curve(self):
        p = [dict(time=0, azimuth=0, elevation=0, distance=1, height=0),
             dict(time=1, azimuth=0, elevation=0, distance=1, height=-0.8)]
        for interp, detail in (('linear', 'v15 baseline'), ('smooth', 'v15 baseline'), ('smooth', 'extended contracts')):
            self.assertAlmostEqual(tm.interpolate_pose(p, 0.5, interp, detail)['height'], -0.4, places=6)
        self.assertAlmostEqual(tm.interpolate_pose(p, 1.0, 'linear')['height'], -0.8)


class OrbitGeometry(unittest.TestCase):
    def test_boom_is_a_pure_translation(self):
        """Com mira da fonte a lente não gira: só o olho e o alvo sobem juntos."""
        flat = dw.orbit_pose(0, 0, 1, (0, 0, 2), (0, 0, 2))
        down = dw.orbit_pose(0, 0, 1, (0, 0, 2), (0, 0, 2), height=-0.4)
        self.assertTrue(np.allclose(flat[:3, :3], down[:3, :3]))       # mesma orientação
        self.assertAlmostEqual(down[1, 3] - flat[1, 3], 0.8)            # +y é para baixo no OpenCV
        self.assertAlmostEqual(down[0, 3], 0.0)
        self.assertAlmostEqual(down[2, 3], 0.0)

    def test_crane_with_pivot_aim_tilts(self):
        up = dw.orbit_pose(0, 0, 1, (0, 0, 2), None, height=0.4)
        self.assertLess(up[1, 3], 0)                                    # câmera subiu
        self.assertGreater(up[1, 2], 0.01)                              # e inclinou para baixo

    def test_height_is_not_elevation(self):
        """Elevação gira em torno do alvo (muda z); altura não."""
        boom = dw.orbit_pose(0, 0, 1, (0, 0, 2), (0, 0, 2), height=0.4)
        arc = dw.orbit_pose(0, 20, 1, (0, 0, 2), (0, 0, 2))
        self.assertAlmostEqual(boom[2, 3], 0.0, places=9)
        self.assertGreater(abs(arc[2, 3]), 0.1)

    def test_height_scales_with_pivot_distance(self):
        near = dw.orbit_pose(0, 0, 1, (0, 0, 1), (0, 0, 1), height=0.5)
        far = dw.orbit_pose(0, 0, 1, (0, 0, 4), (0, 0, 4), height=0.5)
        self.assertAlmostEqual(far[1, 3] / near[1, 3], 4.0)


class NodeIntegration(unittest.TestCase):
    def run_node(self, trajectory, **kw):
        args = dict(camera_trajectory=trajectory, profile='124 frames (~5.17s)', interpolation='linear', instruction='')
        args.update(kw)
        out = editor.H3Camera().run(**args)
        return out['result'] if isinstance(out, dict) else out

    def test_prompt_describes_a_crane(self):
        r = self.run_node(path((0, 0, 0, 1, 0), (1, 0, 0, 1, -0.35)))
        self.assertIn('CRANE the CAMERA straight DOWN', r[0])
        self.assertIn('boom, not an elevation arc', r[0])
        self.assertIn('Height is a straight vertical camera translation', r[0])
        self.assertIn('"height": -0.35', r[2].replace(' ', '').replace('"height":-0.35', '"height": -0.35'))

    def test_rejects_out_of_range_and_nonzero_first_keyframe(self):
        with self.assertRaises(ValueError):
            self.run_node(path((0, 0, 0, 1, 0), (1, 0, 0, 1, 9)))
        with self.assertRaises(ValueError):
            self.run_node(path((0, 0, 0, 1, 0.2), (1, 0, 0, 1, 0)))

    def test_loop_closure_needs_height_back_home(self):
        img = np.zeros((1, 64, 64, 3), dtype=np.float32)
        home = self.run_node(path((0, 0, 0, 1, 0), (1, 360, 0, 1, 0)), reference_image=img)
        away = self.run_node(path((0, 0, 0, 1, 0), (1, 360, 0, 1, 0.5)), reference_image=img)
        self.assertIn('<Picture 2>', home[0])
        self.assertNotIn('<Picture 2>', away[0])

    def test_warp_follows_the_boom(self):
        rng = np.random.default_rng(0)
        img = rng.random((1, 90, 160, 3)).astype(np.float32)
        depth = np.repeat(np.linspace(0.2, 0.9, 90)[None, :, None, None].repeat(160, 2), 3, -1).astype(np.float32)
        flat = self.run_node(path((0, 0, 0, 1, 0), (1, 0, 0, 1, 0)), reference_image=img, depth=depth,
                             depth_animation='Depth Warp', warp_length=73)
        boom = self.run_node(path((0, 0, 0, 1, 0), (1, 0, 0, 1, -0.5)), reference_image=img, depth=depth,
                             depth_animation='Depth Warp', warp_length=73)
        # o primeiro frame é igual nos dois; o último muda só por causa da grua
        self.assertTrue(np.allclose(flat[8][0], boom[8][0]))
        self.assertFalse(np.allclose(flat[8][-1], boom[8][-1]))
        # descer a câmera abre buraco embaixo do quadro, não em cima
        holes = boom[9][-1]
        self.assertGreater(float(holes[-10:].mean()), float(holes[:10].mean()))


if __name__ == '__main__':
    unittest.main()
