"""Depth Warp para o Camera H3 / Depth warp for Camera H3.

PT: Reprojeta a imagem (ou a sequencia) de referencia pela profundidade seguindo a trajetoria de
    keyframes do Camera H3 e entrega o video de controle no formato do Viggle Meridian, o fine-tune
    do MiniMax-H3 guiado por render de nuvem de pontos: buracos cinza 128, z-buffer 3x3,
    poda de bordas de profundidade, canvas classe 480 e fx = W/(2 tan(hfov/2)).
EN: Reprojects the reference image (or sequence) through depth along the Camera H3 keyframe path and
    outputs the control video in Viggle Meridian format, the point-cloud-guided MiniMax-H3 fine-tune:
    grey 128 holes, 3x3 z-buffer, depth-edge pruning, 480-class canvas, fx = W/(2 tan(hfov/2)).

NOTICE: a matematica de warp/orbita (reference_warp_frame, look_at, orbit_pose, depth_to_z) e um
port de ComfyUI-CrossViewWarp (github.com/cseti007/ComfyUI-CrossViewWarp, crossview_warp_node.py),
Apache License 2.0, usado tambem pelo renderizador legado da v30. Ver THIRD_PARTY_NOTICES.md.

O renderer rapido (PointCloud.render) produz o mesmo resultado do laco de splat original: em cada
passada de offset o pixel alvo tem um unico pixel-base, entao o "ultimo a escrever" pode ser
resolvido uma vez por pixel-base em vez de 25 vezes por ponto. tests/test_v30_depth.py compara os
dois pixel a pixel.
"""
import json
import logging
import math
import os
import re
import time

import numpy as np

from .trajectory_math import interpolate_pose

ANIMATIONS = ['Off', 'Depth Warp']
LEGACY_FORMAT = 'CrossView (LTX)'   # v30: fora da lista do widget, aceito so em workflows salvos
AIMS = ['source aim', 'look at pivot']
DIRECTIONS = ['panel (geometric)', 'model_path (Guide Render)']
MAGENTA = np.array([255, 0, 255], dtype=np.uint8)
SPLAT = 2
FPS = 24.0
# PT: ~6 GB em float32 RGB. Acima disso o ComfyUI tende a estourar a RAM antes do warp terminar.
# EN: ~6 GB of float32 RGB. Past this ComfyUI tends to run out of RAM before the warp finishes.
PIXEL_BUDGET = 500_000_000
PREVIEW_SIDE = 384
PREVIEW_SAMPLES = 8
PERCENTILE_SAMPLES = 16_000_000
RELATIVE_PIVOT_Z = 1.05


# =============================================================================
# Port literal do CrossViewWarp (Apache-2.0). Mantido para os testes de paridade.
# =============================================================================

def reference_warp_frame(rgb_ref, depth_ref, C_ref, C_tgt, fx_pix, splat, cx, cy):
    """Laco original do CrossViewWarp (fallback NumPy), sem alteracoes de comportamento."""
    H, W = depth_ref.shape
    fy_pix = fx_pix
    u, v = np.meshgrid(np.arange(W), np.arange(H))
    z = depth_ref
    fin = np.isfinite(z) & (z > 0)
    thr = np.percentile(z[fin], 99.5) if fin.any() else 0
    fin = fin & (z < thr)
    Xc = np.stack([(u - W / 2.0) / fx_pix * z, (v - H / 2.0) / fy_pix * z, z], -1).reshape(-1, 3)
    Xw = (C_ref[:3, :3] @ Xc.T).T + C_ref[:3, 3]
    Ci = np.linalg.inv(C_tgt)
    Xd = (Ci[:3, :3] @ Xw.T).T + Ci[:3, 3]
    zt = Xd[:, 2]
    with np.errstate(invalid='ignore', divide='ignore'):
        uf = Xd[:, 0] / zt * fx_pix + cx
        vf = Xd[:, 1] / zt * fy_pix + cy
    ui = np.round(np.nan_to_num(uf, nan=-1e6, posinf=1e6, neginf=-1e6)).astype(int)
    vi = np.round(np.nan_to_num(vf, nan=-1e6, posinf=1e6, neginf=-1e6)).astype(int)
    val = fin.ravel() & (zt > 0)
    order = np.argsort(-zt)
    sel = order[val[order]]
    tu0 = ui[sel]
    tv0 = vi[sel]
    cols = np.ascontiguousarray(rgb_ref.reshape(-1, 3)[sel])
    warp = np.tile(MAGENTA, (H, W, 1))
    flat = warp.reshape(-1, 3)
    for dy in range(-splat, splat + 1):
        for dx in range(-splat, splat + 1):
            tu = tu0 + dx
            tv = tv0 + dy
            ok = (tu >= 0) & (tu < W) & (tv >= 0) & (tv < H)
            flat[tv[ok] * W + tu[ok]] = cols[ok]
    return warp.astype(np.uint8)


def look_at(eye, target, world_down=np.array([0.0, 1.0, 0.0])):
    f = target - eye
    f = f / (np.linalg.norm(f) + 1e-9)
    right = np.cross(world_down, f)
    rn = np.linalg.norm(right)
    if rn < 1e-6:
        # Olhando reto para cima/baixo: sem isso a base colapsa e a inversa falha.
        right = np.cross(np.array([0.0, 0.0, 1.0]), f)
        rn = np.linalg.norm(right)
    right = right / (rn + 1e-9)
    down = np.cross(f, right)
    C = np.eye(4)
    C[:3, 0], C[:3, 1], C[:3, 2], C[:3, 3] = right, down, f, eye
    return C


