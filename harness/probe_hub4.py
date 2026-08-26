"""PROBE 4 (17/08): mapear a SAIDA das telas de fim de turno, tecla a tecla.

Motivo: `dismiss_to_menu` (versao B-primeiro) terminou PRESA numa caixa de
"Regional Rankings" com as 7 regioes em N/A (logs/hub2/b_t1_PRESO.png) — 16
toques sem chegar ao menu. Antes de mexer no helper eu preciso ver a sequencia
real de telas e qual botao sai de cada uma.

So aperta o botao pedido (default B). Nunca mistura. Sai por b.load().
Uso: python probe_hub4.py [B|A] [n_toques]
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
BTN = sys.argv[1] if len(sys.argv) > 1 else "B"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 10

b = BizHawkBridge()
g = Game(b, shot_dir=O)
b.load(STATE); b.advance(90); b.speed(400)
print(f"inicio: cash={world.read_cash_k(b)}", flush=True)

g.end_turn()
b.advance(120)


def tela(tag):
    p = b.screenshot(O / f"p4_{BTN}_{tag}.png")
    img = Image.open(p).convert("RGB")
    h = hashlib.md5(img.tobytes()).hexdigest()[:8]
    print(f"  {tag:>3}: menu={world.at_main_menu_img(img)} hash={h} "
          f"land={world.land_pixels(img)} cash={world.read_cash_k(b)} -> {p}", flush=True)
    return h, img


h0, _ = tela("t0")
for i in range(1, N + 1):
    b.press(BTN, hold=5, wait=25)
    b.advance(120)
    h, img = tela(str(i))
    if world.at_main_menu_img(img):
        print(f"MENU alcancado com {i} toques de {BTN}", flush=True)
        break

b.load(STATE); b.advance(60); b.speed(100)
print(f"restaurado; cash={world.read_cash_k(b)}", flush=True)
