"""v32: o que o node declara é exatamente o que o run() aceita.

Esta é a checagem que faltava quando o widget instruction saiu: o ComfyUI chama run(**inputs)
só com as entradas declaradas em INPUT_TYPES, então qualquer parâmetro obrigatório fora dessa
lista derruba a execução.

python -B tests/test_v32_contract.py
"""
import importlib, inspect, sys, types, unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1]
pkg = types.ModuleType('integration'); pkg.__path__ = [str(root)]; sys.modules['integration'] = pkg
editor = importlib.import_module('integration.experimental')


class Contract(unittest.TestCase):
    def nodes(self):
        for name, cls in editor.NODE_CLASS_MAPPINGS.items():
            yield name, cls

    def test_every_node_runs_with_only_its_declared_inputs(self):
        for name, cls in self.nodes():
            with self.subTest(node=name):
                data = cls.INPUT_TYPES()
                declared = set(data.get('required', {})) | set(data.get('optional', {})) | set(data.get('hidden', {}))
                signature = inspect.signature(getattr(cls, cls.FUNCTION))
                required = {p.name for p in signature.parameters.values()
                            if p.name != 'self' and p.default is inspect.Parameter.empty
                            and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)}
                missing = required - declared
                self.assertEqual(missing, set(), f'{name}.{cls.FUNCTION} exige {missing}, que não está em INPUT_TYPES')
                takes_kwargs = any(p.kind is p.VAR_KEYWORD for p in signature.parameters.values())
                if not takes_kwargs:
                    accepted = {p.name for p in signature.parameters.values() if p.name != 'self'}
                    self.assertEqual(declared - accepted, set(), f'{name} declara entradas que {cls.FUNCTION} não aceita')

    def test_camera_runs_the_way_comfyui_calls_it(self):
        import json
        data = editor.H3Camera.INPUT_TYPES()
        values = {}
        for group in ('required', 'optional'):
            for key, spec in data[group].items():
                kind, options = spec[0], (spec[1] if len(spec) > 1 else {})
                if isinstance(kind, list):
                    values[key] = options.get('default', kind[0])
                elif kind in ('STRING', 'INT', 'FLOAT', 'BOOLEAN'):
                    values[key] = options.get('default', '' if kind == 'STRING' else 0)
        values['camera_trajectory'] = json.dumps([dict(time=0, azimuth=0, elevation=0, distance=1, height=0),
                                                  dict(time=1, azimuth=20, elevation=5, distance=1, height=-0.2)])
        result = editor.H3Camera().run(**values)      # exatamente como o ComfyUI chama
        self.assertEqual(len(result), 10)
        self.assertIn('CRANE', result[0])


    def test_migration_layouts_cover_the_node(self):
        """A migração lê valores antigos por posição. Cada layout histórico precisa ser um
        prefixo/subconjunto coerente do node de hoje, e nenhum campo atual pode faltar no mais recente."""
        import re
        source = (root / 'web' / 'legacy-workflow.js').read_text(encoding='utf-8')
        removed = [name.strip().strip("'") for name in re.search(r'REMOVED = \[(.*?)\];', source).group(1).split(',')]
        data = editor.H3Camera.INPUT_TYPES()
        current = [key for group in ('required', 'optional') for key, spec in data[group].items()
                   if isinstance(spec[0], list) or spec[0] in ('STRING', 'INT', 'FLOAT', 'BOOLEAN')]
        # o layout mais recente (V31_SLIM) mais o que saiu = tudo que o node tem hoje
        v31 = [name.strip().strip("'") for name in
               re.search(r"const V31 = \[\.\.\.V29, (.*?)\];", source, re.S).group(1).replace('\n', '').split(',')
               if name.strip() and 'WARP' not in name and 'OFFSETS' not in name]
        for name in removed:
            self.assertNotIn(name, current, f'{name} voltou ao node: tire da lista REMOVED')
        for name in current:
            self.assertIn(name, source, f'{name} não aparece em nenhum layout da migração')
        self.assertTrue(set(v31).issubset(set(current) | set(removed)))
        # e a trava por nome está exportada
        self.assertIn('export const VALUES_KEY', source)
        self.assertIn('export function packValues', source)
        self.assertIn('export function applyValues', source)

    def test_every_frame_mode_runs(self):
        """Action Frame dependia do instruction, que saiu na v32: agora só pede a imagem."""
        import json
        import numpy as np
        data = editor.H3Camera.INPUT_TYPES()
        base = {}
        for group in ('required', 'optional'):
            for key, spec in data[group].items():
                kind, options = spec[0], (spec[1] if len(spec) > 1 else {})
                if isinstance(kind, list):
                    base[key] = options.get('default', kind[0])
                elif kind in ('STRING', 'INT', 'FLOAT', 'BOOLEAN'):
                    base[key] = options.get('default', '' if kind == 'STRING' else 0)
        base['camera_trajectory'] = json.dumps([dict(time=0, azimuth=0, elevation=0, distance=1, height=0),
                                                dict(time=1, azimuth=20, elevation=0, distance=1, height=0)])
        for mode, frames in (('Freeze Frame', 1), ('Action Frame', 1), ('Motion Frame', 72)):
            with self.subTest(mode=mode):
                values = dict(base, frame_mode=mode, reference_image=np.zeros((frames, 64, 64, 3), dtype=np.float32))
                result = editor.H3Camera().run(**values)
                self.assertEqual(len(result), 10)
                self.assertIn('<Picture 1>' if mode == 'Action Frame' else
                              ('<Video 1>' if mode == 'Motion Frame' else '<Picture 1>'), result[0])
        with self.assertRaises(ValueError):   # Action Frame ainda exige a imagem
            editor.H3Camera().run(**dict(base, frame_mode='Action Frame'))


if __name__ == '__main__':
    unittest.main()
