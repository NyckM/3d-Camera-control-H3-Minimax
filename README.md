# bruxosdovfx · Camera H3 v32

## v32

- **Altura (grua).** Eixo novo nos keyframes, separado da elevação: a elevação gira a câmera em torno do sujeito; a altura sobe e desce a câmera sem girar, mantendo a direção da lente, então o sujeito se desloca no quadro. Entra no prompt, no warp, no render de guia e na prévia do painel. Unidade: múltiplos do raio inicial, de −3 a 3.
- **Node compacto.** Os widgets secundários ficam atrás do botão **Advanced** do node. Visíveis: trajetória, profile, interpolation, frame_mode, source_fps, ui_language, depth_animation e warp_length.
- **Painel 2×2.** Em cima o que gira (órbita, elevação), embaixo o que desloca (distância, altura). O disco de órbita não é mais cortado.
- **中文.** Terceiro idioma no seletor do painel e no widget `ui_language`. Cobre a interface; textos sem versão em chinês caem no inglês.
- **Removidos:** o widget `instruction` e os modos experimentais. Escreva a cena no **Camera Prompt Compose**. Workflows salvos antes da v32 são remapeados por nome ao carregar; se o seu `instruction` tinha texto, ele aparece uma vez no console do navegador.

## Meridian — v31

