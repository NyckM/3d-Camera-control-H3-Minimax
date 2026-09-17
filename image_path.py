"""PT: Caminho de camera sobre a imagem. EN: Camera path over the image."""

import json

PADRAO = json.dumps([
    {'x': 0.30, 'y': 0.75, 'label': '', 'framing': 0.55},
    {'x': 0.50, 'y': 0.45, 'label': '', 'framing': 0.40},
    {'x': 0.62, 'y': 0.22, 'label': '', 'framing': 0.28},
])

CURVAS = ['ease-in-out', 'linear']

AJUDA = {
    'waypoints': (
        'Os pontos do caminho em JSON, na ordem em que a câmera passa por eles. O painel abaixo escreve isso '
        'quando você clica na imagem. Cada ponto tem x e y em fração do quadro (0 a 1, origem no canto superior '
        'esquerdo), um label opcional e framing, que é o quanto do quadro a câmera enquadra ali: valor menor é um '
        'plano mais fechado. São de 2 a 12 pontos.',
        'The path points as JSON, in the order the camera visits them. The panel below writes this when you click '
        'on the image. Each point has x and y as a fraction of the frame (0 to 1, origin at the top-left), an '
        'optional label and framing, which is how much of the frame the camera holds there: a smaller value is a '
        'tighter shot. Between 2 and 12 points.'),
    'duration_s': (
        'Quanto tempo a câmera leva para percorrer o caminho inteiro, em segundos. O tempo é repartido entre os '
        'trechos pela distância de cada um, então trechos longos levam mais tempo e a velocidade fica constante.',
        'How long the camera takes to travel the whole path, in seconds. The time is split between segments by '
        'their length, so longer segments take longer and the speed stays constant.'),
    'speed_curve': (
        'ease-in-out arranca e freia suave nas pontas do movimento. linear mantém uma única velocidade do primeiro '
        'ao último ponto, o que é mais previsível para medir um teste.',
        'ease-in-out accelerates and brakes gently at the ends of the move. linear holds one single speed from the '
        'first point to the last, which is more predictable when measuring a test.'),
    'hold_end_s': (
        'Segundos parados no último ponto, depois de chegar. Serve para o plano final respirar antes de cortar. '
        'Zero significa que a câmera ainda está em movimento no último frame.',
        'Seconds held still on the last point after arriving. It lets the final framing breathe before a cut. Zero '
        'means the camera is still moving on the last frame.'),
    'instruction': (
        'Texto seu, acrescentado uma vez no fim do prompt. Use para o que o node não sabe: o cenário, a luz, o '
        'estilo. Não repita o caminho nem os tempos, que já saem escritos.',
        'Your own text, added once at the end of the prompt. Use it for what the node does not know: the location, '
        'the lighting, the style. Do not repeat the path or the timings, which are already written out.'),
    'reference_image': (
        'Ligue a mesma imagem que vai para a geração. Ela aparece no painel e você clica em cima para marcar os '
        'pontos. A proporção real dela também entra no prompt.',
        'Connect the same image you feed to the generation. It shows in the panel and you click on it to mark the '
        'points. Its real aspect ratio also goes into the prompt.'),
}


def ajuda(nome):
    pt, en = AJUDA[nome]
    return 'PT: ' + pt + '\nEN: ' + en


def _limita(valor, minimo, maximo):
    return max(minimo, min(maximo, float(valor)))


def valida_pontos(bruto):
    """PT: Le e confere os pontos. EN: Reads and checks the points."""
    try:
        pontos = json.loads(bruto)
    except (TypeError, ValueError) as erro:
        raise ValueError('waypoints precisa ser um array JSON. / waypoints must be a JSON array.') from erro
    if not isinstance(pontos, list) or not 2 <= len(pontos) <= 12:
        raise ValueError('Use de 2 a 12 pontos. / Use between 2 and 12 points.')
    limpos = []
    for item in pontos:
        if not isinstance(item, dict):
            raise ValueError('Cada ponto precisa ser um objeto. / Each point must be an object.')
        limpos.append({
            'x': _limita(item.get('x', 0.5), 0.0, 1.0),
            'y': _limita(item.get('y', 0.5), 0.0, 1.0),
            'framing': _limita(item.get('framing', 0.4), 0.05, 1.0),
            'label': str(item.get('label', '') or '').strip()[:60],
        })
    return limpos


