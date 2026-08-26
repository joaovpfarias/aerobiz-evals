"""Identifica os 12 icones de comando abrindo cada um a partir de um savestate.

Os icones nao tem rotulo ao focar, entao a unica forma de saber o que fazem e
abrir. Como recarregamos o savestate antes de cada sonda, nenhuma acao vaza para
o jogo.

Uso: python probe_icons.py [--state ../states/f0_ingame.state]
"""

import argparse
import pathlib

from PIL import Image

from bridge import BizHawkBridge

OUT = pathlib.Path(__file__).parent.parent / "logs" / "run_f0" / "icons"
COLS, ROWS = 6, 2


def probe(b, state, row, col):
    b.load(state)
    b.advance(20)
    for _ in range(row):
        b.press("Down", hold=3, wait=10)
    for _ in range(col):
        b.press("Right", hold=3, wait=10)
    b.press("A", hold=5, wait=40)
    b.advance(200)  # texto tem animacao de maquina de escrever
    return b.screenshot(OUT / f"icon_r{row}c{col}.png")


def montage(paths, dst, scale=2, cols=2):
    imgs = [Image.open(p).convert("RGB") for p in paths]
    w, h = imgs[0].size
    rows = (len(imgs) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols * scale, h * rows * scale), (20, 20, 20))
    for i, img in enumerate(imgs):
        big = img.resize((w * scale, h * scale), Image.NEAREST)
        sheet.paste(big, ((i % cols) * w * scale, (i // cols) * h * scale))
    sheet.save(dst)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default="../states/f0_ingame.state")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    b = BizHawkBridge()
    paths = []
    for row in range(ROWS):
        for col in range(COLS):
            p = probe(b, a.state, row, col)
            paths.append(p)
            print(f"icone r{row}c{col} -> {p}", flush=True)
    half = len(paths) // 2
    print(montage(paths[:half], OUT / "montagem_1.png"))
    print(montage(paths[half:], OUT / "montagem_2.png"))
    b.load(a.state)


if __name__ == "__main__":
    main()
