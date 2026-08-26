"""Usa press_until_change (espera a tela mudar de verdade, sem corrida) na
fase 'Which business venture will you purchase?' (1a A, ANTES da 2a A), que e
onde o probe4 teve o unico sinal solido de troca de tipo."""
import sys

sys.path.insert(0, ".")

from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from world import on_map_screen, point_cursor_at_world, read_cash_k, wait_text

CITY = sys.argv[1] if len(sys.argv) > 1 else "NA13"
N_RIGHT = int(sys.argv[2]) if len(sys.argv) > 2 else 4
GUARD = "../states/_venture_guard.state"


def main():
    b = BizHawkBridge()
    ex = Executor(b)
    g = ex.g

    b.load(GUARD)
    b.advance(90)
    ex._ensure_menu()
    ex.reset_world_state(routes=[{"from": "NA13", "to": "NA14", "flights": 1}])
    cash0 = read_cash_k(b)

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
    shot = g.shot(f"v9_s1_{CITY}_i0")
    print(f"i=0 (deve ser Concert Hall) -> {shot}")

    for i in range(1, N_RIGHT + 1):
        changed = g.press_until_change("Right", max_presses=3, poll=4, settle=25, threshold=40)
        shot = g.shot(f"v9_s1_{CITY}_i{i}")
        print(f"i={i} changed={changed} -> {shot}")

    cash_chk = read_cash_k(b)
    print(f"cash (deve seguir {cash0}K): {cash_chk}K")
    print("PARADO -- nada confirmado ainda, inspecione v9_*.png")


if __name__ == "__main__":
    main()
