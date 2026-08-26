"""Quantos frames a troca de regiao (R) realmente precisa para ser LIDA?

O laco fechado de switch_to_region gasta 150 frames por tecla. Se a leitura
estabiliza antes, da para cortar sem perder a verificacao — e o invariante de
regiao roda depois de TODA acao, entao isso e custo por acao no eval inteiro.
"""
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/regtempo"); O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge(); ex = Executor(b); g = Game(b, shot_dir=O); ex.g = g

b.load("../states/eval_single_2000_lv5.state"); b.advance(90); b.speed(400)
ex._ensure_menu()
g.open_cmd("negotiate"); world.wait_text(b)
ok, cel, det = ex._pick_free_staff()
for _ in range(5):
    world.wait_text(b); b.press("A", hold=5, wait=25); b.advance(90)
    if world.on_map_screen(Image.open(b.screenshot()).convert("RGB")):
        break
print("no mapa da negociacao; staff:", ok, cel, flush=True)

for i in range(8):
    antes = world.read_region(b)
    b.press("R", hold=4, wait=25)
    traj = []
    for n in range(1, 13):  # ate 12 x 20 = 240 frames
        b.advance(20)
        traj.append((n * 20, world.read_region(b)))
    mudou = next((f for f, r in traj if r is not None and r != antes), None)
    estavel = [r for _, r in traj[-4:]]
    print(f"  R#{i+1}: antes={antes} 1a leitura nova em {mudou} frames | "
          f"ultimas 4 leituras={estavel}", flush=True)
b.speed(100)
