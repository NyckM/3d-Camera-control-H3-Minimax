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

// Ordem dos widgets até a v31, usada para ler widgets_values antigos por nome.
export const LEGACY_WIDGETS = ['camera_trajectory', 'profile', 'interpolation', 'instruction', 'subject_framing',
  'minimax_format', 'elevation_range', 'orbit_direction', 'subject_box', 'runtime_task', 'prompt_detail',
  'frame_mode', 'source_fps', 'freeze_index', 'ui_language', 'loop_closure', 'experiment_mode', 'depth_animation',
  'warp_hfov', 'warp_depth_ratio', 'warp_invert_depth', 'warp_smooth_depth', 'warp_aim', 'warp_pivot_depth',
  'warp_direction', 'warp_length', 'warp_long_side', 'warp_offset_azimuth', 'warp_offset_elevation',
  'warp_offset_distance', 'warp_hold_at', 'warp_hold_frames', 'warp_format'];

const slotName = input => input?.widget?.name ?? input?.name;

/**
 * Migra um gráfico serializado no lugar.
 * @param {object} graph  conteúdo do .json do workflow
 * @param {string[]} current  nomes dos widgets da versão atual, na ordem (opcional)
 * @returns {{nodes:number, links:number, dropped:number, texts:string[]}}
 */
export function migrateGraph(graph, current = null) {
  const report = { nodes: 0, links: 0, dropped: 0, texts: [] };
  if (!graph || !Array.isArray(graph.nodes)) return report;
  const removed = new Set(REMOVED);
  const remaps = new Map();   // id do node -> (slot antigo -> slot novo)
  const orphans = new Set();  // links que apontavam para um widget que não existe mais

  for (const node of graph.nodes) {
    if (node?.type !== NODE_TYPE) continue;
    let touched = false;

    // 1) valores: lê por nome na ordem antiga e reescreve na ordem atual.
    const values = node.widgets_values;
    if (Array.isArray(values) && values.length > LEGACY_WIDGETS.length - REMOVED.length) {
      const legacy = new Map(LEGACY_WIDGETS.slice(0, values.length).map((name, index) => [name, values[index]]));
      const text = String(legacy.get('instruction') ?? '').trim();
      if (text) report.texts.push(text);
      const order = current || LEGACY_WIDGETS.filter(name => !removed.has(name));
      node.widgets_values = order.map((name, index) => legacy.has(name) ? legacy.get(name) : values[index]);
      touched = true;
    }

    // 2) entradas: descarta as que sumiram e guarda o deslocamento dos slots.
    if (Array.isArray(node.inputs)) {
      const map = new Map();
      const kept = [];
      node.inputs.forEach((input, index) => {
        if (removed.has(slotName(input))) {
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
