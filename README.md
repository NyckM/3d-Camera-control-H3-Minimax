# Meridian Camera H3 — by Bruxos do VFX

**Depth-based camera re-control for MiniMax H3 + Viggle Meridian inside ComfyUI.**  
**Recâmera baseada em profundidade para MiniMax H3 + Viggle Meridian dentro do ComfyUI.**

> Create new camera motion from an existing video using **MoGe + Camera H3 + Meridian**.  
> Crie um novo movimento de câmera a partir de um vídeo existente usando **MoGe + Camera H3 + Meridian**.

> This is not an official MiniMax or Viggle release.  
> Este não é um lançamento oficial da MiniMax ou Viggle.

<img width="581" height="1435" alt="image" src="https://github.com/user-attachments/assets/1cdaef43-e001-45be-acd7-9dd884840d7f" />

https://github.com/user-attachments/assets/3c958ca8-9685-440c-afc3-52da9d1f7143

---

## ✨ How it works / Como funciona

The source video is converted to geometry with **MoGe**.  
**Camera H3** reprojects it from a new virtual camera and creates the Meridian Depth Warp.  
Meridian uses that warped video as the camera guide for the final generation.

O vídeo original é convertido em geometria com **MoGe**.  
O **Camera H3** reprojeta a cena a partir de uma nova câmera virtual e cria o Depth Warp do Meridian.  
O Meridian usa esse vídeo reprojetado como guia para a geração final.

```text
Source Video
    ↓
MoGe Geometry
    ↓
Camera H3 — Depth Warp
    ↓
Meridian
    ↓
Final Video
```

**The camera comes from the Depth Warp — not from the text prompt.**  
**A câmera vem do Depth Warp — não do prompt de texto.**

---

## 🎥 Two workflows / Dois workflows

| Workflow | Base | Use / Uso |
|---|---|---|
| **Meridian INT8 — Quality** | Converted Meridian INT8 diffusion model | **Best visual quality in our current tests** / **Melhor qualidade visual nos testes atuais** |
| **Meridian LoRA — H3 Base** | MiniMax H3 FL2VA + Meridian Teacher + Turbo | Lighter and keeps the standard H3 base / Mais leve e mantém a base H3 padrão |

### 🟣 Meridian INT8 — Quality

Uses the converted Meridian model, DMD LoRA and H3 3-step LoRA.  
Usa o modelo Meridian convertido, DMD LoRA e H3 3-step LoRA.

**Recommended when final image quality is the priority.**  
**Recomendado quando a prioridade é a qualidade final.**

https://github.com/user-attachments/assets/dd73c770-727b-4b9a-9833-e4651eb7f8df

### 🔵 Meridian LoRA — H3 Base

Uses the original **MiniMax H3 FL2VA** base with the official Meridian **Teacher → Turbo** adapters.

Usa a base original **MiniMax H3 FL2VA** com os adaptadores oficiais Meridian **Teacher → Turbo**.

> Teacher must be loaded before Turbo. Do not use Turbo alone.  
> A Teacher deve ser carregada antes da Turbo. Não use a Turbo sozinha.

---

## 📦 Requirements / Requisitos

All models and custom nodes used by both workflows are listed here.  
Todos os modelos e custom nodes usados pelos dois workflows estão nesta tabela.

