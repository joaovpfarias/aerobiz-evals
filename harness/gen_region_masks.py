"""Congela as MASCARAS de terra das 7 regioes em harness/region_masks.json.

Gerador OFFLINE. Roda a partir de logs/regioes/reg_0..6.png (as telas de mapa
limpas, sem rota desenhada) e grava a mascara amostrada em `land_pixels`
(step=3, faixa y<140) como lista de indices.

Por que congelar em vez de ler os PNGs em tempo de import: os PNGs vivem em
`logs/`, que e area de trabalho e ja foi limpa antes. O detector nao pode
depender de arquivo de log para existir.

reg_7.png e DESCARTADO de proposito: land_pixels(reg_7)==2262==land_pixels(reg_0),
isto e, e o wrap-around do ciclo de R de volta a regiao 0, nao uma oitava regiao.

Uso:
    python harness/gen_region_masks.py
"""
import json
import os

from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
REGIOES = os.path.join(RAIZ, "logs", "regioes")
SAIDA = os.path.join(AQUI, "region_masks.json")

STEP = 3
YMAX = 140
XMAX = 256


def land_index_set(img, step=STEP):
    """Mesma regra de cor de world.land_pixels, devolvida como indices lineares."""
    px = img.load()
    largura = (XMAX + step - 1) // step
    out = []
    for y in range(0, YMAX, step):
        for x in range(0, XMAX, step):
            p = px[x, y]
            if p[1] > p[0] + 30 and p[1] > p[2] + 10:
                out.append((y // step) * largura + (x // step))
    return out


def main():
    dados = {"step": STEP, "ymax": YMAX, "xmax": XMAX, "regioes": {}}
    for r in range(7):
        caminho = os.path.join(REGIOES, "reg_%d.png" % r)
        img = Image.open(caminho).convert("RGB")
        if img.size != (256, 224):
            raise SystemExit("reg_%d.png nao e 256x224: %s" % (r, img.size))
        idx = land_index_set(img)
        dados["regioes"][str(r)] = idx
        print("r%d: %d pixels de terra (%s)" % (r, len(idx), os.path.basename(caminho)))
    with open(SAIDA, "w") as f:
        json.dump(dados, f)
    print("gravado:", SAIDA)


if __name__ == "__main__":
    main()
