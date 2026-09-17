# bruxosdovfx · Camera H3 Experimental v19.1

PT: Este é o pacote experimental. Instale a pasta `ComfyUI-H3-Camera-Editor-Experimental` e procure **bruxosdovfx • Camera H3 Experimental**. Use o seletor Experimental no HUD. Consulte [EXPERIMENTS.md](EXPERIMENTS.md) para instalação e comparação. O restante deste manual descreve os controles comuns à principal.

EN: This is the experimental package. Install folder `ComfyUI-H3-Camera-Editor-Experimental` and search for **bruxosdovfx • Camera H3 Experimental**. Use the Experimental selector in the HUD. See [EXPERIMENTS.md](EXPERIMENTS.md) for installation and comparison. The rest of this guide describes shared controls.

# bruxosdovfx · Camera H3 v19.1

PT: Editor local de câmera para MiniMax H3 com seletor Português / English. Compila prompts; não carrega um adaptador geométrico. A prévia mostra a trajetória planejada, não prevê o vídeo. Mantém Freeze Frame, Motion Frame, calibração do sentido e o formato literal `[L=..., T=..., W=..., H=...]`.

EN: Local camera editor for MiniMax H3 with a Português / English selector. Compiles prompts; it does not load a geometric adapter. Preview shows the planned path, not a prediction of the video. Preserves Freeze Frame, Motion Frame, direction calibration and literal `[L=..., T=..., W=..., H=...]` syntax.

## Instalar / Install

PT: Feche o ComfyUI. Guarde a versão anterior fora de `custom_nodes` e substitua a pasta `ComfyUI-H3-Camera-Editor` pela pasta deste ZIP. Reinicie e recarregue a página. Procure **bruxosdovfx • Camera H3**. O ID `H3LocalCameraEditor` e as dez saídas anteriores permanecem. `info` começa com `bruxosdovfx v19.1`.

EN: Close ComfyUI. Keep the old version outside `custom_nodes`, then replace `ComfyUI-H3-Camera-Editor` with the folder in this ZIP. Restart and reload the page. Search for **bruxosdovfx • Camera H3**. ID `H3LocalCameraEditor` and the ten existing outputs are retained. `info` starts with `bruxosdovfx v19.1`.

PT: O ZIP Experimental usa a pasta `ComfyUI-H3-Camera-Editor-Experimental` e IDs diferentes. Pode ficar instalado junto. Não deixe duas cópias da versão principal em `custom_nodes`. A instalação experimental está descrita em `EXPERIMENTS.md`.

EN: The Experimental ZIP uses folder `ComfyUI-H3-Camera-Editor-Experimental` and different IDs. It can be installed alongside the main version. Do not keep two copies of the main version in `custom_nodes`. Experimental installation is described in `EXPERIMENTS.md`.

## Novidades / Changes

| Função / Function | Português | English |
|---|---|---|
| `smooth` + `extended contracts` | Mesma curva cúbica monotônica por eixo na prévia e Python. Velocidade contínua nos pontos intermediários; o eixo para em pausas/inversões, sem ultrapassar os extremos. | Matching monotone cubic curves per axis in preview and Python. Continuous velocity at interior waypoints; each axis stops at holds/reversals without overshoot. |
| `smooth` + `v15 baseline` | Smoothstep por trecho: freia em cada keyframe. O nome é legado; correções de texto da v19.1 também se aplicam. | Per-segment smoothstep: stops at each keyframe. The name is legacy; v19.1 text corrections still apply. |
| `linear` | Interpolação linear por trecho. A velocidade pode mudar entre trechos. | Linear interpolation per segment. Speed can change between segments. |
| Distribuir tempos / Redistribute timing | Distribui tempo pela extensão espacial aproximada dos trechos, preservando poses, pausas e voltas. Equaliza velocidade média, não a instantânea. | Distributes time by approximate spatial segment length, preserving poses, holds and turns. Equalizes average, not instantaneous, speed. |
| Desenrolar / Unwrap | Ação explícita: `350 → 10` pode virar `350 → 370`, assumindo arco curto. Preserva voltas explícitas de 360°. Um arco longo pode ser intencional; confira antes de gerar. | Explicit action: `350 → 10` can become `350 → 370`, assuming the short arc. Preserves explicit 360° turns. A long arc can be intentional; review before generating. |
| Pausa inicial/final / Start/end hold | Acrescenta 0,5s na mesma pose e redistribui os demais tempos. Em Motion, só a câmera para. Máximo de 24 keyframes. | Adds 0.5s at the same pose and redistributes other times. In Motion, only the camera stops. Maximum 24 keyframes. |
| Presets | Órbita positiva/negativa, subir/descer, aproximar/afastar e câmera estática. Só substituem o caminho ao aplicar. Começam em `0°, 0°, 1`. | Positive/negative orbit, rise/fall, move closer/away and static camera. Replace the path only when applied. Start at `0°, 0°, 1`. |
| Diagnóstico | Avisa caminho estático, cruzamento de zero e pausas; não altera dados sozinho. | Reports static paths, zero crossings and holds; never silently changes data. |
| Contratos / Contracts | Remove deslocamento artificial do fundo calculado sem profundidade e contradição entre suavização e velocidade constante. | Removes artificial background displacement prescribed without depth and the contradiction between easing and constant speed. |
| `loop_closure` | `auto` mantém fechamento compatível; `off` desliga para comparar. HUD mostra elegibilidade; `info` informa solicitação efetiva. | `auto` retains compatible closure; `off` disables it for comparisons. HUD shows eligibility; `info` reports the actual request. |

