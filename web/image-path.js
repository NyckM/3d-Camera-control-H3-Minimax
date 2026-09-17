import { app } from '../../scripts/app.js';
import { api } from '../../scripts/api.js';
import { resolveLinkedImage } from './linked-image.js';

// PT: Marcador de pontos sobre a imagem; escreve o widget waypoints em JSON.
// EN: Point marker over the image; writes the waypoints widget as JSON.
function build(node) {
  const root = document.createElement('div');
  root.style.cssText = 'font:12px system-ui;color:#c9bfe0';
  const stage = document.createElement('div');
  stage.style.cssText = 'position:relative;width:100%;aspect-ratio:16/9;background:#1c1a24;border:1px solid #34313f;'
    + 'border-radius:8px;overflow:hidden;cursor:crosshair;touch-action:none';
  const picture = document.createElement('img');
  picture.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;object-fit:contain;pointer-events:none';
  const overlay = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  overlay.setAttribute('viewBox', '0 0 100 100');
  overlay.setAttribute('preserveAspectRatio', 'none');
  overlay.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;pointer-events:none';
  const hint = document.createElement('div');
  hint.style.cssText = 'padding-top:6px;font-size:11px;color:#8d85a0;line-height:1.5';
  hint.textContent = 'PT: clique para marcar, arraste um ponto para mover, clique com o botão direito para apagar. '
    + 'EN: click to add, drag a point to move, right-click to delete.';
  stage.append(picture, overlay);
  root.append(stage, hint);

  const widget = name => node.widgets.find(w => w.name === name);
  const read = () => {
    try {
      const list = JSON.parse(widget('waypoints')?.value || '[]');
      return Array.isArray(list) ? list : [];
    } catch { return []; }
  };
  const write = list => {
    const target = widget('waypoints');
    if (!target) return;
    target.value = JSON.stringify(list, null, 2);
    target.callback?.(target.value);
    node.setDirtyCanvas(true, true);
    paint();
  };

  function paint() {
    const list = read();
    const bits = [];
    // Linha do caminho primeiro, para os pontos ficarem por cima dela.
    if (list.length > 1) {
      const d = list.map((p, i) => `${i ? 'L' : 'M'}${p.x * 100},${p.y * 100}`).join(' ');
      bits.push(`<path d="${d}" fill="none" stroke="#f5d97a" stroke-width="0.6" vector-effect="non-scaling-stroke"/>`);
    }
    list.forEach((p, i) => {
      bits.push(`<circle cx="${p.x * 100}" cy="${p.y * 100}" r="1.6" fill="#f5d97a"`
        + ` vector-effect="non-scaling-stroke"/>`);
      bits.push(`<text x="${p.x * 100 + 2.6}" y="${p.y * 100 + 1}" fill="#f5d97a" font-size="3.4"`
        + `>${i + 1}${p.label ? ' ' + String(p.label).replace(/[<&>]/g, '') : ''}</text>`);
    });
    overlay.innerHTML = bits.join('');
  }

  let source = '';
  function refresh() {
    let found = '';
    try { found = resolveLinkedImage(app.graph, node, q => api.apiURL(q)); } catch { found = ''; }
    if (found === source) return;
    source = found;
    picture.style.display = found ? '' : 'none';
    if (found) picture.src = found;
  }

  const at = event => {
    const box = stage.getBoundingClientRect();
    return [Math.min(1, Math.max(0, (event.clientX - box.left) / box.width)),
            Math.min(1, Math.max(0, (event.clientY - box.top) / box.height))];
  };
  const nearest = (x, y, list) => {
    let best = -1, dist = 0.04;
    list.forEach((p, i) => {
      const d = Math.hypot(p.x - x, p.y - y);
      if (d < dist) { dist = d; best = i; }
    });
    return best;
  };

  let dragging = -1;
  stage.addEventListener('contextmenu', event => {
    event.preventDefault();
    const list = read();
    const [x, y] = at(event);
    const index = nearest(x, y, list);
    // Dois pontos e o minimo que o node aceita; abaixo disso nao ha caminho.
    if (index >= 0 && list.length > 2) { list.splice(index, 1); write(list); }
  });
  stage.addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    const list = read();
    const [x, y] = at(event);
    const index = nearest(x, y, list);
    if (index >= 0) { dragging = index; }
    else if (list.length < 12) {
      const last = list[list.length - 1];
      list.push({ x, y, label: '', framing: last ? last.framing : 0.4 });
      write(list);
    }
    stage.setPointerCapture(event.pointerId);
  });
  stage.addEventListener('pointermove', event => {
    if (dragging < 0) return;
    const list = read();
    if (!list[dragging]) { dragging = -1; return; }
    const [x, y] = at(event);
    list[dragging] = { ...list[dragging], x, y };
    write(list);
  });
  stage.addEventListener('pointerup', () => { dragging = -1; });

  paint();
  refresh();
  const timer = setInterval(refresh, 1200);
  return { element: root, paint, destroy: () => clearInterval(timer) };
}

app.registerExtension({
  name: 'bruxosdovfx.h3.image_path',
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== 'BruxosH3ImagePath') return;
    const created = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = created?.apply(this, arguments);
      const picker = build(this);
      const widget = this.addDOMWidget('image_path_picker', 'H3_IMAGE_PATH', picker.element, { serialize: false });
      widget.computeSize = () => [340, 250];
      const target = this.widgets.find(w => w.name === 'waypoints');
      if (target) {
        const previous = target.callback;
        target.callback = function () { const r = previous?.apply(this, arguments); picker.paint(); return r; };
      }
      const removed = this.onRemoved;
      this.onRemoved = function () { picker.destroy(); return removed?.apply(this, arguments); };
      this.setSize([360, Math.max(this.size[1], 560)]);
      return result;
    };
  },
});
