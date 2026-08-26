"""ETAPA 12-HubsCompleto: pode reabrir hub na MESMA cidade apos fechar?

Parte de `_close_hub_resultado.state` (hub em Havana fechado, rota
Washington->Havana ainda de pe). Tenta open_hub(regiao 1) de novo.
"""
from pathlib import Path
from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/close_hub_full_18ago")
O.mkdir(parents=True, exist_ok=True)

b = BizHawkBridge()
g = Game(b, shot_dir=O)
ex = Executor(b)
ex.g = g

b.load("../states/_close_hub_resultado.state")
b.advance(90)
b.speed(400)

ex.reset_world_state(
    hubs={world.HOME},
    routes=[{"from": world.HOME, "to": "SA01", "flights": 1}],
    owned_slots={**world.EVAL_SLOTS_2000, "SA01": 2},
)

caixa_antes = world.read_cash_k(b)
print("caixa antes:", caixa_antes)

ok, det = ex.run({"action": "open_hub", "params": {"region": 1}})
print("open_hub(1) apos close:", ok)
print(det)

caixa_depois = world.read_cash_k(b)
print("caixa depois:", caixa_depois, "delta:", caixa_depois - caixa_antes)

b.save("../states/_hub_reaberto.state")
b.speed(100)
