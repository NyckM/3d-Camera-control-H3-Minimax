import importlib, sys, types, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def package(name,path):
    m=types.ModuleType(name);m.__path__=[str(path)];sys.modules[name]=m
    return importlib.import_module(name+'.experimental')
new=package('v23',ROOT)
class Frames:
    def __init__(self,n=1):self.shape=(n,64,96,3)
    def __getitem__(self,key):return Frames(len(key) if isinstance(key,list) else len(range(self.shape[0])[key]))
class Tests(unittest.TestCase):
    def run_editor(self,**kwargs):
        args=dict(camera_trajectory=json.dumps([dict(time=0,azimuth=0,elevation=0,distance=1),dict(time=.7,azimuth=360,elevation=0,distance=1),dict(time=1,azimuth=360,elevation=0,distance=1)]),profile='124 frames (~5.17s)',interpolation='smooth',instruction='The dancer walks forward and raises both arms.',reference_image=Frames())
        args.update(kwargs);return new.H3Camera().run(**args)
    def test_modes_and_formats(self):
        for mode in ['Action Frame','Motion Frame']:
            for fmt in ['coordinate only','coordinate + H3 sections','compact JSON','compact JSON (no boxes)']:
                with self.subTest(mode=mode,fmt=fmt):
                    r=self.run_editor(frame_mode=mode,reference_image=Frames(72 if mode=='Motion Frame' else 1),minimax_format=fmt)
                    self.assertFalse(r[1]['coverage_loop_closure'])
                    for text in [r[0],r[4]]:
                        self.assertEqual(text.count('The dancer walks forward and raises both arms.'),1)
                        for forbidden in ['stays stationary','remain rigid','subject animation,','Freeze the captured','fixed orbit target','<Picture 2>']:
                            self.assertNotIn(forbidden,text)
                        self.assertIn('<Video 1>' if mode=='Motion Frame' else '<Picture 1>',text)
                    if fmt.startswith('compact JSON'):
                        data=json.loads(r[4]);self.assertIn('model_path',data);self.assertNotIn('path',data)
    def test_freeze_default(self):
        self.assertEqual(new.H3Camera.INPUT_TYPES()['optional']['frame_mode'][1]['default'],'Freeze Frame')
        r=self.run_editor();self.assertTrue(r[1]['coverage_loop_closure']);self.assertIn('remain rigid',r[0])
    def test_action_requirements(self):
        for kw in [dict(reference_image=None),dict(instruction=' '),dict(runtime_task='directed | new camera angle')]:
            with self.assertRaises(ValueError):self.run_editor(frame_mode='Action Frame',**kw)
    def test_motion_requires_sequence(self):
        with self.assertRaises(ValueError):self.run_editor(frame_mode='Motion Frame')
    def test_user_text_unchanged(self):
        text='The subject itself stays stationary while waving.'
        r=self.run_editor(frame_mode='Action Frame',instruction=text)
        self.assertIn(text,r[4])
if __name__=='__main__':unittest.main()
