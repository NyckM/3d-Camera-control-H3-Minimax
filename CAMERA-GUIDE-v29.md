# Camera Guide Render — v29

## Gerar o guia

Adicione **bruxosdovfx • Camera Guide Render** e conecte `Camera H3.storyboard_json` à entrada homônima. Configure resolução, manequim/esfera e chão simples/com marcadores. A duração, FPS, interpolação e sentido vêm do plano calibrado (`model_path`), não da trajetória bruta do HUD.

Saídas: `rgb_frames` (IMAGE RGB float32), `fps`, `length`, `guide_prompt`, `info`.

O render é local na CPU, sem executar H3. Usa NumPy e Torch da instalação ComfyUI. O orçamento máximo é de 32 milhões de pixels por lote (~384 MB para os frames float32, além dos temporários). Comece em 320×192. Em 362 frames, reduza a resolução se necessário. O processamento respeita o botão de interrupção do ComfyUI.

FOV fixo de 40° e proxy estático, compatíveis com a ideia da prévia da v27. Não há reconstrução da sua imagem, transferência de vídeo original, animação do manequim ou previsão do resultado H3. Os frames não incluem câmera, trajetória, texto ou controles. Os marcadores coloridos são opcionais e fazem parte do guia.

## Compor e ligar ao Ref2VA

```text
Camera H3.storyboard_json → Camera Guide Render.storyboard_json
Camera Guide Render.rgb_frames → entrada de vídeo de referência do encoder Ref2VA
Camera Guide Render.guide_prompt → Camera Prompt Compose.camera_prompt
Seu texto de cena e ação → Camera Prompt Compose.scene_prompt
Camera Prompt Compose.prompt → prompt do encoder Ref2VA
```

Mantenha as imagens de identidade ligadas ao encoder. O guia não substitui essas imagens. Faça width/height/length/FPS corresponderem ao workflow de geração; o lote do guia é RGB de 24 fps e 17n+5 frames. Os nomes das entradas de vídeo variam conforme a versão do encoder.

`video_reference_index` define o token `<Video N>` do guia no texto. Seu valor deve corresponder à posição do guia no encoder. Não deduza esse número pelo sufixo interno de uma porta. O padrão é `<Video 1>` para o caso de um único guia.

Use `guide_prompt`, não `minimax_prompt` de Freeze, para esse caminho. O texto do guia separa câmera de aparência/pose/ação. Não combine simultaneamente `guide_prompt` com outro bloco completo de câmera. Para comparação **sem guia**, remova o lote de vídeo e use a saída normal `Camera H3.camera_prompt` no Compose; apenas desligar enabled não remove o vídeo do encoder.

O node antigo H3 Motion Reference não recebe imagens de identidade; para guia + imagens, prefira o encoder Ref2VA do seu workflow existente. A integração completa ainda não foi executada nesta entrega.

## Salvar vídeo

Conecte `rgb_frames` e `fps` ao novo **Camera Guide Video** e sua saída VIDEO ao Save Video nativo. Esse conversor requer `comfy_api.latest` com VideoFromComponents. Instalações antigas podem usar os frames e o FPS diretamente em seu node habitual de salvar vídeo; não precisam do conversor.

## Compatibilidade e limitações

O editor e suas oito saídas permanecem; os dois nodes são opcionais. Freeze/Action/Motion continuam disponíveis. O guia representa movimento da câmera independentemente do modo: o personagem real recebe a ação do prompt. A tarefa de extração de uma imagem estática é rejeitada.

A presença de um guia não garante fidelidade nem impede que o modelo copie sua pose/aparência. Compare com a mesma seed e referências. O preview animado distribuído é um GIF de demonstração; os frames do node são a saída destinada ao encoder.
