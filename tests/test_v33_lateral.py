"""v33 travelling lateral: eixo novo, separado da órbita (e da altura).

python -B tests/test_v33_lateral.py
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
    return json.dumps([dict(zip(('time', 'azimuth', 'elevation', 'distance', 'height', 'lateral'), p)) for p in poses])


class Interpolation(unittest.TestCase):
    def test_legacy_paths_without_lateral(self):
        legacy = [dict(time=0, azimuth=0, elevation=0, distance=1, height=0),
                  dict(time=1, azimuth=40, elevation=0, distance=1, height=0)]
        pose = tm.interpolate_pose(legacy, 0.5, 'linear')
        self.assertEqual(pose['lateral'], 0.0)
        self.assertAlmostEqual(pose['azimuth'], 20.0)

    def test_lateral_interpolates_on_every_curve(self):
        p = [dict(time=0, azimuth=0, elevation=0, distance=1, height=0, lateral=0),
             dict(time=1, azimuth=0, elevation=0, distance=1, height=0, lateral=0.8)]
        for interp, detail in (('linear', 'v15 baseline'), ('smooth', 'v15 baseline'), ('smooth', 'extended contracts')):
            self.assertAlmostEqual(tm.interpolate_pose(p, 0.5, interp, detail)['lateral'], 0.4, places=6)


class OrbitGeometry(unittest.TestCase):
    def test_truck_is_a_pure_translation(self):
        """Com mira da fonte a lente não gira: olho e alvo andam juntos para o lado."""
        flat = dw.orbit_pose(0, 0, 1, (0, 0, 2), (0, 0, 2))
        side = dw.orbit_pose(0, 0, 1, (0, 0, 2), (0, 0, 2), lateral=0.5)
        self.assertTrue(np.allclose(flat[:3, :3], side[:3, :3]))      # mesma orientação
        self.assertAlmostEqual(side[0, 3] - flat[0, 3], 1.0)           # +x é a direita no OpenCV
        self.assertAlmostEqual(side[1, 3], 0.0)
        self.assertAlmostEqual(side[2, 3], 0.0)

    def test_truck_follows_the_rotated_camera_axis(self):
        """Com a câmera girada, 'para o lado' é o lado DELA, não o eixo do mundo."""
        side = dw.orbit_pose(90, 0, 1, (0, 0, 2), (0, 0, 2), lateral=0.5)
        base = dw.orbit_pose(90, 0, 1, (0, 0, 2), (0, 0, 2))
        delta = side[:3, 3] - base[:3, 3]
        self.assertAlmostEqual(float(np.linalg.norm(delta)), 1.0, places=6)
        self.assertAlmostEqual(float(delta[2]), 1.0, places=6)         # virou para +z
        self.assertAlmostEqual(float(delta[0]), 0.0, places=6)

    def test_lateral_is_not_azimuth(self):
        """Órbita mantém a distância ao pivô; travelling não."""
        pivot = np.array([0.0, 0.0, 2.0])
        truck = dw.orbit_pose(0, 0, 1, pivot, (0, 0, 2), lateral=0.5)
        orbit = dw.orbit_pose(30, 0, 1, pivot, (0, 0, 2))
        self.assertGreater(float(np.linalg.norm(truck[:3, 3] - pivot)), 2.05)
        self.assertAlmostEqual(float(np.linalg.norm(orbit[:3, 3] - pivot)), 2.0, places=6)

    def test_height_and_lateral_compose(self):
        both = dw.orbit_pose(0, 0, 1, (0, 0, 2), (0, 0, 2), height=0.25, lateral=0.5)
        self.assertAlmostEqual(both[0, 3], 1.0)
        self.assertAlmostEqual(both[1, 3], -0.5)

    def test_crane_with_pivot_aim_pans(self):
        side = dw.orbit_pose(0, 0, 1, (0, 0, 2), None, lateral=0.5)
        self.assertGreater(side[0, 3], 0)
        self.assertLess(side[0, 2], -0.01)                             # e girou para olhar o pivô


class NodeIntegration(unittest.TestCase):
    def run_node(self, trajectory, **kw):
        args = dict(camera_trajectory=trajectory, profile='124 frames (~5.17s)', interpolation='linear')
        args.update(kw)
        out = editor.H3Camera().run(**args)
        return out['result'] if isinstance(out, dict) else out

    def test_prompt_describes_a_truck(self):
        r = self.run_node(path((0, 0, 0, 1, 0, 0), (1, 0, 0, 1, 0, -0.4)))
        self.assertIn('TRACK the CAMERA sideways to its LEFT', r[0])
        self.assertIn('truck, not an orbit', r[0])
        self.assertIn('Lateral is a straight sideways camera translation', r[0])

    def test_rejects_out_of_range_and_nonzero_first_keyframe(self):
        with self.assertRaises(ValueError):
            self.run_node(path((0, 0, 0, 1, 0, 0), (1, 0, 0, 1, 0, 9)))
        with self.assertRaises(ValueError):
            self.run_node(path((0, 0, 0, 1, 0, 0.2), (1, 0, 0, 1, 0, 0)))

    def test_loop_closure_needs_lateral_back_home(self):
        img = np.zeros((1, 64, 64, 3), dtype=np.float32)
        home = self.run_node(path((0, 0, 0, 1, 0, 0), (1, 360, 0, 1, 0, 0)), reference_image=img)
        away = self.run_node(path((0, 0, 0, 1, 0, 0), (1, 360, 0, 1, 0, 0.5)), reference_image=img)
        self.assertIn('<Picture 2>', home[0])
        self.assertNotIn('<Picture 2>', away[0])

    def test_warp_follows_the_truck(self):
        rng = np.random.default_rng(0)
        img = rng.random((1, 90, 160, 3)).astype(np.float32)
        depth = np.repeat(np.linspace(0.2, 0.9, 90)[None, :, None, None].repeat(160, 2), 3, -1).astype(np.float32)
        flat = self.run_node(path((0, 0, 0, 1, 0, 0), (1, 0, 0, 1, 0, 0)), reference_image=img, depth=depth,
                             depth_animation='Depth Warp', warp_length=73)
        side = self.run_node(path((0, 0, 0, 1, 0, 0), (1, 0, 0, 1, 0, 0.5)), reference_image=img, depth=depth,
                             depth_animation='Depth Warp', warp_length=73)
        self.assertTrue(np.allclose(flat[8][0], side[8][0]))           # frame 1 continua a fonte
        self.assertFalse(np.allclose(flat[8][-1], side[8][-1]))
        holes = side[9][-1]
        self.assertGreater(float(holes[:, -10:].mean()), float(holes[:, :10].mean()))  # buraco à direita


if __name__ == '__main__':
    unittest.main()
