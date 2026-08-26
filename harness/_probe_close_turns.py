"""Depois de close_hub, o jogo ainda recusa reabrir na hora ('You already have
a regional hub in Havana'). Hipotese: fechamento tambem tem LATENCIA (como
abertura tem hubs_pending) e precisa passar turnos. Testar passando turnos
a partir de `_close_hub_clean.state` e tentando open_hub a cada turno."""
from pathlib import Path
from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor, wait_text
from macros import Game

O = Path("../logs/close_hub_full_18ago")
O.mkdir(parents=True, exist_ok=True)

b = BizHawkBridge()
g = Game(b, shot_dir=O)
ex = Executor(b)
ex.g = g

b.load("../states/_close_hub_clean.state")
b.advance(90)
b.speed(400)

ex.reset_world_state(
    hubs={world.HOME},
    routes=[{"from": world.HOME, "to": "SA01", "flights": 1}],
    owned_slots={**world.EVAL_SLOTS_2000, "SA01": 2},
)

for t in range(4):
    ok, det = ex.run({"action": "open_hub", "params": {"region": 1}})
    print(f"[+{t} turnos] open_hub(1):", ok)
    if ok:
        print("  ", det[:300])
        break
    else:
        print("  ", det[:200])
    print(f"  passando 1 turno...")
    g.end_turn()

b.save("../states/_close_hub_after_turns.state")
b.speed(100)
print("DONE")
