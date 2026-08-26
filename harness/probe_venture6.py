"""Testa sequencias de Left/Right isoladas, cada uma a partir de um reload
FRESCO do guard (para nao acumular frames que disparem o auto-avanco do texto
para a tela de confirmacao). Objetivo: achar o caminho ate City Hotel
($72000K) e Commuter Airline ($576000K) a partir de Concert Hall (0,0).
"""
import sys

sys.path.insert(0, ".")

from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from world import on_map_screen, point_cursor_at_world, read_cash_k, wait_text

CITY = sys.argv[1] if len(sys.argv) > 1 else "NA13"
GUARD = "../states/_venture_guard.state"

SEQUENCES = [
    [],
    ["Right"],
    ["Right", "Right"],
    ["Left"],
    ["Left", "Left"],
    ["Left", "Right"],
    ["Right", "Left"],
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
    b.advance(45)
    wait_text(b)
    b.press("A", hold=5, wait=25)
    wait_text(b)
    b.advance(45)


def main():
    b = BizHawkBridge()
    ex = Executor(b)
    g = ex.g

    for seq in SEQUENCES:
        ex.reset_world_state(routes=[{"from": "NA13", "to": "NA14", "flights": 1}])
        to_s2(b, ex, g)
        for key in seq:
            b.press(key, hold=4, wait=18)
            b.advance(35)  # minimo, so o suficiente pro sprite redesenhar
        tag = "start" if not seq else "_".join(k[0] for k in seq)
        shot = g.shot(f"v6_{tag}_{CITY}")
        print(f"seq={seq!r:30} -> {shot}")

    print("PARADO -- inspecione as imagens v6_*.png (nada foi confirmado, cash intocado).")


if __name__ == "__main__":
    main()
