from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from macros import Game
import world

O = Path("../logs/edit2")
b = BizHawkBridge()
g = Game(b, shot_dir=O)

def snap(tag):
    p = b.screenshot(O / f"{tag}.png")
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
for i in range(2):
    b.press("Right", hold=3, wait=14)
    b.advance(40)
b.press("A", hold=5, wait=25)
b.advance(80)
for i in range(1, 6):
    b.press("Right", hold=5, wait=30)
    b.advance(80)
    snap(f"20_flts_step{i}")
