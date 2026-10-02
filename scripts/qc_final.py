#!/usr/bin/env python3
"""Controle de qualidade de um MP4 vertical antes da entrega.

Uso:
    python3 qc_final.py video.mp4 [--largura 1080] [--altura 1920] [--fps 30] [--saida qc/]

Verifica: especificações, erros de decodificação, áudio (codec, sample rate), loudness
(integrado, LRA, true peak), quadros pretos e trechos parados; gera uma folha de contato
(qc_folha.png) com 12 quadros e um qc.json. Sai com código 1 se houver FALHA.

Os resultados automáticos NÃO substituem olhar a folha de contato: confira textos, logo,
zonas seguras, cortes e sobras de texto antigo.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction

from PIL import Image, ImageDraw


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--largura", type=int, default=1080)
    ap.add_argument("--altura", type=int, default=1920)
    ap.add_argument("--fps", type=float, default=30)
    ap.add_argument("--lufs", type=float, default=-14.0, help="alvo de loudness integrado")
    ap.add_argument("--saida", default="qc")
    a = ap.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        sys.exit("ffmpeg/ffprobe não encontrados.")
    os.makedirs(a.saida, exist_ok=True)
    itens = []  # (status, texto)

    def add(status, texto):
        itens.append((status, texto))

    pr = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", a.video])
    if pr.returncode != 0:
        sys.exit("Arquivo ilegível: " + pr.stderr.strip())
    info = json.loads(pr.stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    au = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"].get("duration", 0) or 0)
    if not v:
        sys.exit("Sem stream de vídeo.")

    # especificações
    w, h = v["width"], v["height"]
    add("OK" if (w, h) == (a.largura, a.altura) else "FALHA", f"Resolução {w}x{h} (esperado {a.largura}x{a.altura})")
    fps = float(Fraction(v.get("avg_frame_rate") or "0"))
    add("OK" if abs(fps - a.fps) < 0.05 else "AVISO", f"FPS {fps:.2f} (esperado {a.fps:g})")
    add("OK" if v.get("codec_name") == "h264" else "AVISO", f"Codec de vídeo {v.get('codec_name')} (recomendado h264)")
    add("OK" if v.get("pix_fmt") == "yuv420p" else "AVISO", f"Formato de pixel {v.get('pix_fmt')} (recomendado yuv420p)")
    add("OK", f"Duração {dur:.2f} s; tamanho {int(info['format'].get('size', 0))/1e6:.1f} MB")
    # faststart: o átomo moov deve vir antes do mdat
    with open(a.video, "rb") as f:
        cabeca = f.read(65536)
    if b"moov" in cabeca:
        add("OK", "faststart presente (moov no início)")
    else:
        add("AVISO", "moov não está no início: use -movflags +faststart")

    # decodificação
    dec = run(["ffmpeg", "-v", "error", "-i", a.video, "-f", "null", "-"])
    erros = [l for l in dec.stderr.strip().splitlines() if l.strip()]
    add("OK" if not erros else "FALHA", "Decodificação sem erros" if not erros else f"{len(erros)} erro(s) de decodificação: {erros[0][:120]}")

    # áudio e loudness
    loud = None
    if au:
        sr = int(au.get("sample_rate", 0) or 0)
        add("OK" if au.get("codec_name") == "aac" else "AVISO", f"Áudio {au.get('codec_name')} {sr} Hz, {au.get('channels')} canais")
        if sr != 48000:
            add("AVISO", f"Sample rate {sr} (recomendado 48000)")
        r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", a.video, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"])
        resumo = r.stderr[r.stderr.rfind("Summary:"):] if "Summary:" in r.stderr else ""
        m_i = re.search(r"\bI:\s+(-?[\d.]+)\s+LUFS", resumo)
        m_lra = re.search(r"\bLRA:\s+([\d.]+)\s+LU", resumo)
        m_tp = re.search(r"Peak:\s+(-?[\d.]+)\s+dBFS", resumo)
        if m_i:
            loud = {"integrado_lufs": float(m_i.group(1)),
                    "lra_lu": float(m_lra.group(1)) if m_lra else None,
                    "true_peak_dbtp": float(m_tp.group(1)) if m_tp else None}
            d = abs(loud["integrado_lufs"] - a.lufs)
            add("OK" if d <= 1.5 else "AVISO", f"Loudness integrado {loud['integrado_lufs']} LUFS (alvo {a.lufs:g})")
            if loud["true_peak_dbtp"] is not None:
                add("OK" if loud["true_peak_dbtp"] <= -1.0 else "AVISO",
                    f"True peak {loud['true_peak_dbtp']} dBTP (limite recomendado −1,0)")
            else:
                add("AVISO", "True peak não pôde ser lido")
        else:
            add("AVISO", "Não consegui medir o loudness")
        vol = run(["ffmpeg", "-hide_banner", "-i", a.video, "-vn", "-af", "volumedetect", "-f", "null", "-"])
        mx = re.search(r"max_volume:\s+(-?[\d.]+)\s+dB", vol.stderr)
        if mx and float(mx.group(1)) > -0.1:
            add("AVISO", f"Pico de amostra em {mx.group(1)} dB: risco de clipping")
    else:
        add("AVISO", "Arquivo sem áudio")

    # quadros pretos e trechos parados
    bl = run(["ffmpeg", "-hide_banner", "-i", a.video, "-vf", "blackdetect=d=0.12:pix_th=0.05", "-an", "-f", "null", "-"])
    pretos = [(float(s), float(e)) for s, e in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bl.stderr)]
    if pretos:
        add("AVISO", "Quadros pretos em (s): " + ", ".join(f"{s:.2f}–{e:.2f}" for s, e in pretos))
    else:
        add("OK", "Sem quadros pretos de 0,12 s ou mais")
    fr = run(["ffmpeg", "-hide_banner", "-i", a.video, "-vf", "freezedetect=n=-60dB:d=2", "-an", "-f", "null", "-"])
    parados = [float(s) for s in re.findall(r"freeze_start:\s*([\d.]+)", fr.stderr)]
    if parados:
        add("AVISO", "Imagem parada por 2 s ou mais a partir de (s): " + ", ".join(f"{s:.1f}" for s in parados)
            + " (normal em frame final; confira os demais)")

    # folha de contato: 12 quadros igualmente espaçados
    tmp = tempfile.mkdtemp(prefix="qc_")
    try:
        n = 12
        tempos = [max(0.05, min(dur - 0.1, dur * (i + 0.5) / n)) for i in range(n)]
        ims = []
        for i, t in enumerate(tempos):
            p = os.path.join(tmp, f"q{i}.jpg")
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", a.video, "-frames:v", "1", "-vf", "scale=270:-1", p])
            if os.path.exists(p):
                ims.append((t, Image.open(p).convert("RGB")))
        if ims:
            cw, ch = ims[0][1].size
            cols = 6
            linhas = (len(ims) + cols - 1) // cols
            folha = Image.new("RGB", (cw * cols, ch * linhas))
            d = ImageDraw.Draw(folha)
            for i, (t, im) in enumerate(ims):
                x, y = (i % cols) * cw, (i // cols) * ch
                folha.paste(im, (x, y))
                d.rectangle((x, y, x + 50, y + 14), fill=(0, 0, 0))
                d.text((x + 3, y + 1), f"{t:.1f}s", fill=(255, 255, 0))
            folha.save(os.path.join(a.saida, "qc_folha.png"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # relatório
    simbolo = {"OK": "[OK]    ", "AVISO": "[AVISO] ", "FALHA": "[FALHA] "}
    for st, tx in itens:
        print(simbolo[st] + tx)
    print("Folha de contato: " + os.path.join(a.saida, "qc_folha.png") + "  (olhe a imagem: textos, logo, zonas seguras, cortes)")
    with open(os.path.join(a.saida, "qc.json"), "w", encoding="utf-8") as f:
        json.dump({"itens": itens, "loudness": loud, "duracao_s": dur}, f, ensure_ascii=False, indent=2)
    sys.exit(1 if any(st == "FALHA" for st, _ in itens) else 0)


if __name__ == "__main__":
    main()
