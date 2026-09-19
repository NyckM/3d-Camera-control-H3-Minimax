# Third-party notices

## ComfyUI-CrossViewWarp

`depth_warp.py` (functions `reference_warp_frame`, `look_at`, `rot_x`, `rot_y`, `orbit_pose`,
`depth_to_z`, and the painter/splat format reproduced by `PointCloud.render`) and the orbit math in
`web/depth-warp.js` are adapted from ComfyUI-CrossViewWarp by cseti007:
https://github.com/cseti007/ComfyUI-CrossViewWarp (`crossview_warp_node.py`).

Licensed under the Apache License, Version 2.0: http://www.apache.org/licenses/LICENSE-2.0

Changes: the per-offset splat loop was replaced by a per-base-pixel winner selection that produces
identical output (see `tests/test_v30_depth.py`); frame timing, pivot estimation from `subject_box`,
path offsets and the browser z-buffer preview are new.

Unless required by applicable law or agreed to in writing, software distributed under the License is
distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

## Viggle Meridian

`depth_warp.py` (`meridian_render_reference`, `meridian_render`, `meridian_keep`, `scale_k`, the canvas
ladders and the 480/768 bucket rule) is adapted from Viggle AI's Meridian release
(https://huggingface.co/Viggle/Meridian, `recam/geometry.py` and `recam/h3.py`), Apache License 2.0.
`meridian_nodes.py` follows the reference layout described there. No Meridian weights, prompts or
embeddings are redistributed here; those are covered by the MiniMax H3 Community License.

## Hugging Face diffusers

The transformer/LoRA key mapping in `meridian_convert.py` is the inverse of
`scripts/convert_minimax_h3_to_diffusers.py` and
`src/diffusers/loaders/lora_conversion_utils.py` from huggingface/diffusers, Apache License 2.0.
