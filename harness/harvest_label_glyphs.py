#!/usr/bin/env python3
"""Mostra como arte ASCII os glifos de ROTULO fora de `glyphs_label.json`.

O rotulo e escolhido por um HUMANO olhando o desenho — nunca inferido. Uso:

    python harvest_label_glyphs.py ../logs/pnl_19ago/algum_finance.png
"""
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import world  # noqa: E402


def art(img, a, b, y0):
    px = img.load()
    return ["".join("#" if px[x, y] == world.LABEL_INK else "." for x in range(a, b))
            for y in range(y0, y0 + world.LABEL_BAND_H)]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    img = Image.open(sys.argv[1]).convert("RGB")
    if not world.on_quarterly_report_img2(img):
        print("AVISO: o guard diz que isto nao e o Quarterly Report", flush=True)
    total = 0
    for y, rotulo, valor in world.pnl_rows(img):
        fora = world.label_unknown_glyphs(img, y)
        print(f"y={y:3d}  rotulo lido: {rotulo!r}  valor={valor}")
        for h, (a, b, y0) in fora.items():
            total += 1
            print(f"   glifo NOVO {h} em x=[{a},{b}) largura={b - a}")
            for linha in art(img, a, b, y0):
                print("      ", linha)
    print(f"\n{total} glifo(s) fora do atlas. Rotule a mao em glyphs_label.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
