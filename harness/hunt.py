"""Caca a posicao exata de uma cidade no mapa: move o cursor 1px por vez e
tenta selecionar, ate a tela mudar.

O cursor do mapa e um ponteiro livre e nao ha rotulo ao pairar, entao a unica
forma confiavel de acertar o hotspot e tentar selecionar em cada posicao.

Uso:
  python hunt.py Left 24              # varre 24px para a esquerda tentando A
  python hunt.py Left 24 --button A
  python hunt.py --raster 16 10       # varredura 2D: 16px horizontal x 10 linhas
"""

import argparse
import pathlib

from PIL import Image, ImageChops

from bridge import BizHawkBridge

TMP = pathlib.Path(__file__).parent / "ipc" / "hunt.png"
CHANGED = 2000  # pixels de diferenca que contam como "a tela mudou"


def snap(b):
    return Image.open(b.screenshot(TMP)).convert("RGB")


def diff(a, c):
    return sum(1 for p in ImageChops.difference(a, c).getdata() if p != (0, 0, 0))


def try_select(b, base, button):
    b.press(button, hold=5, wait=25)
    cur = snap(b)
    return diff(base, cur), cur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("direction", nargs="?", choices=["Left", "Right", "Up", "Down"])
    ap.add_argument("steps", nargs="?", type=int, default=20)
    ap.add_argument("--button", default="A")
    ap.add_argument("--raster", nargs=2, type=int, metavar=("W", "H"))
    a = ap.parse_args()
    b = BizHawkBridge()
    base = snap(b)

    if a.raster:
        w, h = a.raster
        for row in range(h):
            for col in range(w):
                d, cur = try_select(b, base, a.button)
                if d > CHANGED:
                    print(f"ACERTOU em linha {row}, coluna {col} ({d} px mudaram)")
                    return
                b.press("Right", hold=1, wait=6)
            b.press("Left", hold=w, wait=6)
            b.press("Down", hold=1, wait=6)
            print(f"linha {row} sem acerto", flush=True)
        print("raster terminou sem acerto")
        return

    for i in range(a.steps + 1):
        d, cur = try_select(b, base, a.button)
        print(f"passo {i}: diff {d}", flush=True)
        if d > CHANGED:
            print(f"ACERTOU no passo {i} — {a.button} funcionou apos {i}px {a.direction}")
            return
        b.press(a.direction, hold=1, wait=6)
    print("varredura terminou sem acerto")


if __name__ == "__main__":
    main()
