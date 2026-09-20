# Meridian Camera H3 — by Bruxos do VFX

**Depth-based camera re-control for MiniMax H3 + Viggle Meridian inside ComfyUI.**  
**Recâmera baseada em profundidade para MiniMax H3 + Viggle Meridian dentro do ComfyUI.**

> Create a new camera movement from an existing video using **MoGe depth**, **Camera H3** and **Meridian**.  
> Crie um novo movimento de câmera a partir de um vídeo existente usando **profundidade MoGe**, **Camera H3** e **Meridian**.

> This is not an official MiniMax or Viggle release.  
> Este não é um lançamento oficial da MiniMax ou Viggle.

---

## ✨ What is it? / O que é?

**Meridian Camera H3** connects the camera tools from **bruxosdovfx · Camera H3** with **Viggle Meridian**.

The source video is converted into geometry with **MoGe**, the Camera H3 node reprojects the scene from a new virtual camera, and Meridian uses this warped video as the camera guide for the final generation.

**Meridian Camera H3** conecta as ferramentas de câmera do **bruxosdovfx · Camera H3** ao **Viggle Meridian**.

O vídeo original é convertido em geometria com **MoGe**, o Camera H3 reprojeta a cena a partir de uma nova câmera virtual e o Meridian usa esse vídeo reprojetado como guia para gerar o resultado final.

```text
Source Video
    ↓
MoGe Geometry
    ↓
Camera H3
    ↓
Depth Warp / New Camera View
    ↓
Meridian
    ↓
MiniMax H3 generation
    ↓
Final Video
```

**The camera motion comes from the Depth Warp, not from a text description.**  
**O movimento de câmera vem do Depth Warp, não de uma descrição em texto.**

---

# 🎥 Two workflows / Dois workflows

The repository includes **two Meridian workflows**.

O repositório inclui **dois workflows do Meridian**.

| Workflow | Base | Main advantage / Principal vantagem | Recommended for / Recomendado para |
|---|---|---|---|
| **Meridian INT8 — Quality** | Converted Meridian diffusion model | **Best quality in our current workflow** / **Melhor qualidade no workflow atual** | Final renders / renders finais |
| **Meridian LoRA — H3 Base** | Standard MiniMax H3 + Meridian LoRAs | Keeps the normal H3 model, prompt and reference pipeline / Mantém o modelo H3, prompt e referências | Flexibility, testing and H3 integration / flexibilidade e integração com H3 |

---

## 🟣 Workflow 1 — Meridian INT8 / Quality

### Recommended for best image quality  
### Recomendado para melhor qualidade de imagem

This workflow uses a **converted Meridian diffusion model** prepared for ComfyUI and quantized to INT8.

Este workflow usa um **modelo diffusion do Meridian convertido** para ComfyUI e quantizado em INT8.

```text
Source Video
    ↓
MoGe
    ↓
Camera H3 — Meridian Depth Warp
    ↓
Meridian Reference
    ↓
Meridian INT8 model
    ↓
Meridian DMD LoRA
    ↓
H3 3-step LoRA
    ↓
Euler Sampler
    ↓
H3 Video VAE
    ↓
Video
```

### Why use it? / Por que usar?

- **Best quality of the two workflows in our current tests**
- More faithful Meridian behavior
- Dedicated Meridian diffusion weights
- Good choice for final renders

- **Melhor qualidade entre os dois workflows nos testes atuais**
- Comportamento mais próximo do Meridian dedicado
- Pesos diffusion específicos do Meridian
- Melhor opção para render final

### Main model / Modelo principal

```text
MeridianH3Camera_int8_pruned.safetensors
```

Place it in:

```text
ComfyUI/models/diffusion_models/H3camera/
```

This workflow also uses:

```text
meridian_dmd_lora_comfyui.safetensors
minimax_h3_taomate_3step_lora_avg_rank_19_bf16.safetensors
minimax_h3_video_vae_int8_convrot.safetensors
meridian_fixed_embed_<frames>.safetensors
```

---

## 🔵 Workflow 2 — Meridian LoRA / Standard H3

### Lighter and more flexible  
### Mais leve e mais flexível

This workflow keeps the **standard MiniMax H3 model** and applies the Meridian adapters on top of it.

Este workflow mantém o **modelo MiniMax H3 padrão** e aplica os adaptadores do Meridian sobre ele.

```text
Standard MiniMax H3
    ↓
Meridian Teacher LoRA
    ↓
Meridian Turbo LoRA
    ↓
Camera H3 Depth Warp
    ↓
Meridian conditioning
    ↓
H3 generation
```

Example base used in the included workflow:

```text
Minimax-h3_Singularity_ref2va_Pruned_v1.3_int8.safetensors
```

Meridian adapters:

```text
meridian_teacher_comfyui.safetensors
meridian_turbo_comfyui.safetensors
```

