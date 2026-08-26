"""Retry cuidadoso: passo a passo, 1 tecla por vez, screenshot apos cada uma,
para achar exatamente onde o seletor de tipo (Left/Right, CALIBRATION antiga)
fica e comprar City Hotel ($72.000K) de fato.

Parte de states/_venture_guard.state (SALVO ANTES da compra de Concert Hall).
"""
import sys

sys.path.insert(0, ".")

from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from world import on_map_screen, point_cursor_at_world, read_cash_k, wait_text

CITY = sys.argv[1] if len(sys.argv) > 1 else "NA13"
GUARD = "../states/_venture_guard.state"


def main():
    b = BizHawkBridge()
    ex = Executor(b)
    g = ex.g

    b.load(GUARD)
    b.advance(90)
    assert ex._ensure_menu()
    ex.reset_world_state(routes=[{"from": "NA13", "to": "NA14", "flights": 1}])
    cash0 = read_cash_k(b)
    livres0 = ex._menu_free_staff()
    print(f"cash={cash0}K livres={livres0}")

    g.open_cmd("buy_sell")
    wait_text(b)
    ok_sel, celula, det_sel = ex._pick_free_staff()
    print("pick_staff:", ok_sel, celula, det_sel)

    for _ in range(5):
        wait_text(b)
        b.press("A", hold=5, wait=25)
        b.advance(90)
        if on_map_screen(Image.open(b.screenshot()).convert("RGB")):
            break

    reg, pos, verif = point_cursor_at_world(b, CITY, None)
    print("cursor:", reg, pos, verif)
    shot0 = g.shot(f"v2_before_pick_{CITY}")
    print("antes do A de selecao da cidade:", shot0)

    # 1 A DE CADA VEZ a partir daqui, com screenshot e texto sempre
    for i in range(6):
        wait_text(b)
        b.press("A", hold=5, wait=25)
        b.advance(120)
        shot = g.shot(f"v2_step{i}_{CITY}")
        img = Image.open(b.screenshot()).convert("RGB")
        om = on_map_screen(img)
        print(f"apos A#{i}: on_map={om} shot={shot}")
        if not om:
            break

    print("PARADO para inspecao visual (nada mais sera apertado).")


if __name__ == "__main__":
    main()
