"""Mede o offset cursor-ponto que ACENDE o nome da cidade na escolha de sede.

Roda sobre a tela JA ABERTA (mapa da regiao). Nao aperta A. Varre um retangulo
de offsets em torno do ponto da cidade e reporta a tinta na caixa de nome.
"""
import argparse
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import locate  # noqa: E402
import world  # noqa: E402
from bridge import BizHawkBridge  # noqa: E402

ROOT = pathlib.Path(__file__).parent.parent
OUT = ROOT / "logs" / "setup"
NAME_BOX = (20, 150, 150, 168)


def ink(p):
    im = Image.open(p).convert("RGB").crop(NAME_BOX)
    return sum(1 for px in im.getdata() if sum(px) > 500)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="EU10")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    b = BizHawkBridge()
    b.speed(400)
    x, y, reg, _ = world.WORLD_CITIES[a.city]
    img = Image.open(b.screenshot(OUT / "_probe0.png")).convert("RGB")
    print("regiao na tela:", world.detect_region(img), "esperada", reg, flush=True)
    achou = []
    for dy in range(-2, 13, 2):
        for dx in range(-2, 9, 2):
            try:
                pos = locate.goto(b, x + dx, y + dy, tol=1)
            except RuntimeError as e:
                print(f"  ({dx},{dy}) goto falhou: {e}", flush=True)
                continue
            p = b.screenshot(OUT / "_probe_h.png")
            k = ink(p)
            if k:
                achou.append((dx, dy, pos, k))
                print(f"  ACENDEU off=({dx},{dy}) cursor={pos} ink={k}", flush=True)
                b.screenshot(OUT / f"_probe_ok_{dx}_{dy}.png")
            else:
                print(f"  ({dx},{dy}) cursor={pos} ink=0", flush=True)
    print("RESULTADO:", achou, flush=True)


main()
