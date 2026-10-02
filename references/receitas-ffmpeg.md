# Receitas ffmpeg para anúncios 9:16

Todas foram usadas ou testadas no ambiente do Claude (ffmpeg + Python com Pillow e NumPy). Troque os valores entre `{}`. Sumário: 1 Diagnóstico · 2 Enquadramento · 3 Zoom lento · 4 Montagem · 5 Legendas e logo · 6 Frame final · 7 Áudio · 8 Renderização · 9 Verificação.

## 1. Diagnóstico

```bash
# metadados
ffprobe -v error -show_format -show_streams -print_format json video.mp4

# cortes de cena (limiar 0.25; confirme visualmente)
ffmpeg -i video.mp4 -an -vf "select='gt(scene,0.25)',showinfo" -f null - 2>&1 | grep -o "pts_time:[0-9.]*"

# folha de contato: 1 quadro a cada 2,5 s, 6 colunas x 4 linhas
ffmpeg -i video.mp4 -vf "fps=1/2.5,scale=360:-1,tile=6x4" -frames:v 1 folha.jpg
# (com mais de 24 quadros, gere folhas em partes: -ss e -t, ou use scripts/analisar_video.py)

# volume médio e pico
ffmpeg -i video.mp4 -af volumedetect -vn -f null - 2>&1 | grep -E "mean_volume|max_volume"
```

No tile, o quadro de índice `i` está no tempo `i × intervalo`. Erro comum: contar o tempo pela linha da folha em vez do índice.

## 2. Enquadramento 9:16

**Crop ancorado no topo com zoom base `z`** (remove a faixa inferior, útil quando ali só há textos antigos):

```
cw = floor(1080 / z), ch = floor(1920 / z)      # arredonde para par
crop=cw:ch:x:0,scale=1080:1920:flags=lanczos     # x = (1080 - cw)/2 para centralizar
```

Com `z = 1.23`: `cw=878`, `ch=1561`, corta ~19% de baixo. Conferir sempre, cena por cena, que nada importante estava na parte cortada.

**Punch-in num ponto de interesse** (`z` 1.4–1.7): escolha `x`,`y` do canto do recorte olhando o quadro:

```
crop={1080/z}:{1920/z}:{x}:{y},scale=1080:1920:flags=lanczos
```

**Vídeo horizontal 16:9 com blur background** (fundo ampliado e escurecido, vídeo principal no centro):

```bash
ffmpeg -i in.mp4 -filter_complex \
"[0:v]split[a][b];\
[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5,eq=brightness=-0.18[bg];\
[b]scale=1080:-2[fg];\
[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1" -an out.mp4
```

Quando a ação da interface está concentrada numa região, prefira crop sobre a região (mais legível) em vez do vídeo pequeno no meio.

## 3. Zoom lento dentro do clipe (Ken Burns)

Depois do crop e do `scale=1080:1920`, amplie devagar até `kb` (ex.: 0,05 = 5%) e recorte o centro:

```
scale=w='trunc(1080*(1+{kb}*t/{D})/2)*2':h='trunc(1920*(1+{kb}*t/{D})/2)*2':eval=frame,
crop=1080:1920:'(iw-1080)/2':0
```

`D` é a duração do clipe. Faça `setpts=PTS-STARTPTS` antes, para `t` valer do início do clipe.

## 4. Montagem por clipes

Um `-ss`/`-t`/`-i` por clipe (mesmo arquivo de origem), um filtro por clipe, depois `concat`:

```bash
ffmpeg -ss {ss1} -t {d1} -i v.mp4 -ss {ss2} -t {d2} -i v.mp4 ... -filter_complex \
"[0:v]setpts=PTS-STARTPTS,{crop_e_zoom},setsar=1,fps=30,format=yuv420p[k0];\
 [1:v]...[k1];\
 [k0][k1]concat=n=2:v=1:a=0[body]"
```

**Ritmo na batida (opcional, só com pulso claro):** `scripts/analisar_video.py` diz se o pulso é claro; com pulso fraco ou ambíguo, não use este método. Se for claro, use durações múltiplas de `60/BPM` (ex.: 94 BPM → 0,64 s por batida; 4 batidas = 2,56 s; 5 = 3,2 s). O total precisa ser um número inteiro de batidas, e o início do áudio deve cair numa batida (fase medida). Confirme com `--checar-cortes` antes de afirmar que os cortes estão na batida. Cortes fora da batida são aceitáveis se a narrativa pedir.

