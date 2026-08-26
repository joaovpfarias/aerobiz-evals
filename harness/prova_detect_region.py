"""ETAPA 1-VerRegiao — aceite OFFLINE de world.detect_region.

Nao sobe emulador. Tres baterias, todas com criterio de aceite explicito:

  A. POSITIVO REAL  — os 12 logs/run_f0/map_t*.png (0, 1 e 2+ rotas desenhadas)
     tem de devolver a regiao 0 em TODOS. Era aqui que a assinatura por
     contagem global devolvia None de t3 em diante.
  B. POSITIVO SINTETICO — as 7 referencias com 2/6/12 rotas pintadas na cor
     MEDIDA das linhas ((90,89,90), extraida do diff map_t01 -> map_t12) tem de
     devolver a propria regiao. Cobre as regioes pequenas, para as quais nao ha
     PNG real com rota e onde a mesma perda absoluta de pixels pesa muito mais.
  C. NEGATIVO — telas que NAO sao mapa limpo tem de devolver None: dialogo
     sintetico tapando >=60% da faixa, e a lista curada de telas de dialogo
     sobre o mapa (etapa1/dem_*, yesno_*) que existem nos logs.

Uso:
    python harness/prova_detect_region.py
"""
import os
import random
import sys

from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
RAIZ = os.path.dirname(AQUI)
LOGS = os.path.join(RAIZ, "logs")

import world  # noqa: E402

# Cor MEDIDA das linhas de rota: diff de logs/run_f0/map_t01.png -> map_t12.png,
# pixels que eram verde e deixaram de ser. Top: (90,89,90) 688px, (0,0,0) 263px.
COR_ROTA = (90, 89, 90)
COR_CIDADE = (255, 251, 239)

falhas = []


def png(*partes):
    return os.path.join(LOGS, *partes)


def bateria_a():
    print("== A. POSITIVO REAL: logs/run_f0/map_t01..12.png (verdade = regiao 0) ==")
    for t in range(1, 13):
        caminho = png("run_f0", "map_t%02d.png" % t)
        if not os.path.exists(caminho):
            print("  t%02d: AUSENTE %s" % (t, caminho))
            continue
        img = Image.open(caminho).convert("RGB")
        r = world.detect_region(img)
        s = world.region_scores(img)
        ok = r == 0
        if not ok:
            falhas.append("A t%02d -> %s" % (t, r))
        print("  t%02d: detect=%s land=%4d prec=%.3f rec=%.3f 2o=r%d %.3f  %s"
              % (t, r, world.land_pixels(img), s[0][0], s[0][1], s[1][2], s[1][0],
                 "OK" if ok else "FALHA"))


def pinta_rotas(base, mask_ref, k, rnd):
    step = world._MASK_STEP
    largura = (world._MASK_XMAX + step - 1) // step
    pontos = [((i % largura) * step, (i // largura) * step) for i in mask_ref]
    im = base.copy()
    d = ImageDraw.Draw(im)
    for _ in range(k):
        p1 = rnd.choice(pontos)
        p2 = rnd.choice(pontos)
        d.line([p1, p2], fill=COR_ROTA, width=2)
        for p in (p1, p2):
            d.ellipse([p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2], fill=COR_CIDADE)
    return im


def bateria_b():
    print("== B. POSITIVO SINTETICO: 7 regioes x {2,6,12} rotas x 20 sorteios ==")
    masks = world._load_region_masks()
    rnd = random.Random(7)
    for r in range(7):
        base = Image.open(png("regioes", "reg_%d.png" % r)).convert("RGB")
        for k in (2, 6, 12):
            pior = None
            erros = 0
            for _ in range(20):
                im = pinta_rotas(base, masks[r], k, rnd)
                lido = world.detect_region(im)
                s = world.region_scores(im)
                if lido != r:
                    erros += 1
                if pior is None or s[0][1] < pior[0][1]:
                    pior = s
            if erros:
                falhas.append("B r%d k%d -> %d erros" % (r, k, erros))
            print("  r%d k=%2d: %2d/20 certos | pior rec=%.3f prec=%.3f 2o=%.3f  %s"
                  % (r, k, 20 - erros, pior[0][1], pior[0][0], pior[1][0],
                     "OK" if not erros else "FALHA"))


def bateria_c():
    print("== C. NEGATIVO: tem de devolver None ==")
    # C1: dialogo sintetico tapando a faixa do mapa, por baixo
    base = Image.open(png("regioes", "reg_0.png")).convert("RGB")
    for frac in (0.6, 0.8, 1.0):
        im = base.copy()
        ImageDraw.Draw(im).rectangle(
            [0, int(140 * (1 - frac)), 255, 139], fill=(40, 40, 120))
        lido = world.detect_region(im)
        ok = lido is None
        if not ok:
            falhas.append("C1 tapa %.0f%% -> %s" % (frac * 100, lido))
        print("  dialogo tapa %3.0f%% da faixa -> %s  %s"
              % (frac * 100, lido, "OK" if ok else "FALHA"))
    # C2: telas reais de dialogo POR CIMA do mapa
    curadas = [
        ("etapa1", "yesno_antes.png"),
        ("etapa1", "dem_yes_apos_A.png"),
        ("etapa1", "dem_no_apos_A.png"),
        ("etapa1", "dem_b_1.png"),
        ("setup", "04b_players.png"),
    ]
    for partes in curadas:
        caminho = png(*partes)
        if not os.path.exists(caminho):
            print("  %s: AUSENTE (pulado)" % "/".join(partes))
            continue
        img = Image.open(caminho).convert("RGB")
        lido = world.detect_region(img)
        s = world.region_scores(img)
        ok = lido is None
        if not ok:
            falhas.append("C2 %s -> %s" % ("/".join(partes), lido))
        print("  %-28s land=%4d prec=%.3f rec=%.3f -> %s  %s"
              % ("/".join(partes), world.land_pixels(img), s[0][0], s[0][1],
                 lido, "OK" if ok else "FALHA"))


def main():
    bateria_a()
    bateria_b()
    bateria_c()
    print("=" * 60)
    if falhas:
        print("REPROVADO — %d falha(s):" % len(falhas))
        for f in falhas:
            print("  -", f)
        return 1
    print("APROVADO — A, B e C sem falha.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
