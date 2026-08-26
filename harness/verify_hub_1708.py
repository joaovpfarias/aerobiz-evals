"""Verificacao curta: correcao de 17/08 (detector unico world.at_main_menu_img) segue de pe.
negotiate_slots EU11 -> negotiate_slots SA01 -> negotiate_slots AF01 -> open_route NA06
Esperado: 4/4 True, caixa caindo na rota.
"""
from pathlib import Path

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/verify_hub_1708"); O.mkdir(parents=True, exist_ok=True)
STATE = "../states/eval_single_2000_lv5.state"

b = BizHawkBridge()
ex = Executor(b)
g = Game(b, shot_dir=O)
ex.g = g
b.load(STATE); b.advance(90); b.speed(400)

cash0 = world.read_cash_k(b)
print(f"cash inicial: {cash0}", flush=True)

acoes = [
    {"action": "negotiate_slots", "params": {"city": "EU11"}},
    {"action": "negotiate_slots", "params": {"city": "SA01"}},
    {"action": "negotiate_slots", "params": {"city": "AF01"}},
    {"action": "open_route", "params": {"to": "NA06"}},
]

res = []
for a in acoes:
    cash_antes = world.read_cash_k(b)
    ok, det = ex.run(a)
    cash_depois = world.read_cash_k(b)
    alvo = a["params"].get("city") or a["params"].get("to")
    print(f"{a['action']:16} {alvo:5} -> {ok}  cash {cash_antes}->{cash_depois}\n    {det}", flush=True)
    res.append(ok)

b.speed(100)
print(f"\nRESULTADO: {sum(res)}/{len(res)} | retries de cursor: {ex.retries_fired}", flush=True)
print("ACEITE:", "OK" if all(res) else "FALHOU", flush=True)

img = b.screenshot(O / "final.png")
print("screenshot:", img, flush=True)
