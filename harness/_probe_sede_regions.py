"""ETAPA 5: mede o mapa da sede — entra na regiao e testa L/R/Left/Right."""
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import world  # noqa: E402
import locate  # noqa: E402
from bridge import BizHawkBridge  # noqa: E402

ROOT = pathlib.Path(__file__).parent.parent
SHOTS = ROOT / "logs" / "etapa5_sede"
STATE = str(ROOT / "states" / "eval_players_screen.state")


def desc(b, name):
    p = b.screenshot(SHOTS / f"{name}.png")
    img = Image.open(p).convert("RGB")
    lp = world.land_pixels(img)
    reg = world.detect_region(img)
    dots = locate.find_dots(img, locate.GREEN) + locate.find_dots(img, locate.BLUE)
    print(f"{name}: land={lp} detect={reg} dots={len(dots)}", flush=True)
    return len(dots)


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    b = BizHawkBridge()
    b.load(STATE)
    b.advance(60)
    b.speed(400)
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(300), extra_frames=450)
    desc(b, "s0_region_menu")
    for i in range(4):
        b.press("A", hold=6, wait=40)
        b.advance(400)
        n = desc(b, f"s1_afterA{i}")
        if n:
            break
    for btn in ("R", "L", "Right", "Left"):
        for k in range(2):
            b.batch(b.seq_press(btn, hold=4, wait=25) + b.seq_advance(250), extra_frames=350)
            desc(b, f"s2_{btn}{k}")


main()
