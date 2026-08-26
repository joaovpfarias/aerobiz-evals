"""Testa o tipo DEFAULT oferecido em VARIAS cidades (sem confirmar nada) --
hipotese: o tipo disponivel muda por cidade (mercado/populacao), nao e sempre
Concert Hall."""
import sys

sys.path.insert(0, ".")

from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from world import on_map_screen, point_cursor_at_world, read_cash_k, wait_text

CITIES = sys.argv[1:] or ["NA14", "NA06", "SA01"]
GUARD = "../states/_venture_guard.state"


def default_type(b, ex, g, city):
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
    point_cursor_at_world(b, city, None)
    wait_text(b)
    b.press("A", hold=5, wait=25)
    wait_text(b)
    b.advance(60)
    wait_text(b)
    b.press("A", hold=5, wait=25)
    wait_text(b)
    b.advance(60)
    shot = g.shot(f"v8_default_{city}")
    return shot


def main():
    b = BizHawkBridge()
    ex = Executor(b)
    g = ex.g

    for city in CITIES:
        shot = default_type(b, ex, g, city)
        print(f"{city}: {shot}")


if __name__ == "__main__":
    main()