## 5. Legendas e logo em PNG

Gere PNGs com `scripts/legenda_png.py`. Para cada legenda, entre no vídeo com fade, deslize e janela de tempo:

```
# entrada: -loop 1 -framerate 30 -t {E-S} -i cap.png
[K:v]format=rgba,fade=t=in:st=0:d=0.14:alpha=1,fade=t=out:st={E-S-0.12}:d=0.12:alpha=1,setpts=PTS+{S}/TB[cp]
[base][cp]overlay=x='(W-w)/2':y='{CY}-h/2+40*max(0,1-(t-{S})/0.2)':enable='between(t,{S},{E})':format=auto[out]
```

`CY` é o centro vertical da legenda (escolha olhando a composição; zona segura). Um PNG de degradê no rodapé (alpha 0→~190) melhora a leitura sobre imagens claras. Uma etiqueta com a logo pequena entra no canto superior esquerdo durante o corpo do vídeo (`overlay=54:300`, ajuste conforme a interface).

## 6. Frame final em dois estágios

Desenhe dois PNGs 1080×1920 com Pillow (fundo da marca, brilho suave, logo, frase; o segundo estágio acrescenta o botão de CTA). Una com `xfade`:

```
-loop 1 -framerate 30 -t 3.2  -i end1.png
-loop 1 -framerate 30 -t 3.45 -i end2.png
[e1][e2]xfade=transition=fade:duration=0.25:offset=2.95[endc]
[body][endc]concat=n=2:v=1:a=0[vout]
```

`offset = duração do estágio 1 − duração da transição`. O `end2` precisa ser 0,25 s mais longo que o tempo que deve ficar na tela.

## 7. Áudio

```bash
# reaproveitar a música original a partir do ponto certo (evite introdução silenciosa)
-ss {inicio_audio} -t {total} -i musica.mp4
# fade de entrada e saída, clique sintetizado, mixagem e loudness
[a]volume=0.9,afade=t=in:st=0:d=0.25,afade=t=out:st={total-1.8}:d=1.8[mus]
# clique (0,3 s) gerado por: -f lavfi -t 0.3 -i "aevalsrc='0.9*sin(2*PI*1500*t)*exp(-t*55)+0.5*sin(2*PI*220*t)*exp(-t*30)':s=48000"
[clk]adelay={ms}|{ms},volume=0.8[clk2]
[mus][clk2]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[aout]
```

Com narração: some `[voz]` no `amix` e reduza a música (~ −8 dB abaixo da voz) com `sidechaincompress` ou volume fixo. Meça o resultado (seção 9), o `loudnorm` de passada única pode errar por alguns décimos de LU.

## 8. Renderização final

```bash
-map "[vout]" -map "[aout]" -t {total} \
-c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -r 30 -movflags +faststart \
-c:a aac -b:a 192k -ar 48000 saida.mp4
```

Se `-t` for maior que o conteúdo, o ffmpeg completa com quadros repetidos; confira a duração real depois.

## 9. Verificação do arquivo final

Use `scripts/qc_final.py`. Comandos avulsos:

```bash
# loudness integrado, LRA e true peak
ffmpeg -i saida.mp4 -af ebur128=peak=true -f null - 2>&1 | tail -25
# quadros pretos (>= 0,12 s)
ffmpeg -i saida.mp4 -vf blackdetect=d=0.12:pix_th=0.05 -an -f null - 2>&1 | grep black_
# erros de decodificação
ffmpeg -v error -i saida.mp4 -f null - 2>&1
```

## Armadilhas conhecidas

- `-loop 1` em PNG sem `-t` gera vídeo infinito: sempre limite a duração.
- `overlay` com `enable` só liga/desliga; o fade precisa estar no próprio PNG (`fade=...:alpha=1`).
- Textos com acento: use fonte que os tenha (Liberation Sans Bold e DejaVu Sans Bold têm).
- `format=yuv420p` antes de `concat`/`xfade`, senão os formatos de pixel divergem e dá erro.
- `scale=...:eval=frame` com `t` só funciona depois de `setpts=PTS-STARTPTS`.
