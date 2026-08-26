"""CALIBRACAO do seletor de FUNCIONARIO da tela de negociacao (r0c2).

Mede: (a) a caixa vermelha de selecao pisca?  (b) geometria das 5 celulas,
(c) quantos toques de cada direcao andam quanto, (d) o seletor e pegajoso?
Parte de ../states/_neg1_feita.state (uma negociacao ja em andamento, entao a
celula 0 esta OCUPADA — que e o caso que quebra a 2a negociacao do turno).
"""
import sys
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
    return (min(xs), min(ys), max(xs), max(ys)), len(pts)


def snap(tag):
    return Image.open(b.screenshot(O / f"{tag}.png")).convert("RGB")


b.load("../states/_neg1_feita.state"); b.advance(90); b.speed(400)
ex._ensure_menu()
g.open_cmd("negotiate")
world.wait_text(b)

print("=== (a) a caixa vermelha pisca? 8 leituras sem input ===", flush=True)
for i in range(8):
    b.advance(10)
    print(f"  leitura {i}: {red_box(snap(f'blink_{i}'))}", flush=True)

print("=== (b) geometria: Right x6 ===", flush=True)
for i in range(7):
    print(f"  Right x{i}: {red_box(snap(f'right_{i}'))}", flush=True)
    b.batch(b.seq_press("Right", hold=3, wait=14) + b.seq_advance(30), extra_frames=120)

print("=== (c) Down a partir do zero ===", flush=True)
b.load("../states/_neg1_feita.state"); b.advance(90)
ex._ensure_menu(); g.open_cmd("negotiate"); world.wait_text(b)
for i in range(4):
    print(f"  Down x{i}: {red_box(snap(f'down_{i}'))}", flush=True)
    b.batch(b.seq_press("Down", hold=3, wait=14) + b.seq_advance(30), extra_frames=120)

b.speed(100)
