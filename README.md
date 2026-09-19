# Meridian Camera H3 — INT8 by Bruxos do VFX

ComfyUI-ready INT8 build of **Viggle/Meridian** for MiniMax H3, integrated with **bruxosdovfx · Camera H3** for depth-based camera warping.

Build INT8 do **Viggle/Meridian** preparado para ComfyUI, integrado ao **bruxosdovfx · Camera H3** para recâmera usando depth warp.

> This is not an official MiniMax or Viggle release.  
> Este não é um lançamento oficial da MiniMax ou Viggle.

---

## 📦 Download / Downloads

All Meridian-specific files are available here:

https://huggingface.co/NyckM/Meridian_CameraH3_INT8_build_by_BruxosdoVFX/tree/main

| File / Arquivo | Use / Uso | ComfyUI folder / Pasta |
|---|---|---|
| `MeridianH3Camera_int8_pruned.safetensors` | Meridian H3 diffusion model / Modelo diffusion Meridian H3 | `ComfyUI/models/diffusion_models/H3camera/` |
| `meridian_dmd_lora_comfyui.safetensors` | Meridian DMD LoRA | `ComfyUI/models/loras/` |
| `meridian_fixed_embed_73.safetensors` | Fixed text embedding — 73 frames | Meridian text-embed folder used by `BruxosMeridianTextCond` |
| `meridian_fixed_embed_90.safetensors` | Fixed text embedding — 90 frames | same / mesma pasta |
| `meridian_fixed_embed_107.safetensors` | Fixed text embedding — 107 frames | same / mesma pasta |
| `meridian_fixed_embed_124.safetensors` | Fixed text embedding — 124 frames | same / mesma pasta |
| `meridian_fixed_embed_141.safetensors` | Fixed text embedding — 141 frames | same / mesma pasta |
| `meridian_fixed_embed_158.safetensors` | Fixed text embedding — 158 frames | same / mesma pasta |
| `meridian_fixed_embed_175.safetensors` | Fixed text embedding — 175 frames | same / mesma pasta |
| `meridian_fixed_embed_243.safetensors` | Fixed text embedding — 243 frames | same / mesma pasta |

> Add the exact text-embed folder used by `BruxosMeridianTextCond` here once the node path is finalized.  
> Adicione aqui a pasta exata usada pelo `BruxosMeridianTextCond` quando o caminho do node estiver definido.

---

## 🧩 Required models / Modelos necessários

| Component / Componente | File / Arquivo | Source / Fonte | Folder / Pasta |
|---|---|---|---|
| Meridian model | `MeridianH3Camera_int8_pruned.safetensors` | Bruxos do VFX HF | `models/diffusion_models/H3camera/` |
| Meridian LoRA | `meridian_dmd_lora_comfyui.safetensors` | Bruxos do VFX HF | `models/loras/` |
| H3 3-step LoRA | `minimax_h3_taomate_3step_lora_avg_rank_19_bf16.safetensors` | Kijai MiniMax-H3 comfy | `models/loras/` |
| H3 Video VAE INT8 | `minimax_h3_video_vae_int8_convrot.safetensors` | Comfy-Org / Kijai | `models/vae/` |
| MoGe | `moge_2_vitl_normal.safetensors` | ComfyUI MoGe | Select in `Load MoGe Model` |
| Meridian text embed | `meridian_fixed_embed_<frames>.safetensors` | Bruxos do VFX HF | Used by `BruxosMeridianTextCond` |

H3 3-step LoRA:
https://huggingface.co/Kijai/MiniMax-H3_comfy/tree/main/loras

H3 Video VAE:
https://huggingface.co/Comfy-Org/MiniMax-H3/tree/main/vae

---

## 🧱 Custom nodes used / Custom nodes usados

| Package / Pacote | Nodes used / Nodes usados | Purpose / Função |
|---|---|---|
| `NyckM/3d-Camera-control-H3-Minimax` | `BruxosH3Camera`, `BruxosH3SubjectBox` | Camera path, subject pivot and Meridian depth warp / trajetória, pivô do sujeito e depth warp |
| Bruxos do VFX Nodes | `BruxosLoadVideo` | Video loading / carregamento de vídeo |
| Meridian Bruxos nodes | `BruxosMeridianReference`, `BruxosMeridianTextCond` | Meridian conditioning, references and fixed text embeddings |
| `ComfyUI-Custom-Scripts` | `ShowText|pysssss` | Displays Meridian report / exibe relatório |
| `ComfyUI-Pixaroma` | `PixaromaLabel` | Workflow labels only / apenas organização visual |
| ComfyUI Core | MoGe, sampler, VAE, video, scheduler and model nodes | Native workflow nodes / nodes nativos |

