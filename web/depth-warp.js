// PT: Prévia ao vivo do Depth Warp na "Visão da câmera". A geometria (pontos, pivô, fx) vem da
// última execução do node; a pose vem da timeline do painel, então arrastar keyframes reprojeta
// na hora. Mesma órbita de depth_warp.py (port do CrossViewWarp, Apache-2.0).
// Com splat 0 bate pixel a pixel com o Python (tests/test_v30_depth.cjs). Com splat > 0 usa
// z-buffer simples: é uma prévia, a saída real vem do Python.
// EN: Live Depth Warp preview inside "Camera view". Geometry (points, pivot, fx) comes from the
// node's last run; the pose comes from the panel timeline, so dragging keyframes reprojects
// immediately. Same orbit as depth_warp.py. Pixel-exact with Python at splat 0; z-buffer at splat > 0.

const rad = v => v * Math.PI / 180;
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const cross = (a, b) => [a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]];
const norm = a => Math.hypot(a[0], a[1], a[2]);
const scale = (a, s) => [a[0]*s, a[1]*s, a[2]*s];
const mul3 = (A, B) => A.map((row, i) => [0, 1, 2].map(j => row[0]*B[0][j] + row[1]*B[1][j] + row[2]*B[2][j]));
const apply3 = (M, v) => M.map(row => row[0]*v[0] + row[1]*v[1] + row[2]*v[2]);

function rotX(a) { const c = Math.cos(a), s = Math.sin(a); return [[1, 0, 0], [0, c, -s], [0, s, c]]; }
function rotY(a) { const c = Math.cos(a), s = Math.sin(a); return [[c, 0, s], [0, 1, 0], [-s, 0, c]]; }

export function lookAt(eye, target) {
  let f = sub(target, eye); f = scale(f, 1 / (norm(f) + 1e-9));
  let right = cross([0, 1, 0], f), rn = norm(right);
  if (rn < 1e-6) { right = cross([0, 0, 1], f); rn = norm(right); }
  right = scale(right, 1 / (rn + 1e-9));
  return { eye, right, down: cross(f, right), forward: f };
}

// +azimuth = câmera para a direita, +elevation = câmera sobe; mesmo sinal do HUD.
export function orbitCamera(pose, pivot, aim = 'source', azSign = 1) {
  const R = mul3(rotY(rad(-pose.azimuth * azSign)), rotX(rad(-pose.elevation)));
  const back = apply3(R, scale(pivot, -1));
  const eye = [pivot[0] + pose.distance*back[0], pivot[1] + pose.distance*back[1], pivot[2] + pose.distance*back[2]];
  let target = aim === 'source' ? [0, 0, norm(pivot)] : pivot;
  // Grua: +y é para baixo no frame OpenCV, então subir a câmera é subtrair em y.
  // Travelling: eixo direito da câmera já girada, o mesmo que o Python usa.
  const radius = norm(pivot), boom = (pose.height || 0) * radius, truck = (pose.lateral || 0) * radius;
  if (boom || truck) {
    const right = apply3(R, [1, 0, 0]);
    const shift = [truck * right[0], -boom + truck * right[1], truck * right[2]];
    eye[0] += shift[0]; eye[1] += shift[1]; eye[2] += shift[2];
    if (aim === 'source') target = [target[0] + shift[0], target[1] + shift[1], target[2] + shift[2]];
  }
  return lookAt(eye, target);
}

// np.round arredonda .5 para o par; Math.round não.
export function roundHalfEven(x) {
  const f = Math.floor(x), d = x - f;
  if (d === 0.5) return f % 2 === 0 ? f : f + 1;
  return Math.round(x);
}

// z: comprimento w*h (NaN = inválido). src: RGB ou RGBA com `channels` por pixel.
export function buildCloud(z, src, w, h, fxNorm, thr = Infinity, channels = 3) {
  const fx = fxNorm * w, keep = [];
  for (let i = 0; i < w*h; i++) { const d = z[i]; if (Number.isFinite(d) && d > 0 && d < thr) keep.push(i); }
  const n = keep.length, X = new Float64Array(n), Y = new Float64Array(n), Z = new Float64Array(n), col = new Uint8Array(n*3);
  keep.forEach((i, k) => {
    const d = z[i], u = i % w, v = (i - u) / w;
    X[k] = (u - w/2) / fx * d; Y[k] = (v - h/2) / fx * d; Z[k] = d;
    col[k*3] = src[i*channels]; col[k*3+1] = src[i*channels+1]; col[k*3+2] = src[i*channels+2];
  });
  return { X, Y, Z, col, n, w, h, fx };
}

