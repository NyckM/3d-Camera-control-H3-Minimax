// Resolves the picture behind the node's reference_image input, so the panel can show the
// image the workflow already loaded instead of making the user pick the same file twice.
// Kept free of ComfyUI imports so it can be tested on its own.
export function resolveLinkedImage(graph, node, apiURL) {
  const input = node?.inputs?.find(i => i.name === 'reference_image');
  if (!input || input.link == null || !graph) return '';
  let linkId = input.link, origin = null, hops = 0;
  const seen = new Set();
  while (linkId != null && hops++ < 12) {
    const link = graph.links?.[linkId];
    if (!link) break;
    const upstream = graph.getNodeById?.(link.origin_id);
    if (!upstream || seen.has(upstream)) break;
    seen.add(upstream);
    origin = upstream;
    // Stop at the first node that can actually hand us pixels.
    if (upstream.imgs?.length) break;
    if (upstream.widgets?.some(w => w.name === 'image')) break;
    // Otherwise keep walking back through Reroute and other pass-through nodes.
    const next = upstream.inputs?.find(i => i.type === 'IMAGE' && i.link != null);
    linkId = next ? next.link : null;
  }
  if (!origin) return '';
  // A node that already rendered a preview: LoadImage, PreviewImage, an executed output.
  const preview = origin.imgs?.find(img => img?.src);
  if (preview) return preview.src;
  // LoadImage before anything ran: read its widget and ask the server for the input file.
  const widget = origin.widgets?.find(w => w.name === 'image');
  if (typeof widget?.value === 'string' && widget.value) {
    const value = widget.value, cut = value.lastIndexOf('/');
    const subfolder = cut >= 0 ? value.slice(0, cut) : '';
    const filename = cut >= 0 ? value.slice(cut + 1) : value;
    const query = `/view?filename=${encodeURIComponent(filename)}&type=input&subfolder=${encodeURIComponent(subfolder)}`;
    return apiURL ? apiURL(query) : query;
  }
  return '';
}
