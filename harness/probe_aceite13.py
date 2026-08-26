"""ACEITE 13/08: negociacao de slots FORA da America do Norte + tentativa de rota.

(a) negotiate_slots numa cidade da Europa — prova pela tela de detalhe (nome do
    pais/cidade) + regiao lida por pixels.
(b) open_route para essa cidade — o jogo deve RECUSAR enquanto nao houver slot.
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/world13"); O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge(); ex = Executor(b); g = Game(b)
ALVO = sys.argv[1] if len(sys.argv) > 1 else "EU11"


def snap(tag):
    p = b.screenshot(O / f"{tag}.png")
    img = Image.open(p).convert("RGB")
    print(f"  {tag}: regiao={world.detect_region(img)} menu={world.at_main_menu_img(img)} caixa={world.read_cash_k(b)}K", flush=True)


b.load("../states/eval_single_2000_lv5.state"); b.advance(90); b.speed(400)
ex._ensure_menu()
print("caixa inicial:", world.read_cash_k(b), "K", flush=True)
snap("20_inicio")

ok, det = ex.run({"action": "negotiate_slots", "params": {"city": ALVO}})
print(f"(a) negotiate_slots {ALVO} -> {ok}: {det}", flush=True)
print("   map_region apos a acao:", ex.map_region, flush=True)
snap("21_pos_negociacao")

ok2, det2 = ex.run({"action": "open_route", "params": {"to": ALVO, "aircraft_index": 1}})
print(f"(b) open_route {ALVO} -> {ok2}: {det2}", flush=True)
print("   map_region apos a acao:", ex.map_region, flush=True)
snap("22_pos_rota")
b.speed(100)
