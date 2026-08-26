"""CADEIA INTERCONTINENTAL: negociar slot na Europa -> esperar -> abrir a rota.

(a) negotiate_slots numa cidade fora da America do Norte, com efeito verificado
    na tela Info->staff;
(b) open_route para essa cidade DEPOIS que a negociacao concluir (o jogo recusa
    antes — isso tambem e medido aqui, de proposito).
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/cadeia"); O.mkdir(parents=True, exist_ok=True)
POS_NEG = "../states/eval_neg_brussels.state"
ALVO = "EU11"
b = BizHawkBridge(); ex = Executor(b); g = Game(b)


def staff_px(tag):
    px, shot = ex._staff_px(f"../cadeia/{tag}")
    return px


def slots_europa(tag):
    """Slots que possuimos na Europa, lidos do mapa do menu principal."""
    img = Image.open(b.screenshot(O / f"{tag}.png")).convert("RGB")
    reg = world.detect_region(img)
    cur = world.read_cursor(b)
    if reg is None:
        return reg, None
    return reg, world.cities_with_slots(img, cursor=cur, region=reg)


def fase_a():
    b.load("../states/eval_single_2000_lv5.state"); b.advance(90); b.speed(400)
    ex._ensure_menu()
    ok, det = ex.run({"action": "negotiate_slots", "params": {"city": ALVO}})
    print(f"(a) negotiate_slots {ALVO} -> {ok}: {det}", flush=True)
    b.save(POS_NEG)
    ok2, det2 = ex.run({"action": "open_route", "params": {"to": ALVO, "aircraft_index": 1}})
    print(f"(b-antes) open_route {ALVO} SEM slot -> {ok2}: {det2}", flush=True)
    b.load(POS_NEG); b.advance(60)


def fase_b(turnos=3):
    b.load(POS_NEG); b.advance(90); b.speed(400)
    ex._ensure_menu()
    for t in range(1, turnos + 1):
        antes = world.read_cash_k(b)
        g.end_turn()
        b.advance(120)
        ex._ensure_menu()
        px = staff_px(f"staff_t{t}")
        reg, slots = slots_europa(f"mapa_t{t}")
        print(f"  turno {t}: caixa {antes}K -> {world.read_cash_k(b)}K | painel staff {px}px | "
              f"mapa regiao={reg} slots={slots}", flush=True)
        if px == 0:
            print("  negociacao CONCLUIDA (funcionario voltou a base)", flush=True)
            break
    b.save("../states/eval_pos_neg_concluida.state")
    ok, det = ex.run({"action": "open_route", "params": {"to": ALVO, "aircraft_index": 1}})
    print(f"(b) open_route {ALVO} apos a negociacao -> {ok}: {det}", flush=True)
    b.speed(100)


if __name__ == "__main__":
    fase = sys.argv[1] if len(sys.argv) > 1 else "ab"
    if "a" in fase:
        fase_a()
    if "b" in fase:
        fase_b(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
