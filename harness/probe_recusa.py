"""Por que _ensure_menu nao escapa da tela de RECUSA de rota?

Importa porque pilot.py aborta o turno quando _ensure_menu devolve False, e
escolher um destino sem slots e a acao mais provavel de um modelo nao calibrado.
"""

import pathlib

from PIL import Image

from bridge import BizHawkBridge
from macros import Game
import world

EVAL = pathlib.Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"
OUT = pathlib.Path(__file__).parent.parent / "logs" / "probe12"


def diag(b, g, tag):
    img = Image.open(g.shot(tag)).convert("RGB")
    print(f"    {tag:22s} menu_red={world.menu_red(img):4d} terra={world.land_pixels(img):5d}")
    return img


def main():
    b = BizHawkBridge()
    g = Game(b, shot_dir=OUT)
    b.load(EVAL)
    b.advance(60)
    g.back_to_menu()
    g.open_cmd("new_route")
    world.point_cursor_at(b, "NA14")
    b.press("A", hold=5, wait=25)
    b.advance(150)
    print("  na tela de recusa:")
    diag(b, g, "80_recusa")

    print("  so B (como faz _ensure_menu hoje):")
    for i in range(6):
        b.batch(b.seq_press("B", hold=5, wait=25) + b.seq_advance(90), extra_frames=200)
        img = diag(b, g, f"81_B{i}")
        if world.at_main_menu_img(img):
            print(f"    -> voltou ao menu com {i+1} B")
            return

    print("  B nao resolveu. Testando A (dispensar a mensagem) e depois B:")
    b.batch(b.seq_press("A", hold=5, wait=25) + b.seq_advance(150), extra_frames=250)
    diag(b, g, "82_apos_A")
    for i in range(6):
        b.batch(b.seq_press("B", hold=5, wait=25) + b.seq_advance(90), extra_frames=200)
        img = diag(b, g, f"83_AB{i}")
        if world.at_main_menu_img(img):
            print(f"    -> voltou ao menu com A + {i+1} B")
            return
    print("    -> nem A+B resolveu")


if __name__ == "__main__":
    main()
