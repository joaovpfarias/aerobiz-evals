"""Por que a rota intercontinental foi recusada + calibracao do aircraft_index.

Modo 'msg <cidade>': abre o fluxo de rota, seleciona a cidade e captura a
MENSAGEM COMPLETA (esperando a datilografia terminar) — a recusa de EU11 veio
com o texto pela metade ("We don't have any aircraft ...").

Modo 'fleet <cidade>': na tela "What type of plane", cicla o seletor com Right
e captura uma tela por posicao. E a calibracao de aircraft_index: cada captura
mostra modelo, alcance e a distancia da rota no cabecalho.
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/prova_ic")
O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge()
ex = Executor(b)
g = Game(b, shot_dir=O)
modo = sys.argv[1]
CID = sys.argv[2] if len(sys.argv) > 2 else "EU11"
STATE = sys.argv[3] if len(sys.argv) > 3 else "../states/prova_ic_slots.state"

b.load(STATE)
b.advance(90)
b.speed(400)
ex._ensure_menu()
g.open_cmd("new_route")
pos, reg, verif = ex._select_city(CID)
print(f"{CID}: regiao={reg} pos={pos} verificada={verif}", flush=True)
world.wait_text(b)
b.advance(120)
p = b.screenshot(O / f"{modo}_{CID}_00.png")
print(" tela pos-selecao:", p, flush=True)

if modo == "fleet":
    for i in range(1, 5):
        b.batch(b.seq_press("Right", hold=3, wait=14) + b.seq_advance(60), extra_frames=150)
        world.wait_text(b)
        b.screenshot(O / f"fleet_{CID}_{i:02d}.png")
        print(f"  idx {i} capturado", flush=True)

ex._ensure_menu()
b.speed(100)