def rot_x(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def orbit_pose(az_deg, el_deg, dist, pivot, aim=None, height=0.0):
    """+azimuth = camera orbita para a DIREITA, +elevation = camera SOBE (frame OpenCV).

    Mesma convencao do HUD do Camera H3, entao a trajetoria do painel entra sem troca de sinal.
    """
    pivot = np.asarray(pivot, dtype=np.float64)
    R_orbit = rot_y(np.radians(-az_deg)) @ rot_x(np.radians(-el_deg))
    eye = pivot + dist * (R_orbit @ (-pivot))
    target = pivot if aim is None else np.asarray(aim, dtype=np.float64)
    if height:
        # Grua: translacao vertical pura. OpenCV tem +y para baixo, entao subir e subtrair em y.
        # Com mira da fonte o alvo sobe junto (a lente nao gira e o sujeito desce no quadro);
        # com mira no pivo a camera sobe e inclina para continuar olhando o pivo.
        shift = np.array([0.0, -float(height) * float(np.linalg.norm(pivot)), 0.0])
        eye = eye + shift
        if aim is not None:
            target = target + shift
    return look_at(eye, target)


def depth_to_z(d, invert, ratio, lo, hi):
    """Brilho relativo -> z (perto = 1, longe = ratio), com percentis do clipe inteiro."""
    d = d.astype(np.float64)
    if invert:
        d = -d
    dn = np.clip((d - lo) / (hi - lo + 1e-9), 0.0, 1.0)
    r = max(float(ratio), 1.01)
    return 1.0 / (1.0 / r + (1.0 - 1.0 / r) * dn)


# =============================================================================
# Renderer rapido, resultado identico ao laco original
# =============================================================================

class PointCloud:
    """Pontos validos de um frame de referencia, desprojetados uma vez (C_ref = identidade)."""

    def __init__(self, rgb, z, fx):
        z = np.asarray(z, dtype=np.float64)
        H, W = z.shape
        fin = np.isfinite(z) & (z > 0)
        self.thr = float(np.percentile(z[fin], 99.5)) if fin.any() else 0.0
        fin &= z < self.thr
        idx = np.flatnonzero(fin)
        zz = z.ravel()[idx]
        u = (idx % W).astype(np.float64)
        v = (idx // W).astype(np.float64)
        self.X = np.stack([(u - W / 2.0) / fx * zz, (v - H / 2.0) / fx * zz, zz], -1)
        c = np.ascontiguousarray(rgb.reshape(-1, 3)[idx]).astype('<u4')
        self.col = c[:, 0] | (c[:, 1] << 8) | (c[:, 2] << 16)
        self.H, self.W, self.fx = H, W, float(fx)

    def render(self, C_tgt, splat=SPLAT, cx=None, cy=None):
        """-> (warp uint8 [H,W,3], hole bool [H,W])."""
        H, W, fx = self.H, self.W, self.fx
        cx = W / 2.0 if cx is None else cx
        cy = H / 2.0 if cy is None else cy
        magenta = np.uint32(255 | (255 << 16))
        out = np.full(H * W, magenta, dtype='<u4')
        written = np.zeros(H * W, dtype=bool)
        if self.X.shape[0]:
            Ci = np.linalg.inv(C_tgt)
            Xd = (Ci[:3, :3] @ self.X.T).T + Ci[:3, 3]
            zt = Xd[:, 2]
            ok = zt > 0
            with np.errstate(invalid='ignore', divide='ignore', over='ignore'):
                uf = Xd[ok, 0] / zt[ok] * fx + cx
                vf = Xd[ok, 1] / zt[ok] * fx + cy
            # Clip so valores enormes nao estouram o int; nada dentro do quadro muda.
            ui = np.round(np.clip(np.nan_to_num(uf, nan=-1e6, posinf=1e6, neginf=-1e6), -1e6, 1e6)).astype(np.int64)
            vi = np.round(np.clip(np.nan_to_num(vf, nan=-1e6, posinf=1e6, neginf=-1e6), -1e6, 1e6)).astype(np.int64)
            s = int(splat)
            PW, PH = W + 2 * s, H + 2 * s
            bu, bv = ui + s, vi + s
            inb = (bu >= 0) & (bu < PW) & (bv >= 0) & (bv < PH)
            key = bv[inb] * PW + bu[inb]
            depth = zt[ok][inb]
            col = self.col[ok][inb]
            if key.size:
                # Pintor do CrossView: ordem de -z, o ultimo (mais perto) vence em cada pixel.
                # A mesma ordem de -z, reagrupada de forma estavel por pixel-base, deixa o
                # vencedor no fim de cada grupo (mais rapido que lexsort nos testes).
                order = np.argsort(-depth)
                order = order[np.argsort(key[order], kind='stable')]
                ks = key[order]
                last = np.ones(ks.size, dtype=bool)
                last[:-1] = ks[1:] != ks[:-1]
                wk = ks[last]
                wc = col[order][last]
                wu = wk % PW - s
                wv = wk // PW - s
                interior = (wu >= s) & (wu < W - s) & (wv >= s) & (wv < H - s)
                base_i = wv[interior] * W + wu[interior]
                col_i = wc[interior]
                bu_b, bv_b, col_b = wu[~interior], wv[~interior], wc[~interior]
                for dy in range(-s, s + 1):
                    for dx in range(-s, s + 1):
                        target = base_i + (dy * W + dx)
                        out[target] = col_i
                        written[target] = True
                        if bu_b.size:
                            tu = bu_b + dx
                            tv = bv_b + dy
                            good = (tu >= 0) & (tu < W) & (tv >= 0) & (tv < H)
                            t2 = tv[good] * W + tu[good]
                            out[t2] = col_b[good]
                            written[t2] = True
        rgb = out.view(np.uint8).reshape(H, W, 4)[..., :3].copy()
        return rgb, ~written.reshape(H, W)


# =============================================================================
# Entradas: tensores do ComfyUI ou arrays NumPy (testes)
# =============================================================================

def _array(x, dtype=np.float32):
    if hasattr(x, 'detach'):
        x = x.detach().cpu()
        if dtype is bool:
            return x.bool().numpy()
        return x.float().numpy().astype(dtype, copy=False)
    return np.asarray(x).astype(dtype, copy=False)


def _frame_rgb(images, index):
    frame = _array(images[index])
    return (np.clip(frame[..., :3], 0.0, 1.0) * 255.0).astype(np.uint8)


def _resize_rgb(rgb, size):
    if rgb.shape[1] == size[0] and rgb.shape[0] == size[1]:
        return rgb
    from PIL import Image
    return np.asarray(Image.fromarray(rgb).resize(size, Image.BOX))


def _resize_float(a, size, nearest=False):
    """Resize de mapa float; nearest preserva NaN (geometria metrica) e mascaras."""
    h, w = a.shape
    if w == size[0] and h == size[1]:
        return a
    if nearest or not np.isfinite(a).all():
        ys = np.minimum(((np.arange(size[1]) + 0.5) * h / size[1]).astype(int), h - 1)
        xs = np.minimum(((np.arange(size[0]) + 0.5) * w / size[0]).astype(int), w - 1)
        return a[ys][:, xs]
    from PIL import Image
    return np.asarray(Image.fromarray(a.astype(np.float32), mode='F').resize(size, Image.BILINEAR))


def parse_box(raw):
    """[L=..,T=..,W=..,H=..] ja validado pelo compilador -> (l, t, w, h) ou None."""
    numbers = re.findall(r'=\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)', str(raw or ''))
    if len(numbers) != 4:
        return None
    return tuple(float(n) for n in numbers)


class DepthSource:
    """Profundidade por frame da fonte, ja no tamanho do warp e em unidades z."""

    def __init__(self, images, depth, moge_geometry, size, hfov, depth_ratio, invert_depth,
                 smooth_depth, used_indices):
        self.images = images
        self.size = size
        self.metric = moge_geometry is not None
        self.invert = bool(invert_depth)
        self.ratio = float(depth_ratio)
        self.smooth = bool(smooth_depth)
        self.notes = []
        count = int(images.shape[0])
        if self.metric:
            if 'depth' not in moge_geometry:
                raise ValueError('PT: moge_geometry sem "depth". Use Run MoGe Inference. '
                                 'EN: moge_geometry has no "depth". Use Run MoGe Inference.')
            self.raw = moge_geometry['depth']
            self.mask = moge_geometry.get('mask')
            if depth is not None:
                self.notes.append('depth + moge_geometry: usando MoGe (métrico) / using MoGe (metric).')
        else:
            if depth is None:
                raise ValueError('PT: Depth Warp precisa de depth (IMAGE) ou moge_geometry. '
                                 'EN: Depth Warp needs depth (IMAGE) or moge_geometry.')
            self.raw = depth
            self.mask = None
        self.count = int(self.raw.shape[0])
        if self.count not in (1, count):
            raise ValueError(f'PT: A profundidade tem {self.count} frames e a referência tem {count}. Use 1 mapa ou um por frame. '
                             f'EN: Depth has {self.count} frames and the reference has {count}. Use 1 map or one per frame.')
        if self.count == 1 and count > 1 and len(set(used_indices)) > 1:
            self.notes.append('PT: um único mapa de profundidade para todos os frames. EN: a single depth map for every frame.')
        W = size[0]
        if hfov and hfov > 0:
            self.fx = W / (2.0 * math.tan(math.radians(hfov) / 2.0))
            self.hfov = float(hfov)
        else:
            K = moge_geometry.get('intrinsics') if self.metric else None
            if K is not None:
                self.fx = float(_array(K)[0][0, 0]) * W
            else:
                self.fx = W / (2.0 * math.tan(math.radians(50.0) / 2.0))
                self.notes.append('PT: hfov 0 sem intrinsics do MoGe; usando 50°. EN: hfov 0 without MoGe intrinsics; using 50°.')
            self.hfov = math.degrees(2 * math.atan(W / (2 * self.fx)))
        self.lo = self.hi = None
        if not self.metric:
            self._percentiles(sorted(set(self._depth_index(i) for i in used_indices)))

    def _depth_index(self, source_index):
        return 0 if self.count == 1 else int(source_index)

    def _brightness(self, depth_index):
        d = _array(self.raw[depth_index])
        if d.ndim == 3:
            d = d.mean(axis=-1)
        return _resize_float(d, self.size)

    def _percentiles(self, depth_indices):
        pixels = self.size[0] * self.size[1] * len(depth_indices)
        stride = max(1, int(math.ceil(math.sqrt(pixels / PERCENTILE_SAMPLES))))
        samples = np.concatenate([self._brightness(i)[::stride, ::stride].ravel() for i in depth_indices]).astype(np.float64)
        if self.invert:
            samples = -samples
        self.lo, self.hi = float(np.percentile(samples, 1)), float(np.percentile(samples, 99))

    def z(self, source_index, rgb):
        index = self._depth_index(source_index)
        if self.metric:
            z = _resize_float(_array(self.raw[index]), self.size, nearest=True).astype(np.float64)
            if self.mask is not None:
                m = _resize_float(_array(self.mask[index], bool).astype(np.float32), self.size, nearest=True) > 0.5
                z = np.where(m, z, np.nan)
            return np.where(np.isfinite(z) & (z > 0), z, np.nan)
        d = self._brightness(index)
        if self.smooth:
            try:
                import cv2
                d = cv2.medianBlur(d.astype(np.float32), 3)
                try:
                    d = cv2.ximgproc.guidedFilter(rgb, d, radius=8, eps=1e-3)
                except Exception:
                    d = cv2.bilateralFilter(d, 9, 0.1, 9.0)
            except ImportError:
                if 'smooth' not in ' '.join(self.notes):
                    self.notes.append('PT: smooth_depth exige opencv-python; ignorado. EN: smooth_depth needs opencv-python; skipped.')
        return depth_to_z(d, self.invert, self.ratio, self.lo, self.hi)


def estimate_pivot(z, fx, box, metric, pivot_depth):
    """Pivô da órbita no frame âncora.

    subject_box: mediana 3D dos pixels válidos da caixa (a câmera gira em volta do sujeito).
    Sem caixa: profundidade relativa usa z=1.05 no eixo (o sujeito mais próximo do centro);
    métrica usa a mediana da metade mais próxima da região central.
    pivot_depth > 0 substitui a profundidade, mantendo a direção do centro da caixa.
    """
    H, W = z.shape
    fin = np.isfinite(z) & (z > 0)
    source = 'auto'
    if box is not None:
        l, t, w, h = box
        x0, x1 = int(math.floor(l * W)), int(math.ceil((l + w) * W))
        y0, y1 = int(math.floor(t * H)), int(math.ceil((t + h) * H))
        region = np.zeros_like(fin)
        region[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] = True
        pick = fin & region
        cu, cv = (l + w / 2) * W, (t + h / 2) * H
        if pick.sum() >= 16:
            vv, uu = np.nonzero(pick)
            zz = z[pick]
            X = (uu - W / 2.0) / fx * zz
            Y = (vv - H / 2.0) / fx * zz
            pivot = np.array([np.median(X), np.median(Y), np.median(zz)])
            source = 'subject_box'
        else:
            zc = float(np.median(z[fin])) if fin.any() else RELATIVE_PIVOT_Z
            pivot = np.array([(cu - W / 2) / fx * zc, (cv - H / 2) / fx * zc, zc])
            source = 'subject_box (sem profundidade válida / no valid depth)'
    elif metric:
        central = np.zeros_like(fin)
        central[H // 8: 4 * H // 5, W // 5: 4 * W // 5] = True
        pick = fin & central
        if not pick.any():
            pick = fin
        zc = z[pick]
        near = zc[zc <= np.percentile(zc, 50)] if zc.size else zc
        pivot = np.array([0.0, 0.0, float(np.median(near)) if near.size else 1.0])
        source = 'centro métrico / metric centre'
    else:
        pivot = np.array([0.0, 0.0, RELATIVE_PIVOT_Z])
        source = 'padrão 1.05 / default 1.05'
    if pivot_depth and pivot_depth > 0:
        scale = float(pivot_depth) / max(float(pivot[2]), 1e-9)
        pivot = pivot * scale
        source = 'pivot_depth'
    pivot[2] = max(float(pivot[2]), 1e-3)
    return pivot, source


def apply_hold(sources, hold_at, hold_frames, source_count, source_fps):
    """play -> segura -> retoma, como o --freeze F:N do Meridian.

    Os frames vivos vão até o frame-fonte hold_at, ele repete por hold_frames saídas e a ação
    recomeça do frame seguinte, no mesmo ritmo. A câmera não para: ela segue a trajetória inteira.
    """
    n = len(sources)
    hold_frames = max(0, int(hold_frames))
    if hold_frames <= 0 or source_count <= 1:
        return sources, None
    hold_at = min(max(0, int(hold_at)), source_count - 1)
    start = next((i for i, s in enumerate(sources) if s >= hold_at), n)
    rate = source_fps / FPS
    out = [min(s, hold_at) for s in sources[:start]] + [hold_at] * hold_frames
    for k in range(max(0, n - len(out))):
        out.append(min(source_count - 1, hold_at + 1 + int(k * rate)))
    out = out[:n]
    tail = max(0, n - start - hold_frames)
    return out, {'at': hold_at, 'frames': min(hold_frames, n - start), 'live': start, 'tail': tail,
                 'last': out[-1] if out else hold_at}


def frame_schedule(plan, length, source_count, frame_mode, source_fps, freeze_index, direction,
                   hold_at=0, hold_frames=0):
    """Pose e frame-fonte de cada frame de saída, com o mesmo tempo do prompt."""
    path = plan['model_path'] if direction == DIRECTIONS[1] else plan['path']
    duration = float(plan['duration_s'])
    last = float(plan['last_frame_s'])
    default_length = int(round(last * FPS)) + 1
    n = int(length) if length and length > 0 else default_length
    # Um comprimento personalizado estica a trajetória inteira sobre ele, preservando a
    # fração de assentamento da tarefa dirigida.
    span = duration * ((n - 1) / FPS) / last if n != default_length and last > 0 else duration
    poses, sources = [], []
    for i in range(n):
        t = (i / FPS) / span if span > 0 else 1.0
        poses.append(interpolate_pose(path, min(max(t, 0.0), 1.0), plan['interpolation'], plan['prompt_detail']))
        if frame_mode == 'Motion Frame' and source_count > 1:
            sources.append(min(source_count - 1, int(i * source_fps / FPS)))
        else:
            sources.append(int(freeze_index) if source_count > 1 else 0)
    hold = None
    if frame_mode == 'Motion Frame' and source_count > 1:
        sources, hold = apply_hold(sources, hold_at, hold_frames, source_count, source_fps)
    return poses, sources, n, hold


def target_size(width, height, long_side):
    if not long_side or long_side <= 0 or max(width, height) <= long_side:
        return width, height
    scale = long_side / float(max(width, height))
    return max(8, int(round(width * scale))), max(8, int(round(height * scale)))


def _save_preview(clouds_by_sample, tmp_dir, meta_base):
    """PNG RGB + profundidade 16 bits empacotada (R alto, G baixo, B=255 inválido)."""
    from PIL import Image
    stamp = f"h3dw_{int(time.time() * 1000)}_{os.getpid() & 0xffff:04x}"
    valid_all = []
    small = []
    for t, rgb, z, thr in clouds_by_sample:
        H, W = z.shape
        size = target_size(W, H, PREVIEW_SIDE)
        rgb_s = _resize_rgb(rgb, size)
        z_s = _resize_float(z.astype(np.float32), size, nearest=True).astype(np.float64)
        ok = np.isfinite(z_s) & (z_s > 0) & (z_s < thr)
        small.append((t, rgb_s, z_s, ok))
        if ok.any():
            valid_all.append(z_s[ok])
    if not valid_all:
        return None
    allz = np.concatenate(valid_all)
    lo, hi = float(allz.min()), float(allz.max())
    span = max(hi - lo, 1e-9)
    samples = []
    for k, (t, rgb_s, z_s, ok) in enumerate(small):
        q = np.where(ok, np.clip((z_s - lo) / span * 65535.0, 0, 65535), 0).astype(np.uint32)
        packed = np.stack([(q >> 8).astype(np.uint8), (q & 255).astype(np.uint8),
                           np.where(ok, 0, 255).astype(np.uint8)], -1)
        f_rgb, f_z = f'{stamp}_{k}_rgb.png', f'{stamp}_{k}_z.png'
        Image.fromarray(rgb_s).save(os.path.join(tmp_dir, f_rgb), compress_level=3)
        Image.fromarray(packed).save(os.path.join(tmp_dir, f_z), compress_level=3)
        samples.append({'t': t, 'rgb': {'filename': f_rgb, 'subfolder': '', 'type': 'temp'},
                        'z': {'filename': f_z, 'subfolder': '', 'type': 'temp'}})
    w, h = small[0][1].shape[1], small[0][1].shape[0]
    return dict(meta_base, w=w, h=h, z_lo=lo, z_hi=hi, samples=samples)


# =============================================================================
# Formato Meridian (Viggle, fine-tune do H3): render de nuvem de pontos com buraco cinza
# =============================================================================
# NOTICE: meridian_render_reference, meridian_keep, scale_k e as escadas de canvas seguem
# recam/geometry.py e recam/h3.py de Viggle/Meridian (huggingface.co/Viggle/Meridian),
# Apache License 2.0. Ver THIRD_PARTY_NOTICES.md.

FORMATS = ['Meridian (H3)']
ALL_FORMATS = FORMATS + [LEGACY_FORMAT]
MERIDIAN_LENGTHS = (73, 90, 107, 124, 141, 158, 175, 243)
MERIDIAN_HOLE = 128        # cinza médio; não há canal de máscara, o prompt fixo diz que cinza é buraco
MERIDIAN_FULL = 1280       # lado do quadrado em que a fonte é letterboxada (densidade de pontos)
MERIDIAN_RES = 512         # resolução da geometria do VGGT-Omega; a poda de bordas roda nessa escala
MERIDIAN_EDGE_RTOL = 0.30  # descarta janelas 3x3 cuja profundidade varia mais de 30 %
MERIDIAN_SPLAT = 1         # 3x3 por ponto, z-buffer
# (largura, altura); a entrada i tem o mesmo aspecto nas duas classes
MERIDIAN_LADDERS = {
    480: [(416, 960), (448, 896), (480, 832), (544, 736), (640, 640), (736, 544), (832, 480), (896, 448), (960, 416)],
    768: [(672, 1536), (704, 1408), (768, 1344), (864, 1184), (1024, 1024), (1184, 864), (1344, 768), (1408, 704), (1536, 672)],
}


def meridian_bucket(w, h):
    """-> ((largura, altura) do alvo 768, (largura, altura) das referências 480), como recam/h3.bucket."""
    lad = MERIDIAN_LADDERS[768]
    i = min(range(len(lad)), key=lambda i: abs(math.log(lad[i][0] / lad[i][1] * h / w)))
    return MERIDIAN_LADDERS[768][i], MERIDIAN_LADDERS[480][i]


def meridian_geometry(src_w, src_h):
    """Grade de pontos (lado maior 1280), recorte central no aspecto do canvas e escala até o canvas 480."""
    target, canvas = meridian_bucket(src_w, src_h)
    s = MERIDIAN_FULL / float(max(src_w, src_h))
    Wp, Hp = max(8, int(round(src_w * s))), max(8, int(round(src_h * s)))
    aspect = canvas[0] / canvas[1]
    if Wp / Hp > aspect:
        bh, bw = Hp, min(Wp, int(round(Hp * aspect)))
    else:
        bw, bh = Wp, min(Hp, int(round(Wp / aspect)))
    x0, y0 = (Wp - bw) // 2, (Hp - bh) // 2
    return {'point': (Wp, Hp), 'box': (x0, y0, bw, bh, canvas[0] / bw), 'canvas': canvas, 'target': target}


def scale_k(K, f):
    """K de uma imagem redimensionada por f, convenção de centro de pixel (x_hi = f*(x_lo+0.5)-0.5)."""
    out = np.array(K, dtype=np.float64) * f
    out[2, 2] = 1.0
    out[:2, 2] += 0.5 * (f - 1)
    return out


def _bilinear(a, out_h, out_w):
    """F.interpolate(mode='bilinear', align_corners=False) sem antialias, em NumPy."""
    h, w = a.shape

    def axis(n_out, n_in):
        x = (np.arange(n_out) + 0.5) * (n_in / n_out) - 0.5
        x = np.clip(x, 0, None)
        i0 = np.minimum(np.floor(x).astype(np.int64), n_in - 1)
        i1 = np.minimum(i0 + 1, n_in - 1)
        return i0, i1, (x - i0).astype(np.float32)

    y0, y1, fy = axis(out_h, h)
    x0, x1, fx = axis(out_w, w)
    top = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    bot = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return top * (1 - fy[:, None]) + bot * fy[:, None]


def _pool3(a, pad_value):
    """max_pool2d(3, stride 1, padding 1) em NumPy (use -a para mínimo)."""
    p = np.pad(a, 1, constant_values=pad_value)
    out = p[:-2, :-2]
    for dy in range(3):
        for dx in range(3):
            if dy or dx:
                out = np.maximum(out, p[dy:dy + a.shape[0], dx:dx + a.shape[1]])
    return out


def meridian_keep(z):
    """Pontos que o Meridian manteria: sem bordas de profundidade na escala 512 e só onde todos os
    'pais' bilineares sobreviveram (mata pixels voadores). Sem confiança do VGGT: a poda de 2 % não existe."""
    H, W = z.shape
    L = float(max(H, W))
    hs, ws = max(3, int(round(H * MERIDIAN_RES / L))), max(3, int(round(W * MERIDIAN_RES / L)))
    small = _resize_float(np.asarray(z, dtype=np.float32), (ws, hs), nearest=True).astype(np.float64)
    valid = np.isfinite(small) & (small > 0)
    # Vizinho inválido (céu mascarado do MoGe) conta como descontinuidade: no VGGT o céu tem profundidade
    # finita e enorme, então a borda sujeito/céu também é podada lá. A borda do quadro não conta.
    mx = _pool3(np.where(valid, small, np.inf), -np.inf)
    mn = -_pool3(np.where(valid, -small, np.inf), -np.inf)
    with np.errstate(invalid='ignore', over='ignore'):
        rel = (mx - mn) / np.maximum(np.abs(np.where(valid, small, 1.0)), 1e-6)
    keep_small = valid & np.isfinite(rel) & (rel <= MERIDIAN_EDGE_RTOL)
    keep = _bilinear(keep_small.astype(np.float32), H, W) > 0.999
    return keep & np.isfinite(z) & (z > 0)


def meridian_render_reference(P, C, extr, intr, H, W, splat=1):
    """Transliteração literal de recam/geometry.render_hw (torch -> NumPy), para os testes."""
    cam = P @ extr[:3, :3].T + extr[:3, 3]
    m = cam[:, 2] > 1e-6
    cam, C = cam[m], C[m]
    z = cam[:, 2]
    u = cam[:, 0] / z * intr[0, 0] + intr[0, 2]
    v = cam[:, 1] / z * intr[1, 1] + intr[1, 2]
    offs = [(dx, dy) for dy in (-splat, 0, splat) for dx in (-splat, 0, splat)]
    x = np.concatenate([np.round(u + dx) for dx, _ in offs]).astype(np.int64)
    y = np.concatenate([np.round(v + dy) for _, dy in offs]).astype(np.int64)
    z = np.tile(z, len(offs))
    C = np.tile(C, (len(offs), 1))
    k = (x >= 0) & (x < W) & (y >= 0) & (y < H)
    idx, z, C = (y[k] * W + x[k]), z[k], C[k]
    zbuf = np.full((H * W,), np.inf)
    np.minimum.at(zbuf, idx, z)
    win = z == zbuf[idx]
    img = np.full((H * W, 3), MERIDIAN_HOLE, dtype=np.uint8)
    img[idx[win]] = C[win]
    cov = np.zeros(H * W, dtype=bool)
    cov[idx] = True
    return img.reshape(H, W, 3), cov.reshape(H, W)


def meridian_render(P, C, extr, intr, H, W, splat=MERIDIAN_SPLAT):
    """Mesmo resultado de meridian_render_reference, inclusive empates, ~2x mais rápido.

    round(u+dx) só difere de round(u)+dx quando a fração é exatamente .5 (arredondamento para o par):
    esses pontos e os da borda são recalculados literalmente. Fora do quadro vai para uma casa-lixo
    extra do buffer, então cada passada escreve na ordem original sem filtrar por máscara.
    """
    cam = P @ extr[:3, :3].T + extr[:3, 3]
    m = cam[:, 2] > 1e-6
    cam = cam[m]
    c = C[m].astype('<u4')
    c32 = c[:, 0] | (c[:, 1] << 8) | (c[:, 2] << 16)
    z = cam[:, 2]
    with np.errstate(over='ignore', invalid='ignore'):
        u = cam[:, 0] / z * intr[0, 0] + intr[0, 2]
        v = cam[:, 1] / z * intr[1, 1] + intr[1, 2]
    trash = H * W
    with np.errstate(invalid='ignore'):
        ru, rv = np.round(u), np.round(v)
        exact = (u - np.floor(u) == 0.5) | (v - np.floor(v) == 0.5) | ~np.isfinite(u) | ~np.isfinite(v)
        safe = ~exact & (ru >= splat) & (ru < W - splat) & (rv >= splat) & (rv < H - splat)
    base = np.full(u.shape[0], trash, dtype=np.int64)
    base[safe] = rv[safe].astype(np.int64) * W + ru[safe].astype(np.int64)
    rest = np.flatnonzero(~safe)
    zbuf = np.full(trash + 1, np.inf)
    passes = []
    for dy in (-splat, 0, splat):
        for dx in (-splat, 0, splat):
            idx = base + (dy * W + dx)
            if rest.size:
                with np.errstate(invalid='ignore'):
                    ur, vr = np.round(u[rest] + dx), np.round(v[rest] + dy)
                    k = (ur >= 0) & (ur < W) & (vr >= 0) & (vr < H)
                ridx = np.full(rest.size, trash, dtype=np.int64)
                ridx[k] = vr[k].astype(np.int64) * W + ur[k].astype(np.int64)
                idx[rest] = ridx
            np.minimum.at(zbuf, idx, z)
            passes.append(idx)
    img = np.full(trash + 1, MERIDIAN_HOLE | (MERIDIAN_HOLE << 8) | (MERIDIAN_HOLE << 16), dtype='<u4')
    cov = np.zeros(trash + 1, dtype=bool)
    for idx in passes:
        win = z == zbuf[idx]
        img[idx[win]] = c32[win]
        cov[idx] = True
    rgb = img[:trash].view(np.uint8).reshape(H, W, 4)[..., :3].copy()
    return rgb, cov[:trash].reshape(H, W)


class MeridianCloud:
    """Pontos do recorte, desprojetados na grade de 1280 e renderizados no canvas 480 (C_ref = identidade)."""

    def __init__(self, rgb, z, fx, box, canvas):
        z = np.asarray(z, dtype=np.float64)
        H, W = z.shape
        x0, y0, bw, bh, f = box
        self.keep = meridian_keep(z)
        vv, uu = np.nonzero(self.keep[y0:y0 + bh, x0:x0 + bw])
        v, u = vv + y0, uu + x0
        zz = z[v, u]
        cx, cy = W / 2.0, H / 2.0
        self.P = np.stack([(u - cx) / fx * zz, (v - cy) / fx * zz, zz], -1)
        self.C = np.ascontiguousarray(rgb[v, u, :3])
        K = np.array([[fx, 0.0, cx - x0], [0.0, fx, cy - y0], [0.0, 0.0, 1.0]])
        self.K = scale_k(K, f)
        self.canvas = canvas
        self.box = box
        self.thr = np.inf

    def render(self, c2w):
        w2c = np.linalg.inv(c2w)
        rgb, cov = meridian_render(self.P, self.C, w2c[:3], self.K, self.canvas[1], self.canvas[0])
        return rgb, ~cov

    def preview_arrays(self, rgb, z):
        x0, y0, bw, bh, _ = self.box
        zc = np.where(self.keep, z, np.nan)[y0:y0 + bh, x0:x0 + bw]
        return np.ascontiguousarray(rgb[y0:y0 + bh, x0:x0 + bw]), zc


def build_depth_warp(plan, frame_mode, reference_image, depth=None, moge_geometry=None, source_fps=24.0,
                     freeze_index=0, subject_box='', hfov=50.0, depth_ratio=6.0, invert_depth=False,
                     smooth_depth=False, aim=AIMS[0], pivot_depth=0.0, direction=DIRECTIONS[0], length=0,
                     long_side=0, english=False, progress=None, temp_dir=None, allocate=None,
                     offset_azimuth=0.0, offset_elevation=0.0, offset_distance=1.0, warp_format=None,
                     hold_at=0, hold_frames=0):
    """-> (warp [N,H,W,3] float, holes [N,H,W] float, info str, preview meta ou None).

    warp_format: 'Meridian (H3)' (cinza 128, z-buffer 3x3, canvas classe 480, só as durações do
    Meridian). O formato magenta da v30 continua no código para workflows salvos.
    offset_*: pose somada a TODA a trajetória só no warp.
    allocate(shape_rgb, shape_mask) devolve buffers graváveis (tensores torch no ComfyUI).
    """
    if reference_image is None:
        raise ValueError('PT: Depth Warp precisa de reference_image (imagem ou frames). '
                         'EN: Depth Warp needs reference_image (image or frames).')
    aim = aim if aim in AIMS else AIMS[0]
    direction = direction if direction in DIRECTIONS else DIRECTIONS[0]
    warp_format = warp_format if warp_format in ALL_FORMATS else FORMATS[0]
    meridian = warp_format != LEGACY_FORMAT
    shape = reference_image.shape
    if len(shape) != 4 or shape[-1] < 3:
        raise ValueError('PT: Use frames RGB [N,H,W,3]. EN: Use RGB frames [N,H,W,3].')
    count, src_h, src_w = int(shape[0]), int(shape[1]), int(shape[2])
    if frame_mode != 'Motion Frame' and not 0 <= int(freeze_index) < count:
        raise ValueError('PT: freeze_index fora do lote. EN: freeze_index outside the batch.')
    poses, sources, n, hold = frame_schedule(plan, length, count, frame_mode, float(source_fps), freeze_index,
                                             direction, hold_at, hold_frames)
    off_az, off_el = float(offset_azimuth or 0.0), float(offset_elevation or 0.0)
    off_dist = float(offset_distance) if offset_distance and offset_distance > 0 else 1.0
    if off_az or off_el or off_dist != 1.0:
        poses = [{'azimuth': p['azimuth'] + off_az, 'elevation': p['elevation'] + off_el,
                  'distance': p['distance'] * off_dist, 'height': p.get('height', 0.0)} for p in poses]
    geo = None
    if meridian:
        if n not in MERIDIAN_LENGTHS:
            raise ValueError(f'PT: O Meridian só aceita {", ".join(map(str, MERIDIAN_LENGTHS))} frames; o warp tem {n}. '
                             f'Use warp_length (ex.: 124) ou o perfil 124/243. '
                             f'EN: Meridian only accepts {", ".join(map(str, MERIDIAN_LENGTHS))} frames; the warp has {n}. '
                             f'Set warp_length (e.g. 124) or the 124/243 profile.')
        geo = meridian_geometry(src_w, src_h)
        size = geo['point']
        W, H = geo['canvas']
    else:
        size = target_size(src_w, src_h, long_side)
        W, H = size
    if n * W * H > PIXEL_BUDGET:
        raise ValueError(f'PT: Depth Warp de {n} frames em {W}x{H} passa de {PIXEL_BUDGET // 1_000_000} milhões de pixels. '
                         f'Use warp_long_side (ex.: 1280 ou 960) ou warp_length menor. '
                         f'EN: A {n}-frame Depth Warp at {W}x{H} exceeds {PIXEL_BUDGET // 1_000_000} million pixels. '
                         f'Use warp_long_side (e.g. 1280 or 960) or a shorter warp_length.')
    source = DepthSource(reference_image, depth, moge_geometry, size, hfov, depth_ratio, invert_depth,
                         smooth_depth, sources)

    def make_cloud(rgb, z):
        return MeridianCloud(rgb, z, source.fx, geo['box'], geo['canvas']) if meridian else PointCloud(rgb, z, source.fx)

    anchor = sources[0]
    anchor_rgb = _resize_rgb(_frame_rgb(reference_image, anchor), size)
    anchor_z = source.z(anchor, anchor_rgb)
    box = parse_box(subject_box) if str(subject_box or '').strip() else None
    pivot, pivot_source = estimate_pivot(anchor_z, source.fx, box, source.metric, pivot_depth)
    aim_point = np.array([0.0, 0.0, float(np.linalg.norm(pivot))]) if aim == AIMS[0] else None

    if allocate is None:
        warp = np.empty((n, H, W, 3), dtype=np.float32)
        holes = np.empty((n, H, W), dtype=np.float32)
    else:
        warp, holes = allocate((n, H, W, 3), (n, H, W))

    cache = {anchor: make_cloud(anchor_rgb, anchor_z)}
    cache_rgbz = {anchor: (anchor_rgb, anchor_z)}
    hole_total = 0.0
    for i in range(n):
        if progress:
            progress(i, n)
        src = sources[i]
        if src not in cache:
            # A fonte avança em ordem: basta manter a âncora e o frame atual, então
            # sequências longas não acumulam RAM.
            for key in list(cache):
                if key != anchor:
                    del cache[key]
                    cache_rgbz.pop(key, None)
            rgb = _resize_rgb(_frame_rgb(reference_image, src), size)
            z = source.z(src, rgb)
            cache[src] = make_cloud(rgb, z)
            cache_rgbz[src] = (rgb, z)
        pose = poses[i]
        C = orbit_pose(pose['azimuth'], pose['elevation'], pose['distance'], pivot, aim_point,
                       pose.get('height', 0.0))
        frame, hole = cache[src].render(C)
        warp[i] = _as_float(frame, allocate)
        holes[i] = _as_float_mask(hole, allocate)
        hole_total += float(hole.mean())
    if progress:
        progress(n, n)

    preview = None
    if temp_dir:
        try:
            picks = sorted(set(int(round(k * (n - 1) / max(1, PREVIEW_SAMPLES - 1))) for k in range(PREVIEW_SAMPLES))) \
                if frame_mode == 'Motion Frame' and count > 1 else [0]
            seen, entries = set(), []
            for i in picks:
                src = sources[i]
                if src in seen:
                    continue
                seen.add(src)
                if src in cache_rgbz:
                    rgb, z = cache_rgbz[src]
                    cloud = cache[src]
                else:
                    rgb = _resize_rgb(_frame_rgb(reference_image, src), size)
                    z = source.z(src, rgb)
                    cloud = make_cloud(rgb, z)
                if meridian:
                    rgb_p, z_p = cloud.preview_arrays(rgb, z)
                    entries.append((i / max(1, n - 1), rgb_p, z_p, np.inf))
                else:
                    entries.append((i / max(1, n - 1), rgb, z, cloud.thr))
            az_sign = -1 if (direction == DIRECTIONS[1] and plan.get('orbit_direction') == 'invert H3 orbit') else 1
            fx_norm = source.fx / (geo['box'][2] if meridian else W)
            preview = _save_preview(entries, temp_dir, {
                'version': 2, 'format': 'meridian' if meridian else 'legacy', 'source_w': W, 'source_h': H,
                'fx_norm': fx_norm, 'pivot': [float(v) for v in pivot], 'aim': 'source' if aim == AIMS[0] else 'pivot',
                'az_sign': az_sign, 'offset': [off_az, off_el, off_dist],
                'splat': MERIDIAN_SPLAT if meridian else SPLAT,
                'hole': [MERIDIAN_HOLE] * 3 if meridian else [255, 0, 255],
                'length': n, 'frame_mode': frame_mode, 'depth_source': 'moge' if source.metric else 'depth'})
        except Exception:
            logging.exception('Camera H3 Depth Warp: falha ao salvar a prévia / could not save preview')

    lines = _warp_info(english, meridian, n, W, H, geo, source, pivot, pivot_source, aim, direction, plan,
                       hole_total, poses, off_az, off_el, off_dist, long_side)
    if hold:
        lines.append(f"Hold: {hold['live']} live frames, source frame {hold['at']} held for {hold['frames']} output frames, "
                     f"then {hold['tail']} frames of action (bullet time: the camera keeps moving)."
                     if english else
                     f"Congelamento: {hold['live']} frames vivos, o frame {hold['at']} da fonte segura por {hold['frames']} "
                     f"frames de saída e a ação retoma por {hold['tail']} (bullet time: a câmera continua andando).")
        if hold['tail'] and hold['last'] >= count - 1:
            lines.append('The source ends during the resume: its last frame is held.' if english else
                         'A fonte acaba durante a retomada: o último frame fica parado.')
    if frame_mode == 'Motion Frame' and count > 1:
        used = max(sources) + 1
        if used < count:
            lines.append(f'Motion: {used} de {count} frames da fonte usados em {n} frames de saída.' if not english else
                         f'Motion: {used} of {count} source frames used across {n} output frames.')
        if sources[-1] == count - 1 and int((n - 1) * source_fps / FPS) > count - 1:
            lines.append('A fonte acaba antes do fim: o último frame fica parado.' if not english else
                         'The source ends early: its last frame is held.')
    lines.extend(source.notes)
    return warp, holes, '\n'.join(lines), preview


def _warp_info(english, meridian, n, W, H, geo, source, pivot, pivot_source, aim, direction, plan, hole_total,
               poses, off_az, off_el, off_dist, long_side):
    max_az = max(abs(p['azimuth']) for p in poses)
    min_el = min(p['elevation'] for p in poses)
    max_el = max(p['elevation'] for p in poses)
    near_source = max_az < 10 and max(abs(min_el), abs(max_el)) < 5 and all(abs(p['distance'] - 1) < 0.1 for p in poses)
    offset_text = f' · offset ({off_az:+g}°, {off_el:+g}°, ×{off_dist:g})' if (off_az or off_el or off_dist != 1.0) else ''
    holes = 100 * hole_total / max(1, n)
    en = english
    geom = (('metric MoGe' if source.metric else f'relative depth · ratio {source.ratio:g}') if en else
            ('MoGe métrico' if source.metric else f'depth relativo · ratio {source.ratio:g}'))
    fmt = 'Meridian' if meridian else 'v30'
    aim_t = ('source aim' if en else 'mira da fonte') if aim == AIMS[0] else ('looks at pivot' if en else 'mira no pivô')
    path_t = ('panel path' if en else 'trajetória do painel') if direction == DIRECTIONS[0] else \
        ('calibrated model_path' if en else 'model_path calibrado')
    lines = [f"Depth Warp ({fmt}): {n} frames {W}x{H} {'@' if en else 'a'} 24 fps · {geom} · hfov {source.hfov:.1f}° · "
             f"{'pivot' if en else 'pivô'} ({pivot[0]:.2f}, {pivot[1]:.2f}, {pivot[2]:.2f}) {'from' if en else 'por'} {pivot_source} · "
             f"{aim_t} · {path_t} · {'average holes' if en else 'buracos médios'} {holes:.1f}%{offset_text}."]
    if meridian:
        tw, th = geo['target']
        lines.append(f'Meridian: <Video 2> render {W}x{H}; generation canvas {tw}x{th}. Wire reference_image as <Video 1> and depth_warp as <Video 2> in bruxosdovfx • Meridian Reference. Grey 128 = hole.'
                     if en else
                     f'Meridian: render <Video 2> em {W}x{H}; canvas de geração {tw}x{th}. Ligue reference_image como <Video 1> e depth_warp como <Video 2> no bruxosdovfx • Meridian Reference. Cinza 128 = buraco.')
        lines.append('Geometry differs from Meridian training: no VGGT-Omega source-camera poses (a moving source camera is treated as static) and no confidence pruning; edge pruning and the 3x3 z-buffer match.'
                     if en else
                     'Geometria diferente do treino do Meridian: sem poses de câmera do VGGT-Omega (câmera da fonte em movimento é tratada como parada) e sem poda por confiança; a poda de bordas e o z-buffer 3x3 são iguais.')
        if max_az > 40:
            lines.append(f'Orbit reaches {max_az:g}°: Meridian reports about 40° as a caution point for large moves.'
                         if en else f'A órbita chega a {max_az:g}°: o Meridian aponta ~40° como ponto de cautela para movimentos grandes.')
        if long_side:
            lines.append('warp_long_side is ignored in Meridian format: the canvas is fixed by its 480-class ladder.'
                         if en else 'warp_long_side é ignorado no formato Meridian: o canvas vem da escada classe 480.')
    else:
        lines.append('Legacy v30 format (magenta holes, 5x5 painter splat), kept for saved workflows; warp_mask is 1 on the holes.'
                     if en else 'Formato legado da v30 (buracos magenta, splat 5x5 de pintor), mantido para workflows salvos; warp_mask vale 1 nos buracos.')
        if near_source:
            lines.append('The warp stays within 10° of the source. Use warp_offset_azimuth for a new angle from frame 1.'
                         if en else 'O warp fica a menos de 10° da fonte. Use warp_offset_azimuth para começar num ângulo novo já no frame 1.')
        if max_az > 90:
            lines.append(f'Orbit reaches {max_az:g}°: past ±90° the warp is mostly holes.'
                         if en else f'A órbita chega a {max_az:g}°: além de ±90° o warp vira quase só buraco.')
    if direction == DIRECTIONS[0] and plan.get('orbit_direction') == 'invert H3 orbit':
        lines.append('The warp follows the panel geometry; only the H3 prompt sign is calibrated by orbit_direction.'
                     if en else 'O warp segue a geometria do painel; orbit_direction só calibra o sinal do prompt do H3.')
    return lines


def _as_float(frame, allocate):
    arr = frame.astype(np.float32) / 255.0
    if allocate is None:
        return arr
    import torch
    return torch.from_numpy(arr)


def _as_float_mask(hole, allocate):
    arr = hole.astype(np.float32)
    if allocate is None:
        return arr
    import torch
    return torch.from_numpy(arr)
