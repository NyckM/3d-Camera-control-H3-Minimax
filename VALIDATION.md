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
