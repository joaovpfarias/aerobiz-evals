from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from macros import Game
import world

O = Path("../logs/edit2")
O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge()
g = Game(b, shot_dir=O)

def snap(tag):
    p = b.screenshot(O / f"{tag}.png")
    print(f"  {tag}: caixa={world.read_cash_k(b)}K", flush=True)
    return p

b.load("../states/_edit_2rotas.state")
b.advance(90)
b.speed(400)
from executor import Executor
ex = Executor(b)
ex._ensure_menu()
g.open_cmd("route_edit")
b.advance(150)
b.press("A", hold=5, wait=25)
b.advance(80)
# now on tab bar, at Model. Move Right x2 to reach Flts
for i in range(2):
    b.press("Right", hold=3, wait=14)
    b.advance(40)
snap("10_flts_tab")
b.press("A", hold=5, wait=25)
b.advance(80)
snap("11_flts_activated")

for i in range(1, 3):
    b.press("Right", hold=3, wait=14)
    b.advance(60)
    snap(f"12_flts_right{i}")
