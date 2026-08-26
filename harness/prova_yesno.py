"""Prova dirigida: a caixa (YES NO) de patrocinio nao paga nada ao ser atravessada.

Parte do savestate de guarda gravado por `probe_demand.py hunt` — o frame exato
em que o jogo pergunta "Rep. of EC ... $372000K is requested. Will you back this
Project?" com o cursor em YES.

Medido antes da correcao (probe_demand.py):
  A     -> 1.133.070K -> 761.070K   (-372.000K)
  B     -> 1.133.070K -> 1.133.070K
Esta prova exige que o caminho de volta do harness se comporte como o B.
"""

import pathlib

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

RAIZ = pathlib.Path(__file__).parent.parent
GUARDA = RAIZ / "states" / "_demand_guard.state"
OUT = RAIZ / "logs" / "etapa1"


def main():
    b = BizHawkBridge(timeout=60)
    g = Game(b)
    ex = Executor(b)
    ex.g = g
    b.speed(400)

    b.load(GUARDA)
    b.advance(60)
    img = Image.open(b.screenshot(OUT / "yesno_antes.png")).convert("RGB")
    sel = world.yesno_prompt(img)
    caixa0 = world.read_cash_k(b)
    print(f"largada: yesno_prompt={sel} caixa={caixa0}K "
          f"menu={world.at_main_menu_img(img)}", flush=True)
    if sel is None:
        print("ABORTA: o savestate de guarda nao esta na caixa de decisao")
        return 1

    ok = ex.dismiss_to_menu()
    img = Image.open(b.screenshot(OUT / "yesno_depois.png")).convert("RGB")
    caixa1 = world.read_cash_k(b)
    print(f"dismiss_to_menu={ok} menu={world.at_main_menu_img(img)} "
          f"caixa={caixa1}K (delta {caixa0 - caixa1}K) "
          f"yesno_prompt={world.yesno_prompt(img)}", flush=True)
    aceite = ok and world.at_main_menu_img(img) and caixa1 == caixa0
    print("PROVA:", "OK — atravessou a caixa de decisao sem pagar" if aceite
          else "FALHOU")
    return 0 if aceite else 1


if __name__ == "__main__":
    raise SystemExit(main())
