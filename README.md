# agent-esits2026set30

**Professional 9:16 vertical ad video editing skill for AI agents** — analyzes, reframes, captions, narrates and quality-checks ad videos for Instagram Reels, Stories and Meta Ads (software / SaaS / digital products).

*Skill profissional de edição de anúncios verticais 9:16 (Reels, Stories, Meta Ads) para agentes de IA.*

---

## O que faz

Editor profissional e estrategista de anúncios verticais 9:16 para softwares, SaaS e produtos digitais. Fluxo completo em 10 etapas:

1. **Diagnóstico** — análise técnica (ffprobe), classificação do material para 9:16, cortes de cena, folhas de contato, análise de áudio
2. **Análise de áudio** — música/voz/ruído/silêncio, volume, ritmo (BPM só quando há pulso claro)
3. **Estratégia editorial** — gancho → demonstração → CTA (3 estruturas), regra do gancho nos 1–3 s, prioridade editorial clara
4. **Enquadramento 9:16 adaptativo** — crop, punch-in, zoom lento, blur background, decidido quadro a quadro (nunca fórmula fixa)
5. **Texto e legendas** — uma ideia por tela, zonas seguras da plataforma, legendas PNG com pílula arredondada e cor por palavra
6. **Identidade visual e logo** — logo discreta no corpo, destaque no final, reconstrução de logo de baixa resolução
7. **CTA e frame final** — logo → frase/benefício → CTA, com ou sem preço (só com autorização)
8. **Áudio e narração** — mixagem ≈ −14 LUFS / true peak ≤ −1 dBTP, roteiro com entonação
9. **Renderização** — H.264, CRF 18–20, 1080×1920, 30 fps, AAC 48 kHz, `+faststart`
10. **Controle de qualidade** — especificações, erros de decodificação, loudness, quadros pretos, trechos parados + folha de contato

### Regra central

**Nunca inventa** funcionalidades, métricas, preços, depoimentos ou resultados. Só entram fatos informados pelo usuário ou comprovados pelo material. Se faltar material para um anúncio honesto, a skill diz o que falta em vez de inventar.

## Entregáveis

1. MP4 final 1080×1920
2. SRT/VTT sincronizado
3. Áudio da narração (se gerado)
4. Roteiro da narração
5. PNG da logo reconstruída (se necessário)
6. Dois ganchos para teste A/B (resultado vs dor)
7. Relatório técnico resumido com limitações honestas

## Requisitos

- ffmpeg + ffprobe
- Python 3 + Pillow + NumPy (SciPy opcional — só acelera a reconstrução de logo)
- Windows: caminhos e comandos já ajustados (`python`, `Get-Command`, fontes locais)

## Instalação

Copie a pasta para o diretório de skills do seu agente (ex.: `~/.agents/skills/`, `~/.claude/skills/` ou via gerenciador de skills). A skill é ativada automaticamente quando o usuário pedir para **editar, reeditar, melhorar, cortar, legendar, narrar ou analisar** um vídeo de anúncio, reels, story, criativo de Meta Ads ou vídeo vertical.

```bash
# Linux/macOS
mkdir -p ~/.agents/skills && cp -r agent-esits2026set30 ~/.agents/skills/
# Windows (PowerShell)
Copy-Item -Path .\agent-esits2026set30 -Destination "$env:USERPROFILE\.agents\skills\" -Recurse
```

## Estrutura

```
agent-esits2026set30/
├── SKILL.md                        # fluxo completo + regras editoriais
├── references/
│   ├── receitas-ffmpeg.md          # comandos ffmpeg testados (enquadramento, montagem, áudio, render)
│   ├── roteiro-e-narracao.md       # linha do tempo, legendas, narração, ganchos A/B, SRT
│   └── logo-reconstrucao.md        # método de reconstrução de logo de baixa resolução
└── scripts/
    ├── analisar_video.py           # diagnóstico completo (ffprobe, cortes de cena, folhas de contato, áudio)
    ├── legenda_png.py              # gera PNGs de legenda (pílula arredondada, cor por palavra)
    └── qc_final.py                 # QC final (especificações, loudness ebur128, quadros pretos, folha)
```

## Licença

[MIT](LICENSE) — use, modifique e distribua livremente, com atribuição.