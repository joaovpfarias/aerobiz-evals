"""Cataloga as cidades das 7 regioes percorrendo o mapa com R durante a criacao de rota.

Sem isto o agente so alcanca a America do Norte — e a vitoria exige hub em TODA
regiao e #1 nas 7. O eval mediria um jogo truncado.
"""
import json
from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from executor import Executor
from macros import Game
from world import activate_cursor, detect_cities

O = Path("../logs/regioes"); O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge(); b.load("../states/eval_single_2000_lv5.state"); b.advance(90); b.speed(400)
ex = Executor(b); g = Game(b)
ex._ensure_menu(); g.open_cmd("new_route"); activate_cursor(b)

catalogo = {}
for i in range(8):  # 7 regioes + volta ao inicio para confirmar o ciclo
    img = Image.open(b.screenshot(O / f"reg_{i}.png")).convert("RGB")
    cidades = detect_cities(img)
    catalogo[i] = [(x, y) for x, y, _ in cidades]
    print(f"regiao {i}: {len(cidades)} cidades", flush=True)
    b.batch(b.seq_press("R", hold=4, wait=25) + b.seq_advance(120), extra_frames=300)

Path("../logs/regioes/catalogo_bruto.json").write_text(json.dumps(catalogo, indent=1), encoding="utf-8")
print("total de cidades por regiao:", {k: len(v) for k, v in catalogo.items()})
