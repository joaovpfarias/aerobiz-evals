"""Por que a acao seguinte a uma rota aberta as vezes nao acha o cursor?"""

import pathlib

from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from macros import Game
import world

EVAL = pathlib.Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"
OUT = pathlib.Path(__file__).parent.parent / "logs" / "probe12"


def diag(g, tag):
    img = Image.open(g.shot(tag)).convert("RGB")
    print(f"    {tag:26s} menu_red={world.menu_red(img):4d} terra={world.land_pixels(img):5d}")
    return img


def main():
    b = BizHawkBridge()
    g = Game(b, shot_dir=OUT)
    ex = Executor(b)
    b.load(EVAL)
    b.advance(60)
    g.back_to_menu()
    b.advance(60)

    print("[1] abrindo NA06:", ex.run({"action": "open_route", "params": {"to": "NA06"}})[0])
    diag(g, "90_apos_NA06")

    print("[2] agora NA03, passo a passo:")
    print("   _ensure_menu ->", ex._ensure_menu())
    diag(g, "91_menu_antes_open_cmd")
    g.open_cmd("new_route")
    diag(g, "92_apos_open_cmd")
    b.advance(150)
    diag(g, "93_apos_settle")
    print("   cursor RAM:", world.read_cursor(b))
    for i in range(6):
        antes = world.read_cursor(b)
        b.batch(b.seq_press("Right" if i % 2 == 0 else "Left", hold=1, wait=6) + b.seq_advance(15),
                extra_frames=60)
        print(f"   toque {i}: {antes} -> {world.read_cursor(b)}")
    diag(g, "94_apos_toques")


if __name__ == "__main__":
    main()