def caixa(ponto, aspecto=None):
    """PT: A regiao que a camera enquadra no ponto. EN: The region the camera frames at the point.

    O framing e a fracao da LARGURA; a altura vem da proporcao do quadro para a caixa nao
    ficar esticada quando a imagem nao e 16:9.
    """
    largura = ponto['framing']
    altura = largura * (aspecto or 16 / 9)
    esquerda = _limita(ponto['x'] - largura / 2, 0.0, 1.0)
    topo = _limita(ponto['y'] - altura / 2, 0.0, 1.0)
    largura = _limita(largura, 0.02, 1.0 - esquerda)
    altura = _limita(altura, 0.02, 1.0 - topo)
    return dict(L=round(esquerda, 3), T=round(topo, 3), W=round(largura, 3), H=round(altura, 3))


def formata(caixa_dict):
    return f"[L={caixa_dict['L']:.3f},T={caixa_dict['T']:.3f},W={caixa_dict['W']:.3f},H={caixa_dict['H']:.3f}]"


def _nome(ponto, indice):
    return ponto['label'] or f'point {indice}'


def _sentido(a, b):
    partes = []
    dx, dy = b['x'] - a['x'], b['y'] - a['y']
    if abs(dx) >= 0.04:
        partes.append('right' if dx > 0 else 'left')
    if abs(dy) >= 0.04:
        partes.append('down' if dy > 0 else 'up')
    movimento = (' and '.join(partes) + ' across the frame') if partes else 'barely at all'
    if b['framing'] < a['framing'] - 0.02:
        movimento += ', tightening as it goes'
    elif b['framing'] > a['framing'] + 0.02:
        movimento += ', widening as it goes'
    return movimento


def constroi_prompt(pontos, duracao, curva, hold, instrucao, aspecto=None, rotulo_aspecto='16:9'):
    caixas = [caixa(p, aspecto) for p in pontos]
    distancias = [max(1e-6, ((b['x'] - a['x']) ** 2 + (b['y'] - a['y']) ** 2) ** 0.5)
                  for a, b in zip(pontos, pontos[1:])]
    total = sum(distancias)
    linhas, relogio = [], 0.0
    for indice, (a, b) in enumerate(zip(pontos, pontos[1:]), start=1):
        # O tempo e repartido pela distancia, senao um trecho curto e um longo levariam o
        # mesmo tempo e a camera aceleraria sozinha no meio do caminho.
        duracao_trecho = duracao * distancias[indice - 1] / total
        inicio, fim = relogio, relogio + duracao_trecho
        relogio = fim
        curva_trecho = ('ease-in' if indice == 1 else 'ease-out' if indice == len(pontos) - 1 else 'linear') \
            if curva == 'ease-in-out' else 'linear'
        linhas.append(
            f'[{inicio:.2f}s-{fim:.2f}s] glide the framing from {_nome(a, indice)} at {formata(caixas[indice - 1])} '
            f'to {_nome(b, indice + 1)} at {formata(caixas[indice])}, moving {_sentido(a, b)}; '
            f'speed_curve {curva_trecho}')
    if hold > 1e-3:
        linhas.append(f'[{relogio:.2f}s-{relogio + hold:.2f}s] hold on {_nome(pontos[-1], len(pontos))} at '
                      f'{formata(caixas[-1])}, camera fully stopped')
    corpo = [
        f'Shot type: one continuous camera move that travels along a path across the reference frame, '
        f'{rotulo_aspecto}, {duracao + hold:.2f}s at 24 fps, no cuts.',
        'Subject: everything in the reference first frame keeps its identity, pose, materials, lighting and '
        'position. Only the framing travels along the path below.',
        f'camera_focus: {" -> ".join(formata(c) for c in caixas)}',
        'The camera_focus boxes are where the camera looks at each moment, in order. Between two of them the '
        'framing glides continuously: it never cuts, never jumps and never skips a point.',
        f'Path in order: {" -> ".join(_nome(p, i) for i, p in enumerate(pontos, start=1))}.',
        'Timing:',
        *linhas,
        'Legibility: keep the picture sharp and readable at every point; camera roll stays zero and the framing '
        'stays level. Natural motion blur is fine; never whole-frame blur.',
        'Hidden-reference rule: the coordinate boxes, point names and timings are direction only. The final picture '
        'must not contain visible dots, arrows, route lines, numbers, boxes or annotation text.',
        'Final picture: only the real scene of the reference frame.',
        f'Additional direction: {instrucao.strip() or "preserve the source scene."}',
    ]
    return '\n'.join(corpo)


