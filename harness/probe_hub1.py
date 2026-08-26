"""PROBE 1 (17/08): o hub da America do Sul de `probe_hub_open_sa.state` ja esta
ATIVO ou ainda em negociacao?

Teste decisivo: por o mapa do MENU PRINCIPAL na regiao 1 e invocar r0c0.
  - "The new route will depart from Havana..."  -> hub ATIVO
  - "We don't have a regional hub here."        -> hub PENDENTE

Sai SEMPRE por b.load() (a tela de recusa e a tela de cursor morto documentada).
Tambem mede: detect_region no mapa do MENU PRINCIPAL (a assinatura REGION_LAND
foi calibrada no mapa da tela de rota, nao aqui) — se ela nao ler, o
switch_to_region do open_hub anda as cegas.
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/hub2"); O.mkdir(parents=True, exist_ok=True)
STATE = sys.argv[1] if len(sys.argv) > 1 else "../states/probe_hub_open_sa.state"

b = BizHawkBridge()
ex = Executor(b)
g = Game(b, shot_dir=O)
ex.g = g
b.load(STATE); b.advance(90); b.speed(400)

print("cash:", world.read_cash_k(b), flush=True)
img = Image.open(b.screenshot(O / "p1_menu0.png")).convert("RGB")
print("menu?", world.at_main_menu_img(img),
      "| land:", world.land_pixels(img),
      "| detect_region:", world.detect_region(img),
      "| livres:", world.free_staff_menu(img), flush=True)

# --- troca a regiao do MENU PRINCIPAL para 1 (America do Sul) ---
reg, verif = world.switch_to_region(b, 1, None)
img = Image.open(b.screenshot(O / "p1_menu_reg1.png")).convert("RGB")
print(f"switch_to_region -> {reg} (verificado={verif}) | land={world.land_pixels(img)}", flush=True)

if reg != 1:
    print("ABORTA: nao consegui por o menu na regiao 1", flush=True)
    b.load(STATE); b.speed(100); sys.exit(1)

# --- invoca r0c0 (nova rota) com o mapa na regiao 1 ---
g.open_cmd("new_route")
world.wait_text(b)
b.advance(150)
shot = b.screenshot(O / "p1_r0c0_regiao1.png")
print("tela apos r0c0:", shot, flush=True)
img = Image.open(shot).convert("RGB")
print("on_map_screen:", world.on_map_screen(img), "| land:", world.land_pixels(img), flush=True)

# recorte do texto ampliado para leitura a olho
img.crop((0, 145, 256, 200)).resize((768, 165), Image.NEAREST).save(O / "p1_texto.png")
print("texto ampliado:", O / "p1_texto.png", flush=True)

b.load(STATE); b.advance(60); b.speed(100)
print("estado restaurado; cash:", world.read_cash_k(b), flush=True)
