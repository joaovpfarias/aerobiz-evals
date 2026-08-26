"""Testa Left (retrocesso) e Up a partir do indice 0 (Concert Hall) na fase
'Which business venture' -- ve se ha wrap ou um 4o item por outro eixo."""
import sys

sys.path.insert(0, ".")

from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from world import on_map_screen, point_cursor_at_world, read_cash_k, wait_text

CITY = sys.argv[1] if len(sys.argv) > 1 else "NA13"
GUARD = "../states/_venture_guard.state"


def to_i0(b, ex, g):
    b.load(GUARD)
    b.advance(90)
    ex._ensure_menu()
    ex.reset_world_state(routes=[{"from": "NA13", "to": "NA14", "flights": 1}])
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


def main():
    b = BizHawkBridge()
    ex = Executor(b)
    g = ex.g

    to_i0(b, ex, g)
    for i in range(1, 4):
        g.press_until_change("Left", max_presses=3, poll=4, settle=25, threshold=40)
        shot = g.shot(f"v10_left_{CITY}_i{i}")
        print(f"LEFT i={i} -> {shot}")

    to_i0(b, ex, g)
    for i in range(1, 4):
        g.press_until_change("Up", max_presses=3, poll=4, settle=25, threshold=40)
        shot = g.shot(f"v10_up_{CITY}_i{i}")
        print(f"UP i={i} -> {shot}")

    print("cash:", read_cash_k(b))
    print("PARADO")


if __name__ == "__main__":
    main()
