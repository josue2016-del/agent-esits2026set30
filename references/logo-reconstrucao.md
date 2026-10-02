# Reconstrução de logo de baixa resolução

Use quando o usuário envia uma logo pequena, borrada ou com fundo (recorte de tela, foto) e pede para "melhorar". O método abaixo recria a imagem em alta resolução com fundo transparente, mantendo forma e cores originais. **Não é vetorização**: se existir SVG, AI ou PDF, peça e use o original.

Antes de começar, avise ao usuário em uma frase o que será feito. Nunca troque a fonte, as cores ou o desenho da logo; se não der para reconstruir fielmente, diga e peça o arquivo original.

## Passo a passo

1. **Ver a imagem ampliada** (4×, LANCZOS) e anotar: o que é a logo, o que é fundo e o que é contaminação (pedaços de outra imagem, sombras, cabelo, triângulos).
2. **Amostrar cores** no fundo (perto do símbolo, perto do texto, nos cantos) e na logo (cada cor do símbolo, texto branco, texto colorido, bordas). Isso decide qual canal separa cada parte do fundo. Exemplo: fundo azul-marinho `(0,13,44)` a azul forte `(0,72,141)`; símbolo com canal máximo > 120; texto branco e ciano com canal verde > 95.
3. **Máscara por região.** Divida a logo em regiões (símbolo, nome, subtítulo) com retângulos e, se preciso, uma reta (para cortar um triângulo no canto). Em cada região, alfa = `smoothstep` do canal escolhido entre um limite baixo e um alto. Zere tudo fora das regiões.
4. **Limpar as bordas.** Os pixels de borda misturam a cor da logo com o fundo antigo. Pegue como "núcleo" os pixels com alfa > 0,92 e substitua a cor dos demais pela do núcleo mais próximo (`scipy.ndimage.distance_transform_edt` com `return_indices=True`). Sem SciPy, dilate o núcleo em passos com um filtro de máximo.
5. **Ampliar.** Cor: BICUBIC (fator 10–12×). Alfa: BICUBIC, `GaussianBlur` de ~0,8× o fator, `smoothstep` em torno de 0,5 (largura ±0,10) e um blur final de ~1,6 px. Isso dá bordas nítidas e sem serrilhado.
6. **Recortar** o conteúdo com margem de ~40 px e salvar PNG RGBA.
7. **Conferir** o PNG sobre fundo escuro, cinza médio e claro. Procure halos, bordas onduladas, partes faltando (um pedaço semitransparente, como a perna clara de um "x", pode ter sido cortado) e sobras do fundo antigo. Se algo falhar, ajuste limites e refaça.

## Código de referência

Os limites (`lo`/`hi`), regiões e canais abaixo são de uma logo específica (símbolo colorido + nome branco + subtítulo ciano sobre azul-marinho). **Reamostre e reajuste para cada logo nova.**

```python
from PIL import Image, ImageFilter
import numpy as np
from scipy import ndimage as ndi

src = Image.open("logo_baixa.png").convert("RGB")
a = np.array(src).astype(float); H, W = a.shape[:2]
g = a[..., 1]; mx = a.max(axis=2)
yy, xx = np.mgrid[0:H, 0:W]

def ss(x, lo, hi):
    t = np.clip((x - lo) / (hi - lo), 0, 1); return t * t * (3 - 2 * t)

# regiões em coordenadas do arquivo original (ajustar!)
aM = ss(mx, 120, 175) * ((xx < 69.5) & (yy >= 8) & (yy <= 72) & ((xx/27.0 + yy/20.0) > 1.02))  # símbolo (corta triângulo do canto)
aT = ss(g, 95, 160)  * ((xx >= 69.5) & (yy < 51.3))                                              # nome
aS = ss(g, 60, 120)  * ((xx >= 69.5) & (yy >= 51.3) & (yy <= 70) & (xx < 190))                   # subtítulo
al = np.clip(aM + aT + aS, 0, 1)

core = al > 0.92
idx = ndi.distance_transform_edt(~core, return_distances=False, return_indices=True)
col = np.where(core[..., None], a, a[idx[0], idx[1]])

S = 12
colI = Image.fromarray(col.clip(0, 255).astype(np.uint8)).resize((W*S, H*S), Image.BICUBIC)
alI = Image.fromarray((al*255).astype(np.uint8)).resize((W*S, H*S), Image.BICUBIC)
alA = np.array(alI.filter(ImageFilter.GaussianBlur(S*0.8))).astype(float)/255
alA = ss(alA, 0.40, 0.60)
alA = np.array(Image.fromarray((alA*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6))).astype(float)/255

out = Image.fromarray(np.dstack([np.array(colI), (alA*255).astype(np.uint8)]).astype(np.uint8), "RGBA")
bb = out.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
pad = 40
out = out.crop((max(bb[0]-pad,0), max(bb[1]-pad,0), min(bb[2]+pad,out.width), min(bb[3]+pad,out.height)))
out.save("logo_hd.png")
```

## Como usar a logo no vídeo

- **Etiqueta no corpo:** altura ~60 px dentro de uma pílula escura (`fill 13,13,18`, alfa ~205), canto superior esquerdo, fora da faixa coberta pela interface.
- **Frame final:** largura ~800–860 px, centralizada, com um brilho suave atrás. Combine com a cor de acento do resto do vídeo.
- Nunca estique: mantenha a proporção da imagem.

## O que dizer ao usuário

Informe: (1) que a imagem foi recriada em alta resolução a partir do arquivo enviado, (2) que não é vetorial, (3) qual foi o tamanho final, (4) que o arquivo original em SVG/AI/PDF dá resultado ainda melhor, e (5) onde ela foi aplicada. Entregue o PNG transparente.
