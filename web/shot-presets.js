// Hand-authored path interpretations; source prompts are not redistributed.
export const SHOT_PRESETS = [
  {
    "id": "C-01",
    "pt": "Aproximação rápida (dolly)",
    "en": "Fast push-in (dolly)",
    "status": "approx",
    "notePt": "Adaptação física do crash zoom; não altera a lente.",
    "noteEn": "Physical adaptation of crash zoom; no lens zoom.",
    "path": [
      {
        "time": 0,
        "azimuth": 0,
        "elevation": 0,
        "distance": 1
      },
      {
        "time": 0.22,
        "azimuth": 0,
        "elevation": 0,
        "distance": 0.25
      },
      {
        "time": 1,
        "azimuth": 0,
        "elevation": 0,
        "distance": 0.25
      }
    ],
    "interpolation": "linear",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-01_crash-zoom-in.txt",
    "sourceSha": "95e76026c3883195d6f67e7f69d80d13d1a0a023"
  },
  {
    "id": "C-01b",
    "pt": "Pausa + aproximação rápida",
    "en": "Hold + fast push-in",
    "status": "approx",
    "notePt": "Dolly substitui zoom óptico. Pausa de 2 s e avanço de 0,2 s na duração de 124 frames; tempos escalam com o clipe.",
    "noteEn": "Dolly replaces optical zoom. 2 s hold and 0.2 s move at 124 frames; timings scale with the clip.",
    "path": [
      {
        "time": 0,
        "azimuth": 0,
        "elevation": 0,
        "distance": 1
      },
      {
        "time": 0.3902439024390244,
        "azimuth": 0,
        "elevation": 0,
        "distance": 1
      },
      {
        "time": 0.4292682926829269,
        "azimuth": 0,
        "elevation": 0,
        "distance": 0.25
      },
      {
        "time": 1,
        "azimuth": 0,
        "elevation": 0,
        "distance": 0.25
      }
    ],
    "interpolation": "linear",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-01b_crash-zoom-in-hold-then-snap.txt",
    "sourceSha": "751fdae1854511c8e6eb1b2d6dbf1c5349e5dca0"
  },
  {
    "id": "C-02",
    "pt": "Whip pan",
    "en": "Whip pan",
    "status": "unsupported",
    "notePt": "Exige pan independente da órbita e troca de alvo.",
    "noteEn": "Requires independent pan and a target change.",
    "path": null,
    "interpolation": "smooth",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-02_whip-pan.txt",
    "sourceSha": "827436c1abd2ffba642f8319abf7ddc464f3fce6"
  },
  {
    "id": "C-03",
    "pt": "Super dolly in",
    "en": "Super dolly in",
    "status": "path",
    "notePt": "Aproximação física de 1 para 0,2 do raio; amplitude proposta, não medida do render.",
    "noteEn": "Physical approach from 1 to 0.2 radius; proposed amplitude, not measured from the render.",
    "path": [
      {
        "time": 0,
        "azimuth": 0,
        "elevation": 0,
        "distance": 1
      },
      {
        "time": 1,
        "azimuth": 0,
        "elevation": 0,
        "distance": 0.2
      }
    ],
    "interpolation": "linear",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-03_super-dolly-in.txt",
    "sourceSha": "a3992edad5442da697a49db0d687ab5ec42bcf03"
  },
  {
    "id": "C-04",
    "pt": "Órbita completa 360°",
    "en": "Full 360° orbit",
    "status": "path",
    "notePt": "Volta completa em azimute positivo no HUD. O sentido enviado respeita orbit_direction.",
    "noteEn": "Full positive HUD orbit. Sent direction follows orbit_direction.",
    "path": [
      {
        "time": 0,
        "azimuth": 0,
        "elevation": 0,
        "distance": 1
      },
      {
        "time": 0.25,
        "azimuth": 90,
        "elevation": 0,
        "distance": 1
      },
      {
        "time": 0.5,
        "azimuth": 180,
        "elevation": 0,
        "distance": 1
      },
      {
        "time": 0.75,
        "azimuth": 270,
        "elevation": 0,
        "distance": 1
      },
      {
        "time": 1,
        "azimuth": 360,
        "elevation": 0,
        "distance": 1
      }
    ],
    "interpolation": "linear",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-04_360-orbit.txt",
    "sourceSha": "6b9e7f07bdfb0390c1cf52b582b52d1b954a6e5d"
  },
  {
    "id": "C-05",
    "pt": "Subida para vista aérea",
    "en": "Rise to overhead view",
    "status": "approx",
    "notePt": "Arco ascendente até 75°, afastando. Não inclui rastreamento da corrida nem posição inicial nos pés.",
    "noteEn": "Rising arc to 75° while pulling away. Does not encode running tracking or an initial feet-level position.",
    "path": [
      {
        "time": 0,
        "azimuth": 0,
        "elevation": 0,
        "distance": 1
      },
      {
        "time": 0.4,
        "azimuth": 0,
        "elevation": 25,
        "distance": 1.3
      },
      {
        "time": 1,
        "azimuth": 0,
        "elevation": 75,
        "distance": 2.5
      }
    ],
    "interpolation": "smooth",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-05_crane-drone-rise.txt",
    "sourceSha": "cb9593d9d683ce14ab6a8cba74fbc85a255bc932"
  },
  {
    "id": "C-06",
    "pt": "Afastamento aéreo",
    "en": "Aerial pullback",
    "status": "path",
    "notePt": "Elevação e afastamento combinados, até 55° e raio 4. Valores propostos dentro dos limites atuais.",
    "noteEn": "Combined rise and retreat to 55° and radius 4. Proposed values within current limits.",
    "path": [
      {
        "time": 0,
        "azimuth": 0,
        "elevation": 0,
        "distance": 1
      },
      {
        "time": 0.5,
        "azimuth": 0,
        "elevation": 25,
        "distance": 2
      },
      {
        "time": 1,
        "azimuth": 0,
        "elevation": 55,
        "distance": 4
      }
    ],
    "interpolation": "smooth",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-06_aerial-pullback.txt",
    "sourceSha": "8d79bcee9b6b7bfd8aa4bee6fd3d9029bbedd8f6"
  },
  {
    "id": "C-07",
    "pt": "Oscilação orbital suave",
    "en": "Gentle orbital shake",
    "status": "approx",
    "notePt": "Oscilação determinística reduzida; não reproduz tracking de corrida nem handheld completo.",
    "noteEn": "Small deterministic oscillation; does not reproduce running tracking or full handheld motion.",
    "path": [
      {
        "time": 0,
        "azimuth": 0,
        "elevation": 0,
        "distance": 1
      },
      {
        "time": 0.13,
        "azimuth": 2,
        "elevation": 1,
        "distance": 1.02
      },
      {
        "time": 0.26,
        "azimuth": -2,
        "elevation": -1,
        "distance": 0.98
      },
      {
        "time": 0.39,
        "azimuth": 3,
        "elevation": 1.5,
        "distance": 1.01
      },
      {
        "time": 0.52,
        "azimuth": -1,
        "elevation": -1.5,
        "distance": 0.99
      },
      {
        "time": 0.65,
        "azimuth": 2,
        "elevation": 1,
        "distance": 1.02
      },
      {
        "time": 0.78,
        "azimuth": -2,
        "elevation": -1,
        "distance": 0.98
      },
      {
        "time": 0.9,
        "azimuth": 1,
        "elevation": 0.5,
        "distance": 1.01
      },
      {
        "time": 1,
        "azimuth": 0,
        "elevation": 0,
        "distance": 1
      }
    ],
    "interpolation": "linear",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-07_handheld.txt",
    "sourceSha": "9121f09ad83a28b0bbcbd6fcab5dad5d26b0ae8e"
  },
  {
    "id": "C-08",
    "pt": "Afastar e voltar (dolly)",
    "en": "Pull out and return (dolly)",
    "status": "approx",
    "notePt": "Dolly substitui zoom óptico; pausa e retorno rápidos em tempos normalizados. Não preserva a duração original de 192 frames.",
    "noteEn": "Dolly replaces optical zoom; normalized hold and fast return. Does not preserve the source 192-frame duration.",
    "path": [
      {
        "time": 0,
        "azimuth": 0,
        "elevation": 0,
        "distance": 1
      },
      {
        "time": 0.25,
        "azimuth": 0,
        "elevation": 0,
        "distance": 1.3
      },
      {
        "time": 0.5,
        "azimuth": 0,
        "elevation": 0,
        "distance": 4
      },
      {
        "time": 0.63,
        "azimuth": 0,
        "elevation": 0,
        "distance": 4
      },
      {
        "time": 0.7,
        "azimuth": 0,
        "elevation": 0,
        "distance": 1
      },
      {
        "time": 1,
        "azimuth": 0,
        "elevation": 0,
        "distance": 1
      }
    ],
    "interpolation": "linear",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-08_yoyo-zoom.txt",
    "sourceSha": "950f4ba6b36811294cbca6a3891670d67a2bbf61"
  },
  {
    "id": "C-09",
    "pt": "Dutch angle",
    "en": "Dutch angle",
    "status": "unsupported",
    "notePt": "Exige roll; o compilador atual mantém roll zero.",
    "noteEn": "Requires roll; the current compiler fixes roll at zero.",
    "path": null,
    "interpolation": "smooth",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-09_dutch-angle.txt",
    "sourceSha": "baa58b96344f2c9af70b5df1951079ee70702012"
  },
  {
    "id": "C-10",
    "pt": "Aproximação extrema",
    "en": "Extreme push-in",
    "status": "approx",
    "notePt": "Aproxima até o raio mínimo 0,1. Não identifica o olho nem garante macro/enquadramento da íris.",
    "noteEn": "Approaches minimum radius 0.1. Does not identify an eye or guarantee iris framing.",
    "path": [
      {
        "time": 0,
        "azimuth": 0,
        "elevation": 0,
        "distance": 1
      },
      {
        "time": 0.65,
        "azimuth": 0,
        "elevation": 0,
        "distance": 0.4
      },
      {
        "time": 1,
        "azimuth": 0,
        "elevation": 0,
        "distance": 0.1
      }
    ],
    "interpolation": "smooth",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/C-10_eyes-in.txt",
    "sourceSha": "8704ee1f4447dd2cfb928ffd0a9d2508435c6325"
  },
  {
    "id": "D-01",
    "pt": "Snorricam",
    "en": "Snorricam",
    "status": "unsupported",
    "notePt": "Exige câmera presa ao corpo e alvo animado.",
    "noteEn": "Requires body-mounted camera and animated target.",
    "path": null,
    "interpolation": "smooth",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/D-01_snorricam.txt",
    "sourceSha": "182dece9b0133b8d64b98a0195d6b9d7825a51a8"
  },
  {
    "id": "D-05",
    "pt": "Snorricam corredor",
    "en": "Snorricam corridor",
    "status": "unsupported",
    "notePt": "Exige câmera presa ao corpo e alvo animado.",
    "noteEn": "Requires body-mounted camera and animated target.",
    "path": null,
    "interpolation": "smooth",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/D-05_snorricam-corridor.txt",
    "sourceSha": "4d7993f129e1252c27e848d52872b411e6e18e9a"
  },
  {
    "id": "D-03",
    "pt": "Rack focus",
    "en": "Rack focus",
    "status": "unsupported",
    "notePt": "É troca de foco, não uma trajetória.",
    "noteEn": "A focus change, not a camera path.",
    "path": null,
    "interpolation": "smooth",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/D-03_rack-focus.txt",
    "sourceSha": "b455252ca2f9af5936ce2f5822f16483ca8b087c"
  },
  {
    "id": "D-04",
    "pt": "Tela dividida",
    "en": "Split screen",
    "status": "unsupported",
    "notePt": "Exige composição com várias câmeras.",
    "noteEn": "Requires multi-camera compositing.",
    "path": null,
    "interpolation": "smooth",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/D-04_multi-panel-split-screen.txt",
    "sourceSha": "5d7231a13e5c27c467a88ea88b7993990a968bf0"
  },
  {
    "id": "K-06n",
    "pt": "Dolly zoom · K-06n",
    "en": "Dolly zoom · K-06n",
    "status": "unsupported",
    "notePt": "Exige variar distância e FOV juntos; o compilador atual mantém focal fixa.",
    "noteEn": "Requires synchronized distance and FOV; the current compiler fixes focal length.",
    "path": null,
    "interpolation": "smooth",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/K-06n_dolly-zoom-k06.txt",
    "sourceSha": "206dfddde84952adbd91affe06ebe1700463dc78"
  },
  {
    "id": "X-01",
    "pt": "Dolly zoom · X-01",
    "en": "Dolly zoom · X-01",
    "status": "unsupported",
    "notePt": "Exige variar distância e FOV juntos; o compilador atual mantém focal fixa.",
    "noteEn": "Requires synchronized distance and FOV; the current compiler fixes focal length.",
    "path": null,
    "interpolation": "smooth",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/X-01_dolly-zoom-composed.txt",
    "sourceSha": "e5b21489447f2b8fdbf6f5df098eea534d03fa2a"
  },
  {
    "id": "X-01b",
    "pt": "Dolly zoom · X-01b",
    "en": "Dolly zoom · X-01b",
    "status": "unsupported",
    "notePt": "Exige variar distância e FOV juntos; o compilador atual mantém focal fixa.",
    "noteEn": "Requires synchronized distance and FOV; the current compiler fixes focal length.",
    "path": null,
    "interpolation": "smooth",
    "source": "https://github.com/loopforge0/minimaxh3-shots-skills/blob/main/prompts/X-01b_dolly-zoom-composed-locked.txt",
    "sourceSha": "d61d632db2b14365bca8b2126984733bda681caf"
  }
];
export function presetPath(id){const entry=SHOT_PRESETS.find(p=>p.id===id);if(!entry?.path)throw Error("Preset has no supported path");return entry.path.map(p=>({...p}));}
