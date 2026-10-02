#!/usr/bin/env python3
"""Diagnóstico de um vídeo para edição 9:16.

Uso:
    python3 analisar_video.py video.mp4 --saida diagnostico/ [--limiar 0.25] [--intervalo 2.5]

Gera na pasta de saída:
    analise.json        resumo técnico, classificação 9:16, cortes de cena, áudio
    folha_01.png ...    folhas de contato com o tempo de cada quadro

Requer ffmpeg, ffprobe, Python, Pillow e NumPy.
A detecção de cena e de voz é apenas indicativa: confirme olhando as folhas de contato.
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

import numpy as np
from PIL import Image, ImageDraw


def run(cmd, binary=False):
    return subprocess.run(cmd, capture_output=True, text=not binary)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    if r.returncode != 0:
        sys.exit("ffprobe falhou: " + r.stderr.strip())
    return json.loads(r.stdout)


def fps_of(stream):
    try:
        return float(Fraction(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0"))
    except (ZeroDivisionError, ValueError):
        return 0.0


def classificar(w, h):
    """Classifica o material para 9:16."""
    if not w or not h:
        return "INADEQUADO", "sem dimensões de vídeo"
    if min(w, h) < 480:
        return "INADEQUADO", "resolução muito baixa (menos de 480 px no lado menor)"
    ar = w / h
    alvo = 9 / 16
    if abs(ar - alvo) / alvo < 0.03:
        nota = "já é 9:16"
        if w < 1080:
            nota += f"; largura {w}px abaixo de 1080 (upscale só no final, se necessário)"
        return "ADEQUADO", nota
    if ar > 1.2:
        return ("REENQUADRÁVEL COM BLUR BACKGROUND",
                "horizontal: use blur background ou crop na região de ação; decida olhando os quadros")
    if ar > alvo:
        return "REENQUADRÁVEL", "mais largo que 9:16 (ex.: 4:5, 1:1): crop lateral ou blur background"
    return "REENQUADRÁVEL COM CROP", "mais alto que 9:16: crop vertical"


def cortes_de_cena(path, limiar):
    r = run(["ffmpeg", "-hide_banner", "-i", path, "-an",
             "-vf", f"select='gt(scene,{limiar})',showinfo", "-f", "null", "-"])
    return [round(float(t), 2) for t in re.findall(r"pts_time:([0-9.]+)", r.stderr)]


def folhas_de_contato(path, duracao, intervalo, saida, cols=6, linhas=4):
    tmp = tempfile.mkdtemp(prefix="quadros_")
    try:
        r = run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps=1/{intervalo},scale=360:-1",
                 "-q:v", "3", os.path.join(tmp, "q_%04d.jpg")])
        if r.returncode != 0:
            return []
        arquivos = sorted(f for f in os.listdir(tmp) if f.endswith(".jpg"))
        if not arquivos:
            return []
        por_folha = cols * linhas
        folhas = []
        for n, ini in enumerate(range(0, len(arquivos), por_folha), start=1):
            grupo = arquivos[ini:ini + por_folha]
            ims = [Image.open(os.path.join(tmp, f)).convert("RGB") for f in grupo]
            w, h = ims[0].size
            nl = (len(ims) + cols - 1) // cols
            folha = Image.new("RGB", (w * cols, h * nl), (0, 0, 0))
            d = ImageDraw.Draw(folha)
            for i, im in enumerate(ims):
                x, y = (i % cols) * w, (i // cols) * h
                folha.paste(im, (x, y))
                t = (ini + i) * intervalo
                d.rectangle((x, y, x + 62, y + 16), fill=(0, 0, 0))
                d.text((x + 3, y + 2), f"{t:.1f}s", fill=(255, 255, 0))
            nome = os.path.join(saida, f"folha_{n:02d}.png")
            folha.save(nome)
            folhas.append(nome)
        return folhas
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def fluxo_espectral(y, sr, hop_s=0.01, n_fft=1024):
    """Força de início de sons (onset) a cada 10 ms, normalizada (z-score)."""
    hop = int(sr * hop_s)
    win = np.hanning(n_fft)
    quadros = [np.abs(np.fft.rfft(y[i:i + n_fft] * win)) for i in range(0, len(y) - n_fft, hop)]
    S = np.log1p(np.array(quadros) * 20)
    fl = np.maximum(np.diff(S, axis=0), 0).sum(axis=1)
    return (fl - fl.mean()) / (fl.std() + 1e-9)


def checar_cortes(path, tempos_audio, tol=0.06):
    """Mede se os tempos (na linha do tempo do áudio de `path`) caem em inícios de som mais que o acaso."""
    sr = 16000
    r = run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"], binary=True)
    x = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    fl = fluxo_espectral(x, sr)

    def perto(t):
        i = int(round(t / 0.01))
        lo, hi = max(i - int(tol / 0.01), 0), i + int(tol / 0.01) + 1
        return float(fl[lo:hi].max()) if lo < len(fl) else float("nan")
    vals = [perto(t) for t in tempos_audio]
    rng = np.random.default_rng(0)
    base = [perto(rng.uniform(0.5, len(fl) * 0.01 - 0.5)) for _ in range(2000)]
    return {"forca_media_nos_cortes": round(float(np.nanmean(vals)), 2),
            "forca_media_aleatoria": round(float(np.mean(base)), 2),
            "alinhado_alem_do_acaso": bool(np.nanmean(vals) > np.mean(base) + 0.3)}


def analisar_audio(path):
    sr = 16000
    r = run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"], binary=True)
    if r.returncode != 0 or len(r.stdout) < sr * 2:
        return None
    x = np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    seg = len(x) // sr
    rms_db = []
    for s in range(seg):
        bloco = x[s * sr:(s + 1) * sr]
        v = float(np.sqrt(np.mean(bloco ** 2)) + 1e-9)
        rms_db.append(round(20 * np.log10(v), 1))
    silencio = float(np.mean([v < -50 for v in rms_db])) if rms_db else 0.0
    pico = float(np.max(np.abs(x)))
    clip = float(np.mean(np.abs(x) >= 0.999))
    audivel = [i for i, v in enumerate(rms_db) if v > -40]
    primeiro_audivel = audivel[0] if audivel else None
    # primeiro segundo em que o nível chega perto do nível típico (mediana dos trechos audíveis)
    ponto_normal = None
    if audivel:
        mediana = float(np.median([rms_db[i] for i in audivel]))
        for i in audivel:
            if rms_db[i] >= mediana - 4:
                ponto_normal = i
                break

    # modulação de envelope na faixa de sílabas (3–6 Hz): indicador fraco de voz, NÃO conclusivo
    def mod_voz(seg_x):
        k = sr // 100
        env = np.convolve(np.abs(seg_x), np.ones(k) / k, "same")[::k]
        env = env - env.mean()
        F = np.abs(np.fft.rfft(env))
        fr = np.fft.rfftfreq(len(env), 0.01)
        sp = F[(fr >= 3) & (fr <= 6)].sum()
        outros = F[(fr >= 0.3) & (fr < 3)].sum() + F[(fr > 6) & (fr < 12)].sum()
        return float(sp / (outros + 1e-9))
    voz = round(mod_voz(x[int(sr * (primeiro_audivel or 0)):]), 3) if audivel and len(x) > sr * 4 else None

    # Ritmo: fluxo espectral + autocorrelação normalizada. Só é confiável se houver um pico dominante.
    ritmo = None
    ini = int((ponto_normal if ponto_normal is not None else 0) * sr)
    y = x[ini:]
    if len(y) > sr * 8:
        fluxo = fluxo_espectral(y, sr)
        f = fluxo - fluxo.mean()
        ac = np.correlate(f, f, "full")[len(f) - 1:]
        if ac[0] > 0:
            ac = ac / ac[0]
            lags = np.arange(len(ac)) * 0.01
            cand = []
            for i in range(int(0.25 / 0.01), min(int(1.4 / 0.01), len(ac) - 1)):
                if ac[i] > ac[i - 1] and ac[i] >= ac[i + 1]:
                    cand.append((round(float(lags[i]), 2), round(float(ac[i]), 3)))
            cand = sorted(cand, key=lambda c: -c[1])[:4]
            if cand:
                lag, forca = cand[0]
                ambiguo = len(cand) > 1 and cand[1][1] > 0.85 * forca
                clara = forca >= 0.35 and not ambiguo
                ritmo = {
                    "bpm_mais_provavel": round(60.0 / lag, 1),
                    "candidatos_periodo_s_forca": cand,
                    "forca_do_pico_principal": forca,
                    "leitura": ("pulso claro: pode servir de referência" if clara else
                                "pulso fraco ou ambíguo: NÃO afirme BPM nem prometa cortes na batida"),
                }
    return {
        "duracao_analisada_s": seg,
        "nivel_rms_dbfs_por_segundo": rms_db,
        "fracao_silencio": round(silencio, 2),
        "pico_amostra": round(pico, 3),
        "fracao_amostras_clipadas": round(clip, 5),
        "primeiro_segundo_audivel": primeiro_audivel,
        "segundo_em_que_chega_ao_nivel_normal": ponto_normal,
        "indicador_de_voz_3a6hz": voz,
        "aviso_voz": ("Indicador fraco; só afirme a existência de voz com transcrição ou depois de ouvir o trecho."),
        "ritmo": ritmo,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--saida", default="diagnostico")
    ap.add_argument("--limiar", type=float, default=0.25, help="limiar da detecção de cena (0.15–0.4)")
    ap.add_argument("--intervalo", type=float, default=2.5, help="segundos entre quadros da folha de contato")
    ap.add_argument("--checar-cortes", default="",
                    help="tempos (s, separados por vírgula, na linha do tempo do ÁUDIO) para testar se caem em inícios de som")
    a = ap.parse_args()

    for ferramenta in ("ffmpeg", "ffprobe"):
        if not shutil.which(ferramenta):
            sys.exit(f"{ferramenta} não encontrado no ambiente.")
    os.makedirs(a.saida, exist_ok=True)

    info = probe(a.video)
    v = next((s for s in info["streams"] if s.get("codec_type") == "video"), None)
    au = next((s for s in info["streams"] if s.get("codec_type") == "audio"), None)
    if not v:
        sys.exit("O arquivo não tem stream de vídeo.")
    w, h = v.get("width"), v.get("height")
    dur = float(info["format"].get("duration", 0) or 0)
    classe, nota = classificar(w, h)

    resumo = {
        "arquivo": os.path.basename(a.video),
        "duracao_s": round(dur, 2),
        "resolucao": f"{w}x{h}",
        "proporcao": round(w / h, 4) if h else None,
        "fps": round(fps_of(v), 2),
        "codec_video": v.get("codec_name"),
        "bitrate_video_kbps": round(int(v.get("bit_rate", 0) or 0) / 1000) or None,
        "tamanho_mb": round(int(info["format"].get("size", 0) or 0) / 1e6, 1),
        "audio": ({"codec": au.get("codec_name"), "sample_rate": au.get("sample_rate"),
                   "canais": au.get("channels"),
                   "bitrate_kbps": round(int(au.get("bit_rate", 0) or 0) / 1000) or None} if au else None),
        "classificacao_9x16": classe,
        "nota_classificacao": nota,
    }
    cortes = cortes_de_cena(a.video, a.limiar)
    folhas = folhas_de_contato(a.video, dur, a.intervalo, a.saida)
    audio = analisar_audio(a.video) if au else None

    resultado = {
        "resumo": resumo,
        "cortes_de_cena_s": cortes,
        "aviso_cortes": "Detecção automática é aproximada: confirme nas folhas de contato.",
        "folhas_de_contato": folhas,
        "intervalo_folha_s": a.intervalo,
        "audio": audio,
    }
    with open(os.path.join(a.saida, "analise.json"), "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    # resumo legível
    print(f"Arquivo: {resumo['arquivo']}")
    print(f"Duração: {resumo['duracao_s']} s | {resumo['resolucao']} | {resumo['fps']} fps | {resumo['codec_video']}")
    print(f"Classificação 9:16: {classe} ({nota})")
    print(f"Cortes de cena (s): {cortes}")
    if audio:
        r = audio["ritmo"]
        print(f"Áudio: silêncio {audio['fracao_silencio']*100:.0f}% | pico {audio['pico_amostra']} | "
              f"clipping {audio['fracao_amostras_clipadas']*100:.3f}% | "
              f"chega ao nível normal em {audio['segundo_em_que_chega_ao_nivel_normal']} s")
        if r:
            print(f"Ritmo: {r['bpm_mais_provavel']} BPM (pico {r['forca_do_pico_principal']}; candidatos {r['candidatos_periodo_s_forca']}) -> {r['leitura']}")
        print("Voz: " + audio["aviso_voz"])
    else:
        print("Sem áudio no arquivo.")
    if a.checar_cortes and au:
        ts = [float(t) for t in a.checar_cortes.split(",") if t.strip()]
        res = checar_cortes(a.video, ts)
        resultado["checagem_cortes"] = res
        print(f"Cortes na batida? {res}")
    print("Folhas de contato: " + ", ".join(folhas))
    print(f"JSON completo em {os.path.join(a.saida, 'analise.json')}")


if __name__ == "__main__":
    main()