### Why use it? / Por que usar?

Because the original **H3 transformer remains the base**, this version is better suited to workflows that need the normal H3 ecosystem.

Como o **transformer original do H3 continua sendo a base**, esta versão é mais indicada para workflows que precisam manter o ecossistema normal do H3.

It can preserve access to:

- H3 text prompting
- H3 image references
- Multiple references
- Existing H3 models
- Existing H3 LoRAs and workflow structures

Ela pode preservar acesso a:

- prompts de texto do H3
- referências de imagem do H3
- múltiplas referências
- modelos H3 existentes
- estruturas e LoRAs já usadas no H3

> **Quality note / Nota de qualidade:**  
> The LoRA workflow is more flexible, but the **Meridian INT8 / Quality workflow currently produces better visual quality** in our tests.  
> O workflow LoRA é mais flexível, mas o **Meridian INT8 / Quality atualmente entrega melhor qualidade visual** em nossos testes.

---

# 🧭 Camera H3

The camera movement is created with:

```text
bruxosdovfx · Camera H3
```

Repository:

https://github.com/NyckM/3d-Camera-control-H3-Minimax

The Camera H3 node defines the virtual camera trajectory used to build the Meridian guide.

O Camera H3 define a trajetória da câmera virtual usada para construir o guia do Meridian.

### Main controls / Controles principais

| Control | Function / Função |
|---|---|
| `camera_trajectory` | Camera keyframes / keyframes da câmera |
| `subject_box` | Defines the subject used as orbit target / define o sujeito usado como alvo da órbita |
| `warp_hfov` | Source camera horizontal FOV / FOV horizontal da câmera original |
| `warp_pivot_depth` | Manual orbit depth pivot / pivô manual de profundidade |
| `warp_offset_azimuth` | Starts the new camera from a different horizontal angle / inicia a câmera em outro ângulo horizontal |
| `warp_offset_elevation` | Initial vertical offset / offset vertical inicial |
| `warp_offset_distance` | Camera distance multiplier / multiplicador da distância |
| `warp_hold_at` | Frame where the action freezes / frame em que a ação congela |
| `warp_hold_frames` | Number of frozen frames while the camera continues / quantidade de frames congelados enquanto a câmera continua |
| `warp_format` | Use `Meridian (H3)` |

---

# 🧊 Depth Warp

**Depth Warp** is the bridge between Camera H3 and Meridian.

O **Depth Warp** é a ponte entre o Camera H3 e o Meridian.

It takes the source image/video and its depth information and reprojects the scene according to the new camera trajectory.

Ele recebe a imagem/vídeo original e sua profundidade e reprojeta a cena de acordo com a nova trajetória de câmera.

```text
Source frame
+
Depth / Geometry
+
Camera trajectory
=
Warped frame from the new camera
```

Areas that were never visible to the original camera become **neutral gray**.

Áreas que nunca foram vistas pela câmera original ficam em **cinza neutro**.

Those missing regions are later reconstructed by Meridian/H3.

Essas regiões ausentes são reconstruídas depois pelo Meridian/H3.

### Depth source / Fonte de profundidade

Recommended:

```text
MoGe
```

Model:

```text
moge_2_vitl_normal.safetensors
```

Typical workflow:

```text
Load MoGe Model
    ↓
MoGe Inference
    ↓
Camera H3.moge_geometry
```

---

# 🧩 Meridian Reference

`bruxosdovfx · Meridian Reference` prepares the source video, warped video, references and latent conditioning expected by Meridian.

`bruxosdovfx · Meridian Reference` prepara o vídeo original, o vídeo reprojetado, referências e conditioning latent usado pelo Meridian.

Conceptually:

```text
<Video 1> = original source video
<Video 2> = Camera H3 Depth Warp
```

The **second video is the new-camera guide**.

O **segundo vídeo é o guia da nova câmera**.

Additional image references can also be connected depending on the workflow.

Referências extras de imagem também podem ser conectadas dependendo do workflow.

---

# 🖼 References / Referências

The LoRA workflow is especially useful when you want to keep the normal H3 reference system.

O workflow LoRA é especialmente útil quando você quer manter o sistema normal de referências do H3.

Possible references include:

```text
<Picture 1>
<Picture 2>
...
<Picture 9>

<Video 1>
<Video 2>
<Video 3>
```

In Meridian:

```text
<Video 1> = source video
<Video 2> = depth-warp camera guide
```

---

# ⏱ Frame lengths / Quantidade de frames

Supported Meridian frame counts:

```text
73
90
107
124
141
158
175
243
```

These values must match across the workflow:

```text
frame_load_cap
=
warp_length
=
Meridian Reference length
=
text embedding frame count
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

If the lengths do not match, the conditioning will not represent the intended Meridian sequence correctly.

Se as durações não coincidirem, o conditioning não representará corretamente a sequência esperada pelo Meridian.

---

# ⚙️ Recommended settings / Configurações recomendadas

| Setting | Value |
|---|---|
| FPS | `24` |
| Sampler | `Euler` |
| CFG | `1.0` |
| H3 Sigma Shift | `3.0 / 3.0` |
| DMD sigmas | `1.0, 0.8571428571428571, 0.6, 0.0` |
| Warp format | `Meridian (H3)` |
| Warp reference resolution | around `832 × 480` |
| Generation resolution | around `1344 × 768` |

For faster testing, start with:

```text
73 frames
```

For a common working setup:

```text
124 frames
```

---

# 📦 Models / Modelos

Meridian-specific files:

https://huggingface.co/NyckM/Meridian_CameraH3_INT8_build_by_BruxosdoVFX/tree/main

## Quality workflow

| File | Folder |
|---|---|
| `MeridianH3Camera_int8_pruned.safetensors` | `ComfyUI/models/diffusion_models/H3camera/` |
| `meridian_dmd_lora_comfyui.safetensors` | `ComfyUI/models/loras/` |
| `minimax_h3_taomate_3step_lora_avg_rank_19_bf16.safetensors` | `ComfyUI/models/loras/` |
| `minimax_h3_video_vae_int8_convrot.safetensors` | `ComfyUI/models/vae/` |
| `meridian_fixed_embed_<frames>.safetensors` | Meridian text-embed folder |
| `moge_2_vitl_normal.safetensors` | MoGe model folder |

H3 3-step LoRA:

https://huggingface.co/Kijai/MiniMax-H3_comfy/tree/main/loras

H3 Video VAE:

https://huggingface.co/Comfy-Org/MiniMax-H3/tree/main/vae

## LoRA workflow

Requires:

```text
MiniMax H3 base model
meridian_teacher_comfyui.safetensors
meridian_turbo_comfyui.safetensors
MiniMax H3 Video VAE
MoGe
```

The **Teacher LoRA must be applied before the Turbo LoRA**.

A **Teacher LoRA deve ser aplicada antes da Turbo LoRA**.

---

# 🧱 Custom nodes / Custom nodes necessários

## Required / Necessários

### Camera H3

```text
NyckM/3d-Camera-control-H3-Minimax
```

https://github.com/NyckM/3d-Camera-control-H3-Minimax

Used for:

- camera trajectory
- subject orbit
- depth warp
- Meridian warp format
- camera offsets
- bullet-time hold

Usado para:

- trajetória de câmera
- órbita em torno do sujeito
- depth warp
- formato Meridian
- offsets de câmera
- congelamento de ação / bullet time

### Bruxos do VFX Nodes

https://github.com/NyckM/Bruxos-do-VFX-Nodes

Used for video loading and Bruxos workflow utilities.

Usado para carregamento de vídeo e utilidades dos workflows Bruxos.

### ComfyUI / MoGe

The workflow uses the ComfyUI MoGe implementation for geometry estimation.

O workflow usa a implementação MoGe do ComfyUI para estimativa de geometria.

---

## Optional / Opcionais

### ComfyUI Custom Scripts

https://github.com/pythongosssss/ComfyUI-Custom-Scripts

Used by:

```text
ShowText|pysssss
```

Only displays reports and debug information.

Serve apenas para exibir relatórios e informações de debug.

### Pixaroma

https://github.com/pixaroma/ComfyUI-Pixaroma

Used only for visual workflow labels.

Usado apenas para os labels visuais do workflow.

It can be removed without changing the generation.

Pode ser removido sem alterar a geração.

---

# 🔧 Basic workflow setup / Configuração básica

## 1. Load the source video / Carregue o vídeo

Use:

```text
24 FPS
```

The input can be a static-camera shot or a moving sequence, but strong source-camera motion can make depth reprojection less predictable.

A entrada pode ser um plano travado ou uma sequência em movimento, mas movimentos fortes da câmera original podem tornar a reprojeção de profundidade menos previsível.

---

## 2. Estimate geometry / Estime a geometria

```text
Video
↓
MoGe Inference
```

MoGe estimates the geometry used by the virtual camera.

O MoGe estima a geometria usada pela câmera virtual.

---

## 3. Create the new camera / Crie a nova câmera

Use **Camera H3** to define:

```text
Azimuth
Elevation
Distance
Subject pivot
Timing
```

The camera path can contain multiple keyframes.

A trajetória pode conter vários keyframes.

---

## 4. Enable Meridian Depth Warp

Set:

```text
depth_animation = Depth Warp
warp_format = Meridian (H3)
```

Preview the warp before generation.

Visualize o warp antes de gerar.

If the geometry already looks wrong in the warp preview, Meridian will receive a bad camera guide.

Se a geometria já estiver errada no preview do warp, o Meridian receberá um guia de câmera incorreto.

---

## 5. Choose the engine / Escolha o engine

### Maximum quality / Máxima qualidade

Use:

```text
Meridian INT8 / Quality
```

### Standard H3 + Meridian / H3 padrão + Meridian

Use:

```text
Meridian LoRA
```

---

## 6. Generate / Gere

Keep:

```text
FPS = 24
CFG = 1.0
Sampler = Euler
Shift = 3.0
```

Then decode with the H3 Video VAE and save the output.

Depois faça o decode com o H3 Video VAE e salve o vídeo.

---

# 🧠 Tips / Dicas

### Start with small camera changes

Meridian is more stable with moderate camera changes.

O Meridian é mais estável com mudanças moderadas de câmera.

Large angle changes expose more unseen areas and require more reconstruction.

Mudanças grandes de ângulo revelam mais regiões que nunca apareceram no vídeo original e exigem mais reconstrução.

---

### Use `subject_box`

A correct `subject_box` gives Camera H3 a better orbit target.

Um `subject_box` correto oferece ao Camera H3 um alvo de órbita melhor.

---

### Check the gray areas

Gray regions in the Depth Warp are expected.

Regiões cinzas no Depth Warp são esperadas.

They represent parts of the scene that were hidden from the original camera.

Elas representam partes da cena que estavam escondidas da câmera original.

---

### Use offsets to start from a new angle

Example:

```text
warp_offset_azimuth = -25
```

This lets the first output frame already start from a different virtual camera angle.

Isso permite que o primeiro frame já comece a partir de um ângulo virtual diferente.

---

### Bullet time

Use:

```text
warp_hold_at
warp_hold_frames
```

The source action freezes while the virtual camera continues moving.

A ação do vídeo congela enquanto a câmera virtual continua se movendo.

---

# ⚠️ Limitations / Limitações

- Depth Warp is a **camera control signal**, not the final render.
- Missing geometry must still be generated by Meridian/H3.
- Large camera changes may become unstable.
- Incorrect depth produces incorrect reprojection.
- Handheld/source-camera motion is harder than a locked camera.
- Output quality still depends on the H3/Meridian model, source video and references.

- O Depth Warp é um **sinal de controle de câmera**, não o render final.
- Geometria ausente ainda precisa ser criada pelo Meridian/H3.
- Mudanças grandes de câmera podem ficar instáveis.
- Profundidade incorreta gera reprojeção incorreta.
- Vídeos com câmera original em movimento são mais difíceis que planos travados.
- A qualidade final ainda depende do modelo H3/Meridian, vídeo fonte e referências.

---

# 📁 Included workflows / Workflows incluídos

```text
MeridianBruxos_v3_Quality.json
MeridianBruxos_v3_lora.json
```

### `MeridianBruxos_v3_Quality.json`

Uses the converted **Meridian INT8 diffusion model**.

Usa o **modelo diffusion Meridian INT8 convertido**.

**Recommended when final visual quality is the priority.**  
**Recomendado quando a prioridade é a qualidade visual final.**

### `MeridianBruxos_v3_lora.json`

Uses a **standard MiniMax H3 model + Meridian Teacher/Turbo LoRAs**.

Usa um **modelo MiniMax H3 padrão + LoRAs Meridian Teacher/Turbo**.

**Recommended when H3 compatibility, prompts and references are the priority.**  
**Recomendado quando compatibilidade com H3, prompts e referências são prioridade.**

---

# 📜 License / Licença

This project integrates tools and workflows around **MiniMax H3** and **Viggle Meridian**.

Este projeto integra ferramentas e workflows ao redor do **MiniMax H3** e **Viggle Meridian**.

The model weights remain subject to the licenses of their original authors.

Os pesos dos modelos continuam sujeitos às licenças de seus autores originais.

Before commercial use or redistribution, read the current licenses and notices for:

- MiniMax H3
- Viggle Meridian
- any redistributed or converted model weights
- third-party custom nodes

Antes de uso comercial ou redistribuição, consulte as licenças atuais de:

- MiniMax H3
- Viggle Meridian
- quaisquer pesos convertidos ou redistribuídos
- custom nodes de terceiros

---

# 🧙 Bruxos do VFX

Developed and adapted for ComfyUI by **Bruxos do VFX**.

Desenvolvido e adaptado para ComfyUI por **Bruxos do VFX**.

Camera H3:

https://github.com/NyckM/3d-Camera-control-H3-Minimax

Bruxos do VFX Nodes:

https://github.com/NyckM/Bruxos-do-VFX-Nodes

Meridian INT8 files:

https://huggingface.co/NyckM/Meridian_CameraH3_INT8_build_by_BruxosdoVFX/tree/main