class ImagePath:
    DESCRIPTION = (
        'PT: Marque pontos em cima da sua imagem e o node escreve um movimento de câmera que percorre esses '
        'pontos, em coordenadas [L,T,W,H]. É um travelling em espaço de tela, diferente da órbita 3D do Camera H3: '
        'aqui a câmera desliza pelo quadro em vez de girar em torno de um alvo. Compila prompt, não embedding.\n'
        'EN: Mark points over your image and the node writes a camera move that travels through them, in [L,T,W,H] '
        'coordinates. This is a screen-space travelling move, unlike the 3D orbit of Camera H3: here the framing '
        'glides across the frame instead of circling a target. It compiles a prompt, not an embedding.')
    CATEGORY = 'bruxosdovfx/Camera H3'
    FUNCTION = 'run'
    RETURN_TYPES = ('STRING', 'STRING')
    RETURN_NAMES = ('camera_prompt', 'waypoints_json')
    OUTPUT_TOOLTIPS = (
        'PT: O movimento escrito em coordenadas, pronto para o prompt da geração. Use no lugar da parte de câmera '
        'do seu prompt, mantendo a sua descrição de cena.\n'
        'EN: The move written in coordinates, ready for the generation prompt. Use it in place of the camera part '
        'of your prompt, keeping your own scene description.',
        'PT: Os pontos conferidos e normalizados, em JSON. Útil para salvar um caminho e reaproveitar depois.\n'
        'EN: The checked and normalised points, as JSON. Useful to save a path and reuse it later.')

    @classmethod
    def INPUT_TYPES(cls):
        return {
            'required': {
                'waypoints': ('STRING', {'default': PADRAO, 'multiline': True, 'tooltip': ajuda('waypoints')}),
                'duration_s': ('FLOAT', {'default': 5.0, 'min': 0.5, 'max': 60.0, 'step': 0.1,
                                         'tooltip': ajuda('duration_s')}),
                'speed_curve': (CURVAS, {'default': 'ease-in-out', 'tooltip': ajuda('speed_curve')}),
                'hold_end_s': ('FLOAT', {'default': 0.0, 'min': 0.0, 'max': 10.0, 'step': 0.1,
                                         'tooltip': ajuda('hold_end_s')}),
                'instruction': ('STRING', {'default': '', 'multiline': True, 'tooltip': ajuda('instruction')}),
            },
            'optional': {
                'reference_image': ('IMAGE', {'tooltip': ajuda('reference_image')}),
            },
        }

    def run(self, waypoints, duration_s, speed_curve, hold_end_s, instruction, reference_image=None):
        pontos = valida_pontos(waypoints)
        aspecto, rotulo = None, '16:9'
        forma = getattr(reference_image, 'shape', None)
        if forma is not None and len(forma) >= 4 and int(forma[1]) > 0:
            aspecto = int(forma[2]) / int(forma[1])
            rotulo = f'{aspecto:.2f}:1'
        prompt = constroi_prompt(pontos, float(duration_s), speed_curve, float(hold_end_s),
                                 instruction, aspecto, rotulo)
        return (prompt, json.dumps(pontos, ensure_ascii=False, indent=2))


NODE_CLASS_MAPPINGS = {'BruxosH3ImagePath': ImagePath}
NODE_DISPLAY_NAME_MAPPINGS = {'BruxosH3ImagePath': 'bruxosdovfx • H3 Image Path'}
