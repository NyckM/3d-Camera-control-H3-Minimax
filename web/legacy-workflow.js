// PT: A v32 tirou os widgets instruction e experiment_mode do Camera H3. Tanto widgets_values quanto
// os links de entradas convertidas são POSICIONAIS, então um workflow salvo antes disso carrega com os
// valores deslocados e os fios no soquete errado. Este módulo reescreve o gráfico por NOME antes do
// ComfyUI montá-lo, e serve tanto para a extensão quanto para consertar um .json na mão.
// EN: v32 removed the instruction and experiment_mode widgets from Camera H3. Both widgets_values and the
// links of converted inputs are POSITIONAL, so a workflow saved earlier loads with shifted values and
// wires on the wrong socket. This module rewrites the graph BY NAME before ComfyUI builds it; it is used
// by the extension and can also repair a .json offline.

export const NODE_TYPE = 'BruxosH3Camera';
export const REMOVED = ['instruction', 'experiment_mode'];

// Ordens de widgets que já existiram. A migração testa todas contra as opções reais do node e
// fica com a que encaixa — assim ela conserta tanto workflows antigos quanto arquivos já salvos
// com os valores deslocados, sem depender de adivinhar a versão.
// Widget orders that have existed. The migration tries them all against the node's real option
// lists and keeps the one that fits, repairing both old workflows and files already saved shifted.
const V29 = ['camera_trajectory', 'profile', 'interpolation', 'instruction', 'subject_framing', 'minimax_format',
  'elevation_range', 'orbit_direction', 'subject_box', 'runtime_task', 'prompt_detail', 'frame_mode', 'source_fps',
  'freeze_index', 'ui_language', 'loop_closure', 'experiment_mode'];
const WARP = ['warp_hfov', 'warp_depth_ratio', 'warp_invert_depth', 'warp_smooth_depth', 'warp_aim',
  'warp_pivot_depth', 'warp_direction', 'warp_length', 'warp_long_side'];
const OFFSETS = ['warp_offset_azimuth', 'warp_offset_elevation', 'warp_offset_distance'];
const V30 = [...V29, 'depth_animation', ...WARP];
const V31 = [...V29, 'depth_animation', ...WARP, ...OFFSETS, 'warp_hold_at', 'warp_hold_frames', 'warp_format'];
// A v31 publicada não tinha runtime_task, prompt_detail nem freeze_index como widgets.
const V31_SLIM = V31.filter(name => !['runtime_task', 'prompt_detail', 'freeze_index'].includes(name));
const V30_SLIM = V30.filter(name => !['runtime_task', 'prompt_detail', 'freeze_index'].includes(name));
export const LEGACY_WIDGETS = V31_SLIM;
export const LAYOUTS = [V31_SLIM, V31, V30_SLIM, V30, V29];

const slotName = input => input?.widget?.name ?? input?.name;

/**
 * Migra um gráfico serializado no lugar.
 * @param {object} graph  conteúdo do .json do workflow
 * @param {string[]} current  nomes dos widgets da versão atual, na ordem (opcional)
 * @returns {{nodes:number, links:number, dropped:number, texts:string[]}}
 */
/**
 * Quanto uma leitura dos valores antigos combina com o que cada widget aceita hoje.
 * Só conta o que dá para checar: listas de opções e campos numéricos.
 */
export function scoreLayout(values, order, spec, current) {
  if (!spec) return order === current ? 1 : 0;
  const read = new Map(order.slice(0, values.length).map((name, index) => [name, values[index]]));
  let score = 0;
  for (const name of current) {
    const field = spec[name];
    if (!field || !read.has(name)) continue;
    const value = read.get(name);
    if (Array.isArray(field.options)) score += field.options.includes(value) ? 1 : -1;
    else if (field.numeric) score += typeof value === 'number' ? 1 : -1;
    else if (field.boolean) score += typeof value === 'boolean' ? 1 : -1;
  }
  return score;
}

/**
 * Migra um gráfico serializado no lugar.
 * @param {object} graph  conteúdo do .json do workflow
 * @param {string[]} current  nomes dos widgets da versão atual, na ordem
 * @param {object} spec  { nome: {options|numeric|boolean} } do node atual, para validar a leitura
 * @returns {{nodes:number, links:number, dropped:number, texts:string[], layout:string}}
 */
