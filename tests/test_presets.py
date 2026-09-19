from pathlib import Path
import json,types,sys,importlib
p=Path(__file__).resolve().parents[1]
s=(p/'web/shot-presets.js').read_text(encoding='utf-8');rows=json.loads(s.split('export const SHOT_PRESETS = ',1)[1].split(';\nexport function',1)[0])
m=types.ModuleType('catalog');m.__path__=[str(p.resolve())];sys.modules['catalog']=m
base=importlib.import_module('catalog.camera')
count=0
for row in rows:
 if row['path']:
  base.validate_path(json.dumps(row['path']));count+=1
assert count==9 and len(rows)==18
print('All 9 preset paths accepted by backend; 18 entries classified.')
