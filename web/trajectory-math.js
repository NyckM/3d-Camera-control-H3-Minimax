// Signed angles are never normalized during playback / Reprodução preserva voltas e sinais.
export const AXES = ['azimuth', 'elevation', 'distance', 'height'];
export const AXIS_DEFAULTS = {azimuth: 0, elevation: 0, distance: 1, height: 0};
// height: grua. Sobe e desce a câmera sem girar em torno do alvo, em múltiplos do raio inicial.
// height: boom. Raises and lowers the camera without orbiting, in units of the starting radius.
// Trajetórias e presets anteriores à v32 não têm height / paths and presets before v32 have no height.
export const axis = (point, name) => {const value = point[name]; return value == null ? AXIS_DEFAULTS[name] : value;};

function validate(path) {
  if (!Array.isArray(path) || !path.length) throw new Error('Empty camera path / Trajetória vazia.');
  let previous = -Infinity;
  for (const point of path) {
    if (!Number.isFinite(point.time) || !AXES.every(k => Number.isFinite(axis(point, k))))
      throw new Error('Non-finite camera value / Valor de câmera não finito.');
    if (point.time <= previous) throw new Error('Times must increase / Tempos devem ser crescentes.');
    previous = point.time;
  }
}

function slope(path, index, name) {
  if (index === 0 || index === path.length - 1) return 0;
  const [a, b, c] = path.slice(index - 1, index + 2);
  const h0 = b.time - a.time, h1 = c.time - b.time;
  const d0 = (axis(b, name) - axis(a, name)) / h0, d1 = (axis(c, name) - axis(b, name)) / h1;
  if (d0 === 0 || d1 === 0 || Math.sign(d0) !== Math.sign(d1)) return 0;
  const w0 = 2*h1 + h0, w1 = h1 + 2*h0;
  return (w0 + w1) / (w0 / d0 + w1 / d1);
}

// Must match trajectory_math.py / Deve corresponder ao módulo Python.
export function interpolatePose(path, time, interpolation = 'smooth', detail = 'v15 baseline') {
  validate(path);
  if (!Number.isFinite(time)) throw new Error('Time must be finite / Tempo deve ser finito.');
  if (time <= path[0].time) return Object.fromEntries(AXES.map(k => [k, axis(path[0], k)]));
  if (time >= path.at(-1).time) return Object.fromEntries(AXES.map(k => [k, axis(path.at(-1), k)]));
  const rightIndex = path.findIndex(p => p.time >= time);
  const a = path[rightIndex - 1], b = path[rightIndex], h = b.time - a.time;
  const u = (time - a.time) / h;
  if (interpolation !== 'smooth') return Object.fromEntries(AXES.map(k => [k, axis(a, k) + (axis(b, k) - axis(a, k))*u]));
  if (detail !== 'extended contracts') {
    const ease = u*u*(3 - 2*u);
    return Object.fromEntries(AXES.map(k => [k, axis(a, k) + (axis(b, k) - axis(a, k))*ease]));
  }
  const h00 = 2*u**3 - 3*u**2 + 1, h10 = u**3 - 2*u**2 + u;
  const h01 = -2*u**3 + 3*u**2, h11 = u**3 - u**2;
  return Object.fromEntries(AXES.map(k => {
    const pa = axis(a, k), pb = axis(b, k);
    const value = h00*pa + h10*h*slope(path, rightIndex-1, k) + h01*pb + h11*h*slope(path, rightIndex, k);
    return [k, Math.max(Math.min(pa, pb), Math.min(Math.max(pa, pb), value))];
  }));
}

