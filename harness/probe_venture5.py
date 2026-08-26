"""Confirma grid 2x2 do seletor de tipo (achado no probe4: Right no estagio de
2 A's ja muda Concert Hall -> Grand Hotel). Testa Down a partir do mesmo
estagio para achar City Hotel ($72000K), depois COMPRA de fato."""
import sys

sys.path.insert(0, ".")

from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from world import on_map_screen, point_cursor_at_world, read_cash_k, wait_text

CITY = sys.argv[1] if len(sys.argv) > 1 else "NA13"
GUARD = "../states/_venture_guard.state"
DO_BUY = "--buy" in sys.argv


def to_selector(b, ex, g):
    g.open_cmd("buy_sell")
    wait_text(b)
    ex._pick_free_staff()
    for _ in range(5):
        wait_text(b)
        b.press("A", hold=5, wait=25)
        b.advance(90)
        if on_map_screen(Image.open(b.screenshot()).convert("RGB")):
            break
    point_cursor_at_world(b, CITY, None)
    wait_text(b)
    b.press("A", hold=5, wait=25)
    wait_text(b)
    b.advance(60)
    wait_text(b)
    b.press("A", hold=5, wait=25)
    wait_text(b)
    b.advance(60)


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

    to_selector(b, ex, g)
    g.shot(f"v5_grid00_{CITY}")
    print("grid (0,0) deve ser Concert Hall")

    b.press("Down", hold=4, wait=20)
    b.advance(90)
    shot_10 = g.shot(f"v5_grid10_{CITY}")
    print(f"apos Down: {shot_10}")

    b.press("Down", hold=4, wait=20)
    b.advance(90)
    shot_10b = g.shot(f"v5_grid10b_{CITY}")
    print(f"apos 2o Down (deve ser igual, sem wrap): {shot_10b}")

    cash_mid = read_cash_k(b)
    print(f"cash aqui ainda deve ser {cash0}K: {cash_mid}K")

    if not DO_BUY:
        print("--buy nao passado: PARANDO SEM COMPRAR. Rode de novo com --buy para confirmar.")
        return

    # CONFIRMA: espera-se estar em (1,0) = City Hotel $72000K aqui.
    print("CONFIRMANDO COMPRA (2 A's, padrao _step)")
    for etapa in ("confirmacao 1", "confirmacao 2"):
        wait_text(b)
        b.press("A", hold=5, wait=25)
        wait_text(b)
        b.advance(90)
        print(f"  {etapa} ok")
    ex._ensure_menu()
    cash1 = read_cash_k(b)
    livres1 = ex._menu_free_staff()
    print(f"cash: {cash0}K -> {cash1}K ({cash1 - cash0:+d}K)")
    print(f"funcionarios livres: {livres0} -> {livres1}")
    b.save("../states/_venture_cityhotel.state")
    print("salvo em ../states/_venture_cityhotel.state")


if __name__ == "__main__":
    main()
