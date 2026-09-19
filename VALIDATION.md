# Validação v32

- `python -B tests/test_v32_height.py`: 10 testes. Interpolação da altura em trajetórias sem o campo (cai em 0) e nas três curvas; grua com mira da fonte é translação pura (mesma orientação, olho e alvo sobem juntos); com mira no pivô a câmera sobe e inclina; altura não mexe em z e elevação mexe; a altura escala com a distância do pivô; o prompt descreve CRANE e diz que não é arco de elevação; keyframe 1 fora de zero e valores fora de −3..3 são recusados; loop closure exige a altura de volta; no warp o primeiro frame continua igual e o último muda, com os buracos aparecendo embaixo ao descer a câmera.
- `node tests/test_v32_height_panel.cjs`: quatro cards na ordem órbita, elevação, distância, altura; o disco cabe dentro do card; altura travada no keyframe da fonte; limite de ±3 aplicado; a prévia do warp reprojeta ao mexer na altura, sem nova execução; o seletor 中文 traduz os rótulos. Sem exceções de página.
- `python -B tests/test_v32_contract.py`: para cada node registrado, todo parâmetro obrigatório do `run()` existe em `INPUT_TYPES` e vice-versa, e o Camera H3 é executado exatamente como o ComfyUI o chama (`run(**inputs)` com os padrões declarados). Foi a checagem que faltava quando o widget `instruction` saiu: o node aparecia certo na tela e só quebrava na execução.
- `node tests/test_v32_migrate.cjs`: workflow salvo na v31 carregado na v32 — `instruction` e `experiment_mode` somem, os soquetes reais continuam nos índices 0..2, o fio do `subject_box` segue o NOME e não o índice antigo, o fio que ia para `instruction` é removido junto com a referência na saída de origem, os valores são realinhados por nome e rodar a migração duas vezes não muda nada.
- `python -B tests/test_v26.py`: node compacto — oito widgets visíveis, o resto marcado como advanced, sem `instruction` e sem `experiment_mode`, e `ui_language` com 中文.
- Regressões: test_v23, test_guide_render, test_presets, test_v30_depth, test_v31_meridian, test_v31_convert, test_v31_reference, test_spatial, test_v24, test_v27, test_v28 e os dois testes de prévia do warp passaram. test_v25 continua falhando na mesma asserção de arredondamento do pacote v29 original.
- Não verificado: a tradução para o chinês é minha e não passou por falante nativo; cobre a interface do painel, não os tooltips longos dos widgets, que caem no inglês.

# Validação v31

- `python -B tests/test_v31_meridian.py`: 13 testes. Render Meridian idêntico à transliteração literal de `recam/geometry.render_hw` em 12 cenas (com empates de profundidade e frações exatas de .5); escadas de canvas 480/768; `scale_k` na convenção de centro de pixel; bilinear igual a `align_corners=False`; poda de bordas e dilatação de 1 px na escala 512; saída 832x480 com cinza 128 nos buracos; durações recusadas fora das oito do Meridian; play/hold/resume incluindo fim da fonte e `source_fps` diferente de 24.
- `python -B tests/test_v31_convert.py`: 10 testes. Nomes que o ComfyUI usa para detectar o H3; QKV fundido e fc1 trocado no transformer; dtypes preservados; chave desconhecida recusada; na LoRA, o delta efetivo `B @ A` de cada projeção é preservado após fundir QKV em bloco diagonal e trocar as metades do fc1; alpha por tensor, por `__metadata__` e por `lora_adapter_metadata` (com `alpha_pattern` e `use_rslora`); projeção ausente vira bloco zero; `--pruned` remove os adaptadores AdaLN; codec bf16 conferido contra padrões de bits conhecidos. Os arquivos gerados abrem na biblioteca oficial `safetensors`.
- `python -B tests/test_v31_reference.py`: 5 testes com dublês de torch/comfy. Ordem `<Video 1>` depois `<Video 2>`, ambas na classe 480; alvo na classe 768 do aspecto (1344x768 e 768x1344); fonte curta segura o último frame; durações e comprimento do warp validados; override manual de canvas.
- Compressão (`test_v31_convert.py`): codec fp8 e4m3fn arredonda sempre para o valor representável mais próximo (conferido contra a enumeração dos 255 códigos finitos) e nunca emite o código NaN; a curva do tempo bate com a fórmula do `TimeEmbedder` do ComfyUI e cabe em 8 componentes; a camada AdaLN projetada reproduz a completa dentro de 3% em t = 0, 0.13, 0.5, 0.77 e 1.0; o arquivo podado sai com `adaln_t_table`, sem `time_embedder` e com AdaLN [saída, 8] em F32; o fp8 sai com escala por camada e o marcador `scaled_fp8`; a LoRA AdaLN é projetada na mesma base.
- Regressões: todos os testes v23–v30 continuam passando (`test_v25` segue falhando na mesma asserção de arredondamento do pacote v29 original).
- Tempo na CPU do ambiente de teste: ~0,17 s por frame no formato Meridian (832x480 a partir de 1280x720 de pontos).
- Não executado: o modelo Meridian em si (pesos, GPU e VGGT-Omega ausentes). A estrutura dos `.pt` de embedding, o carregamento da LoRA convertida no ComfyUI e a qualidade final não foram verificados.

# Validação v30

