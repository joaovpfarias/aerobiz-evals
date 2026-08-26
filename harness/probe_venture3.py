"""Compra REAL de City Hotel ($72.000K) em CITY, parametro.

Achado no probe2 (17/08): a tela pousa em Concert Hall JA COM (YES NO) armado
depois de exatamente 3 A's a partir do clique no mapa (nao 4 -- o 4o A confirma
sem querer). A partir dai, Right/Left troca o TIPO (preco muda), e SO ENTAO um
A confirma. Preco e a fonte da verdade -- nunca conta so toques.
"""
import sys

sys.path.insert(0, ".")

from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from world import on_map_screen, point_cursor_at_world, read_cash_k, wait_text

CITY = sys.argv[1] if len(sys.argv) > 1 else "NA13"
GUARD = "../states/_venture_guard.state"
TARGET_PRICE_TAG = "72000"  # City Hotel


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

    # EXATAMENTE 3 A's: pousa no tipo default (Concert Hall) com (YES NO) armado,
    # texto ja totalmente digitado -- CONFIRMADO no probe2 (v2_step2).
    for i in range(3):
        wait_text(b)
        b.press("A", hold=5, wait=25)
        b.advance(120)
    shot = g.shot(f"v3_armado_{CITY}")
    print(f"apos 3 A's (deve ser Concert Hall $144000K, YES/NO armado, SEM confirmar): {shot}")

    # cicla tipos com RIGHT ate achar City Hotel (preco $72000K), max 3 (4 tipos, sem wrap)
    tipos_vistos = []
    for i in range(4):
        shot = g.shot(f"v3_tipo{i}_{CITY}")
        tipos_vistos.append(shot)
        print(f"tipo[{i}] shot={shot}")
        b.press("Right", hold=4, wait=20)
        b.advance(90)

    print("Screenshots de todos os tipos vistos (Right x3 a partir de Concert Hall):")
    for s in tipos_vistos:
        print(" ", s)
    print("NADA CONFIRMADO AINDA -- inspecione as imagens antes do proximo passo.")


if __name__ == "__main__":
    main()
