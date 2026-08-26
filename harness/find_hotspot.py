"""Descobre o deslocamento do hotspot do cursor do mapa.

O cursor e um sprite de aviao; o ponto sensivel (que define "sobre qual cidade
estou") nao e necessariamente o centro do sprite. Aqui varremos um quadrado ao
redor de uma cidade conhecida tentando selecionar em cada posicao — o offset que
funcionar vale para todas as cidades.

Uso: python find_hotspot.py 204 84 [--radius 8] [--button A]
"""

import argparse
import pathlib

from PIL import Image, ImageChops

from bridge import BizHawkBridge
from locate import STEP_PX, goto

TMP = pathlib.Path(__file__).parent / "ipc" / "hot.png"
CHANGED = 2000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cx", type=int)
    ap.add_argument("cy", type=int)
    ap.add_argument("--radius", type=int, default=8)
    ap.add_argument("--button", default="A")
    a = ap.parse_args()
    b = BizHawkBridge()

    r = a.radius
    start = (a.cx - r, a.cy - r)
    print(f"posicionando em {start} (canto do quadrado {2*r+1}x{2*r+1})...", flush=True)
    goto(b, *start)
    cols = (2 * r) // STEP_PX + 1

    base = Image.open(b.screenshot(TMP)).convert("RGB")
    for row in range(cols):
        for col in range(cols):
            b.press(a.button, hold=5, wait=20)
            cur = Image.open(b.screenshot(TMP)).convert("RGB")
            d = sum(1 for p in ImageChops.difference(base, cur).getdata() if p != (0, 0, 0))
            if d > CHANGED:
                ox = start[0] + col * STEP_PX - a.cx
                oy = start[1] + row * STEP_PX - a.cy
                print(f"ACERTOU: centro do cursor deve ficar em cidade+({ox},{oy}) — {d} px")
                return
            b.press("Right", hold=1, wait=5)
        for _ in range(cols):
            b.press("Left", hold=1, wait=5)
        b.press("Down", hold=1, wait=5)
        print(f"  linha {row + 1}/{cols} sem acerto", flush=True)
    print("varredura completa sem acerto — o botao ou a tela estao errados")


if __name__ == "__main__":
    main()
