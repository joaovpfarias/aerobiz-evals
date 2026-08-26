"""ETAPA 12-HubsCompleto: probe COMPLETO do fluxo close_hub (r1c0, aba Close).

Usa `_hub_rota_do_hub.state`: hub confirmado em Havana (SA01, regiao 1) +
rota Washington->Havana + rota Havana->SA03 partindo do HUB (nao da base).
Objetivo: medir (a) efeito de fechar o hub nas rotas que partiam dali,
(b) custo/credito em caixa, (c) o que a cidade "perde" ao perder o hub.

Roda a sequencia completa de A's (destrutivo!) — savestate de guarda salvo
antes. Screenshots em cada etapa.
"""
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

b.load("../states/_hub_rota_do_hub.state")
b.advance(90)
b.speed(400)

ex.reset_world_state(
    hubs={world.HOME, "SA01"},
    routes=[{"from": world.HOME, "to": "SA01", "flights": 1},
            {"from": "SA01", "to": "SA03", "flights": 1}],
    owned_slots={**world.EVAL_SLOTS_2000, "SA01": 2, "SA03": 1},
)

b.save("../states/_close_hub_guard.state")

caixa_antes = world.read_cash_k(b)
livres_antes = ex._menu_free_staff()
print(f"ANTES: caixa={caixa_antes}K livres={livres_antes}")

# --- ir para regiao 1 e abrir r1c0 ---
ex._ensure_menu()
ok_reg, det = ex._goto_region(1)
print("goto_region(1):", ok_reg, det)

g.open_cmd("home_info")
wait_text(b)
b.advance(120)
img0 = Image.open(b.screenshot(O / "00_staff_screen.png")).convert("RGB")
print("on_staff_screen:", world.on_staff_screen(img0))
print("staff_action_is_bid (neutro):", world.staff_action_is_bid(img0))

# Navegar para Close: Down 1x + Right 2x (celula (1,2))
b.press("Down", hold=3, wait=14); b.advance(40)
b.press("Right", hold=3, wait=14); b.advance(40)
b.press("Right", hold=3, wait=14); b.advance(60)
img1 = Image.open(b.screenshot(O / "01_close_selecionado.png")).convert("RGB")
is_bid = world.staff_action_is_bid(img1)
print("staff_action_is_bid apos Down+Right+Right:", is_bid, "(esperado False=Close)")

if is_bid is not False:
    print("ABORTANDO: nao chegou em Close. Restaurando guard e saindo.")
    b.load("../states/_close_hub_guard.state")
    b.speed(100)
    raise SystemExit(1)

# Confirmar Close
b.press("A", hold=5, wait=25)
b.advance(150)
wait_text(b)
img2 = Image.open(b.screenshot(O / "02_apos_A1.png")).convert("RGB")
print("apos A1 (deveria listar hubs da regiao / Close Set-up)")

b.press("A", hold=5, wait=25)
b.advance(150)
wait_text(b)
img3 = Image.open(b.screenshot(O / "03_apos_A2.png")).convert("RGB")
print("apos A2 (deveria ser detalhe do hub / Shall we close?)")

b.press("A", hold=5, wait=25)
b.advance(200)
wait_text(b)
img4 = Image.open(b.screenshot(O / "04_apos_A3.png")).convert("RGB")
print("apos A3 (confirmacao final)")

# Voltar ao menu principal
for _ in range(8):
    if world.at_main_menu_img(Image.open(b.screenshot()).convert("RGB")):
        break
    b.press("B", hold=5, wait=25)
    b.advance(100)
img5 = Image.open(b.screenshot(O / "05_menu.png")).convert("RGB")
print("de volta ao menu:", world.at_main_menu_img(img5))

caixa_depois = world.read_cash_k(b)
livres_depois = ex._menu_free_staff()
print(f"DEPOIS: caixa={caixa_depois}K ({caixa_depois - caixa_antes:+d}K) livres={livres_depois}")

# --- checar se o hub sumiu: invocar r1c0 de novo na regiao 1 ---
ex._ensure_menu()
ex._goto_region(1)
g.open_cmd("home_info")
wait_text(b)
b.advance(120)
img6 = Image.open(b.screenshot(O / "06_r1c0_pos_close.png")).convert("RGB")
print("r1c0 pos-close: on_staff_screen=", world.on_staff_screen(img6),
      "staff_action_is_bid=", world.staff_action_is_bid(img6))
for _ in range(8):
    if world.at_main_menu_img(Image.open(b.screenshot()).convert("RGB")):
        break
    b.press("B", hold=5, wait=25)
    b.advance(100)

# --- checar a rota SA01->SA03 (que partia do hub): ainda existe? ---
ex._ensure_menu()
g.open_cmd("route_edit")
wait_text(b)
b.advance(120)
img7 = Image.open(b.screenshot(O / "07_route_edit_pos_close.png")).convert("RGB")
print("route_edit pos-close capturado")
for _ in range(8):
    if world.at_main_menu_img(Image.open(b.screenshot()).convert("RGB")):
        break
    b.press("B", hold=5, wait=25)
    b.advance(100)

b.save("../states/_close_hub_resultado.state")
b.speed(100)
print("\nScreenshots em", O)
print("Savestate de resultado: ../states/_close_hub_resultado.state")
print("Guard (pre-close):      ../states/_close_hub_guard.state")
