"""Onde de fato o tipo (tipo/preco) pode ser trocado? Testa Right em CADA
estagio (apos 1 A, apos 2 A's) antes do 3o A armar o (YES NO)."""
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
    print(f"cash={cash0}K")

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

    # 1o A: "Which business venture will you purchase?"
    wait_text(b)
    b.press("A", hold=5, wait=25)
    wait_text(b)  # espera terminar de digitar
    b.advance(60)
    g.shot(f"v4_s1_estavel_{CITY}")
    print("apos 1 A (estavel): tentando Right aqui")
    b.press("Right", hold=4, wait=20)
    b.advance(90)
    g.shot(f"v4_s1_apos_right_{CITY}")

    # 2o A: "Concert Hall $144000K / You must negotiate..."
    wait_text(b)
    b.press("A", hold=5, wait=25)
    wait_text(b)
    b.advance(60)
    g.shot(f"v4_s2_estavel_{CITY}")
    print("apos 2 A (estavel): tentando Right aqui")
    b.press("Right", hold=4, wait=20)
    b.advance(90)
    g.shot(f"v4_s2_apos_right_{CITY}")
    b.press("Right", hold=4, wait=20)
    b.advance(90)
    g.shot(f"v4_s2_apos_right2_{CITY}")

    cash_check = read_cash_k(b)
    print(f"cash apos tudo isso (deve seguir {cash0}K se nada foi confirmado): {cash_check}K")
    print("PARADO -- nada confirmado, inspecione as imagens.")


if __name__ == "__main__":
    main()
