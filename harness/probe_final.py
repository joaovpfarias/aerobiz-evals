"""Prova final da tarefa 1.3: duas rotas abertas em sequencia, com evidencia."""

import pathlib

from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from macros import Game
import world

EVAL = pathlib.Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"
OUT = pathlib.Path(__file__).parent.parent / "logs" / "probe12"


def main():
    b = BizHawkBridge()
    g = Game(b, shot_dir=OUT)
    ex = Executor(b)
    b.load(EVAL)
    b.advance(60)

    g.back_to_menu()
    b.advance(60)
    img0 = Image.open(g.shot("70_menu_antes")).convert("RGB")
    print(f"inicio: caixa {world.read_cash_k(b)}K, terra={world.land_pixels(img0)}")

    # NA14 = Philadelphia: nao temos slots -> o jogo RECUSA (aceite literal da tarefa)
    print("\n[aceite literal] open_route NA14:")
    print("  ", ex.run({"action": "open_route", "params": {"to": "NA14", "aircraft_index": 0}}))

    for dest in ("NA06", "NA03", "NA02", "NA05"):
        c0 = world.read_cash_k(b)
        ok, det = ex.run({"action": "open_route", "params": {"to": dest, "aircraft_index": 0}})
        c1 = world.read_cash_k(b)
        g.back_to_menu()
        b.advance(90)
        g.shot(f"71_menu_depois_{dest}")
        print(f"\n[{dest}] ok={ok}\n  {det}\n  caixa {c0}K -> {c1}K")

    p = g.info_screen("map", "72_rotas_final")
    print("\ntabela de rotas final:", p)
    print("caixa final:", world.read_cash_k(b), "K")


if __name__ == "__main__":
    main()
