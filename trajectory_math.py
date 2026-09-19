"""Camera interpolation shared with the HUD / Interpolação compartilhada com o HUD.

Angles stay unwrapped: 0 -> 360 is a full turn / Ângulos mantêm voltas completas.
"""
import math

AXES = ('azimuth', 'elevation', 'distance', 'height')
# height: deslocamento vertical da camera em multiplos do raio inicial (grua/boom). Elevation gira em
# torno do alvo; height sobe e desce sem girar. / height: vertical camera offset in units of the starting
# radius (boom). Elevation orbits the target; height rises and falls without orbiting.
DEFAULTS = {'azimuth': 0.0, 'elevation': 0.0, 'distance': 1.0, 'height': 0.0}


def axis(point, name):
    """Trajetorias antigas nao tem height / older paths have no height."""
    value = point.get(name)
    return float(DEFAULTS[name] if value is None else value)


def _validate(path):
    if not path:
        raise ValueError('Empty camera path / Trajetória vazia.')
    previous = -math.inf
    for point in path:
        if not math.isfinite(point['time']) or not all(math.isfinite(axis(point, k)) for k in AXES):
            raise ValueError('Non-finite camera value / Valor de câmera não finito.')
        if point['time'] <= previous:
            raise ValueError('Times must increase / Tempos devem ser crescentes.')
        previous = point['time']


def _slope(path, index, name):
    """Monotone PCHIP slope; stop at endpoints, holds and reversals / Tangente sem ultrapassagem."""
    if index == 0 or index == len(path) - 1:
        return 0.0
    left, center, right = path[index - 1:index + 2]
    h0 = center['time'] - left['time']
    h1 = right['time'] - center['time']
    d0 = (axis(center, name) - axis(left, name)) / h0
    d1 = (axis(right, name) - axis(center, name)) / h1
    if d0 == 0 or d1 == 0 or (d0 > 0) != (d1 > 0):
        return 0.0
    w0, w1 = 2 * h1 + h0, h1 + 2 * h0
    return (w0 + w1) / (w0 / d0 + w1 / d1)


def interpolate_pose(path, time, interpolation='smooth', detail='v15 baseline'):
    """Sample raw signed angles/radius / Amostra ângulos com sinal e raio.

    baseline: smoothstep per segment / suavização em cada trecho.
    extended contracts: monotone cubic per axis / cúbica monotônica por eixo.
    linear: no easing, independent of detail / sem suavização, em qualquer modo.
    """
    _validate(path)
    if not math.isfinite(time):
        raise ValueError('Time must be finite / Tempo deve ser finito.')
    if time <= path[0]['time']:
        return {name: axis(path[0], name) for name in AXES}
    if time >= path[-1]['time']:
        return {name: axis(path[-1], name) for name in AXES}
    for index, (left, right) in enumerate(zip(path, path[1:])):
        if time <= right['time']:
            h = right['time'] - left['time']
            u = (time - left['time']) / h
            if interpolation != 'smooth':
                return {name: axis(left, name) + (axis(right, name) - axis(left, name)) * u for name in AXES}
            if detail != 'extended contracts':
                ease = u * u * (3 - 2 * u)
                return {name: axis(left, name) + (axis(right, name) - axis(left, name)) * ease for name in AXES}
            h00 = 2*u**3 - 3*u**2 + 1
            h10 = u**3 - 2*u**2 + u
            h01 = -2*u**3 + 3*u**2
            h11 = u**3 - u**2
            pose = {}
            for name in AXES:
                a, b = axis(left, name), axis(right, name)
                value = (h00 * a + h10 * h * _slope(path, index, name)
                         + h01 * b + h11 * h * _slope(path, index + 1, name))
                # Protect tiny floating point excursions / Protege contra erro de arredondamento.
                pose[name] = min(max(value, min(a, b)), max(a, b))
            return pose
