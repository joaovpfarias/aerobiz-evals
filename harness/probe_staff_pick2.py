"""CALIBRACAO parte 2: linha de baixo do seletor de funcionario + deteccao de OCUPADO."""
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/staffpick"); O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge(); ex = Executor(b); g = Game(b)
RED = (255, 0, 0)


def red_box(img):
    px = img.load()
    pts = [(x, y) for y in range(0, 150) for x in range(0, 256) if px[x, y] == RED]
    if not pts:
        return None
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def snap(tag):
    return Image.open(b.screenshot(O / f"{tag}.png")).convert("RGB")


b.load("../states/_neg1_feita.state"); b.advance(90); b.speed(400)
ex._ensure_menu(); g.open_cmd("negotiate"); world.wait_text(b)
b.advance(30)
print("=== linha de baixo: Down, depois Right x4 ===", flush=True)
b.batch(b.seq_press("Down", hold=3, wait=14) + b.seq_advance(30), extra_frames=120)
for i in range(5):
    print(f"  Down + Right x{i}: {red_box(snap(f'b_right_{i}'))}", flush=True)
    b.batch(b.seq_press("Right", hold=3, wait=14) + b.seq_advance(30), extra_frames=120)

print("=== Up a partir de (1,2) ===", flush=True)
b.batch(b.seq_press("Up", hold=3, wait=14) + b.seq_advance(30), extra_frames=120)
print(f"  Up: {red_box(snap('b_up'))}", flush=True)

print("=== o seletor e PEGAJOSO? sai e reabre o comando ===", flush=True)
ex._ensure_menu(); g.open_cmd("negotiate"); world.wait_text(b); b.advance(30)
print(f"  ao reabrir: {red_box(snap('b_reabre'))}", flush=True)
b.speed(100)
