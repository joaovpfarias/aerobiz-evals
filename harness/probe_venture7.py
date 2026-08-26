"""Replica EXATA da receita que funcionou no probe4 (2 A's com advance(60) cada,
wait_text entre elas) e testa Down/Down+Right com advance CURTO logo em seguida,
pra nao perder a janela antes do auto-avanco do texto para 'Is this OK'."""
import sys

sys.path.insert(0, ".")

from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from world import on_map_screen, point_cursor_at_world, read_cash_k, wait_text

CITY = sys.argv[1] if len(sys.argv) > 1 else "NA13"
GUARD = "../states/_venture_guard.state"

SEQUENCES = [
    ["Right"],
    ["Right", "Right"],
    ["Right", "Right", "Right"],
]


def to_s2(b, ex, g):
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

    for seq in SEQUENCES:
        ex.reset_world_state(routes=[{"from": "NA13", "to": "NA14", "flights": 1}])
        to_s2(b, ex, g)
        for key in seq:
            b.press(key, hold=4, wait=18)
            b.advance(40)
        tag = "_".join(k[0] for k in seq) + "b"
        shot = g.shot(f"v7_{tag}_{CITY}")
        cash_chk = read_cash_k(b)
        print(f"seq={seq!r:20} -> {shot}  cash={cash_chk}K")

    print("PARADO -- inspecione v7_*.png")


if __name__ == "__main__":
    main()