O Depth Warp gera o vídeo de controle no formato do [Viggle Meridian](https://huggingface.co/Viggle/Meridian) (fine-tune do MiniMax-H3 guiado por render de nuvem de pontos): buraco cinza 128, z-buffer 3x3, poda de bordas de profundidade e canvas classe 480. Junto vêm os nodes **Meridian Text Cond** e **Meridian Reference**, que montam o ref2va com `<Video 1>` = clipe original e `<Video 2>` = warp, e `meridian_convert.py`, que converte transformer, LoRA DMD e embeddings congelados do formato diffusers para o do ComfyUI sem precisar de Torch.

`warp_hold_at` / `warp_hold_frames` congelam a ação enquanto a câmera continua andando (o `--freeze F:N` do Meridian).

Detalhes, ligação do workflow, conversão de pesos e o caso de base podada: **MERIDIAN-v31.md**.

## Depth Warp — v30

Opção **◈ Depth Warp** no cabeçalho do painel (widget `depth_animation`). Com `reference_image` e `depth` ou `moge_geometry` conectados, o node anima a referência pela profundidade seguindo os keyframes: cena reprojetada com buracos cinza. Duas saídas novas no fim, `depth_warp` (IMAGE) e `warp_mask` (MASK); as oito anteriores continuam nas mesmas posições.

Depois da primeira execução a **Visão da câmera** mostra o warp e reprojeta ao vivo enquanto você arrasta os keyframes. Funciona em Freeze, Action e Motion Frame. `warp_offset_azimuth/elevation/distance` deslocam o warp inteiro para começar num ângulo novo já no frame 1.

Consulte **DEPTH-WARP-v30.md** para os widgets e limites do warp, e **MERIDIAN-v31.md** para o pipeline completo. Sem dependências novas; roda na CPU.

## Guia RGB opcional — v29

Novo **Camera Guide Render**: conecta `storyboard_json` e gera frames RGB de manequim/esfera seguindo o plano calibrado. A saída `guide_prompt` funciona com o Camera Prompt Compose. Novo **Camera Guide Video** converte os frames para VIDEO nas versões compatíveis do ComfyUI.

Consulte **CAMERA-GUIDE-v29.md** para a ligação ao Ref2VA, imagens de identidade, numeração do vídeo e comparação com texto somente. Render testado localmente; inferência H3 e integração real com Torch/ComfyUI ainda não executadas.

## Presets de trajetória — v28

O seletor **Presets** contém 18 movimentos catalogados a partir dos exemplos públicos de loopforge0. Nove têm trajetórias aplicáveis; nove ficam disponíveis para consulta, com o botão Aplicar desativado e explicação da limitação.

1. Escolha o preset. A seleção não altera o caminho.
2. Leia a descrição. O símbolo ≈ indica aproximação, como dolly físico em lugar de zoom óptico.
3. Clique **Aplicar trajetória / Apply path**. A trajetória e a interpolação são substituídas; duração e modo de cena permanecem iguais.
4. Edite os keyframes normalmente. **Desfazer preset / Undo preset** restaura o caminho e a interpolação anteriores à última aplicação, inclusive descartando ajustes feitos depois dela. Esse histórico é local à sessão.

As amplitudes são propostas para o editor, não medidas dos vídeos. Tempos normalizados acompanham a duração atual: a pausa de 2 s do C-01b só corresponde a 2 s no perfil de 124 frames. A descrição original não garante que o modelo respeite esses tempos.

Consulte **PRESETS-v28.md** para a classificação, fontes e limitações de cada movimento. Personagens, cenários, áudio e prompts completos do repositório não foram incorporados. Não há importador automático de texto livre nesta versão; é um catálogo de conversões manuais revisadas.

## Visão e controle espacial — v27

- **Visão da câmera / Camera view** mostra um manequim 3D em perspectiva conforme a pose da timeline. O botão mostra/oculta a janela sem alterar a trajetória.
- As linhas douradas no editor representam o campo de visão da câmera. A proporção acompanha a referência local/conectada, com 16:9 quando não há referência; o FOV vertical é ilustrativo e fixo em 40°.
- Pontos numerados e ícone da câmera usam interseção geométrica do ponteiro com a esfera da órbita. O movimento considera o zoom e o ângulo de observação, preservando tempo e distância. Alt + roda ou Distance ajustam o raio separadamente.
- O arraste preserva o hemisfério inicial e se limita à borda da esfera quando o cursor sai de sua projeção. Para alcançar o outro lado, gire a vista do editor e arraste novamente. A elevação respeita o limite do painel. Não é um gizmo de translação XYZ livre.
- O primeiro frame continua fixo. Voltas acumuladas não são reduzidas automaticamente a 0–360°. Campos numéricos continuam disponíveis para edição exata.
- A imagem/vídeo original permanece no editor. O manequim é apenas uma referência geométrica estática, não uma reconstrução 3D da imagem nem uma previsão da ação. A câmera da prévia segue a trajetória salva do HUD; a calibração de sinal enviada ao H3 continua sendo feita pelo compilador.
- Implementação própria, sem novas dependências e sem incorporar arquivos do toyxyz. Os arquivos indicados pelo usuário foram usados como referência de funcionalidades.

## Composição de prompt — v26

Nova saída **camera_prompt** ao final do editor e novo node **Camera Prompt Compose**. Conecte seu texto de cena/ação ao Compose, as instruções de câmera à outra entrada e a saída ao encoder de texto do workflow existente. `enabled = false` devolve o prompt original.

Consulte **INTEGRACAO-v26.md** para REF2VA/FLFVA, diferenças entre as saídas e limites da integração. As sete saídas anteriores mantêm suas posições; agora são oito no editor. Nenhum encoder externo foi substituído ou testado nesta entrega.

## UI da v25

- Zoom visual de 50% a 400%, começando em 160%. Use a roda sobre o canvas ou os botões −/+. Isso amplia a referência e a cena de edição sem modificar a trajetória nem o prompt.
- **Ampliar canvas / Expand canvas** alterna a área de edição para 560 px e largura total. Clique novamente para voltar.
- **Restaurar vista / Reset view** restaura zoom e ângulo de observação.
- Arraste os pontos numerados diretamente no canvas: horizontal altera azimute, vertical altera elevação. Os tempos permanecem iguais. O primeiro ponto fica fixo.
- Pontos próximos recebem marcadores separados com linhas para suas posições reais; as setas do teclado também ajustam o marcador em foco.
- Alt + roda altera a distância da câmera do keyframe selecionado. O controle Distance continua disponível.
- Os marcadores da timeline continuam arrastáveis para mudar o tempo. A edição de posições no canvas e o zoom mantêm o vídeo tocando.
- Controles novos disponíveis em português e inglês. Zoom/expansão são preferências locais desta sessão e não ficam salvos no workflow.

## Vídeo durante a edição — v24

1. Clique **Imagem / vídeo** e selecione um vídeo local compatível com o navegador (MP4 H.264 ou WebM).
2. Use o botão **▶** compartilhado para reproduzir vídeo e trajetória. O vídeo aparece ao lado do plano de câmera e também no cartão central da cena.
3. Ajuste os controles ou arraste a câmera: o playback continua, alterando o keyframe selecionado. O primeiro keyframe permanece fixo.
4. Clique **+ Keyframe agora** para inserir e selecionar um ponto na posição atual da timeline, sem interromper o vídeo. Um ponto já existente nesse instante é selecionado; limite de 24 pontos.
5. Clique ou arraste na timeline para pausar e buscar um instante. Play no fim reinicia a prévia; a reprodução para ao chegar ao final.
6. Use **usar o node** para remover o vídeo local e restaurar a imagem conectada.

O vídeo inteiro é mapeado à duração de saída. A velocidade indicada vale apenas para a prévia; não altera source_fps nem os frames de geração. A referência toca sem áudio. Se o navegador não aceitar o codec ou a velocidade necessária, o painel informa o erro.

O arquivo local não é enviado ao servidor nem salvo no workflow: selecione-o novamente após recarregar. Esta versão abre vídeo pelo seletor local; não extrai automaticamente o vídeo de nodes upstream. Para gerar, continue conectando a referência ao workflow. A visualização mostra a ação original e o plano de câmera, não uma reconstrução do vídeo em outro ângulo.

## Modos

- **Freeze Frame**: congela a cena e move a câmera. Continua como padrão.
- **Action Frame / Animar imagem**: anima a imagem com a ação escrita em `instruction` enquanto a câmera se move.
- **Motion Frame**: preserva a ação de um vídeo usando Ref2VA.

## Action Frame

Conecte uma imagem em `reference_image`, selecione Action Frame e descreva a ação em `instruction`, por exemplo: `A woman walks forward and raises her right hand. Her coat moves in the wind.`

Use a mesma imagem no workflow nativo de imagem para vídeo e conecte `minimax_prompt`, `length` e `fps`. Não conecte `options` ao H3 Edit nem repita a imagem inicial como âncora final. Se runtime_task estiver disponível, mantenha `scene coverage | camera path`.

Imagem e ação não vazia são obrigatórias. Pausas da câmera afetam somente o ponto de vista. Action e Motion desativam fechamento por ancoragem final e rejeitam a tarefa de extração de imagem estática.

## Motion Frame

Use uma sequência com Ref2VA e o encoder H3 Motion Reference. Conecte `minimax_prompt` e `length` do editor. A sequência também precisa ser ligada diretamente ao encoder, preparada em 24 fps e comprimento compatível. O editor atual tem sete saídas e não exporta o lote IMAGE reamostrado. A documentação histórica descreve saídas IMAGE que não existem nesta interface.

## Mudanças

Ação antes da câmera nos prompts temporais; coreografia sem duplicação; JSON temporal com uma única trajetória calibrada; Action suportado também nos experimentos compactos. IDs, sete saídas e padrão Freeze preservados. Nenhuma dependência adicionada.

## Instalação

Feche ComfyUI, guarde a versão anterior fora de custom_nodes e substitua a pasta ComfyUI-H3-Camera-Editor pela pasta deste pacote. Reinicie e recarregue a interface. Evite duas cópias dos mesmos nodes em custom_nodes.

## Validação

Execute `python -B tests/test_v23.py`. Testes de contratos de prompt não comprovam qualidade visual. Não foi executada inferência H3 nesta entrega. Compare Freeze/Action com mesma imagem, modelo, seed e trajetória; observe personagem caminhando/acenando e uma pausa intermediária da câmera. Avalie ação e câmera separadamente.

README-LEGACY.md preserva a documentação antiga como histórico.
