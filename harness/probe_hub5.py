"""PROBE 5 (17/08): a narracao de fim de turno anda SOZINHA?

O probe 4 mostrou que depois de `end_turn` o jogo ainda esta contando o
trimestre: "Passenger Totals for Europe", relatorios por companhia e as jogadas
dos rivais ("AirRoma entered into negotiations with Mexico City"). Dez toques de
B nao chegaram ao menu.

Aqui NAO se aperta nada: so avanca frames. Se o menu aparecer sozinho, a saida
segura de `dismiss_to_menu` e ESPERAR, e nao apertar — o que elimina de vez o
risco de confirmar uma compra por engano (foi assim que $276.000K sumiram).

Uso: python probe_hub5.py [frames_por_bloco] [blocos]
"""
import hashlib
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from macros import Game

O = Path("../logs/hub2"); O.mkdir(parents=True, exist_ok=True)
STATE = "../states/_hub_chain.state"
BLOCO = int(sys.argv[1]) if len(sys.argv) > 1 else 400
N = int(sys.argv[2]) if len(sys.argv) > 2 else 20

b = BizHawkBridge()
g = Game(b, shot_dir=O)
b.load(STATE); b.advance(90); b.speed(400)
cash0 = world.read_cash_k(b)
print(f"inicio: cash={cash0}", flush=True)

g.end_turn()
b.advance(60)

anterior = None
for i in range(N):
    b.advance(BLOCO)
    p = b.screenshot(O / f"p5_{i:02d}.png")
    img = Image.open(p).convert("RGB")
    h = hashlib.md5(img.tobytes()).hexdigest()[:8]
    menu = world.at_main_menu_img(img)
    parado = "  (tela PARADA)" if h == anterior else ""
    print(f"  bloco {i:02d} (+{(i + 1) * BLOCO} frames): menu={menu} hash={h} "
          f"cash={world.read_cash_k(b)}{parado}", flush=True)
    anterior = h
    if menu:
        print(f"MENU alcancado SEM apertar nada, em {(i + 1) * BLOCO} frames", flush=True)
        break

b.load(STATE); b.advance(60); b.speed(100)
print(f"restaurado; cash={world.read_cash_k(b)}", flush=True)
