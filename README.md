# bruxosdovfx · Camera H3

`#bruxosdovfx`

Visual camera editor, path compiler and optional RGB camera-guide system for **MiniMax H3** inside ComfyUI.  
Editor visual de câmera, compilador de trajetória e sistema opcional de guia RGB para **MiniMax H3** dentro do ComfyUI.

Drag the camera, create keyframes, preview motion, use trajectory presets and generate H3 camera-path prompts.  
Arraste a câmera, crie keyframes, visualize o movimento, use presets de trajetória e gere prompts de câmera para H3.

> **PT:** O node compila prompts e trajetórias. Não é um adaptador geométrico e não garante que o H3 siga a câmera perfeitamente.  
> **EN:** The node compiles prompts and camera paths. It is not a geometric adapter and cannot guarantee perfect H3 camera tracking.

---

## Instalação / Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/NyckM/3d-Camera-control-H3-Minimax
```

Reinicie o ComfyUI e procure **bruxosdovfx • Camera H3**.  
Restart ComfyUI and search for **bruxosdovfx • Camera H3**.

Evite manter duas cópias dos mesmos nodes em `custom_nodes`.  
Avoid keeping two copies of the same nodes inside `custom_nodes`.

---

## Nodes

### `bruxosdovfx • Camera H3`

Editor principal de câmera.  
Main camera editor.

Principais funções / Main features:

- camera keyframes
- orbit, elevation and distance
- editable timeline
- `smooth` and `linear` interpolation
- Redistribute timing
- Unwrap
- Start / End Hold
- Loop Closure / Close Orbit
- Pure Orbit
- diagnostics
- Freeze Frame
- Action Frame
- Motion Frame
- `subject_box`
- local image/video preview
- 3D Camera View
- trajectory presets
- `camera_prompt`
- `minimax_prompt`
- `storyboard_json`
- optional RGB Camera Guide workflow

---

### `bruxosdovfx • H3 Subject Box`

Define **em torno de quem a câmera deve orbitar**.  
Defines **who the camera should orbit around**.

Desenhe uma caixa sobre o sujeito e conecte `subject_box` ao Camera H3.  
Draw a box over the subject and connect `subject_box` to Camera H3.

Formato / Format:

```text
[L=0.62, T=0.18, W=0.24, H=0.55]
```

`L` e `T` definem posição; `W` e `H`, tamanho. Valores de `0` a `1`.  
`L` and `T` define position; `W` and `H` define size. Values range from `0` to `1`.

Útil principalmente quando o sujeito está fora do centro.  
Especially useful when the subject is off-center.

`subject_box` não recorta, não aplica zoom e não força o sujeito a permanecer dentro da caixa.  
`subject_box` does not crop, zoom or force the subject to remain inside the box.

Se vazio, o centro/imagem completa é usado como referência.  
If empty, the image center/full image is used as the reference.

---

### `bruxosdovfx • Camera Prompt Compose`

Combina o prompt da cena/ação com as instruções da câmera.  
Combines the scene/action prompt with camera instructions.

```text
scene_prompt + camera_prompt → prompt
```

Use a saída no encoder de texto do workflow.  
Use the output in your workflow text encoder.

`enabled = false` devolve o prompt original.  
`enabled = false` returns the original prompt.

---

### `bruxosdovfx • Camera Guide Render`

Renderiza localmente um guia RGB seguindo o plano calibrado da câmera.  
Locally renders an RGB guide following the calibrated camera path.

Pode usar manequim ou esfera, com chão simples ou marcadores.  
It can use a mannequin or sphere, with a simple ground plane or markers.

Entrada principal / Main input:

```text
Camera H3.storyboard_json → Camera Guide Render.storyboard_json
```

Saídas / Outputs:

- `rgb_frames`
- `fps`
- `length`
- `guide_prompt`
- `info`

O render roda localmente na CPU usando NumPy e Torch da instalação ComfyUI.  
The render runs locally on CPU using ComfyUI's NumPy and Torch installation.

Comece em resoluções pequenas, como `320×192`, especialmente em sequências longas.  
Start with small resolutions such as `320×192`, especially for long sequences.

---

### `bruxosdovfx • Camera Guide Video`

Converte os frames RGB e FPS em VIDEO para o Save Video nativo.  
Converts RGB frames and FPS into VIDEO for the native Save Video node.

```text
Camera Guide Render.rgb_frames
Camera Guide Render.fps
        ↓
