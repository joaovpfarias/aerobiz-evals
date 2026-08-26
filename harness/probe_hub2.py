"""PROBE 2 (17/08): a TELA DE FUNCIONARIO do comando de hub (r1c0).

Ela parece a da negociacao (grade 2x2 + acao no canto), mas as abas sao
**Open/Close** e nao Bid/Return. Antes de reusar _pick_free_staff eu preciso
medir, nesta tela:
  - staff_sel_cell / staff_free_cells funcionam com a MESMA geometria?
  - onde ficam Open e Close (o BID_BOX/RETURN_BOX pode nao servir) e qual esta
    destacado ao abrir?
Nada e confirmado: sai por b.load().
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from macros import Game

O = Path("../logs/hub2"); O.mkdir(parents=True, exist_ok=True)
STATE = sys.argv[1] if len(sys.argv) > 1 else "../states/prova_ic_rota_sa.state"

b = BizHawkBridge()
g = Game(b, shot_dir=O)
b.load(STATE); b.advance(90); b.speed(400)

img = Image.open(b.screenshot(O / "p2_menu0.png")).convert("RGB")
print("cash:", world.read_cash_k(b), "| menu?", world.at_main_menu_img(img),
      "| regiao:", world.detect_region(img), "| livres:", world.free_staff_menu(img), flush=True)

reg, verif = world.switch_to_region(b, 1, None)
print(f"switch_to_region -> {reg} (verif={verif})", flush=True)
if reg != 1:
    b.load(STATE); b.speed(100); sys.exit("nao chegou na regiao 1")

g.open_cmd("home_info")
world.wait_text(b)
b.advance(150)
shot = b.screenshot(O / "p2_hub_staff.png")
img = Image.open(shot).convert("RGB")
print("tela:", shot, flush=True)
print("staff_sel_cell:", world.staff_sel_cell(img), flush=True)
print("staff_free_cells:", world.staff_free_cells(img), flush=True)
print("BID_BOX px:", world.count_rgb(img, world.BID_BOX, world.BID_ON_RGB),
      "| RETURN_BOX px:", world.count_rgb(img, world.RETURN_BOX, world.BID_ON_RGB), flush=True)
print("staff_action_is_bid:", world.staff_action_is_bid(img), flush=True)
print("on_staff_screen:", world.on_staff_screen(img), flush=True)

# zoom no canto das abas e na tela inteira x3 para ler os rotulos
img.crop((190, 10, 256, 60)).resize((396, 300), Image.NEAREST).save(O / "p2_abas_zoom.png")
img.resize((768, 672), Image.NEAREST).save(O / "p2_hub_staff_x3.png")
print("zooms:", O / "p2_abas_zoom.png", O / "p2_hub_staff_x3.png", flush=True)

b.load(STATE); b.advance(60); b.speed(100)
print("restaurado; cash:", world.read_cash_k(b), flush=True)
