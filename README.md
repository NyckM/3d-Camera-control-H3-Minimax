# Camera H3 da Bruxos do VFX

`#bruxosdovfx`

<img width="517" height="693" alt="Captura de tela 2026-09-10 115449" src="https://github.com/user-attachments/assets/2eaf4253-3339-4ff1-af9d-961d572ef601" />

Planejador visual de câmera para o MiniMax H3 dentro do ComfyUI. Você arrasta a câmera numa esfera 3D, marca keyframes numa timeline, e o node compila essa trajetória em prompts que o H3 entende.

Ele **compila prompts, não embeddings de câmera**. Não existe adaptador geométrico aqui: o H3 continua livre para errar ângulo, tempo e escala. O que este node faz é escrever a instrução da forma mais precisa e menos ambígua possível, e várias decisões dele existem porque a forma anterior falhava de um jeito específico.

Não chama API, não baixa nada, não tem dependência Python além da biblioteca padrão.



https://github.com/user-attachments/assets/a9b541e5-2b18-4f1d-8e16-37445b6dbac4



https://github.com/user-attachments/assets/ea9af03e-2c8e-4589-abf0-9c002241aba2




---

## Instalação

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/<seu-usuario>/ComfyUI-H3-Camera-Editor
```

Reinicie o ComfyUI. O node aparece em **`Bruxos do VFX/Camera H3`** com o nome **Camera H3 da Bruxos do VFX**.

---

## Ligações

| Saída deste node | Onde ligar |
|---|---|
| `compiled_prompt` | `compiled_prompt` do Text Encode H3 Edit / Generate |
| `options` | `options` do Text Encode H3 Edit / Generate |
| `length` | a contagem de frames da geração |
| `fps` | o `fps` do node de criação de vídeo |

`compiled_prompt` **e** `options` são obrigatórios juntos. A saída `minimax_prompt` é alternativa a `compiled_prompt`, nunca adicional — ligue uma ou outra na mesma entrada.

Ligue também a sua imagem em `reference_image`. É a mesma imagem que já alimenta o `source_image` do H3 Edit; ligando aqui ela aparece no painel e a proporção real do quadro entra no prompt.

https://github.com/user-attachments/assets/33149617-bde1-4199-ae65-078f2f3dec23



Para salvar o vídeo, decodifique o resultado do sampler com o **VAE de vídeo H3** — não com o decodificador calibrado de scene coverage, que espera janelas fixas que uma trajetória arbitrária não tem.

---

## O painel

Arraste a câmera roxa na esfera para orbitar. O arraste **trava no eixo do primeiro movimento**: horizontal orbita, vertical eleva. Solte e arraste de novo para trocar de eixo. Isso existe porque, sem a trava, tentar dar uma volta simples ganhava elevação sem querer.

- **Role o mouse** para mudar a distância.
- **Arraste o fundo** para girar a visualização, sem alterar a trajetória.
- **Keyframes** define quantos pontos a timeline tem, de 2 a 24. O primeiro é sempre a imagem original e não pode ser movido.
- **⟳ Órbita pura** zera a elevação de todos os keyframes e mantém o azimute. É o atalho para uma volta na altura dos olhos.
- **Imagem de referência** carrega um arquivo local para a prévia. Só é preciso quando o node roda fora do ComfyUI; com `reference_image` ligada a foto vem sozinha.

O painel avisa a partir de 20° de elevação que o horizonte já sai do quadro, e de novo a partir de 45°, quando o vídeo tende a virar plongée.

### Barra "Testes"

No topo do painel, dois botões ligam e desligam funções que estão em avaliação, mais um indicador:

| Botão | O que faz |
|---|---|
| **Contratos estendidos** | Alterna o widget `prompt_detail` |
| **Ângulo único (imagem)** | Alterna o widget `runtime_task` |
| **loop closure** | Indicador, só leitura. Fica verde quando a trajetória fecha uma volta completa |

Os botões escrevem nos widgets de verdade, então a escolha fica salva no workflow e os dois nunca discordam.

---

## Widgets

### `camera_trajectory`
A trajetória em JSON, escrita pelo painel. Cada keyframe tem `time` (0 a 1), `azimuth` em graus, `elevation` em graus e `distance` como múltiplo do raio inicial. Dá para editar à mão. O primeiro keyframe tem que ser `time=0, azimuth=0, elevation=0, distance=1`, que é a imagem original.

### `profile`
124, 243 ou 362 frames a 24 fps. **Todos** os tempos do plano saem daqui: os instantes dos keyframes, as faixas de cada trecho e a duração declarada no prompt. Por isso `length` e `fps` são saídas — ligue-as em vez de digitar os números à mão em dois lugares.

### `interpolation`
`smooth` ou `linear`. Em `smooth`, a câmera suaviza a entrada e a saída da tomada e mantém taxa constante no meio; ela só para onde o sentido do giro realmente inverte.

### `instruction`
Texto livre que entra **uma vez**, no fim do prompt. Escreva aqui só o que o node não tem como saber: cenário, qual é o alvo quando há mais de uma pessoa, referência de estilo. Já sai pronto e não precisa repetir: congelamento da cena, primeira imagem como referência, mira travada, roll zero, ângulos, tempos, tomada única sem cortes.

> Cuidado com contradições. Escrever "keep camera radius constant" enquanto algum keyframe muda a distância faz o prompt afirmar duas coisas opostas.

### `subject_framing`
Quanto o sujeito ocupa do quadro **na imagem original**. Calibrado contra as caixas reais do tutorial que a MiniMax distribui: uma figura de corpo inteiro a distância mede `W=0.071, H=0.249`, um grande primeiro plano mede `W=0.52, H=0.701`.

| opção | largura | altura | quando usar |
|---|---|---|---|
| `close-up` | 53% | 72% | cabeça e ombros |
| `medium shot` | 28% | 56% | cintura para cima |
| `wide shot` | 9,7% | 34% | corpo inteiro ao longe |

### `subject_box`
Onde o sujeito está, no formato `[L=0.516, T=0.148, W=0.071, H=0.249]`. Vazio usa os limites da imagem inteira — deliberadamente, sem chutar uma caixa. Preencha se o sujeito estiver bem fora do centro.

### `minimax_format`
O mesmo plano em quatro redações, para a saída `minimax_prompt`:

- `coordinate only` — bloco de coordenadas em texto
- `coordinate + H3 sections` — o mesmo, embrulhado em `subject_definitions` / `summary` / `retention_analysis` / …
- `compact JSON` — objeto JSON, quase sem prosa
- `compact JSON (no boxes)` — só parâmetros de câmera, sem caixa de tela

### `elevation_range`
Alcance do controle de elevação: `+/-15`, `+/-30` (padrão), `+/-60`, `+/-89`. Também escala a sensibilidade do arraste vertical.

Com o campo de visão assumido, o horizonte já sai do quadro por volta de 20° — a 13° o chão ocupa 82% da imagem. O range antigo de ±89 era quase todo inútil e deixava o arraste hipersensível. **Reduzir o range nunca reescreve keyframe:** um ponto em 70° continua em 70° e o slider se abre para caber nele.

### `orbit_direction`
`invert H3 orbit` ou `same as HUD`. Calibração do sentido entre o que o painel desenha e o que o H3 entrega. Não altera a trajetória salva.

### `runtime_task`
- `scene coverage | camera path` (padrão) — **vídeo**, com a duração vindo do `profile`.
- `directed | new camera angle` — **uma imagem** de um novo ângulo. Fixa 39 frames, ignora o `profile`, completa o movimento em 65% do clipe e pede que o enquadramento fique imóvel no resto, porque é dessa cauda parada que o decodificador tira a imagem final.

Os perfis de *character sheet* não são oferecidos: o upstream levanta erro se forem combinados com o âncora de frame que este node usa.

### `prompt_detail`
- `v15 baseline` (padrão) — o prompt sai exatamente como na versão anterior.
- `extended contracts` — acrescenta separação de eixos, teste de direção por borda de quadro, completude do giro, graus por segundo e magnitude de paralaxe.

O modo estendido tem quase o dobro de palavras. Prompt maior não é automaticamente melhor, então ele é opt-in: alterne só este widget na mesma trajetória para comparar.

---



https://github.com/user-attachments/assets/0882bfde-9f62-4a1f-9bda-7da121dbe7e2



## Saídas

### `compiled_prompt` — STRING
Prompt em prosa nas seções do H3: `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape`, `non_diegetic_music`.

### `options` — H3EDIT_OPTIONS
As 13 chaves que o encoder do H3 Edit lê. Preenchidas explicitamente, todas: o upstream cai para os widgets legados escondidos dele em qualquer chave ausente, e esses guardam valores velhos de workflows salvos.

`coverage_arc_degrees` e `coverage_direction` saem do giro real. `coverage_loop_closure` liga sozinha quando a trajetória fecha — veja abaixo.

### `storyboard_json` — STRING
A tabela de storyboard: proporção do quadro, duração, a trajetória crua e cada trecho com modo de câmera, curva de velocidade e as poses de início e fim.

### `info` — STRING
Diagnóstico legível. Ligue num `PreviewText`. Mostra a versão, a task ativa, a contagem de frames, avisos de keyframes fora do range e se a loop closure está ligada.

### `minimax_prompt` — STRING
A mesma trajetória na redação escolhida em `minimax_format`. Alternativa ao `compiled_prompt`.

### `length` — INT e `fps` — FLOAT
Contagem de frames e taxa contra as quais o plano foi cronometrado. Ligue nos nodes de geração e de vídeo. Se a geração rodar com outra contagem, a coreografia descreve uma cena que não existe.

`fps` é FLOAT porque é o que o `CreateVideo` do ComfyUI aceita. `length` é a contagem de frames; os tempos dos keyframes usam o instante do último frame visível, `(length - 1) / fps`, então o arquivo dura um intervalo de frame a mais.

### `h3world_actions` — STRING
Cronograma de ações para o [H3-World](https://arxiv.org/abs/2609.01560), que codifica **uma cláusula de texto por latente de vídeo** — 37 num clipe de 124 frames.

```
latent  1 [0.000s-0.139s] J     the camera pans left slowly
latent 37 [4.986s-5.125s] F+L+K the camera pans right and tilts up fast
```

`W`, `A`, `S` e `D` nunca são emitidos, porque movem o personagem. A saída declara os próprios limites, e eles não são detalhes:

- **Pan não é órbita.** É a câmera girando onde está. A perspectiva não muda, nada oculto é revelado, e o sujeito escorrega para fora do quadro.
- **Distância não tem tecla**, então o raio é descartado.
- **Só 124 frames é horizonte treinado.**
- **`I` contra `K` não está publicado.** A cláusula em texto é o que o H3-World codifica; a coluna de teclas é conveniência.

Isso não substitui a integração: o H3-World exige a LoRA, a codificação por intervalo e o roteamento de atenção dirigida do pacote de nodes correspondente.

---

## Loop closure

Quando a trajetória fecha uma volta — **arco de exatamente 360°, mesma elevação e mesma distância do início** — o node liga `coverage_loop_closure`. No upstream, essa flag codifica a imagem de origem uma segunda vez e crava o último frame nela.

Isso é uma âncora no latente, não texto. Para uma volta completa é a diferença entre *pedir* o giro e *obrigá-lo*: o modelo não consegue parar no meio do caminho.

| trajetória | loop closure |
|---|---|
| 360° | ligada |
| duas voltas (−720°) | ligada |
| 355° | desligada |
| 360° mudando distância | desligada |
| 360° mudando altura | desligada |

Os três últimos importam: se a câmera termina em outro raio ou outra altura, o último frame não é igual ao primeiro, e cravar a imagem lá brigaria com a trajetória.

**Se o seu giro não completa, feche a volta.** É a única função aqui que age fora do prompt.

---

## Limitações

- É orientação por prompt. O H3 pode errar ângulo, tempo e escala, e nenhuma redação resolve isso por completo.
- Sem `subject_box` preenchido, o node não sabe onde o sujeito está no quadro.
- Sem `reference_image` ligada, as coordenadas são normalizadas para 16:9.
- O modo `directed | new camera angle` entrega imagem, não vídeo.
- O cronograma do H3-World descreve pan e tilt, que são um plano diferente da órbita desenhada no painel.

---

## Créditos

Node dos **Bruxos do VFX**.

Depende do [`ethanfel/ComfyUI-MiniMax-H3-Edit`](https://github.com/ethanfel/ComfyUI-MiniMax-H3-Edit). O vocabulário de movimento segue o `buildViewPrompt` da skill Multi-Shot da MiniMax e o formato de coordenadas da skill Coordinate Camera Control Designer. A saída de ações implementa o esquema descrito em [H3-World, arXiv:2609.01560](https://arxiv.org/abs/2609.01560).