Camera Guide Video
        ↓
Save Video
```

Requer `comfy_api.latest` com `VideoFromComponents`.  
Requires `comfy_api.latest` with `VideoFromComponents`.

Instalações antigas podem usar `rgb_frames` + `fps` diretamente em outro node de vídeo.  
Older installs can use `rgb_frames` + `fps` directly in another video-saving node.

---

## Como usar / Basic use

- Arraste a câmera no canvas para orbitar. / Drag the camera on the canvas to orbit.
- Scroll muda a distância. / Mouse wheel changes distance.
- `Alt + wheel` ajusta a distância do keyframe selecionado. / adjusts selected keyframe distance.
- Arraste o fundo para girar apenas a visualização. / Drag the background to rotate the preview only.
- Use keyframes para construir a trajetória. / Use keyframes to build the path.
- **Pure Orbit / Órbita pura** zera a elevação. / resets elevation.
- **Play** mostra a trajetória planejada. / previews the planned path.
- O primeiro keyframe permanece fixo. / The first keyframe remains fixed.
- Até **24 keyframes** podem ser usados. / Up to **24 keyframes** can be used.

A prévia mostra o movimento planejado, não o resultado final do H3.  
The preview shows the planned motion, not the final H3 result.

---

## Ligações principais / Main connections

### H3 Edit

| Saída / Output | Ligue em / Connect to |
|---|---|
| `compiled_prompt` | H3 Edit Text Encode |
| `options` | H3 Edit Text Encode |
| `reference_first` | source image / imagem inicial |
| `length` | generation |
| `fps` | video output |

`compiled_prompt` + `options` trabalham juntos no H3 Edit.  
`compiled_prompt` + `options` are used together with H3 Edit.

### H3 Native / Ref2VA

| Saída / Output | Uso / Use |
|---|---|
| `minimax_prompt` | Native H3 / Ref2VA prompt |
| `camera_prompt` | Camera Prompt Compose |
| `storyboard_json` | Camera Guide / structured path |
| `length` | generation length |
| `fps` | output FPS |

---

## Modos / Modes

### Freeze Frame

Use uma foto ou frame de referência.  
Use a still image or reference frame.

- conecte `reference_image`
- `freeze_index` escolhe o frame do lote
- conecte `reference_first` ao source image do H3 Edit
- conecte `compiled_prompt` + `options` ao H3 Edit Text Encode

No H3 nativo, use `minimax_prompt` + primeiro frame no workflow FL2VA.  
With native H3, use `minimax_prompt` + the first frame in an FL2VA workflow.

Freeze Frame continua como modo padrão.  
Freeze Frame remains the default mode.

---

### Action Frame / Animar imagem

Anima a imagem usando a ação escrita em `instruction` enquanto a câmera percorre a trajetória.  
Animates the image using the action written in `instruction` while the camera follows the path.

Exemplo / Example:

```text
A woman walks forward and raises her right hand.
Her coat moves in the wind.
```

Use a mesma imagem no workflow nativo image-to-video e conecte:

```text
minimax_prompt
length
fps
```

Action Frame exige imagem e ação não vazia.  
Action Frame requires an image and a non-empty action.

Se `runtime_task` estiver disponível, use:

```text
scene coverage | camera path
```

Pausas da câmera afetam o ponto de vista, não a ação descrita.  
Camera holds affect viewpoint, not the described action.

---

### Motion Frame

Use vídeo ou sequência de frames como referência de movimento.  
Use a video or frame sequence as motion reference.

Recomendações / Recommendations:

- referência entre **2–15 s**
- informe o FPS real em `source_fps`
- use `scene coverage | camera path`
- use modelo **H3 Ref2VA**
- use Ref2VA / H3 Motion Reference

A sequência precisa ser ligada diretamente ao encoder.  
The sequence must be connected directly to the encoder.

Prepare em **24 fps** e com comprimento compatível.  
Prepare it at **24 fps** with a compatible length.

O áudio original não é enviado.  
Original audio is not forwarded.

---

## Interpolação / Interpolation

### `smooth`

Movimento suavizado entre keyframes.  
Smoothed motion between keyframes.

Com contratos estendidos, tenta manter velocidade mais contínua entre os pontos.  
With extended contracts, it attempts to keep motion speed more continuous between waypoints.

### `linear`

Movimento linear por trecho.  
Straight interpolation per segment.

---

## Timing

Os tempos usam o último frame visível:

```text
(length - 1) / fps
```

Video timing uses the timestamp of the last visible frame.

### Redistribute timing

Redistribui os tempos dos keyframes para equilibrar a velocidade média.  
Redistributes keyframe timing for a more even average speed.

### Start / End Hold

Adiciona aproximadamente **0.5 s** de pausa no início ou no fim.  
Adds approximately **0.5 s** of hold at the start or end.

### Unwrap

Corrige cruzamentos de ângulo como:

```text
350° → 10°
```

para usar o arco curto sem salto visual no editor.  
to use the short arc without a visual jump in the editor.

Voltas acumuladas continuam preservadas quando fazem parte da trajetória.  
Accumulated full rotations remain preserved when they are part of the path.

---

## Loop Closure

`loop_closure = auto` pode ancorar o último frame ao primeiro quando a trajetória é compatível.  
`loop_closure = auto` can anchor the last frame to the first when the path is compatible.

### Liga / ON

Normalmente quando há:

- Freeze Frame
- `scene coverage | camera path`
- exatamente `+360°` ou `-360°`
- mesma elevação final
- mesma distância final
- imagem conectada

### Desliga / OFF

Exemplos:

- `359°`
- `720°`
- Motion Frame
- still-image / new-angle task
- altura final diferente
- distância final diferente
- `loop_closure = off`

**Close Orbit / Fechar volta** ajusta a pose final para fechar a trajetória.  
**Close Orbit** adjusts the final pose to close the path.

Action e Motion desativam fechamento por âncora final quando incompatível com a tarefa.  
Action and Motion disable final anchor closure when incompatible with the task.

---

## Diagnostics

O painel pode identificar situações como:

- holds / pauses
- static camera paths
- zero crossings
- paths that may not close cleanly

Os diagnósticos ajudam a revisar a trajetória, mas não medem a fidelidade final do H3.  
Diagnostics help review the path but do not measure final H3 fidelity.

---

## Editor de câmera / Camera editor

### Zoom e canvas / Zoom and canvas

- zoom visual de **50% a 400%**
- `− / +`
- mouse wheel
- **Expand canvas**
- **Reset view**

Zoom e expansão afetam somente a interface.  
Zoom and canvas expansion affect only the UI.

Não modificam a trajetória nem o prompt.  
They do not modify the camera path or prompt.

---

### Edição direta / Direct editing

Arraste os pontos numerados diretamente no canvas:

- horizontal → azimuth
- vertical → elevation
- `Alt + wheel` → distance
- timeline marker → keyframe time

Pontos próximos recebem marcadores separados.  
Nearby points receive separated markers.

As setas do teclado podem ajustar o marcador em foco.  
Arrow keys can adjust the focused marker.

O arraste preserva o hemisfério inicial e é limitado pela esfera orbital.  
Dragging preserves the initial hemisphere and is constrained by the orbit sphere.

Não é um gizmo XYZ livre.  
It is not a free XYZ translation gizmo.

---

## Camera View 3D

A janela **Camera view** mostra um manequim 3D estático pela pose atual da câmera.  
The **Camera view** window shows a static 3D mannequin from the current camera pose.

As linhas douradas representam aproximadamente o campo de visão.  
Golden lines approximately represent the camera field of view.

- proporção segue a referência local/conectada
- fallback: `16:9`
- FOV vertical ilustrativo fixo em **40°**

O manequim é apenas uma referência geométrica.  
The mannequin is only a geometric reference.

Não é reconstrução 3D da imagem e não prevê a ação do personagem.  
It is not a 3D reconstruction of the image and does not predict character action.

---

## Vídeo durante a edição / Video while editing

Clique **Imagem / vídeo** e selecione um vídeo local compatível com o navegador:

- MP4 H.264
- WebM

O botão **▶** reproduz vídeo e trajetória juntos.  
The **▶** button plays video and camera path together.

Você pode continuar ajustando a câmera durante o playback.  
You can continue editing the camera during playback.

`+ Keyframe agora / + Keyframe now` adiciona um ponto no tempo atual.  
`+ Keyframe now` adds a point at the current time.

O vídeo inteiro é mapeado à duração de saída.  
The full video is mapped to the output duration.

A velocidade da prévia não altera `source_fps` nem os frames de geração.  
Preview speed does not change `source_fps` or generation frames.

O vídeo local:

- não é enviado ao servidor
- não é salvo no workflow
- toca sem áudio
- precisa ser selecionado novamente após recarregar

The local video:

- is not uploaded to the server
- is not stored in the workflow
- plays without audio
- must be selected again after reload

---

## Presets de trajetória / Camera path presets

O menu **Presets** contém **18 movimentos** adaptados dos exemplos públicos de `loopforge0/minimaxh3-shots-skills`.  
The **Presets** menu contains **18 camera moves** adapted from the public `loopforge0/minimaxh3-shots-skills` examples.

**9 presets** possuem trajetória aplicável.  
**9 presets** provide an applicable path.

**9 presets** permanecem disponíveis somente como referência.  
**9 presets** remain available as reference only.

### Como usar / How to use

1. Selecione o preset. / Select a preset.
2. Leia a descrição. / Read the description.
3. Clique **Aplicar trajetória / Apply path**.
4. Edite os keyframes normalmente. / Edit the keyframes normally.
5. Use **Desfazer preset / Undo preset** para restaurar a trajetória anterior.

Aplicar um preset substitui trajetória e interpolação, mantendo duração e modo de cena.  
Applying a preset replaces path and interpolation while keeping duration and scene mode.

O histórico de Undo é local à sessão.  
Undo history is local to the current session.

### Presets aplicáveis / Applicable presets

| Preset | Movimento / Motion |
|---|---|
| C-01 | Aproximação rápida / Fast dolly in |
| C-01b | Pausa + aproximação rápida / Hold + fast dolly |
| C-03 | Super dolly in |
| C-04 | Órbita completa 360° / Full 360° orbit |
| C-05 | Subida para vista aérea / Crane-drone rise |
| C-06 | Afastamento aéreo / Aerial pullback |
| C-07 | Oscilação orbital suave / Soft orbital oscillation |
| C-08 | Afastar e voltar / Dolly out and return |
| C-10 | Aproximação extrema / Extreme push-in |

Alguns presets são aproximações físicas.  
Some presets are physical approximations.

Exemplo: um dolly pode substituir um zoom óptico.  
Example: a dolly can replace an optical zoom.

### Somente referência / Reference only

Alguns presets exigem recursos atualmente não suportados:

- independent pan + target switching
- camera roll / Dutch angle
- body-mounted camera / Snorricam
- animated target tracking
- rack focus
- multi-camera composition
- simultaneous FOV + distance animation for dolly zoom

Nesses casos, **Apply path** fica desativado.  
In these cases, **Apply path** is disabled.

Veja `PRESETS-v28.md` para fontes e limitações individuais.  
See `PRESETS-v28.md` for individual sources and limitations.

---

## Camera Guide + Ref2VA

O **Camera Guide Render** cria um vídeo-guia simples para representar a trajetória da câmera sem depender somente de texto.  
**Camera Guide Render** creates a simple guide video representing camera motion without relying only on text.

Ligação principal / Main connection:

```text
Camera H3.storyboard_json
    ↓
