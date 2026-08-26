"""A na cidade do mapa de NEGOCIACAO seleciona? Testa NA (conhecida) e EU."""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/negeu"); O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge(); ex = Executor(b); g = Game(b)
ALVO = sys.argv[1] if len(sys.argv) > 1 else "NA13"


def snap(tag):
    img = Image.open(b.screenshot(O / f"{tag}.png")).convert("RGB")
    print(f"  {tag}: mapa={world.on_map_screen(img)} regiao={world.detect_region(img)} "
          f"ram={world.read_cursor(b)}", flush=True)
    return img


b.load("../states/eval_single_2000_lv5.state"); b.advance(90); b.speed(400)
ex._ensure_menu()
g.open_cmd("negotiate")
for i in range(3):
    b.batch(b.seq_press("A", hold=5, wait=25) + b.seq_advance(150), extra_frames=400)
snap("30_mapa")

x, y, reg, _ = world.WORLD_CITIES[ALVO]
if reg != 0:
    atual, ok = world.switch_to_region(b, reg, None)
    print("  regiao apos R:", atual, ok, flush=True)
# escrita direta, sem activate_cursor: o cursor ja se mexeu com d-pad neste fluxo
b.batch(b.seq_write(world.CURSOR_X, x) + b.seq_write(world.CURSOR_Y, y) + b.seq_advance(20))
snap("31_cursor")
b.press("A", hold=5, wait=25); b.advance(200); world.wait_text(b)
snap("32_apos_A")
b.press("A", hold=5, wait=25); b.advance(200); world.wait_text(b)
snap("33_apos_A")
b.speed(100)