// Integrate the spherical path, not the straight chord (360° must not become zero).
// Integra a trajetória esférica; uma volta de 360° nunca vira distância zero.
export function segmentLength(a, b, referenceRadius = 1) {
  const da = (b.azimuth - a.azimuth) * Math.PI/180;
  const de = (b.elevation - a.elevation) * Math.PI/180;
  const dr = b.distance - a.distance;
  const e0 = a.elevation*Math.PI/180;
  const steps = Math.max(32, Math.min(4096, Math.ceil((Math.abs(da) + Math.abs(de))*20)));
  let length = 0;
  for (let i = 0; i < steps; i++) {
    const u = (i + .5)/steps, r = a.distance + dr*u, e = e0 + de*u;
    length += Math.sqrt(dr*dr + r*r*(de*de + Math.cos(e)**2*da*da))/steps;
  }
  return length/Math.max(Math.abs(referenceRadius), 1e-12);
}

// Equalizes average geometric speed per moving segment. Use linear interpolation for this mode.
// Iguala velocidade geométrica média por trecho móvel. Use interpolação linear neste modo.
// Holds keep their original duration / Pausas mantêm a duração original.
export function uniformTimes(path) {
  validate(path);
  if (path.length < 2) return path.map(p => ({...p}));
  const span = path.at(-1).time - path[0].time;
  const lengths = path.slice(1).map((p, i) => segmentLength(path[i], p, path[0].distance));
  const holds = path.slice(1).map((p, i) => AXES.every(k => p[k] === path[i][k]));
  let held = 0, total = 0;
  lengths.forEach((length, i) => { if (holds[i]) held += path[i+1].time-path[i].time; else total += length; });
  if (total === 0) return path.map(p => ({...p}));
  const available = span - held;
  let time = path[0].time;
  const result = [{...path[0]}];
  lengths.forEach((length, i) => {
    time += holds[i] ? path[i+1].time-path[i].time : available*length/total;
    result.push({...path[i+1], time});
  });
  result.at(-1).time = path.at(-1).time;
  validate(result);
  return result;
}

// Explicitly adds a normalized-time hold while preserving poses / Adiciona pausa preservando poses.
export function addHold(path, side, amount) {
  validate(path);
  if (path.length < 2 || path.length >= 24) throw new Error('Hold requires 2–23 keyframes / Pausa exige 2–23 keyframes.');
  if (path[0].time !== 0) throw new Error('First time must be 0 / Primeiro tempo deve ser 0.');
  if (!['start', 'end'].includes(side)) throw new Error('Choose start or end / Escolha início ou fim.');
  const end = path.at(-1).time;
  if (!Number.isFinite(amount) || amount <= 0 || amount >= end)
    throw new Error('Hold must fit inside the trajectory / Pausa deve caber na trajetória.');
  const scale = (end - amount)/end;
  let result;
  if (side === 'start') {
    result = [{...path[0]}, ...path.map(p => ({...p, time: amount+p.time*scale}))];
  } else {
    result = [...path.map(p => ({...p, time: p.time*scale})), {...path.at(-1)}];
  }
  result[0].time = 0;
  result.at(-1).time = end;
  validate(result);
  return result;
}

export const UNWRAP_LIMITATION = {
  en: 'Shortest-arc assumption for jumps over 180° between angles in [0, 360). Intentional long arcs may change. Full turns and already unwrapped angles are preserved. Review before using.',
  pt: 'Supõe o arco curto em saltos maiores que 180° entre ângulos em [0, 360). Arcos longos intencionais podem mudar. Voltas completas e ângulos já desenrolados são preservados. Revise antes de usar.'
};

// Explicit operation only: no angle repair during loading or interpolation.
// Operação explícita: nunca corrige ângulos automaticamente ao carregar ou reproduzir.
export function unwrapCrossings(path) {
  validate(path);
  const result = [{...path[0]}];
  let offset = 0;
  for (let i = 1; i < path.length; i++) {
    const a = path[i-1].azimuth, b = path[i].azimuth, delta = b - a;
    const wrapped = a >= 0 && a < 360 && b >= 0 && b < 360;
    if (wrapped && Math.abs(delta) > 180 && Math.abs(delta) < 360) offset += delta > 0 ? -360 : 360;
    result.push({...path[i], azimuth: b + offset});
  }
  return result;
}
