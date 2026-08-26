"""Amplia (e opcionalmente recorta) um screenshot — texto de SNES em 256x224 fica
ilegivel por visao sem upscale. Nearest-neighbor preserva as bordas dos pixels.

Uso:
  python zoom.py entrada.png [saida.png] [--scale 4] [--crop x,y,w,h]
  python zoom.py entrada.png --grid          # sobrepoe grade de coordenadas
"""

import argparse
import pathlib

from PIL import Image, ImageDraw


def zoom(src, dst=None, scale=4, crop=None, grid=False):
    img = Image.open(src).convert("RGB")
    if crop:
        x, y, w, h = crop
        img = img.crop((x, y, x + w, y + h))
    big = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    if grid:
        d = ImageDraw.Draw(big)
        step = 16 * scale
        for gx in range(0, big.width, step):
            d.line([(gx, 0), (gx, big.height)], fill=(255, 0, 0), width=1)
            d.text((gx + 2, 2), str(gx // scale), fill=(255, 0, 0))
        for gy in range(0, big.height, step):
            d.line([(0, gy), (big.width, gy)], fill=(255, 0, 0), width=1)
            d.text((2, gy + 2), str(gy // scale), fill=(255, 0, 0))
    dst = dst or str(pathlib.Path(src).with_suffix("")) + f"_x{scale}.png"
    big.save(dst)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst", nargs="?")
    ap.add_argument("--scale", type=int, default=4)
    ap.add_argument("--crop", help="x,y,w,h em pixels da imagem original")
    ap.add_argument("--grid", action="store_true")
    a = ap.parse_args()
    crop = tuple(int(v) for v in a.crop.split(",")) if a.crop else None
    print(zoom(a.src, a.dst, a.scale, crop, a.grid))


if __name__ == "__main__":
    main()