export function migrateGraph(graph, current = null, spec = null) {
  const report = { nodes: 0, links: 0, dropped: 0, texts: [], layout: '' };
  if (!graph) return report;
  // Um Camera H3 dentro de um subgraph tem os mesmos widgets e os mesmos links posicionais,
  // e o ComfyUI monta essas definições separadamente — sem isto, só o nível de cima era migrado.
  for (const definition of graph.definitions?.subgraphs ?? []) {
    const inner = migrateGraph(definition, current, spec);
    report.nodes += inner.nodes; report.links += inner.links; report.dropped += inner.dropped;
    report.texts.push(...inner.texts);
    report.layout = report.layout || inner.layout;
  }
  if (!Array.isArray(graph.nodes)) return report;
  const order = current || LEGACY_WIDGETS.filter(name => !REMOVED.includes(name));
  const removed = new Set(REMOVED);
  const remaps = new Map();   // id do node -> (slot antigo -> slot novo)
  const orphans = new Set();  // links que apontavam para um widget que não existe mais

  for (const node of graph.nodes) {
    if (node?.type !== NODE_TYPE) continue;
    let touched = false;

    // 1) valores: escolhe a ordem antiga que melhor encaixa nas opções de hoje.
    const values = node.widgets_values;
    if (Array.isArray(values) && values.length) {
      let best = { layout: order, score: scoreLayout(values, order, spec, order), name: 'atual' };
      for (const candidate of LAYOUTS) {
        const score = scoreLayout(values, candidate, spec, order);
        if (score > best.score) best = { layout: candidate, score, name: `${candidate.length} widgets` };
      }
      if (best.layout !== order) {
        const read = new Map(best.layout.slice(0, values.length).map((name, index) => [name, values[index]]));
        const text = String(read.get('instruction') ?? '').trim();
        if (text) report.texts.push(text);
        node.widgets_values = order.map((name, index) => read.has(name) ? read.get(name) : values[index]);
        report.layout = best.name;
        touched = true;
      }
    }

    // 2) entradas: descarta as que sumiram e guarda o deslocamento dos slots.
    if (Array.isArray(node.inputs)) {
      const map = new Map();
      const kept = [];
      node.inputs.forEach((input, index) => {
        if (removed.has(slotName(input)) || (spec && slotName(input) && !spec[slotName(input)] &&
            !['reference_image', 'depth', 'moge_geometry'].includes(slotName(input)))) {
          if (input?.link != null) orphans.add(input.link);
          return;
        }
        map.set(index, kept.length);
        kept.push(input);
      });
      if (kept.length !== node.inputs.length) {
        node.inputs = kept;
        remaps.set(node.id, map);
        touched = true;
      }
    }
    if (touched) report.nodes++;
  }
  if (!remaps.size) return report;

  // 3) links: [id, origem, slot_origem, destino, slot_destino, tipo]. Só o destino muda.
  const fix = link => {
    const id = Array.isArray(link) ? link[0] : link?.id;
    const target = Array.isArray(link) ? link[3] : link?.target_id;
    const slot = Array.isArray(link) ? link[4] : link?.target_slot;
    if (orphans.has(id)) return false;
    const map = remaps.get(target);
    if (!map) return true;
    if (!map.has(slot)) return false;
    const next = map.get(slot);
    if (next !== slot) {
      if (Array.isArray(link)) link[4] = next; else link.target_slot = next;
      report.links++;
    }
    return true;
  };
  for (const key of ['links', 'floatingLinks']) {
    if (Array.isArray(graph[key])) {
      const before = graph[key].length;
      graph[key] = graph[key].filter(fix);
      report.dropped += before - graph[key].length;
    }
  }
  // Uma saída pode listar um link que deixou de existir.
  const alive = new Set((graph.links || []).map(link => Array.isArray(link) ? link[0] : link?.id));
  for (const node of graph.nodes) {
    for (const output of node?.outputs || []) {
      if (Array.isArray(output.links)) output.links = output.links.filter(id => alive.has(id));
    }
  }
  return report;
}

// =============================================================================
// Trava definitiva: valores gravados por NOME dentro do próprio node
// =============================================================================
// O ComfyUI guarda widgets_values por POSIÇÃO, então qualquer widget que eu acrescente, remova ou
// mova embaralha todo workflow salvo antes. Gravando também um mapa nome -> valor em node.properties
// (que o ComfyUI serializa junto), o carregamento passa a não depender de ordem nenhuma: o que foi
// salvo a partir daqui sobrevive a qualquer mudança futura no node.
// ComfyUI stores widgets_values BY POSITION, so any widget added, removed or moved scrambles every
// previously saved workflow. Writing a name -> value map into node.properties (serialised by ComfyUI)
// makes loading order-independent: anything saved from here on survives future node changes.

export const VALUES_KEY = 'bruxos_widget_values';

export function packValues(widgets) {
  const out = {};
  for (const widget of widgets || []) {
    if (widget?.name != null && typeof widget.value !== 'object') out[widget.name] = widget.value;
  }
  return out;
}

/** -> quantos widgets foram restaurados por nome. */
export function applyValues(widgets, saved) {
  if (!saved || typeof saved !== 'object') return 0;
  let restored = 0;
  for (const widget of widgets || []) {
    if (widget?.name != null && Object.prototype.hasOwnProperty.call(saved, widget.name)) {
      const value = saved[widget.name];
      if (widget.value !== value) widget.value = value;
      restored++;
    }
  }
  return restored;
}

/**
 * Rede de segurança para arquivos já salvos embaralhados: um widget de lista com valor fora das
 * opções volta ao padrão, em vez de derrubar a execução com "Value not in list".
 * -> nomes dos widgets que foram corrigidos.
 */
export function sanitizeWidgets(widgets, spec) {
  const fixed = [];
  if (!spec) return fixed;
  for (const widget of widgets || []) {
    const field = spec[widget?.name];
    if (!field) continue;
    const value = widget.value;
    if (Array.isArray(field.options)) {
      if (!field.options.includes(value)) { widget.value = field.default ?? field.options[0]; fixed.push(widget.name); }
    } else if (field.numeric && typeof value !== 'number') {
      const parsed = Number(value);
      widget.value = Number.isFinite(parsed) ? parsed : (field.default ?? 0);
      fixed.push(widget.name);
    } else if (field.boolean && typeof value !== 'boolean') {
      widget.value = field.default ?? false; fixed.push(widget.name);
    }
  }
  return fixed;
}
