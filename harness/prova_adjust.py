"""Aceite ETAPA 2-RotaAjuste: adjust_route (Flts +2, Fare mid->high) na rota
Washington-Havana de probe_hub_open_sa.state, via Executor.run() real."""
from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from executor import Executor
from macros import Game
import world

O = Path("../logs/adjust_aceite")
O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge()
g = Game(b, shot_dir=O)
b.load("../states/probe_hub_open_sa.state")
b.advance(90)
b.speed(400)
ex = Executor(b)
ex.g = g
ex.routes = [{"from": "NA13", "to": "SA01", "flights": 1, "fare_level": "mid"}]
ex._ensure_menu()
print("caixa antes:", world.read_cash_k(b), "rotas:", ex.routes, flush=True)

ok, det = ex.run({"action": "adjust_route",
                  "params": {"route": "SA01", "flights_week": 3, "fare_level": "high"}})
print("RESULT", ok, "|", det, flush=True)
print("rotas depois (memoria do harness):", ex.routes, flush=True)
print("caixa depois:", world.read_cash_k(b), flush=True)

# evidencia visual: reabrir route_edit e fotografar
g.open_cmd("route_edit")
b.advance(150)
p = b.screenshot(O / "z_final_summary.png")
Image.open(p).convert("RGB").resize((768, 672)).save(O / "z_final_summary_big.png")
b.speed(100)
