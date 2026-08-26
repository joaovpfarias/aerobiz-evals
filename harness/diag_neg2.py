"""DIAGNOSTICO: por que a 2a negociacao do turno falha com 'cursor do mapa nao respondeu'.

Reproduz pelo caminho do piloto (Executor.run) e captura a tela no momento EXATO
da falha: abre o comando de negociacao pela 2a vez e fotografa cada A.
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/neg2"); O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge(); ex = Executor(b); g = Game(b)

b.load("../states/eval_single_2000_lv5.state"); b.advance(90); b.speed(400)

print("=== 1a negociacao (EU11) pelo Executor.run ===", flush=True)
ok, det = ex.run({"action": "negotiate_slots", "params": {"city": "EU11"}})
print(f"  -> {ok} | {det}", flush=True)

b.save("../states/_neg1_feita.state")

print("=== reabre o comando de negociacao (o que a 2a acao faz) ===", flush=True)
ex._ensure_menu()
g.open_cmd("negotiate")
img = Image.open(b.screenshot(O / "00_tela_funcionarios.png")).convert("RGB")
print(f"  tela apos open_cmd: mapa={world.on_map_screen(img)} cursor={world.read_cursor(b)}", flush=True)

for i in range(4):
    b.batch(b.seq_press("A", hold=5, wait=25) + b.seq_advance(150), extra_frames=400)
    img = Image.open(b.screenshot(O / f"0{i+1}_apos_A{i+1}.png")).convert("RGB")
    print(f"  A{i+1}: mapa={world.on_map_screen(img)} land={world.land_pixels(img)} "
          f"menu={world.at_main_menu_img(img)} cursor={world.read_cursor(b)}", flush=True)

b.speed(100)
print("capturas em", O.resolve(), flush=True)
