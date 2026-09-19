# Meridian (Viggle) — v31

O [Meridian](https://huggingface.co/Viggle/Meridian) é um fine-tune completo do transformer `ref2va` do MiniMax-H3 que gera um clipe a partir de **duas referências de vídeo**: `<Video 1>` é o clipe original e `<Video 2>` é um render da cena vista da câmera nova, com buracos cinza. É exatamente o papel do nosso Depth Warp.

O texto é um embedding congelado: não existe text encoder nem prompt. **A câmera vem inteira do `<Video 2>`.** As saídas de prompt do Camera H3 não são usadas aqui; o que importa é a trajetória.

Três peças novas na v31:

1. `warp_format = Meridian (H3)` no Camera H3, que gera o `<Video 2>` no formato do Meridian.
2. Os nodes **Meridian Text Cond** e **Meridian Reference**, que montam o conditioning.
3. `meridian_convert.py`, que converte os pesos do formato diffusers para o do ComfyUI.

## 1. O formato do warp

| | Formato Meridian |
|---|---|
| Buraco | cinza 128, sem canal de máscara |
| Splat | 3×3, z-buffer |
| Poda | bordas de profundidade acima de 30% na escala 512, mantendo só onde todos os "pais" bilineares sobreviveram |
| Resolução | canvas classe 480 (832×480 em 16:9), recorte central |
| Durações | 73, 90, 107, 124, 141, 158, 175 ou 243 frames |

A matemática do render é um port de `recam/geometry.py` do Meridian e bate pixel a pixel com o laço original em `tests/test_v31_meridian.py`. `warp_long_side` é ignorado neste formato: o canvas vem da escada do próprio modelo.

**Duas diferenças de geometria que continuam:** o Meridian usa o VGGT-Omega, que estima a profundidade **e a pose da câmera de cada frame**, além de podar por confiança. O nosso warp usa MoGe ou depth relativo e assume a câmera da fonte parada. Em plano travado isso é equivalente; em câmera na mão, não. O VGGT-Omega é licença não comercial e gated, então não dá para embutir.

## 2. Congelar a ação (bullet time)

`warp_hold_at` e `warp_hold_frames` reproduzem o `--freeze F:N` do Meridian, em Motion Frame: a ação roda até o frame `warp_hold_at` da fonte, congela por `warp_hold_frames` frames de saída e retoma do frame seguinte. **A câmera não para** — ela segue a trajetória inteira do painel, que é o efeito do exemplo "play, hold, resume" deles.

Exemplo: fonte de 24 fps, `warp_length = 73`, `warp_hold_at = 24`, `warp_hold_frames = 25` → 24 frames vivos, 25 congelados no frame 24 e 24 de ação retomada.

Por enquanto isso são dois widgets; o painel ainda mostra só a câmera, sem marcadores de tempo na timeline.

## 3. Ligação no ComfyUI

```text
Load Video (force_rate 24) ─┬─> Camera H3.reference_image
                            └─> Meridian Reference.source_video      (<Video 1>)
Run MoGe Inference ────────────> Camera H3.moge_geometry
Camera H3.depth_warp ──────────> Meridian Reference.warp_video       (<Video 2>)
Meridian Text Cond ────────────> Meridian Reference.text_cond
Load VAE (H3 video VAE) ───────> Meridian Reference.vae

Meridian Reference.positive ──> BasicGuider ──> SamplerCustomAdvanced ──> VAE Decode
Meridian Reference.latent  ──────────────────────^
Load Diffusion Model (Meridian) → Load LoRA (Model Only) → ModelSamplingMiniMaxH3 (3.0 / 3.0) → BasicGuider
```

- `length` do Meridian Reference e `warp_length` do Camera H3 precisam ser o mesmo número, e um dos oito aceitos.
- Amostragem da LoRA DMD: **Euler**, CFG 1.0, e `ManualSigmas` com `1.0, 0.8571428571428571, 0.6, 0.0` — quatro pontos, três passos. Sem a LoRA, o professor pede 50 passos com shift 12.
- O embedding congelado é **um por duração**: carregue o que bate com `length`.

## 4. Converter os pesos

O `meridian_convert.py` roda sem Torch (exceto o modo `text`) e trabalha em memmap, então não carrega os 62 GB na RAM:

```bash
cd ComfyUI/custom_nodes/ComfyUI-H3-Camera-Editor

# Transformer: diffusers -> ComfyUI (bf16, ~62 GB)
python meridian_convert.py transformer /caminho/Meridian/transformer \
    ../../models/diffusion_models/minimax_h3_ref2va_meridian_bf16.safetensors

# LoRA DMD (rank 128)
python meridian_convert.py lora /caminho/Meridian/lora/pytorch_lora_weights.safetensors \
    ../../models/loras/meridian_dmd_lora_comfyui.safetensors

# Embedding de texto da duração que você vai usar
python meridian_convert.py text /caminho/Meridian/assets/fixed_embed_124.pt \
    ../../models/text_cond/meridian_fixed_embed_124.safetensors
```

O que a conversão faz, seguindo o mapeamento do script oficial do diffusers ao contrário:

- `to_q`/`to_k`/`to_v` voltam a ser um `qkv_proj` fundido. Na LoRA isso vira `lora_A` concatenado e `lora_B` em bloco diagonal, o que preserva o delta exato de cada projeção.
- `ff.net.0.proj` vira `mlp.fc1` com as **metades trocadas**: o SwiGLU do diffusers lê `[valor; porta]` e o do ComfyUI calcula `fc2(silu(porta) × valor)` a partir de `[porta; valor]`. Na LoRA a troca vale só para `lora_B`.
- Renomes de `proj_in`, `context_embedder`, `norm_out`, `token_refiner.refiner_blocks` e afins.
- `rope.inv_freq` é recalculado: o diffusers não o guarda, e é por essa chave que o ComfyUI detecta o H3.
- A escala da LoRA (`alpha / rank`, incluindo `alpha_pattern` e `use_rslora`) é embutida em `lora_B`, então o arquivo sai sem tensores `.alpha` — que é a convenção do ComfyUI, onde alpha ausente significa escala 1.

## 5. Reduzir o tamanho: podar o AdaLN e quantizar

O transformer tem 33 bilhões de parâmetros, mas **13 bilhões deles são só as camadas `adaln_proj`**, que recebem 2688 entradas vindas do embedding de tempo. Como esse embedding percorre uma curva suave em função de `t`, ele cabe numa base de 8 componentes: é isso que os checkpoints "pruned" (curve-form) do ComfyUI fazem, e é o que explica um arquivo int8 cair de 47 GB para 21 GB.

O conversor faz a poda:

```bash
# 33,1 bilhões -> ~19,5 bilhões de parâmetros
python meridian_convert.py transformer /caminho/Meridian/transformer saida_podada.safetensors --prune-adaln

# podado e já em fp8 escalado (escala por camada)
python meridian_convert.py transformer /caminho/Meridian/transformer saida_fp8.safetensors --prune-adaln --fp8
```

Ele calcula `silu(time_embedder(t))` num grid de 1024 pontos com a mesma fórmula do `TimeEmbedder` do ComfyUI, tira a base por SVD, grava `adaln_t_table` e substitui cada `adaln_proj.linear` por `W @ base`. O erro relativo da aproximação é medido e impresso na conversão. O ComfyUI detecta esse formato pela chave `adaln_t_table` e passa a interpolar a tabela em vez de rodar o time embedder.

Tamanhos aproximados:

| Arquivo | Parâmetros | Tamanho |
|---|---|---|
| bf16 completo | 33,1 bi | ~62 GiB |
| bf16 podado | ~19,5 bi | ~37 GiB |
| fp8 podado | ~19,5 bi | ~19 GiB |
| int8 podado (via toolkit) | ~19,5 bi | ~20 GiB |

**int8** é a melhor opção de qualidade por byte, mas o formato nativo do ComfyUI (`TensorWiseINT8Layout`, com a rotação convrot) vem do pacote `comfy_kitchen`, que não dá para reproduzir às cegas sem errar a convenção. O caminho seguro é gerar o **bf16 podado** e quantizar com o [ComfyUI Quantization Toolkit](https://github.com/SparknightLLC/ComfyUI-INT8-Toolkit) em `int8_convrot`, exportando no formato nativo para não requantizar a cada execução. É o mesmo processo que produziu o int8 podado que você já roda.

O `--fp8` grava no formato `scaled_fp8`: cada peso grande vira e4m3fn com uma escala por camada (`<camada>.scale_weight`), e o ComfyUI converte isso em metadados `comfy_quant` ao carregar. Sem a escala, fp8 seria ruim aqui: pesos típicos (~0,02) cairiam na faixa subnormal do e4m3, que tem só 3 bits de mantissa a partir de 2⁻⁹.

### A LoRA na base podada

Com a poda, o conversor grava também `saida_podada.safetensors.adaln_basis.safetensors`. Passe esse arquivo ao converter a LoRA e os adaptadores AdaLN são **projetados na mesma base** em vez de descartados:

```bash
python meridian_convert.py lora /caminho/Meridian/lora/pytorch_lora_weights.safetensors \
    meridian_dmd_lora_comfyui.safetensors --pruned --adaln-basis saida_podada.safetensors.adaln_basis.safetensors
```

Sem a base, `--pruned` cai no comportamento das conversões da comunidade: remove os 51 adaptadores AdaLN, o que é uma conversão parcial.

### O que continua valendo

O Meridian não é uma LoRA sobre o H3: todos os pesos mudaram, então a sua base H3 int8 pruned não serve, e a LoRA DMD dele só funciona sobre o transformer do Meridian.

## 6. Licença

Os pesos do Meridian são um derivado do MiniMax-H3 e seguem a **MiniMax H3 Community License**, cujo território de uso exclui União Europeia, Reino Unido, Coreia do Sul e Estados Unidos. O código do Meridian (`recam/`, `inference/`, `service/`) é Apache-2.0, e é dele que vêm as partes portadas aqui. Nada disso é redistribuído neste pacote: converta a sua própria cópia.

## 7. O que não foi testado

O formato do warp, a conversão de pesos, a poda do AdaLN, o codec fp8 e a montagem do conditioning têm testes automáticos (paridade de render, equivalência numérica da LoRA, arredondamento fp8 conferido contra a enumeração dos 255 valores representáveis, camada AdaLN projetada comparada com a completa, formas do ref2va com dublês). Mas **nada disso foi executado com o modelo Meridian de verdade**: não há GPU nem os pesos aqui. Em particular, continuam por confirmar se o embedding congelado do Meridian tem as chaves que o conversor procura (`prompt_embeds` / `text_token_tags`), se a LoRA convertida carrega sem chaves sobrando, se o ComfyUI aceita o `scaled_fp8` gerado aqui, se a base de 8 componentes é suficiente nos pesos reais (o erro é medido e impresso: se passar de ~1%, use `--adaln-rank 16`) e se o resultado visual bate com o pipeline oficial.
