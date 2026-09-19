from .experimental import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# PT: v31 - nodes do Meridian. Falham so se o ComfyUI nao tiver os nodes nativos do H3.
# EN: v31 - Meridian nodes. They only fail if ComfyUI lacks the native H3 nodes.
try:
    from .meridian_nodes import NODE_CLASS_MAPPINGS as _MERIDIAN, NODE_DISPLAY_NAME_MAPPINGS as _MERIDIAN_NAMES
    NODE_CLASS_MAPPINGS.update(_MERIDIAN)
    NODE_DISPLAY_NAME_MAPPINGS.update(_MERIDIAN_NAMES)
except Exception as error:  # pragma: no cover
    import logging
    logging.warning(f'[bruxosdovfx] nodes do Meridian nao carregaram / Meridian nodes did not load: {error}')
from .banner import print_banner

# PT: conta so os nodes visiveis; os alias depreciados nao entram na contagem.
# EN: counts only the visible nodes; deprecated aliases are left out.
print_banner(len({c for c in NODE_CLASS_MAPPINGS.values() if not getattr(c, 'DEPRECATED', False)}))

WEB_DIRECTORY = './web'
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']