PT: Os tempos do vídeo usam o instante do último frame `(length - 1) / 24`. Em `directed | new camera angle`, o movimento termina em 65% do clipe de 39 frames e a prévia mostra a pausa restante. Duração do arquivo e instante do último frame são medidas diferentes.

EN: Video path times use final frame timestamp `(length - 1) / 24`. In `directed | new camera angle`, movement ends at 65% of the 39-frame clip and preview shows the remaining hold. File duration and final frame timestamp are different measurements.

## Freeze Frame

PT: Conecte foto ou lote IMAGE em `reference_image`. `freeze_index` escolhe um frame a partir de zero. Ligue `reference_first` à imagem de origem do H3 Edit, `compiled_prompt` e `options` ao encoder existente, e `length` / `fps` à geração/saída. Em H3 nativo use `minimax_prompt` e o primeiro frame no workflow FL2VA. As opções H3 Edit não ancoram automaticamente o último frame no nativo.

EN: Connect a photo or IMAGE batch to `reference_image`. `freeze_index` selects one zero-based frame. Connect `reference_first` to H3 Edit's source image, `compiled_prompt` and `options` to its encoder, and `length` / `fps` to generation/output. Native H3 uses `minimax_prompt` and the first frame in an FL2VA workflow. H3 Edit options do not automatically anchor the last frame in native workflows.

## Motion Frame

PT: Conecte frames em ordem temporal em `reference_image`, selecione Motion Frame e informe o FPS real em `source_fps`. Aceita referência de 2–15 segundos. Use `runtime_task = scene coverage | camera path`, modelo **H3 Ref2VA** e o encoder **bruxosdovfx • H3 Motion Reference**. O node chama `MiniMaxH3ReferenceToVideo` nativo; sua instalação precisa fornecer esse encoder.

EN: Connect chronologically ordered frames to `reference_image`, select Motion Frame and enter actual `source_fps`. Accepts 2–15 seconds of reference. Use `runtime_task = scene coverage | camera path`, an **H3 Ref2VA** model and **bruxosdovfx • H3 Motion Reference**. The node calls native `MiniMaxH3ReferenceToVideo`; your installation must provide that encoder.

| Origem / From | Destino / To |
|---|---|
| Editor `reference_frames` | Motion Reference `reference_frames` |
| Editor `minimax_prompt` | Motion Reference `prompt` |
| Editor `length` | Motion Reference `length` |
| Encoder Qwen H3 / H3 Qwen encoder | Motion Reference `clip` |
| VAE de vídeo H3 / H3 video VAE | Motion Reference `vae` |
| Motion Reference `positive`, `latent` | Guider e sampler Ref2VA / Ref2VA guider and sampler |
| Editor `fps` | Saída de vídeo / Video output |

PT: A referência é reamostrada para 24 fps e cortada em `17k+5`; até 16 frames finais podem ser descartados. `info` mostra as contagens. O áudio original não é encaminhado. `profile` controla duração de saída independentemente da fonte. Em Motion não conecte `options` ao H3 Edit: use Ref2VA. A câmera e a preservação da ação continuam dependentes da geração pelo modelo.

EN: Reference is resampled to 24 fps and trimmed to `17k+5`; up to 16 trailing frames can be discarded. `info` reports counts. Original audio is not forwarded. `profile` controls output duration independently. In Motion do not connect `options` to H3 Edit: use Ref2VA. Camera following and action preservation still depend on model generation.