Camera H3:
https://github.com/NyckM/3d-Camera-control-H3-Minimax

Bruxos do VFX Nodes:
https://github.com/NyckM/Bruxos-do-VFX-Nodes

ComfyUI Custom Scripts:
https://github.com/pythongosssss/ComfyUI-Custom-Scripts

Pixaroma:
https://github.com/pixaroma/ComfyUI-Pixaroma

---

## 🎥 Workflow / Fluxo

```text
Source Video
    ↓
Resize to reference resolution
    ↓
MoGe Geometry
    ↓
Camera H3 — Meridian Depth Warp
    ↓
Meridian Reference
    ↓
Meridian H3 + DMD LoRA + H3 3-step LoRA
    ↓
Euler Sampler
    ↓
H3 Video VAE
    ↓
Video
```

The camera motion comes from the **warp video**, not from the text prompt.

O movimento de câmera vem do **warp video**, não do prompt de texto.

---

## ⚙️ Recommended settings / Configurações recomendadas

| Setting | Value |
|---|---|
| FPS | `24` |
| Sampler | `Euler` |
| CFG | `1.0` |
| H3 Sigma Shift | `3.0 / 3.0` |
| DMD sigmas | `1.0, 0.8571428571428571, 0.6, 0.0` |
| Reference resolution | around `832 × 480` |
| Generation resolution | around `1344 × 768` |

Supported frame counts / Quantidades suportadas:

`73 · 90 · 107 · 124 · 141 · 158 · 175 · 243`

### Important / Importante

These values must match:

```text
frame_load_cap
=
warp_length
=
Meridian Reference length
=
text embedding frame count
```

Example / Exemplo:

```text
124
=
124
=
124
=
meridian_fixed_embed_124.safetensors
```

---

## ⚠️ Workflow checks / Ajustes importantes

Before publishing the workflow, update these points:

1. **Change `frame_load_cap` from `121` to `124`.**  
   **Troque `frame_load_cap` de `121` para `124`.**

2. The workflow currently references:

```text
H3Camera/MeridianH3Camera.safetensors
```

but the published file is:

```text
H3camera/MeridianH3Camera_int8_pruned.safetensors
```

Update the workflow dropdown to the published filename.

Atualize o dropdown da workflow para usar o mesmo nome do arquivo publicado.

3. Confirm and document the folder scanned by:

```text
BruxosMeridianTextCond
```

so users know exactly where to place the `meridian_fixed_embed_*.safetensors` files.

4. The `PixaromaLabel` nodes are cosmetic. They can be removed if you want fewer custom-node dependencies.

Os nodes `PixaromaLabel` são apenas visuais e podem ser removidos para reduzir dependências.

5. `ShowText|pysssss` is also optional for generation; it only displays the Meridian report.

O `ShowText|pysssss` também é opcional para gerar; ele apenas mostra o relatório.

---

## 📐 Camera H3

Useful controls / Controles principais:

- `warp_hfov` — source lens / lente do vídeo original
- `subject_box` — subject orbit target / alvo da órbita
- `warp_pivot_depth` — manual depth pivot / pivô manual de profundidade
- `warp_offset_azimuth` — initial horizontal camera offset
- `warp_offset_elevation` — initial vertical offset
- `warp_offset_distance` — camera distance
- `warp_hold_at` + `warp_hold_frames` — hold action while camera keeps moving
- `warp_format = Meridian (H3)`

Large camera changes may become unstable.

Mudanças muito grandes de câmera podem gerar instabilidade.

---

## 📜 License / Licença

This build is derived from **MiniMax H3** and **Viggle/Meridian**.

Esta build é derivada do **MiniMax H3** e do **Viggle/Meridian**.

Read the licenses and notices of the original models before commercial use or redistribution.

Leia as licenças e avisos dos modelos originais antes de uso comercial ou redistribuição.
