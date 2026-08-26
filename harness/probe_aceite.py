"""Criterio de aceite da tarefa 1.3: PROVAR que uma rota abre.

Verifica os tres sinais independentes: retorno do Executor, caixa (RAM) e a
rota DESENHADA no mapa (diff de pixels no segmento entre as duas cidades).
"""

import pathlib

from PIL import Image, ImageChops

from bridge import BizHawkBridge
from executor import Executor
from macros import Game
import world

EVAL = pathlib.Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"
OUT = pathlib.Path(__file__).parent.parent / "logs" / "probe12"


def mapa(b, g, nome):
    """Screenshot do MENU PRINCIPAL, que e onde as rotas aparecem desenhadas.

    Nao usar Info->map: assim que existe pelo menos uma rota, esse item passa a
    mostrar a TABELA de rotas em vez do mapa, e o diff de pixels vira 'a tela
    inteira mudou' — numero que parece evidencia de rota desenhada e nao e.
    """
    g.back_to_menu()
    b.advance(90)
    return Image.open(g.shot(nome)).convert("RGB")


def rota_desenhada(antes, depois, a, c):
    """Ha pixels novos no corredor reto entre as duas cidades?"""
    ax, ay = world.city_xy(a)
    cx, cy = world.city_xy(c)
    d = ImageChops.difference(antes, depois)
    box = d.crop((0, 0, 256, 140)).getbbox()
    novos = 0
    px = d.load()
    for t in range(1, 20):
        x = round(ax + (cx - ax) * t / 20.0)
        y = round(ay + (cy - ay) * t / 20.0)
        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):
                if sum(px[x + dx, y + dy]) > 60:
                    novos += 1
    return box, novos


def main():
    b = BizHawkBridge()
    g = Game(b)
    ex = Executor(b)

    for dest in ("NA14", "NA06"):
        print(f"\n===== open_route -> {dest} =====")
        b.load(EVAL)
        b.advance(60)
        antes_img = mapa(b, g, f"60_mapa_antes_{dest}")
        caixa0 = world.read_cash_k(b)
        ok, det = ex.run({"action": "open_route", "params": {"to": dest, "aircraft_index": 0}})
        caixa1 = world.read_cash_k(b)
        depois_img = mapa(b, g, f"61_mapa_depois_{dest}")
        box, novos = rota_desenhada(antes_img, depois_img, world.HOME, dest)
        print(f"  Executor -> ({ok}, {det!r})")
        print(f"  caixa: {caixa0}K -> {caixa1}K  (delta {caixa1 - caixa0:+d}K)")
        print(f"  diff do mapa: bbox={box}  pixels novos no corredor Washington-{dest}: {novos}")
        print(f"  VEREDITO: {'ROTA ABERTA' if ok and caixa1 < caixa0 and novos > 0 else 'nao abriu'}")


if __name__ == "__main__":
    main()