## Loop closure

| Caso / Case | Resultado em `auto` / Result in `auto` |
|---|---|
| 359°, elevação/elevation 0, distância/distance 1 | OFF |
| 360°, elevação/elevation final 2 | OFF |
| 360°, distância/distance final 0.85 | OFF |
| Exatamente / Exactly ±360°, mesma altura e raio / same elevation and radius, Freeze Frame, imagem conectada / connected image, camera path | ON |
| 720°, Motion Frame ou tarefa de imagem / or still-image task | OFF |
| `loop_closure = off` | Sempre OFF / Always OFF |

PT: Tolerância de 0,000001. `Fechar volta` altera a pose final; não ignora `off`. ON pede ancoragem ao H3 Edit com imagem e opções conectadas. Não comprova que ocorreu uma volta inteira.

EN: Tolerance 0.000001. `Close orbit` changes the final pose; does not override `off`. ON requests anchoring from H3 Edit with connected image and options. It does not prove a full orbit occurred.

## Controles preservados / Existing controls

| Controle / Control | Português | English |
|---|---|---|
| `ui_language` | Traduz painel e diagnóstico, salvo no workflow. Prompts em inglês. | Translates panel and diagnostics, saved in workflow. English prompts. |
| `camera_trajectory` | Tempo normalizado, azimute sem limitar a 360, elevação e raio. Primeiro ponto fixo na referência. | Normalized time, unwrapped azimuth, elevation and radius. First point fixed to reference. |
| `subject_box` | Região inicial medida como `[L=0.516, T=0.148, W=0.071, H=0.249]`. Vazio usa limites da imagem, sem adivinhar sujeito. | Measured initial region such as `[L=0.516, T=0.148, W=0.071, H=0.249]`. Empty uses image boundaries, without guessing a subject. |
| `orbit_direction` | Calibra sinal enviado ao H3; não altera o caminho no HUD. | Calibrates sign sent to H3; leaves HUD path unchanged. |
| `elevation_range` | Limita slider; preserva valores salvos além dele. | Limits slider; preserves saved values beyond its range. |
| `instruction` | Direção adicional; evite contradizer keyframes ou Freeze/Motion. | Additional direction; avoid contradicting keyframes or Freeze/Motion. |
| `minimax_format` | Redação de `minimax_prompt`. A opção legada `compact JSON (no boxes)` também mantém caixa literal. | `minimax_prompt` wording. Legacy `compact JSON (no boxes)` also preserves the literal box. |
| `subject_framing` | Tipo de plano da imagem: close-up = rosto e ombros; medium shot = cintura para cima; wide shot = sujeito e cenário. Nesta versão, este seletor apenas registra o tipo de plano: não aplica zoom, recorte ou movimento à câmera. Pode deixar como está. Para indicar onde está o sujeito na imagem, use subject_box [L=..., T=..., W=..., H=...]. | Image framing: close-up = face and shoulders; medium shot = waist up; wide shot = subject and surroundings. In this version, this selector only records the shot type: it does not apply camera zoom, cropping or movement. You can leave it as is. To indicate the subject location in the image, use subject_box [L=..., T=..., W=..., H=...]. |
| Play / Imagem / Image | Anima câmera e carrega foto só na prévia. Conecte IMAGE para gerar. | Animates camera and loads preview-only photo. Connect IMAGE for generation. |
| Órbita pura / Pure orbit | Zera elevação; mantém distância/azimute. | Resets elevation; retains distance/azimuth. |
| `h3world_actions` | Texto aproximado de pan/tilt; não implementa órbita nem recebe vídeo Motion. | Approximate pan/tilt text; does not implement orbit or consume Motion video. |

## Validação / Validation

PT: Testes cobrem interpolação Python/JavaScript, pausas, voltas completas, idioma sem modificar prompts, fechamento, referências e roteamento nativo com substituto de teste. `preview.html` abre por servidor HTTP local. Não foi executada inferência H3 nesta entrega; compare a qualidade nos seus renders. Consulte `EXPERIMENTS.md` para os testes de prompt.

EN: Tests cover Python/JavaScript interpolation, holds, full turns, language without prompt changes, closure, references and native routing through a test double. Open `preview.html` through a local HTTP server. No H3 inference was run for this release; compare quality in your renders. See `EXPERIMENTS.md` for prompt tests.


PT: v19.1 esclarece a ajuda do tipo de plano; mantém os valores do seletor e o comportamento da geração.

EN: v19.1 clarifies shot-type help; preserves selector values and generation behavior.
