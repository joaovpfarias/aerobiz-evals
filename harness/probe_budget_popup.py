"""Fotografa a tela de orcamentos ANTES e DEPOIS de abrir a popup de ordem.

Motivo: `on_budget_screen` = "existe coluna selecionada", e a coluna e detectada
pelo realce do CABECALHO. Com a popup aberta esse realce provavelmente some, e o
guard que exige `on_budget_screen` antes do A de confirmacao passa a recusar o
proprio passo que deveria proteger. Antes de mexer no guard, ver a tela.
"""

import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import world  # noqa: E402
from bridge import BizHawkBridge  # noqa: E402
from macros import Game  # noqa: E402

OUT = pathlib.Path(__file__).parent.parent / "logs" / "calib_budget_19ago"
STATES = pathlib.Path(__file__).parent.parent / "states"

b = BizHawkBridge()
g = Game(b, shot_dir=OUT)
b.load(str((STATES / "eval_single_2000_lv5.state").resolve()))
b.advance(120)
g.back_to_menu()
g.open_cmd("budgets")
b.advance(200)

img = Image.open(g.shot("popup_0_base")).convert("RGB")
print("base:      col=%s  on_budget=%s  orders=%s"
      % (world.read_budget_col(img), world.on_budget_screen(img), world.read_budget_orders(img)), flush=True)

b.press("A", hold=5, wait=25)
b.advance(200)
img = Image.open(g.shot("popup_1_aberta")).convert("RGB")
print("popup:     col=%s  on_budget=%s  orders=%s"
      % (world.read_budget_col(img), world.on_budget_screen(img), world.read_budget_orders(img)), flush=True)

b.press("Down", hold=3, wait=14)
b.advance(60)
img = Image.open(g.shot("popup_2_apos_down")).convert("RGB")
print("apos Down: col=%s  on_budget=%s  orders=%s"
      % (world.read_budget_col(img), world.on_budget_screen(img), world.read_budget_orders(img)), flush=True)
print("shots em", OUT, flush=True)