// out: RGBA (w*h*4). zbuf: Float64Array(w*h). hole: cor dos buracos (magenta no CrossView, cinza 128 no Meridian).
// Devolve a fração de buracos.
export function renderCloud(cloud, cam, splat, out, zbuf, hole = [255, 0, 255]) {
  const { X, Y, Z, col, n, w, h, fx } = cloud, { eye, right, down, forward } = cam;
  for (let i = 0; i < w*h; i++) { out[i*4] = hole[0]; out[i*4+1] = hole[1]; out[i*4+2] = hole[2]; out[i*4+3] = 255; zbuf[i] = Infinity; }
  for (let k = 0; k < n; k++) {
    const px = X[k] - eye[0], py = Y[k] - eye[1], pz = Z[k] - eye[2];
    const zc = px*forward[0] + py*forward[1] + pz*forward[2];
    if (!(zc > 0)) continue;
    const xc = px*right[0] + py*right[1] + pz*right[2], yc = px*down[0] + py*down[1] + pz*down[2];
    const u = roundHalfEven(xc / zc * fx + w/2), v = roundHalfEven(yc / zc * fx + h/2);
    if (u < -splat || u >= w + splat || v < -splat || v >= h + splat) continue;
    for (let dy = -splat; dy <= splat; dy++) {
      const ty = v + dy; if (ty < 0 || ty >= h) continue;
      for (let dx = -splat; dx <= splat; dx++) {
        const tx = u + dx; if (tx < 0 || tx >= w) continue;
        const t = ty*w + tx;
        if (zc < zbuf[t]) { zbuf[t] = zc; out[t*4] = col[k*3]; out[t*4+1] = col[k*3+1]; out[t*4+2] = col[k*3+2]; }
      }
    }
  }
  let holes = 0; for (let i = 0; i < w*h; i++) if (zbuf[i] === Infinity) holes++;
  return holes / (w*h);
}

// PNG de profundidade: R = byte alto, G = byte baixo, B = 255 inválido.
export function decodeDepth(rgba, w, h, lo, hi) {
  const z = new Float64Array(w*h), span = hi - lo;
  for (let i = 0; i < w*h; i++) z[i] = rgba[i*4+2] > 127 ? NaN : lo + (rgba[i*4]*256 + rgba[i*4+1]) / 65535 * span;
  return z;
}

async function pixels(url) {
  const img = new Image(); img.decoding = 'async'; img.src = url;
  await img.decode();
  const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
  const ctx = c.getContext('2d', { willReadFrequently: true }); ctx.drawImage(img, 0, 0);
  return ctx.getImageData(0, 0, c.width, c.height).data;
}

export async function loadDepthPreview(meta, urlFor) {
  const { w, h } = meta;
  const samples = await Promise.all(meta.samples.map(async sample => {
    const [rgb, zp] = await Promise.all([pixels(urlFor(sample.rgb)), pixels(urlFor(sample.z))]);
    return { t: sample.t, cloud: buildCloud(decodeDepth(zp, w, h, meta.z_lo, meta.z_hi), rgb, w, h, meta.fx_norm, Infinity, 4) };
  }));
  const canvas = document.createElement('canvas'); canvas.width = w; canvas.height = h;
  const ctx = canvas.getContext('2d');
  return { meta, samples, canvas, ctx, image: ctx.createImageData(w, h), zbuf: new Float64Array(w*h),
           splat: Math.max(1, Math.round(meta.splat * w / Math.max(1, meta.source_w))) };
}

export function composePose(pose, meta, offset) {
  const off = offset || { azimuth: 0, elevation: 0, distance: 1 };
  return { azimuth: pose.azimuth * (meta.az_sign || 1) + (off.azimuth || 0), elevation: pose.elevation + (off.elevation || 0),
           distance: pose.distance * (off.distance > 0 ? off.distance : 1), height: pose.height || 0,
           lateral: pose.lateral || 0 };
}

export function drawDepthWarp(canvas, pose, state, playhead = 0, offset = null) {
  const width = canvas.clientWidth || 400, height = canvas.clientHeight || 230, dpr = Math.min(globalThis.devicePixelRatio || 1, 2);
  canvas.width = Math.round(width*dpr); canvas.height = Math.round(height*dpr);
  const ctx = canvas.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.fillStyle = '#10131b'; ctx.fillRect(0, 0, width, height);
  const { meta, samples } = state;
  let sample = samples[0];
  for (const s of samples) if (Math.abs(s.t - playhead) < Math.abs(sample.t - playhead)) sample = s;
  const cam = orbitCamera(composePose(pose, meta, offset), meta.pivot, meta.aim, 1);
  const holes = renderCloud(sample.cloud, cam, state.splat, state.image.data, state.zbuf, meta.hole || [255, 0, 255]);
  state.ctx.putImageData(state.image, 0, 0);
  const aspect = meta.w / meta.h, w = Math.min(width, height*aspect), h = w / aspect, left = (width - w)/2, top = (height - h)/2;
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(state.canvas, left, top, w, h);
  ctx.strokeStyle = '#6c8097'; ctx.strokeRect(left, top, w, h);
  const text = `depth warp · ${Math.round(holes*100)}% holes · ${meta.depth_source}`;
  ctx.font = '10px ui-monospace,monospace';
  ctx.fillStyle = '#000a'; ctx.fillRect(left, top + h - 16, Math.min(w, ctx.measureText(text).width + 10), 16);
  ctx.fillStyle = '#f5d7ff'; ctx.fillText(text, left + 5, top + h - 5);
  return holes;
}
