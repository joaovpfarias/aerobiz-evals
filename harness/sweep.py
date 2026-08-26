"""Varre o cursor do mapa em uma direcao e detecta em que passo a caixa de
mensagem acende (nome da cidade sob o cursor).

O cursor do mapa e um ponteiro livre (1px por frame segurado), e o rotulo da
cidade so aparece quando o hotspot esta exatamente sobre o ponto. Varrer e mais
barato que adivinhar coordenadas.

Uso:
  python sweep.py Left 12                 # 12 passos para a esquerda
  python sweep.py Left 12 --step 2        # 2px por passo
  python sweep.py --probe                 # so mede a caixa agora
"""

import argparse
import pathlib

from PIL import Image

from bridge import BizHawkBridge

# Interior da caixa de mensagem em coords originais (256x224). Calibrado:
# exclui o retrato da secretaria (esquerda) e a moldura em relevo (direita),
# que sao claros e davam falso positivo. Com texto = ~400, vazia = 0.
BOX = (62, 152, 232, 188)  # x0, y0, x1, y1
TMP = pathlib.Path(__file__).parent / "ipc" / "sweep.png"


def box_brightness(bridge, path=None):
    """Numero de pixels claros (texto) dentro da caixa de mensagem."""
    p = bridge.screenshot(path or TMP)
    img = Image.open(p).convert("RGB").crop(BOX)
    return sum(1 for r, g, b in img.getdata() if (r + g + b) / 3 > 140)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("direction", nargs="?", choices=["Left", "Right", "Up", "Down"])
    ap.add_argument("steps", nargs="?", type=int, default=10)
    ap.add_argument("--step", type=int, default=1, help="frames segurados por passo (~px)")
    ap.add_argument("--probe", action="store_true")
    a = ap.parse_args()
    b = BizHawkBridge()

    if a.probe or not a.direction:
        print(f"pixels claros na caixa: {box_brightness(b)}")
        return

    base = box_brightness(b)
    print(f"passo 0 (inicio): {base} pixels claros")
    best = (0, base)
    for i in range(1, a.steps + 1):
        b.press(a.direction, hold=a.step, wait=10)
        n = box_brightness(b)
        mark = "  <<< ACENDEU" if n > base + 20 else ""
        print(f"passo {i} ({a.direction} x{i * a.step}px): {n}{mark}", flush=True)
        if n > best[1]:
            best = (i, n)
    print(f"\nmelhor: passo {best[0]} com {best[1]} pixels claros")


if __name__ == "__main__":
    main()
