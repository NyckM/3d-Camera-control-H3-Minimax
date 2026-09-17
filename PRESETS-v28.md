# Presets v28

Interpretações manuais dos movimentos, não trajetórias extraídas dos renders. Amplitudes escolhidas para o editor. Nenhum texto de personagem, cenário ou áudio é copiado. Tempos normalizados escalam com a duração atual. Freeze/Action/Motion não é alterado.

Origem: https://github.com/loopforge0/minimaxh3-shots-skills/tree/main/prompts

O README de origem alerta que os prompts são exemplos específicos, não templates, e que alguns tempos solicitados não foram respeitados pelo modelo.

- **C-01 Aproximação rápida (dolly)** (approx): Adaptação física do crash zoom; não altera a lente. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-01_crash-zoom-in.txt)
- **C-01b Pausa + aproximação rápida** (approx): Dolly substitui zoom óptico. Pausa de 2 s e avanço de 0,2 s na duração de 124 frames; tempos escalam com o clipe. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-01b_crash-zoom-in-hold-then-snap.txt)
- **C-02 Whip pan** (unsupported): Exige pan independente da órbita e troca de alvo. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-02_whip-pan.txt)
- **C-03 Super dolly in** (path): Aproximação física de 1 para 0,2 do raio; amplitude proposta, não medida do render. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-03_super-dolly-in.txt)
- **C-04 Órbita completa 360°** (path): Volta completa em azimute positivo no HUD. O sentido enviado respeita orbit_direction. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-04_360-orbit.txt)
- **C-05 Subida para vista aérea** (approx): Arco ascendente até 75°, afastando. Não inclui rastreamento da corrida nem posição inicial nos pés. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-05_crane-drone-rise.txt)
- **C-06 Afastamento aéreo** (path): Elevação e afastamento combinados, até 55° e raio 4. Valores propostos dentro dos limites atuais. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-06_aerial-pullback.txt)
- **C-07 Oscilação orbital suave** (approx): Oscilação determinística reduzida; não reproduz tracking de corrida nem handheld completo. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-07_handheld.txt)
- **C-08 Afastar e voltar (dolly)** (approx): Dolly substitui zoom óptico; pausa e retorno rápidos em tempos normalizados. Não preserva a duração original de 192 frames. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-08_yoyo-zoom.txt)
- **C-09 Dutch angle** (unsupported): Exige roll; o compilador atual mantém roll zero. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-09_dutch-angle.txt)
- **C-10 Aproximação extrema** (approx): Aproxima até o raio mínimo 0,1. Não identifica o olho nem garante macro/enquadramento da íris. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-10_eyes-in.txt)
- **D-01 Snorricam** (unsupported): Exige câmera presa ao corpo e alvo animado. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/D-01_snorricam.txt)
- **D-05 Snorricam corredor** (unsupported): Exige câmera presa ao corpo e alvo animado. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/D-05_snorricam-corridor.txt)
- **D-03 Rack focus** (unsupported): É troca de foco, não uma trajetória. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/D-03_rack-focus.txt)
- **D-04 Tela dividida** (unsupported): Exige composição com várias câmeras. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/D-04_multi-panel-split-screen.txt)
- **K-06n Dolly zoom · K-06n** (unsupported): Exige variar distância e FOV juntos; o compilador atual mantém focal fixa. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/K-06n_dolly-zoom-k06.txt)
- **X-01 Dolly zoom · X-01** (unsupported): Exige variar distância e FOV juntos; o compilador atual mantém focal fixa. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/X-01_dolly-zoom-composed.txt)
- **X-01b Dolly zoom · X-01b** (unsupported): Exige variar distância e FOV juntos; o compilador atual mantém focal fixa. [Fonte](https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/X-01b_dolly-zoom-composed-locked.txt)