Camera Guide Render.storyboard_json

Camera Guide Render.rgb_frames
    ↓
Ref2VA reference video input

Camera Guide Render.guide_prompt
    ↓
Camera Prompt Compose.camera_prompt

Seu prompt de cena/ação
    ↓
Camera Prompt Compose.scene_prompt
```

A saída final do Compose vai para o encoder Ref2VA.  
The final Compose output goes to the Ref2VA encoder.

### Identity references / Referências de identidade

Mantenha as imagens de identidade conectadas normalmente ao encoder.  
Keep identity images connected normally to the encoder.

O Camera Guide **não substitui** essas imagens.  
Camera Guide **does not replace** those images.

O node H3 Motion Reference antigo não recebe imagens de identidade; para guide + identity images, prefira o Ref2VA do workflow existente.  
The older H3 Motion Reference node does not take identity images; for guide + identity images, prefer the Ref2VA encoder from your existing workflow.

---

## `video_reference_index`

Define qual token `<Video N>` representa o Camera Guide dentro do prompt.  
Defines which `<Video N>` token represents Camera Guide inside the prompt.

Exemplo / Example:

```text
<Video 1>
```

O valor deve corresponder à posição real do vídeo no encoder.  
The value must match the video's actual position in the encoder.

Não deduza o número pelo sufixo interno de uma porta.  
Do not infer this number from an internal port suffix.

---

## `guide_prompt` vs `camera_prompt`

### Com Camera Guide / With Camera Guide

Use:

```text
Camera Guide Render.guide_prompt
```

Não combine `guide_prompt` com outro bloco completo de câmera ao mesmo tempo.  
Do not combine `guide_prompt` with another complete camera block at the same time.

### Sem Camera Guide / Without Camera Guide

Remova o lote de vídeo do encoder e use:

```text
Camera H3.camera_prompt
```

Apenas desligar `enabled` não remove um vídeo já conectado ao encoder.  
Disabling `enabled` alone does not remove a video already connected to the encoder.

Use `guide_prompt`, não `minimax_prompt` de Freeze, no caminho Camera Guide + Ref2VA.  
Use `guide_prompt`, not the Freeze `minimax_prompt`, for the Camera Guide + Ref2VA path.

---

## Formato do Camera Guide / Camera Guide format

O guia usa:

- RGB float32 frames
- 24 fps
- comprimento em padrão `17n + 5`
- FOV visual fixo de 40°
- proxy estático

Os frames não incluem:

- câmera visível
- trajetória desenhada
- textos
- controles da interface

Marcadores coloridos são opcionais e fazem parte do guia.  
Colored markers are optional and are part of the guide.

O guia representa **movimento de câmera**, não movimento do personagem.  
The guide represents **camera motion**, not character motion.

A ação do personagem continua vindo do prompt.  
Character action still comes from the prompt.

---

## Principais controles / Main controls

| Controle | PT | EN |
|---|---|---|
| `ui_language` | Idioma do painel. | UI language. |
| `camera_trajectory` | Tempo, azimute, elevação e distância. | Time, azimuth, elevation and distance keyframes. |
| `instruction` | Instrução extra / ação. | Extra instruction / action. |
| `subject_box` | Posição inicial do sujeito. | Initial subject position. |
| `orbit_direction` | Corrige o sentido enviado ao H3. | Corrects direction sent to H3. |
| `elevation_range` | Faixa do controle vertical. | Vertical control range. |
| `subject_framing` | Registra close-up, medium ou wide. | Records close-up, medium or wide framing. |
| `minimax_format` | Formato do `minimax_prompt`. | `minimax_prompt` format. |
| `prompt_detail` | Baseline ou contratos estendidos. | Baseline or extended contracts. |
| `runtime_task` | Vídeo ou nova vista estática. | Video or new still-image angle. |
| `interpolation` | Smooth ou Linear. | Smooth or Linear. |
| `loop_closure` | Fechamento automático compatível. | Compatible automatic loop closure. |

`subject_framing` não aplica zoom ou crop.  
`subject_framing` does not apply zoom or crop.

---

## Saídas / Outputs

| Saída / Output | Uso / Use |
|---|---|
| `compiled_prompt` | Prompt para H3 Edit |
| `options` | Opções para H3 Edit |
| `minimax_prompt` | Prompt alternativo / native H3 |
| `storyboard_json` | Dados estruturados da trajetória |
| `info` | Diagnóstico |
| `length` | Número de frames |
| `fps` | FPS de saída |
| `h3world_actions` | Aproximação textual de pan/tilt |
| `camera_prompt` | Bloco de câmera para Compose |

`h3world_actions` descreve pan/tilt aproximado; não representa uma órbita geométrica real.  
`h3world_actions` describes approximate pan/tilt; it is not a true geometric orbit.

---

## Fluxos rápidos / Quick workflows

### H3 Edit / Freeze

```text
reference_image
      ↓
