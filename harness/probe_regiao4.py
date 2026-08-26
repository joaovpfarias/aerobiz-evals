"""Por que switch_to_region para na regiao 3 quando o alvo e a 4?

Percorre o ciclo de R no MAPA DE NEGOCIACAO, uma tecla por vez, e mede
land_pixels + detect_region em cada passo.
"""
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/reg4"); O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge(); ex = Executor(b); g = Game(b, shot_dir=O); ex.g = g

b.load("../states/eval_single_2000_lv5.state"); b.advance(90); b.speed(400)
ex._ensure_menu()
g.open_cmd("negotiate")
world.wait_text(b)
ok, cel, det = ex._pick_free_staff()
print("staff:", ok, cel, det, flush=True)
for _ in range(5):
    world.wait_text(b)
    b.press("A", hold=5, wait=25)
    b.advance(90)
    if world.on_map_screen(Image.open(b.screenshot()).convert("RGB")):
        break
print("no mapa da negociacao", flush=True)

for i in range(9):
    img = Image.open(b.screenshot(O / f"R{i}.png")).convert("RGB")
    print(f"  R x{i}: land={world.land_pixels(img):5}  detect={world.detect_region(img)}", flush=True)
    b.batch(b.seq_press("R", hold=4, wait=25) + b.seq_advance(150), extra_frames=400)
b.speed(100)
