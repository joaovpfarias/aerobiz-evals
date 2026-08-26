"""ETAPA 12-HubsCompleto (c): compara slots do mapa ANTES/DEPOIS do close_hub
de verdade (codigo corrigido), sem reabrir depois."""
from pathlib import Path
from PIL import Image
import world
from bridge import BizHawkBridge
from executor import Executor

O = Path("../logs/close_hub_final_18ago")
O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge()
ex = Executor(b)

b.load("../states/_hub_rota_do_hub.state")
b.advance(90)
b.speed(400)
ex.reset_world_state(
    hubs={world.HOME, "SA01"},
    routes=[{"from": world.HOME, "to": "SA01", "flights": 1},
            {"from": "SA01", "to": "SA03", "flights": 1}],
    owned_slots={**world.EVAL_SLOTS_2000, "SA01": 2, "SA03": 1},
)

ex._ensure_menu()
ex._goto_region(1)
img_antes = Image.open(b.screenshot(O / "slots_ANTES_hub.png")).convert("RGB")
cur = tuple(b.read_ram(world.CURSOR_X, 3)[::2])
slots_antes = world.cities_with_slots(img_antes, cursor=cur, region=1)
print("ANTES (com hub):", slots_antes)

ok, det = ex.run({"action": "close_hub", "params": {"region": 1}})
print("close_hub:", ok)
b.save("../states/_hub_fechado_de_verdade.state")

ex._ensure_menu()
ex._goto_region(1)
img_depois = Image.open(b.screenshot(O / "slots_DEPOIS_hub.png")).convert("RGB")
cur2 = tuple(b.read_ram(world.CURSOR_X, 3)[::2])
slots_depois = world.cities_with_slots(img_depois, cursor=cur2, region=1)
print("DEPOIS (sem hub):", slots_depois)

b.speed(100)
print("DONE")
