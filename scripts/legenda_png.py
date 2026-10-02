#!/usr/bin/env python3
"""Gera PNGs de legenda (pílula arredondada, várias cores por linha).

Uso:
    python3 legenda_png.py especificacao.json pasta_saida/

Formato do JSON:
{
  "acento": "#FFD21F",                 # cor de destaque (opcional, padrão amarelo)
  "fonte": "/caminho/Fonte-Bold.ttf",  # opcional; padrão Liberation Sans Bold ou DejaVu Sans Bold
  "legendas": [
    {"arquivo": "c00.png",
     "estilo": "escuro",               # "escuro" (fundo translúcido) ou "acento" (fundo na cor de acento)
     "linhas": [
        [{"t": "Miolo de agenda pronto", "c": "branco", "s": 66}],
        [{"t": "em ", "c": "branco", "s": 96}, {"t": "1 CLIQUE.", "c": "acento", "s": 118}]
     ]}
  ]
}
Cores: "branco", "acento", "escuro" ou hex (#RRGGBB). Tamanhos em px para vídeo 1080x1920.
Imprime o tamanho de cada PNG (use para posicionar no overlay).
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONTES = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\seguisb.ttf",
]


def achar_fonte(pedida):
    for caminho in ([pedida] if pedida else []) + FONTES:
        if caminho and os.path.exists(caminho):
            return caminho
    sys.exit("Nenhuma fonte Bold encontrada; informe \"fonte\" no JSON.")


def cor(valor, acento):
    tabela = {"branco": (255, 255, 255), "acento": acento, "escuro": (13, 13, 18)}
    if valor in tabela:
        return tabela[valor]
    v = valor.lstrip("#")
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def desenhar(caminho_saida, linhas, estilo, acento, fonte, pad_x=44, pad_y=28, gap=10, raio=44):
    medidor = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    F = lambda s: ImageFont.truetype(fonte, int(s))
    linhas_m = []
    for segs in linhas:
        w = sum(medidor.textlength(sg["t"], font=F(sg["s"])) for sg in segs)
        h = max(F(sg["s"]).getbbox("Ag")[3] for sg in segs)
        linhas_m.append((segs, w, h))
    W = int(max(l[1] for l in linhas_m) + 2 * pad_x)
    H = int(sum(l[2] for l in linhas_m) + gap * (len(linhas_m) - 1) + 2 * pad_y)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fundo = (13, 13, 18, 205) if estilo == "escuro" else tuple(acento) + (255,)
    d.rounded_rectangle((0, 0, W - 1, H - 1), radius=raio, fill=fundo)
    y = pad_y
    for segs, w, h in linhas_m:
        x = (W - w) / 2
        for sg in segs:
            d.text((x, y), sg["t"], font=F(sg["s"]), fill=cor(sg.get("c", "branco"), acento))
            x += medidor.textlength(sg["t"], font=F(sg["s"]))
        y += h + gap
    img.save(caminho_saida)
    return W, H


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    saida = sys.argv[2]
    os.makedirs(saida, exist_ok=True)
    acento = cor(spec.get("acento", "#FFD21F"), (255, 210, 31))
    fonte = achar_fonte(spec.get("fonte"))
    for leg in spec["legendas"]:
        destino = os.path.join(saida, leg["arquivo"])
        w, h = desenhar(destino, leg["linhas"], leg.get("estilo", "escuro"), acento, fonte)
        print(f"{destino}  {w}x{h}")


if __name__ == "__main__":
    main()