| Type | Workflow | Model / Node | Link | Function / Função | Local |
|---|---|---|---|---|---|
| **Model** | Quality | `MeridianH3Camera_int8_pruned.safetensors` | [Download](https://huggingface.co/NyckM/Meridian_CameraH3_INT8_build_by_BruxosdoVFX/tree/main/diffusion_models/H3camera) | Converted Meridian INT8 model / Modelo Meridian INT8 convertido | `models/diffusion_models/H3camera/` |
| **LoRA** | Quality | `meridian_dmd_lora_comfyui.safetensors` | [Download](https://huggingface.co/NyckM/Meridian_CameraH3_INT8_build_by_BruxosdoVFX/blob/main/lora/meridian_dmd_lora_comfyui.safetensors) | Meridian DMD acceleration | `models/loras/` |
| **LoRA** | Quality | `minimax_h3_taomate_3step_lora_avg_rank_19_bf16.safetensors` | [Download](https://huggingface.co/Kijai/MiniMax-H3_comfy/tree/main/loras) | H3 3-step acceleration / Aceleração H3 em 3 steps | `models/loras/minimax/` |
| **Text Embed** | Quality | `meridian_fixed_embed_<frames>.safetensors` | [Download](https://huggingface.co/NyckM/Meridian_CameraH3_INT8_build_by_BruxosdoVFX/tree/main) | Fixed Meridian conditioning / Conditioning fixo do Meridian | Meridian text-cond folder |
| **Model** | LoRA | `minimax_h3_fl2va_bf16.safetensors` | [Download](https://huggingface.co/Comfy-Org/MiniMax-H3/blob/main/diffusion_models/minimax_h3_fl2va_bf16.safetensors) | Official H3 FL2VA base / Base oficial H3 FL2VA | `models/diffusion_models/Minimax/` |
| **LoRA** | LoRA | `meridian_teacher_lora.safetensors` | [Download](https://huggingface.co/Viggle/Meridian/tree/main/comfyui) | Meridian camera teacher adapter | `models/loras/` |
| **LoRA** | LoRA | `meridian_turbo_lora.safetensors` | [Download](https://huggingface.co/Viggle/Meridian/tree/main/comfyui) | Meridian turbo adapter | `models/loras/` |
| **Text Encoder** | LoRA* | `qwen3vl_32b_minimax_h3_int8_convrot.safetensors` | [Download](https://huggingface.co/Comfy-Org/MiniMax-H3/tree/main/text_encoders) | H3 text encoder for editable prompts/references / Text encoder para prompts e referências | `models/text_encoders/` |
| **VAE** | Both | `minimax_h3_video_vae_int8_convrot.safetensors` | [Download](https://huggingface.co/Comfy-Org/MiniMax-H3/tree/main/vae) | H3 Video VAE | `models/vae/Minimax/` |
| **Depth** | Both | `moge_2_vitl_normal.safetensors` | [MoGe](https://github.com/microsoft/MoGe) | Geometry/depth estimation / Estimativa de geometria e profundidade | Select in `Load MoGe Model` |
| **Custom Node** | Both | **Camera H3 — Bruxos do VFX** | [GitHub](https://github.com/NyckM/3d-Camera-control-H3-Minimax) | Camera editor, Depth Warp and Meridian Reference / Editor de câmera, Depth Warp e Meridian Reference | `custom_nodes/` |
| **Custom Node** | Both | **Bruxos do VFX H3 Frames** | [GitHub](https://github.com/NyckM/Minimax-h3) | Valid H3 frame grid / Grade válida de frames H3 | `custom_nodes/` |
| **Custom Node** | Both | **Bruxos do VFX Compare** | [GitHub](https://github.com/NyckM/Video-Util-ComfYUI) | Video comparison / Comparação de vídeo | `custom_nodes/` |
| **Custom Node** | Both | **ComfyUI-Custom-Scripts** | [GitHub](https://github.com/pythongosssss/ComfyUI-Custom-Scripts) | `ShowText` / relatório | `custom_nodes/` |
| **Custom Node** | Both | **ComfyUI-Pixaroma** | [GitHub](https://github.com/pixaroma/ComfyUI-Pixaroma) | Workflow labels / Labels visuais | `custom_nodes/` |

\* The Qwen text encoder is needed when using the editable H3 text/reference path.  
\* O Qwen text encoder é necessário quando você usa o caminho editável de texto/referências do H3.

### Main download repositories / Repositórios principais

- [Bruxos do VFX — Meridian INT8 build](https://huggingface.co/NyckM/Meridian_CameraH3_INT8_build_by_BruxosdoVFX/tree/main)
- [Viggle — Meridian](https://huggingface.co/Viggle/Meridian)
- [Comfy-Org — MiniMax H3](https://huggingface.co/Comfy-Org/MiniMax-H3)
- [Kijai — MiniMax H3](https://huggingface.co/Kijai/MiniMax-H3_comfy)

---

## 🧭 Camera H3 + Depth Warp

Set:

```text
depth_animation = Depth Warp
warp_format = Meridian (H3)
```

`<Video 1>` is the original source video.  
`<Video 2>` is the Depth Warp generated by Camera H3.

`<Video 1>` é o vídeo original.  
`<Video 2>` é o Depth Warp gerado pelo Camera H3.

Gray areas are parts of the scene that were not visible from the source camera and must be reconstructed by Meridian/H3.

As áreas cinzas são regiões que não eram visíveis na câmera original e precisam ser reconstruídas pelo Meridian/H3.

### Main controls / Controles principais

| Control | Use / Uso |
|---|---|
| `camera_trajectory` | Camera keyframes / Keyframes da câmera |
| `subject_box` | Orbit target / Alvo da órbita |
| `warp_hfov` | Source camera FOV / FOV da câmera original |
| `warp_pivot_depth` | Orbit depth pivot / Pivô de profundidade |
| `warp_offset_azimuth` | Horizontal starting offset |
| `warp_offset_elevation` | Vertical starting offset |
| `warp_offset_distance` | Camera distance |
| `warp_hold_at` + `warp_hold_frames` | Bullet-time hold / Congela a ação enquanto a câmera continua |

---

## ⏱ Frames and settings / Frames e configurações

Supported Meridian lengths:

```text
73 · 90 · 107 · 124 · 141 · 158 · 175 · 243
```

For the **Quality / fixed-embedding workflow**, these values must match:

```text
frame count
=
warp length
=
Meridian Reference length
=
fixed text embedding length
```

Example:

```text
124
=
124
=
124
=
meridian_fixed_embed_124.safetensors
```

Recommended / Recomendado:

| Setting | Value |
|---|---|
| FPS | `24` |
| Sampler | `Euler` |
| CFG | `1.0` |
| MiniMax H3 shift | `3.0 / 3.0` |
| DMD sigmas | `1.0, 0.8571428571428571, 0.6, 0.0` |
| Warp format | `Meridian (H3)` |
| Typical output | around `1344 × 768` |

---

## 🔧 Basic use / Uso básico

1. Load the source video at **24 fps**. / Carregue o vídeo original em **24 fps**.
2. Run **MoGe** geometry estimation. / Gere a geometria com **MoGe**.
3. Create the camera path in **Camera H3**. / Crie a trajetória no **Camera H3**.
4. Enable **Depth Warp → Meridian (H3)** and check the preview. / Ative **Depth Warp → Meridian (H3)** e confira o preview.
5. Choose **Quality INT8** or **LoRA H3** and generate. / Escolha **Quality INT8** ou **LoRA H3** e gere.

> If the Depth Warp geometry is already wrong, the final model receives a bad camera guide.  
> Se a geometria do Depth Warp já estiver errada, o modelo final receberá um guia de câmera incorreto.

---

## ⚠️ Limitations / Limitações

- Large camera changes expose more unseen geometry and can become unstable. / Mudanças grandes de câmera revelam mais geometria ausente e podem ficar instáveis.
- Incorrect depth produces incorrect reprojection. / Profundidade incorreta gera reprojeção incorreta.
- Source-camera motion is harder than a locked shot. / Movimento na câmera original é mais difícil que plano travado.
- Depth Warp is a control signal; the final reconstruction is generated by Meridian/H3. / O Depth Warp é um sinal de controle; a reconstrução final é gerada pelo Meridian/H3.
- 
🙏 Acknowledgements

Special thanks to the creators and contributors behind H3 Edit, Viggle Meridian, and LTX Cross View Warp. Their work, research, implementations, and open releases were essential references for understanding camera control, view reprojection, depth-based warping, and multi-view generation workflows.

This project builds on ideas and techniques made possible by those communities, and we are grateful for the tools, documentation, experiments, and knowledge they shared with the open-source ecosystem.


---

## 📜 License / Licença

This project integrates tools and workflows around **MiniMax H3** and **Viggle Meridian**. Model weights remain subject to the licenses of their original authors.

Este projeto integra ferramentas e workflows ao redor do **MiniMax H3** e **Viggle Meridian**. Os pesos continuam sujeitos às licenças de seus autores originais.

Read the current MiniMax H3, Viggle Meridian and third-party node licenses before commercial use or redistribution.

Leia as licenças atuais do MiniMax H3, Viggle Meridian e dos nodes de terceiros antes de uso comercial ou redistribuição.

---

## 🧙 Bruxos do VFX

Developed and adapted for ComfyUI by **Bruxos do VFX**.  
Desenvolvido e adaptado para ComfyUI por **Bruxos do VFX**.

- [Camera H3](https://github.com/NyckM/3d-Camera-control-H3-Minimax)
- [H3 Frames](https://github.com/NyckM/Minimax-h3)
- [Video Compare](https://github.com/NyckM/Video-Util-ComfYUI)
- [Meridian INT8 models](https://huggingface.co/NyckM/Meridian_CameraH3_INT8_build_by_BruxosdoVFX/tree/main)
