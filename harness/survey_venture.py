"""Survey de catalogo de business venture SEM gastar caixa: abre a tela de
tipo, cicla Right lendo hash, tira screenshot de cada tipo, e sai com B
ANTES do YES/NO. Verifica que B nao debita caixa (testado na 1a cidade).

Uso: python survey_venture.py NA01 NA04 NA07 ...
"""
import sys

sys.path.insert(0, ".")

from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from world import on_map_screen, point_cursor_at_world, read_cash_k, venture_type_hash, wait_text

GUARD = "../states/_venture_guard.state"


def open_type_screen(b, ex, g, city):
    b.load(GUARD)
    b.advance(90)
    ex._ensure_menu()
    g.open_cmd("buy_sell")
    wait_text(b)
    ex._pick_free_staff()
    for _ in range(5):
        wait_text(b)
        b.press("A", hold=5, wait=25)
        b.advance(90)
        if on_map_screen(Image.open(b.screenshot()).convert("RGB")):
            break
    reg, pos, verif = point_cursor_at_world(b, city, None)
    wait_text(b)
    b.press("A", hold=5, wait=25)
    wait_text(b)
    b.advance(60)


def survey_city(b, ex, g, city, test_b_abort=False):
    caixa_antes = read_cash_k(b)
    open_type_screen(b, ex, g, city)
    shots = []
    hash_atual = venture_type_hash(Image.open(b.screenshot()).convert("RGB"))
    shots.append(g.shot(f"survey_{city}_t0"))
    for i in range(1, 5):
        mudou = False
        for _tent in range(3):
            b.press("Right", hold=4, wait=18)
            b.advance(60)
            novo = venture_type_hash(Image.open(b.screenshot()).convert("RGB"))
            if novo != hash_atual:
                hash_atual = novo
                mudou = True
                break
        if not mudou:
            break
        shots.append(g.shot(f"survey_{city}_t{i}"))
    n_tipos = len(shots)
    if test_b_abort:
        b.press("B", hold=5, wait=25)
        b.advance(60)
        caixa_pos_b = read_cash_k(b)
        print(f"{city}: B-abort test caixa {caixa_antes} -> {caixa_pos_b} "
              f"(delta={caixa_pos_b-caixa_antes if caixa_pos_b and caixa_antes else 'NA'})")
    print(f"{city}: {n_tipos} tipo(s), shots={shots}")
    return n_tipos, shots


def main():
    cities = sys.argv[1:] or ["NA01", "NA04", "NA07", "NA08", "NA09", "NA11", "NA12", "NA15", "NA16"]
    b = BizHawkBridge()
    ex = Executor(b)
    g = ex.g
    for i, city in enumerate(cities):
        survey_city(b, ex, g, city, test_b_abort=(i == 0))
    print("caixa final:", read_cash_k(b))
    print("PARADO")


if __name__ == "__main__":
    main()
