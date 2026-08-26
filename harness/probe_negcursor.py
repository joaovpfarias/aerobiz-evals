"""O cursor do mapa da NEGOCIACAO usa as mesmas variaveis de RAM do mapa de rota?

Se nao usar, escrever 0x257F/0x2581 move nada e o A seleciona outra coisa (ou
nada) — que e exatamente o sintoma visto: A na cidade e o jogo continua no mapa.
"""
from pathlib import Path

from PIL import Image, ImageChops

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/negeu"); O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge(); ex = Executor(b); g = Game(b)

b.load("../states/eval_single_2000_lv5.state"); b.advance(90); b.speed(400)
ex._ensure_menu()
g.open_cmd("negotiate")
# A1 = escolhe "Bid"; A2 = mensagem; A3 = escolhe o funcionario -> mapa
for i in range(3):
    b.batch(b.seq_press("A", hold=5, wait=25) + b.seq_advance(150), extra_frames=400)
    img = Image.open(b.screenshot(O / f"20_A{i+1}.png")).convert("RGB")
    print(f"A{i+1}: mapa={world.on_map_screen(img)} ram={world.read_cursor(b)}", flush=True)

print("--- toques de d-pad ---", flush=True)
antes = Image.open(b.screenshot(O / "21_antes.png")).convert("RGB")
for _ in range(5):
    b.batch(b.seq_press("Right", hold=2, wait=10) + b.seq_advance(20), extra_frames=100)
    print("  ram apos Right:", world.read_cursor(b), flush=True)
dep = Image.open(b.screenshot(O / "22_depois.png")).convert("RGB")
print("bbox do que mudou na tela:", ImageChops.difference(antes, dep).crop((0, 0, 256, 140)).getbbox(),
      flush=True)
for _ in range(5):
    b.batch(b.seq_press("Down", hold=2, wait=10) + b.seq_advance(20), extra_frames=100)
    print("  ram apos Down:", world.read_cursor(b), flush=True)
dep2 = Image.open(b.screenshot(O / "23_depois_down.png")).convert("RGB")
print("bbox Down:", ImageChops.difference(dep, dep2).crop((0, 0, 256, 140)).getbbox(), flush=True)
b.speed(100)
