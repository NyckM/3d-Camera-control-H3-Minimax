import json,sys,types,importlib,unittest
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
m=types.ModuleType('guide_test');m.__path__=[str(root)];sys.modules['guide_test']=m
g=importlib.import_module('guide_test.guide_render');editor=importlib.import_module('guide_test.experimental')
def plan():
 path=[dict(time=0,azimuth=0,elevation=0,distance=1),dict(time=.5,azimuth=180,elevation=0,distance=1),dict(time=1,azimuth=360,elevation=0,distance=1)]
 result=editor.H3Camera().run(json.dumps(path),'124 frames (~5.17s)','linear','A person waves.')
 return g.parse_plan(result[2])
class Tests(unittest.TestCase):
 def test_render_shape_and_loop(self):
  p,n,fps=plan();frames=g.render_sequence(p,64,64,n,fps,'mannequin','markers')
  self.assertEqual(frames.shape,(124,64,64,3));self.assertEqual(frames.dtype,np.float32)
  self.assertTrue(np.isfinite(frames).all());self.assertTrue((frames>=0).all() and (frames<=1).all())
  np.testing.assert_allclose(frames[0],frames[-1],atol=1e-6)
  self.assertGreater(np.abs(frames[0]-frames[31]).sum(),10)
 def test_limits_and_cancel(self):
  p,n,fps=plan()
  with self.assertRaises(ValueError):g.render_sequence(p,1024,1024,n,fps,'ball','plain')
  def cancel(n):raise InterruptedError()
  with self.assertRaises(InterruptedError):g.render_sequence(p,64,64,n,fps,'ball','plain',cancel)
 def test_poles_and_closeups(self):
  for elevation in [-89,0,89]:
   for distance in [.1,1,4]:
    pixels=g.render_frame(dict(azimuth=720,elevation=elevation,distance=distance),64,64,'ball','plain')
    self.assertTrue(np.isfinite(pixels).all())
 def test_input_and_holds(self):
  p,n,fps=plan();p['runtime_task']='directed | new camera angle'
  with self.assertRaises(ValueError):g.parse_plan(json.dumps(p))
  with self.assertRaises(ValueError):g.parse_plan('[]')
 def test_node_with_comfy_doubles(self):
  # Validate the wrapper wiring; these are not real Torch/ComfyUI integration tests.
  saved={name:sys.modules.get(name) for name in ['torch','comfy','comfy.utils','comfy.model_management']}
  try:
   torch=types.ModuleType('torch');torch.from_numpy=lambda x:x;sys.modules['torch']=torch
   sys.modules['comfy']=types.ModuleType('comfy');utils=types.ModuleType('comfy.utils')
   class Bar:
    def __init__(self,n):pass
    def update_absolute(self,n):pass
   utils.ProgressBar=Bar;sys.modules['comfy.utils']=utils
   management=types.ModuleType('comfy.model_management');management.throw_exception_if_processing_interrupted=lambda:None;sys.modules['comfy.model_management']=management
   p,_,_=plan();r=g.CameraGuideRender().render(json.dumps(p),64,64,video_reference_index=2)
   self.assertEqual(r[0].shape[0],r[2]);self.assertEqual(r[1],24);self.assertIn('<Video 2>',r[3]);self.assertIn('-360',r[3]);self.assertNotIn('A person waves.',r[3])
  finally:
   for name,value in saved.items():
    if value is None:sys.modules.pop(name,None)
    else:sys.modules[name]=value
if __name__=='__main__':unittest.main()
