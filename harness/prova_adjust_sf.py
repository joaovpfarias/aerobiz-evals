"""Segunda prova: mesma acao adjust_route numa rota com folga no teto de Flts
(Washington-San Fran, teto medido = 2) -- confirma que a alavanca de Flts
FUNCIONA (nao so detecta teto) via Executor.run() real."""
from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from executor import Executor
from macros import Game
import world

O = Path("../logs/adjust_aceite_sf")
O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge()
g = Game(b, shot_dir=O)
b.load("../states/_edit_2rotas.state")
b.advance(90)
b.speed(400)
ex = Executor(b)
ex.g = g
ex.routes = [{"from": "NA13", "to": "NA06", "flights": 1, "fare_level": "mid"}]
ex._ensure_menu()
print("caixa antes:", world.read_cash_k(b), "rotas:", ex.routes, flush=True)

ok, det = ex.run({"action": "adjust_route",
                  "params": {"route": "NA06", "flights_week": 2, "fare_level": "high"}})
print("RESULT", ok, "|", det, flush=True)
print("rotas depois:", ex.routes, flush=True)
print("caixa depois:", world.read_cash_k(b), flush=True)

g.open_cmd("route_edit")
b.advance(150)
p = b.screenshot(O / "z_final_summary.png")
Image.open(p).convert("RGB").resize((768, 672)).save(O / "z_final_summary_big.png")
b.speed(100)
