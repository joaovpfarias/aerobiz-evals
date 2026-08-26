"""Validacao final de _do_close_hub corrigido: fechar + confirmar reabertura
funcional (round-trip completo via Executor.run, sem atalhos manuais)."""
from pathlib import Path
import world
from bridge import BizHawkBridge
from executor import Executor

O = Path("../logs/close_hub_final_18ago")
O.mkdir(parents=True, exist_ok=True)

b = BizHawkBridge()
ex = Executor(b)
ex.g.shots = O

b.load("../states/_hub_rota_do_hub.state")
b.advance(90)
b.speed(400)

ex.reset_world_state(
    hubs={world.HOME, "SA01"},
    routes=[{"from": world.HOME, "to": "SA01", "flights": 1},
            {"from": "SA01", "to": "SA03", "flights": 1}],
    owned_slots={**world.EVAL_SLOTS_2000, "SA01": 2, "SA03": 1},
)

print("=== close_hub(1) via Executor.run ===")
ok, det = ex.run({"action": "close_hub", "params": {"region": 1}})
print("ok=", ok)
print(det)
print("harness hubs:", ex.hubs)
print("harness routes:", ex.routes)

print("\n=== reabrir open_hub(1) imediatamente apos ===")
ok2, det2 = ex.run({"action": "open_hub", "params": {"region": 1}})
print("ok=", ok2)
print(det2[:500])

b.save("../states/_close_hub_verificado_final.state")
b.speed(100)
print("\nDONE")
