import importlib,sys,types,json,unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
m=types.ModuleType('integration');m.__path__=[str(root)];sys.modules['integration']=m
editor=importlib.import_module('integration.experimental')
compose=importlib.import_module('integration.prompt_compose')
class IntegrationTests(unittest.TestCase):
 def result(self,**kwargs):
  args=dict(camera_trajectory=json.dumps([dict(time=0,azimuth=0,elevation=0,distance=1),dict(time=.5,azimuth=360,elevation=0,distance=1),dict(time=1,azimuth=360,elevation=0,distance=1)]),profile='124 frames (~5.17s)',interpolation='smooth',instruction='Only a purple dancer.',subject_box='[L=0.2, T=0.1, W=0.3, H=0.7]')
  args.update(kwargs);return editor.H3Camera().run(**args)
 def test_camera_neutral_and_calibrated(self):
  r=self.result();self.assertEqual(len(r),10);text=r[7]
  for forbidden in ['purple dancer','<Picture','<Video','frozen','remain rigid','subject animation','Silence']:
   self.assertNotIn(forbidden,text)
  self.assertIn('-360',text);self.assertIn('scene action continues',text);self.assertIn('[L=0.2',text)
  self.assertEqual(editor.H3Camera.RETURN_NAMES[7],'camera_prompt')
 def test_scene_exact_prefix_and_bypass(self):
  scene='  A dancer walks.\nFire burns.  ';cam=self.result()[7];node=compose.CameraPromptCompose()
  combined=node.compose(scene,cam)[0];self.assertTrue(combined.startswith(scene+'\n\n'))
  self.assertEqual(node.compose(scene,cam,False)[0],scene)
  self.assertEqual(node.compose(combined,cam)[0],combined)
  self.assertEqual(node.compose(scene,' ')[0],scene)
 def test_compact_node_hides_the_advanced_widgets(self):
  data=editor.H3Camera.INPUT_TYPES()
  visible=[k for g in ('required','optional') for k,v in data[g].items()
           if (isinstance(v[0],list) or v[0] in ('STRING','INT','FLOAT','BOOLEAN')) and not (len(v)>1 and v[1].get('advanced'))]
  self.assertEqual(visible,['camera_trajectory','profile','interpolation','frame_mode','source_fps','ui_language','depth_animation','warp_length'])
  self.assertNotIn('instruction',data['required'])
  self.assertNotIn('experiment_mode',data['optional'])
  self.assertIn('中文',data['optional']['ui_language'][0])
 def test_registration(self):
  self.assertIs(editor.NODE_CLASS_MAPPINGS['BruxosH3CameraPromptCompose'],compose.CameraPromptCompose)
if __name__=='__main__':unittest.main()