- `python -B tests/test_v30_depth.py`: 15 testes. Renderer rápido do formato legado idêntico pixel a pixel ao laço original em 288 combinações de pose/pivô/mira/splat (e numa cena 1080p); pose inicial com mira da fonte é identidade; convenção de sinal igual ao HUD; Off bloqueia saídas; Freeze/Motion/Action; comprimento personalizado; `model_path`; MoGe métrico com máscara e intrinsics; pivô por `subject_box`; offsets; erros explícitos; VALIDATE_INPUTS com valores vazios; arquivos da prévia.
- `node tests/test_v30_depth.cjs`: prévia JS contra fixture gerada pelo Python, splat 0: 0 pixels diferentes em 4 poses; bases de câmera iguais a 1e-9.
- `node tests/test_v30_depth_panel.cjs` (Chromium headless via Playwright): botão liga/desliga sem alterar a trajetória, carrega a prévia no formato do `onExecuted`, buracos crescem com a órbita, edição reprojeta sem nova execução, volta ao manequim, tradução EN. Sem exceções de página. Screenshot inspecionada.
- Regressões: test_v23, test_v26 (atualizado para 10 saídas), test_guide_render, test_presets, test_spatial, test_v24, test_v27, test_v28 passaram. test_v25 falha na mesma asserção de arredondamento de azimute (104 == 104.47) também no pacote v29 original, antes das mudanças.
- Tempo na CPU do ambiente de teste: 0,48 s por frame 1080p (laço original: 2,6 s); 121 frames 960×540 em Motion Frame: 19 s.
- Não executado dentro de uma instalação ComfyUI real: Torch, ProgressBar, ExecutionBlocker, `onExecuted` e `/view` foram exercitados só por substitutos. Sem inferência do H3; a qualidade do vídeo gerado não foi medida.

# Validação v29

- Cinco testes do renderer passaram com NumPy real: shape/dtype/faixa, volta completa, movimento, limites de memória, cancelamento e posições extremas.
- O wrapper do node foi testado com doubles de Torch/ComfyUI; isso não comprova integração com essas APIs reais. O conversor VIDEO não foi executado no ComfyUI.
- Render real de 124 frames em 320×192 exportado como GIF de demonstração; contact sheet de vistas frontal/lateral/traseira inspecionada.
- Nove testes anteriores de backend passaram. Sintaxe Python verificada.
- Sem inferência H3. Não foi medido ganho de fidelidade com referência visual.

# Validação v28

- Teste Edge headless `tests/test_v28.cjs`: seleção sem alteração, aplicação de órbita 360°, interpolação, desfazer, bloqueio de efeitos não representáveis e tempos normalizados de pausa/avanço. Inclui regressões de vídeo, scrub, edição e Freeze.
- Todos os nove paths passaram pelo validador Python do editor; 18 itens classificados.
- Quatro testes de composição de prompt passaram. Screenshot inspecionada; sem exceções de página no teste.
- Sem inferência H3 ou execução dentro do ComfyUI. Os presets são interpretações dos movimentos, não reconstruções dos renders originais.

# Validação v27

- `node tests/test_spatial.cjs`: 45 casos de geometria; correspondência entre projeção e arraste, identidade sem deslocamento, preservação de voltas, limites, base nos polos e frustum finito.
- `node tests/test_v27.cjs`: Edge headless com vídeo sintético; visão de câmera atualiza após arraste, toggle de visibilidade, raio e tempo preservados, zoom, primeiro frame fixo, teclado, playback e scrub. Sem exceções de página. Screenshot inspecionada.
- `python -B tests/test_v26.py` e `python -B tests/test_v23.py`: nove testes de backend passaram.
- Sem inferência H3 ou execução dentro do ComfyUI. O render simplificado usa ordenação de faces e recorte pelo plano próximo; não representa geometria reconstruída da referência.

# Validação v26

4 testes novos de composição passaram: registro, saída neutra/calibrada, preservação do texto/bypass/idempotência e independência dos experimentos. Os 5 testes de regressão do backend também passaram. Sem inferência ou execução de workflows REF2VA/FLFVA.

# Validação v25

Teste de navegador test_v25.cjs passou: zoom não altera JSON, expansão do canvas, arraste de órbita/elevação, proteção do primeiro frame, teclado e zoom durante vídeo. Inclui regressões de playback da v24. Screenshot inspecionada. Os cinco testes de backend também passaram. Sem teste dentro do ComfyUI.

# Validação v24

- Teste de integração em Microsoft Edge headless com vídeo WebM sintético decodificado pelo navegador: play/pause, edição sem interromper reprodução, inserção de keyframe durante reprodução, scrub sincronizado, alteração de duração, remoção da referência e padrão Freeze.
- Zero exceções de página no teste; captura de tela do painel inspecionada.
- Cinco testes de backend herdados da v23 passaram, incluindo 24 combinações de formatos e experimentos.
- Sintaxe dos módulos JavaScript alterados e dos arquivos Python verificada.
- Não executado dentro de uma instalação ComfyUI nem realizada inferência H3. Compatibilidade com todos os codecs não foi testada.

Teste de navegador: instale Playwright, disponibilize Microsoft Edge e execute `node tests/test_v24.cjs` na pasta do pacote. PLAYWRIGHT_MODULE pode indicar o módulo Playwright instalado; BROWSER_CHANNEL pode selecionar outro canal disponível. A captura de teste é salva no diretório temporário do sistema.
