"""Testar se falta 1 A para COMMITAR o close (a tela 'All flights listed
above will be closed' pode precisar de confirmacao extra, nao so B para sair).
Do zero, savestate limpo `_hub_rota_do_hub.state`."""
from pathlib import Path
from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor, wait_text
from macros import Game

O = Path("../logs/close_hub_full_18ago/extra_a")
O.mkdir(parents=True, exist_ok=True)

b = BizHawkBridge()
g = Game(b, shot_dir=O)
ex = Executor(b)
ex.g = g

b.load("../states/_hub_rota_do_hub.state")
b.advance(90)
b.speed(400)

ex.reset_world_state(
    hubs={world.HOME, "SA01"},
    routes=[{"from": world.HOME, "to": "SA01", "flights": 1},
            {"from": "SA01", "to": "SA03", "flights": 1}],
    owned_slots={**world.EVAL_SLOTS_2000, "SA01": 2, "SA03": 1},
)

caixa0 = world.read_cash_k(b)
print("caixa antes:", caixa0)

ex._ensure_menu()
ex._goto_region(1)
g.open_cmd("home_info")
wait_text(b)
b.advance(120)

b.press("Down", hold=3, wait=14); b.advance(40)
b.press("Right", hold=3, wait=14); b.advance(40)
b.press("Right", hold=3, wait=14); b.advance(60)
img = Image.open(b.screenshot(O / "00_close_sel.png")).convert("RGB")
print("close selecionado:", world.staff_action_is_bid(img))

# Confirmar Close
b.press("A", hold=5, wait=25); b.advance(150); wait_text(b)
img1 = Image.open(b.screenshot(O / "01.png")).convert("RGB")

# Passo extra: press A MAIS VEZES que antes (ate 6), screenshot cada vez,
# parando se voltar ao menu
for i in range(2, 8):
    b.press("A", hold=5, wait=25); b.advance(180); wait_text(b)
    img_i = Image.open(b.screenshot(O / f"{i:02d}.png")).convert("RGB")
    at_menu = world.at_main_menu_img(img_i)
    print(f"apos A{i}: at_main_menu={at_menu}")
    if at_menu:
        break

caixa1 = world.read_cash_k(b)
print(f"caixa apos sequencia: {caixa0}K -> {caixa1}K ({caixa1-caixa0:+d}K)")

ex._ensure_menu()
b.save("../states/_close_hub_v2.state")

print("\n=== testar reabrir agora ===")
ex.reset_world_state(
    hubs={world.HOME},
    routes=[{"from": world.HOME, "to": "SA01", "flights": 1}],
    owned_slots={**world.EVAL_SLOTS_2000, "SA01": 2},
)
ok, det = ex.run({"action": "open_hub", "params": {"region": 1}})
print("open_hub(1):", ok)
print(det[:400])

b.speed(100)
print("DONE")