Camera H3
 ├─ reference_first → H3 source image
 ├─ compiled_prompt → H3 Edit Text Encode
 └─ options → H3 Edit Text Encode
```

### Native H3 / Action

```text
Image + instruction
        ↓
     Camera H3
        ↓
minimax_prompt + length + fps
        ↓
Native H3 image-to-video workflow
```

### Motion / Ref2VA

```text
Reference video
      ↓
Ref2VA / Motion Reference

Camera H3
   ↓
minimax_prompt + length
```

### Camera Guide

```text
Camera H3.storyboard_json
        ↓
Camera Guide Render
   ↙              ↘
rgb_frames      guide_prompt
   ↓                ↓
Ref2VA          Camera Prompt Compose
```

---

## Performance do Camera Guide

O render possui orçamento máximo de aproximadamente **32 milhões de pixels por lote**.  
The renderer has an approximate maximum budget of **32 million pixels per batch**.

Isso equivale a cerca de **384 MB** somente para frames RGB float32, além de temporários.  
This is roughly **384 MB** for RGB float32 frames alone, plus temporary buffers.

Para sequências longas, reduza a resolução.  
For long sequences, reduce resolution.

O processamento respeita o botão de interrupção do ComfyUI.  
Processing respects ComfyUI's interrupt button.

---

## Limitações / Limitations

- H3 ainda pode errar ângulo, escala, timing e direção.  
  H3 can still miss angle, scale, timing and direction.

- A prévia não simula o resultado final.  
  Preview does not simulate the final result.

- `subject_box` identifica o alvo, mas não trava composição.  
  `subject_box` identifies the target but does not lock composition.

- Motion Frame depende do Ref2VA preservar a ação.  
  Motion Frame depends on Ref2VA preserving the action.

- O editor não é um gizmo XYZ livre.  
  The editor is not a free XYZ translation gizmo.

- Camera roll / Dutch angle não é suportado atualmente.  
  Camera roll / Dutch angle is currently unsupported.

- O FOV da prévia é fixo; dolly zoom real não é suportado.  
  Preview FOV is fixed; true dolly zoom is not supported.

- O Camera Guide não garante fidelidade e pode influenciar pose ou aparência.  
  Camera Guide does not guarantee fidelity and may influence pose or appearance.

- O Camera Guide não substitui referências de identidade.  
  Camera Guide does not replace identity references.

- A tarefa de extração de imagem estática é rejeitada no caminho Camera Guide.  
  Still-image extraction tasks are rejected in the Camera Guide path.

Para comparar resultados, use a mesma seed, referências, modelo e trajetória.  
For comparisons, use the same seed, references, model and camera path.

---

## Compatibilidade / Compatibility

- Freeze Frame continua como padrão. / Freeze Frame remains the default.
- Action Frame continua disponível. / Action Frame remains available.
- Motion Frame continua disponível. / Motion Frame remains available.
- Camera Guide é opcional. / Camera Guide is optional.
- O editor mantém as saídas existentes e adiciona `camera_prompt`. / The editor preserves existing outputs and adds `camera_prompt`.
- Nenhuma nova dependência é exigida pelo editor principal. / The main editor adds no new dependency.

`Camera Guide Video` depende de APIs recentes do ComfyUI.  
`Camera Guide Video` depends on newer ComfyUI APIs.

---

## Validação / Validation

```bash
python -B tests/test_v23.py
```

Os testes validam estrutura e contratos de prompt.  
Tests validate structure and prompt contracts.

Eles não comprovam qualidade visual do H3.  
They do not prove H3 visual quality.

Compare Freeze / Action / Motion usando mesma imagem, modelo, seed e trajetória sempre que possível.  
Compare Freeze / Action / Motion using the same image, model, seed and path whenever possible.

---

## Documentação adicional / Additional documentation

- `CAMERA-GUIDE-v29.md` — Camera Guide + Ref2VA
- `PRESETS-v28.md` — presets, fontes e limitações
- `INTEGRACAO-v26.md` — prompt / encoder integration
- `EXPERIMENTS.md` — experimental version
- `README-LEGACY.md` — historical documentation

---

## Experimental

A versão Experimental pode ficar instalada junto da principal.  
The Experimental version can be installed alongside the main version.

Pasta / Folder:

```text
3d-Camera-control-H3-Minimax-Experimental
```

Veja / See:

```text
EXPERIMENTS.md
```

---

## Créditos / Credits

Node dos **Bruxos do VFX**.  
Node by **Bruxos do VFX**.

Baseado na integração H3 Edit de:

`ethanfel/ComfyUI-MiniMax-H3-Edit`

Camera vocabulary follows MiniMax camera-control conventions.  
O vocabulário de câmera segue as convenções de controle de câmera da MiniMax.

Os presets de trajetória são adaptações manuais dos exemplos públicos de:

`loopforge0/minimaxh3-shots-skills`

As trajetórias foram reinterpretadas para os controles disponíveis no editor; personagens, cenários, áudio e prompts completos do projeto original não foram incorporados.  
The paths were manually reinterpreted for the controls available in the editor; characters, scenes, audio and full prompts from the source project were not incorporated.

O Camera Guide é um render geométrico auxiliar e não contém implementação do modelo MiniMax H3.  
Camera Guide is an auxiliary geometric renderer and does not contain MiniMax H3 model implementation.
