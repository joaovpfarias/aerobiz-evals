"""Probe: R troca de regiao? em que tela? o mapa lembra a regiao entre comandos?

Cada passo IMPRIME a regiao LIDA da tela (world.detect_region) — nada de contar
apertos e acreditar.
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/world13"); O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge(); ex = Executor(b); g = Game(b)


def reg(tag):
    p = b.screenshot(O / f"{tag}.png")
    img = Image.open(p).convert("RGB")
    r = world.detect_region(img)
    print(f"  {tag}: regiao={r} land={world.land_pixels(img)} menu={world.at_main_menu_img(img)}",
          flush=True)
    return r


def fase1():
    b.load("../states/eval_single_2000_lv5.state"); b.advance(90); b.speed(400)
    ex._ensure_menu()
    reg("00_menu")
    g.open_cmd("new_route")
    world.activate_cursor(b)
    reg("01_rota_mapa")
    b.batch(b.seq_press("R", hold=4, wait=25) + b.seq_advance(150), extra_frames=400)
    reg("02_rota_R1")
    b.batch(b.seq_press("R", hold=4, wait=25) + b.seq_advance(150), extra_frames=400)
    reg("03_rota_R2")
    ex._ensure_menu()
    reg("04_menu_depois")
    g.open_cmd("new_route")
    world.activate_cursor(b)
    reg("05_rota_reaberta")
    ex._ensure_menu()


def fase2():
    """Mapa da NEGOCIACAO: R funciona la?"""
    ex._ensure_menu()
    g.open_cmd("negotiate")
    seq = []
    for _ in range(2):
        seq += b.seq_press("A", hold=5, wait=25) + b.seq_advance(150)
    b.batch(seq, extra_frames=600)
    world.activate_cursor(b)
    reg("10_neg_mapa")
    b.batch(b.seq_press("R", hold=4, wait=25) + b.seq_advance(150), extra_frames=400)
    reg("11_neg_R1")
    b.batch(b.seq_press("R", hold=4, wait=25) + b.seq_advance(150), extra_frames=400)
    reg("12_neg_R2")
    ex._ensure_menu()
    reg("13_menu")


if __name__ == "__main__":
    fase = sys.argv[1] if len(sys.argv) > 1 else "1"
    if "1" in fase:
        fase1()
    if "2" in fase:
        fase2()
    b.speed(100)
