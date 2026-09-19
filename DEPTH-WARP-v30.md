# Depth Warp — v30/v31

Opção do **bruxosdovfx • Camera H3** que **anima a sua referência pela profundidade** seguindo os mesmos keyframes da trajetória. A saída é um vídeo com a cena reprojetada no novo ponto de vista e **cinza 128** onde a câmera original nunca viu.

É o `<Video 2>` do [Viggle Meridian](https://huggingface.co/Viggle/Meridian), o fine-tune do MiniMax-H3 guiado por render de nuvem de pontos. A ligação completa com o Meridian está em **MERIDIAN-v31.md**; aqui ficam os controles do warp em si.

## Ligar

1. No cabeçalho do painel, clique **◈ Depth Warp** (ou mude `depth_animation` para `Depth Warp`).
2. Conecte a referência em `reference_image` (imagem ou sequência).
3. Conecte **uma** fonte de profundidade:
   - `moge_geometry` ← **Run MoGe Inference** (nativo do ComfyUI). Recomendado: profundidade em metros, com máscara e intrinsics. `warp_depth_ratio`, `warp_invert_depth` e `warp_smooth_depth` deixam de valer.
   - `depth` ← Depth Anything V2 ou similar (claro = perto). 1 mapa, ou um por frame.
4. Rode o node uma vez. A **Visão da câmera** passa a mostrar a cena reprojetada, e arrastar keyframes, mudar a timeline ou os offsets reprojeta **ao vivo**, sem rodar de novo.

Saídas novas, acrescentadas ao fim (as 8 anteriores não mudaram de posição):

| Saída | O que é |
|---|---|
| `depth_warp` (IMAGE) | vídeo de controle, cinza 128 nos buracos |
| `warp_mask` (MASK) | 1 onde é buraco (área a gerar), 0 onde há pixel reprojetado |

Com `depth_animation = Off` nada é calculado e os nodes ligados nessas duas saídas são **bloqueados** (não executam), então dá para deixar a ligação feita e alternar.

## Como os modos se comportam

| Modo | O que é reprojetado |
|---|---|
| Freeze Frame | o frame `freeze_index`, parado, com a câmera andando |
| Action Frame | a imagem, parada; a ação continua vindo do prompt |
| Motion Frame | cada frame da sequência na sua hora (`source_fps` → 24 fps), com o mapa de profundidade do mesmo frame |

## Widgets

| Widget | Padrão | Uso |
|---|---|---|
| `warp_hfov` | 50 | Lente horizontal assumida. `0` lê as intrinsics do MoGe (~10% curtas). Não é o FOV ilustrativo de 40° do painel. |
| `warp_depth_ratio` | 6 | Só depth relativo. Close de rosto 2.5–4, plano médio 4–8, cena ampla 8–16. |
| `warp_invert_depth` | off | Só depth relativo. Ligue se o fundo andar como se fosse frente. |
| `warp_smooth_depth` | off | Só depth relativo. Menos pontinhos; usa opencv. |
| `warp_aim` | `source aim` | Orbita o pivô mantendo a mira da câmera original: keyframe 1 = imagem exata. `look at pivot` centraliza o pivô. |
| `warp_pivot_depth` | 0 (auto) | Centro da órbita. Auto: mediana 3D do `subject_box`; sem caixa, 1.05 no depth relativo ou a metade mais próxima do centro no MoGe. O raio é `distance × pivô`. |
| `warp_direction` | `panel (geometric)` | Segue exatamente o que o painel desenha. `model_path` usa o caminho calibrado por `orbit_direction`, como o Camera Guide Render. |
| `warp_length` | 0 | Frames do warp. 0 = `length` do perfil. O Meridian só aceita 73, 90, 107, 124, 141, 158, 175 e 243. |
| `warp_long_side` | 0 | Reduz o maior lado antes do warp. Ignorado no formato Meridian, que tem canvas fixo. |
| `warp_offset_azimuth` / `_elevation` / `_distance` | 0 / 0 / 1 | Pose somada a **toda** a trajetória, só no warp. |
| `warp_hold_at` / `warp_hold_frames` | 0 / 0 | Congela a ação com a câmera andando (bullet time). Veja MERIDIAN-v31.md. |

### Por que existe o offset

No Camera H3 o keyframe 1 é sempre a imagem original (0°, 0°, 1). Quando o clipe inteiro deve começar num ângulo novo, `warp_offset_azimuth = -25`, por exemplo, faz o warp começar 25° à esquerda já no frame 1 e depois seguir os seus keyframes a partir dali. O prompt do H3 não muda. Quando o warp inteiro fica a menos de 10° da fonte, o `info` avisa.

## O formato do render

Cinza 128 nos buracos, z-buffer com splat 3×3, poda de bordas de profundidade (janelas 3×3 com variação acima de 30% na escala 512, mantendo só onde todos os "pais" bilineares sobreviveram) e canvas classe 480 com recorte central — 832×480 em 16:9. A matemática é um port de `recam/geometry.py` do Meridian e bate pixel a pixel com o laço original em `tests/test_v31_meridian.py`.

**Duas diferenças de geometria:** o Meridian usa o VGGT-Omega, que estima profundidade **e a pose da câmera de cada frame**, além de podar por confiança. Aqui a fonte é MoGe ou depth relativo e a câmera da fonte é tratada como parada. Em plano travado é equivalente; em câmera na mão, não.

## Limites

- A prévia do painel usa a geometria (pivô, hfov, profundidade, `subject_box`) da **última execução**; só a pose é ao vivo. Mudou algum desses? Rode de novo. Depois de recarregar a página a prévia some até a próxima execução.
- A prévia usa z-buffer em até 384 px; a saída real vem do Python no formato exato.
- Acima de ~40° o próprio Viggle aponta instabilidade no Meridian.
- Limite de 500 milhões de pixels por saída (~6 GB em float32).
- Tempo na CPU do ambiente de teste: ~0,17 s por frame no canvas 832×480 a partir de 1280×720 de pontos.
- O warp não gera nada sozinho: é o sinal de controle. A qualidade final depende do modelo.

> O renderizador magenta da v30 continua no código para não quebrar workflows salvos, mas saiu da lista de opções do widget.
