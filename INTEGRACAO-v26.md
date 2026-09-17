# Integrar câmera ao prompt — v26

```text
Camera H3.camera_prompt ────────┐
                               ▼
Seu texto de cena/ação → Camera Prompt Compose → prompt do encoder existente
```

1. Adicione **bruxosdovfx • Camera H3** e **bruxosdovfx • Camera Prompt Compose**.
2. No editor, defina trajetória, duração e sentido da câmera.
3. Conecte a nova saída `camera_prompt` (oitava saída) à entrada homônima do Compose.
4. Escreva seu texto em `scene_prompt` ou conecte uma saída STRING. No ComfyUI, converta esse widget em entrada caso necessário.
5. Conecte `prompt` do Compose à entrada STRING de prompt do encoder que seu workflow já usa.
6. Mantenha imagens, vídeos de referência, modelo, sampler e condicionamentos do workflow. Faça a contagem de frames e FPS corresponder às saídas `length` e `fps` do editor.
7. Compare com `enabled = false`: o Compose devolve exatamente o texto original.

## REF2VA e FLFVA

Este é um compositor de texto, sem chamada a encoder específico. Em REF2VA, mantenha as referências ligadas ao encoder existente. Em FLFVA, mantenha as entradas de frames inicial/final do workflow existente. O Compose apenas fornece o texto; não conecta nem altera esses frames.

Os nomes exatos das entradas dependem dos nodes instalados. Se o encoder usa uma entrada CONDITIONING, ligue o texto antes, no node que codifica o prompt. Se exige JSON ou seções estruturadas, não coloque este texto diretamente nesse campo: use a entrada de instrução livre apropriada. Não foram testados workflows REF2VA/FLFVA reais nesta entrega, nem confirmada equivalência da nomenclatura FLFVA com FL2VA.

## Saída independente do modo de cena

`camera_prompt` não inclui `instruction`, comandos Freeze, tokens de referência, silêncio, ancoragem final ou metadados de diagnóstico. Usa apenas geometria calibrada e interpolação; o prompt de cena vem do Compose.

Para usar somente o controle de câmera, você pode deixar o editor em **Freeze Frame**, sem referência e com `instruction` vazio: a saída `camera_prompt` é neutra e não congela a cena. As saídas antigas `compiled_prompt`/`minimax_prompt` continuam seguindo o modo Freeze/Action/Motion e não devem ser confundidas com essa nova saída.

Action Frame ainda exige imagem e instrução; Motion Frame ainda exige sequência. Esses modos são úteis quando você também usa as saídas completas, mas não são exigidos para o caminho modular acima.

Não conecte também `compiled_prompt`/`minimax_prompt` à mesma composição: isso duplicaria instruções completas. O Compose evita reaplicar o mesmo bloco quando ele já está no fim do texto.

Se o texto original pedir uma câmera diferente ou o workflow ancorar uma pose incompatível com a ação, a composição não resolve essa contradição automaticamente. Não apaga nem reescreve o prompt do usuário.

## Exemplo de cena

`A woman walks across the courtyard, turns her head and waves. Her coat and the nearby leaves move in the wind.`

Adicione a órbita no editor e envie somente `camera_prompt` ao Compose. Mantenha a mesma seed para comparar enabled ligado/desligado. O resultado continua dependendo da interpretação do modelo.
