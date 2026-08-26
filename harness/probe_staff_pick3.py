"""CALIBRACAO parte 3: o que e a 5a celula (sem cracha) e o contador de funcionarios livres."""
from pathlib import Path

import numpy as np
from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/staffpick"); O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge(); ex = Executor(b); g = Game(b)
BADGE = (189, 0, 41)


def badge_px(img, box):
    a = np.array(img)[box[1]:box[3], box[0]:box[2]]
    return int(((a[:, :, 0] == BADGE[0]) & (a[:, :, 1] == BADGE[1]) & (a[:, :, 2] == BADGE[2])).sum())


def snap(tag):
    return Image.open(b.screenshot(O / f"{tag}.png")).convert("RGB")


BAR = (72, 170, 115, 190)

b.load("../states/eval_single_2000_lv5.state"); b.advance(90); b.speed(400)
ex._ensure_menu()
img = snap("c_menu_zero_neg")
print(f"menu SEM negociacao: barra={badge_px(img, BAR)}px", flush=True)

b.load("../states/_neg1_feita.state"); b.advance(90)
ex._ensure_menu()
img = snap("c_menu_uma_neg")
print(f"menu com 1 negociacao: barra={badge_px(img, BAR)}px", flush=True)

print("=== a 5a celula (linha 1, coluna 2) ===", flush=True)
g.open_cmd("negotiate"); world.wait_text(b); b.advance(30)
b.batch(b.seq_press("Down", hold=3, wait=14) + b.seq_advance(30), extra_frames=120)
b.batch(b.seq_press("Right", hold=3, wait=14, times=2) + b.seq_advance(30), extra_frames=200)
img = snap("c_celula5")
print(f"  painel Area/Type/Wait: {world.staff_panel_px(img)}px", flush=True)
b.batch(b.seq_press("A", hold=5, wait=25) + b.seq_advance(150), extra_frames=400)
img = snap("c_celula5_apos_A")
print(f"  apos A: mapa={world.on_map_screen(img)}", flush=True)
b.speed(100)
