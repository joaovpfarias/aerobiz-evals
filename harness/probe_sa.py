from pathlib import Path
from PIL import Image
from bridge import BizHawkBridge
from macros import Game
import world

O = Path("../logs/edit_sa")
O.mkdir(parents=True, exist_ok=True)
b = BizHawkBridge()
g = Game(b, shot_dir=O)

def snap(tag, big=True):
    p = b.screenshot(O / f"{tag}.png")
    if big:
        Image.open(p).convert("RGB").resize((768,672)).save(O / f"{tag}_big.png")
    print(f"  {tag}: caixa={world.read_cash_k(b)}K", flush=True)
    return p

b.load("../states/probe_hub_open_sa.state")
b.advance(90)
b.speed(400)
from executor import Executor
ex = Executor(b)
ex._ensure_menu()
snap("00_menu")
g.open_cmd("route_edit")
b.advance(150)
snap("01_route_summary")
