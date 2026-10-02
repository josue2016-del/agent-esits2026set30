# Roteiro, legendas, narração e ganchos A/B

Sumário: 1 Linha do tempo · 2 Roteiro de legendas · 3 Roteiro de narração · 4 Entonação · 5 Com TTS · 6 Sem TTS · 7 Ganchos A/B · 8 Formato do SRT.

Tudo aqui só usa fatos informados pelo usuário. Se um benefício, número ou promessa não foi dado, não entra no roteiro (nem na legenda, nem na fala).

## 1. Linha do tempo

Escolha a estrutura (A padrão, B prova direta, C demonstração) e distribua o tempo conforme o material. Exemplo de 30 s:

| Janela | Função | Observação |
|---|---|---|
| 0–3 s | Gancho | Produto ou resultado na tela, promessa em uma frase |
| 3–7 s | Dor | Só se existir cena que mostre a dor; senão, comprima |
| 7–20 s | Demonstração | Cada funcionalidade que o usuário informou, uma por tela |
| 20–24 s | Resultado | A ação concluída (ex.: arquivo gerado) |
| 24–30 s | Fechamento e CTA | Logo, frase final, botão |

Janelas de 1,5–3,5 s por ideia; nada de plano parado acima de ~5 s sem função. Se usar a batida, arredonde as janelas para múltiplos dela (ver `receitas-ffmpeg.md`, seção 4).

## 2. Roteiro de legendas

- Uma ideia por tela, até ~7 palavras, em duas linhas curtas quando precisar.
- Palavra-chave em cor de acento (ex.: "1 CLIQUE").
- Não repita a mesma mensagem com palavras diferentes (ex.: "menos trabalho manual" e "menos retrabalho").
- A legenda acompanha a fala: mesmo texto ou um resumo claro dele.

## 3. Roteiro de narração

Escreva no mesmo tempo das legendas, com cerca de 2,5–3,2 palavras por segundo para ritmo energético (abaixo disso fica lento; acima fica apressado e ilegível). Modelo de tabela:

| Tempo | Fala | Entonação |
|---|---|---|
| 0–3,2 s | "..." | explosiva, ênfase em "..." |

Também entregue o bloco de texto corrido pronto para colar num gerador de voz, uma linha por cena.

Regras de conteúdo:
- Só fatos comprovados. Sem superlativos ("o mais rápido", "o melhor") nem números de tempo que o usuário não informou.
- Sem preço se o usuário não autorizou mostrar.
- Sem urgência, escassez ou promoção inventadas.
- Se o produto é um lançamento (o usuário disse), a fala pode usar "Chegou" ou "Novo", sem prometer mais do que o produto faz.

## 4. Entonação

Marcação que funciona bem em geradores de voz e em gravação manual:
- **MAIÚSCULAS** para ênfase (a palavra que carrega o benefício).
- **"..."** para uma pausa curta (~0,3 s), antes da palavra que quer destacar.
- **"?"** sobe a voz; **"!"** dá energia no fim.
- Frases curtas; uma respiração por cena.

Direção geral para lançamento: sorriso na voz, energia alta, ritmo um pouco acima do normal (1,05–1,10× no TTS), ênfase clara no gancho e no CTA, queda seca na palavra do resultado ("...gerou!"). Não acelere a fala para encaixar mais texto: corte texto.

## 5. Com TTS disponível

1. Confirme quais serviços existem e estão autorizados nesta conversa (ElevenLabs, OpenAI Audio etc.). Não prometa antes de verificar.
2. Gere uma faixa por cena (mais fácil de encaixar no tempo do que uma faixa única).
3. Ajuste a duração de cada faixa à janela; se passar, corte texto ou escolha outra voz/ritmo em vez de acelerar demais.
4. Mixe: voz ~8 dB acima da música, música com ducking, loudness ~−14 LUFS e true peak ≤ −1 dBTP medidos no arquivo final.
5. Entregue também o arquivo de áudio da narração.

Parâmetros úteis de gerador de voz, quando existirem: estabilidade baixa e estilo alto dão mais expressão; velocidade 1,05–1,10×. Se o serviço não tiver esses controles, use pontuação e MAIÚSCULAS.

## 6. Sem TTS

Entregue: roteiro com tempos, entonação, bloco corrido para colar, SRT e uma frase clara: "A narração precisa ser gravada ou gerada separadamente; o vídeo funciona sem som com as legendas na tela." Se o vídeo tem música, ela continua tocando; diga que, ao gravar a voz, a música deve ficar ~8 dB abaixo.

## 7. Ganchos A/B

Mude principalmente o início (0–3 s); mantenha o resto comparável.

- **A — Resultado:** mostra logo o resultado ou a transformação. Ex.: "[Produto] entrega [resultado comprovado] em [ação informada]."
- **B — Dor:** apresenta o problema do público. Ex.: "Ainda [faz a tarefa difícil do jeito antigo]?"

Um terceiro gancho (pergunta ou curiosidade) pode entrar como extra. Use só benefícios informados pelo usuário.

## 8. Formato do SRT

```
1
00:00:00,000 --> 00:00:03,200
Primeira linha
segunda linha

2
00:00:03,200 --> 00:00:05,000
...
```

Numeração sequencial, tempo `HH:MM:SS,mmm`, no máximo duas linhas por bloco, UTF-8. Os tempos do SRT precisam ser exatamente os das legendas no vídeo; se você mudar o vídeo, atualize o SRT.
