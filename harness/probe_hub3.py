"""PROBE 3 (17/08): caminhada passo a passo do fluxo de hub (r1c0) COM sucesso.

Parte de `prova_ic_rota_sa.state` (pre-hub, rota Washington->Havana aberta,
caixa 1.166.820K, 4 negociadores livres). Objetivo: descobrir quantas telas
existem entre o seletor de funcionario e a mensagem final, se ha escolha de
CIDADE, e em que passo exatamente o caixa e debitado.

Cada A e seguido de captura + leitura de caixa. Salva o estado final em
../states/_hub3_pos.state para reaproveitar.
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/hub2"); O.mkdir(parents=True, exist_ok=True)
STATE = "../states/prova_ic_rota_sa.state"
REG = int(sys.argv[1]) if len(sys.argv) > 1 else 1

b = BizHawkBridge()
ex = Executor(b)
g = Game(b, shot_dir=O)
ex.g = g
b.load(STATE); b.advance(90); b.speed(400)

img = Image.open(b.screenshot(O / "p3_00_menu.png")).convert("RGB")
cash0 = world.read_cash_k(b)
print(f"inicio: cash={cash0} regiao={world.detect_region(img)} livres={world.free_staff_menu(img)}",
      flush=True)

reg, verif = world.switch_to_region(b, REG, None)
print(f"switch_to_region -> {reg} (verif={verif})", flush=True)
if reg != REG:
    b.load(STATE); b.speed(100); sys.exit("regiao errada")

g.open_cmd("home_info")
world.wait_text(b)
b.advance(120)
img = Image.open(b.screenshot(O / "p3_01_staff.png")).convert("RGB")
if not world.on_staff_screen(img):
    img.resize((768, 672), Image.NEAREST).save(O / "p3_01_naostaff_x3.png")
    b.load(STATE); b.speed(100)
    sys.exit(f"nao e a tela de staff (recusa?) -> {O / 'p3_01_naostaff_x3.png'}")

ok, cel, det = ex._pick_free_staff()
print(f"pick_free_staff -> {ok} {cel} {det}", flush=True)
if not ok:
    b.load(STATE); b.speed(100); sys.exit("nao escolheu funcionario")

for i in range(1, 8):
    antes = world.read_cash_k(b)
    world.wait_text(b)
    b.press("A", hold=5, wait=25)
    b.advance(150)
    p = b.screenshot(O / f"p3_A{i}.png")
    img = Image.open(p).convert("RGB")
    depois = world.read_cash_k(b)
    menu = world.at_main_menu_img(img)
    print(f"A{i}: cash {antes} -> {depois} ({depois - antes:+d}) | menu={menu} | "
          f"land={world.land_pixels(img)} | staff={world.on_staff_screen(img)}", flush=True)
    img.crop((0, 145, 256, 200)).resize((768, 165), Image.NEAREST).save(O / f"p3_A{i}_txt.png")
    if menu:
        break

b.advance(120)
img = Image.open(b.screenshot(O / "p3_fim.png")).convert("RGB")
print(f"FIM: cash={world.read_cash_k(b)} (delta {world.read_cash_k(b) - cash0:+d}) "
      f"menu={world.at_main_menu_img(img)} livres={world.free_staff_menu(img)} "
      f"regiao={world.detect_region(img)}", flush=True)
b.save("../states/_hub3_pos.state")
b.speed(100)
print("estado salvo em ../states/_hub3_pos.state", flush=True)
