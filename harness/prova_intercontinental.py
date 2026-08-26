"""PROVA do criterio de aceite: agir FORA da America do Norte pelo EXECUTOR.

Fases (cada uma salva savestate para poder retomar sem repetir a espera):
  a  negotiate_slots numa cidade da Europa, pelo caminho que o pilot chama
  w  end_turn ate a negociacao concluir (sinal: painel Info->staff volta a 0px)
  d  le a tela de detalhe da cidade (quantos slots temos LA) — e a NA13 de
     referencia, para saber qual das 4 colunas e a nossa
  b  open_route NA13 -> cidade europeia, com o aviao de longo alcance

Uso: python prova_intercontinental.py <fase> [cidade]
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/prova_ic")
O.mkdir(parents=True, exist_ok=True)
EVAL = "../states/eval_single_2000_lv5.state"
S_NEG = "../states/prova_ic_neg.state"       # logo apos disparar a negociacao
S_SLOT = "../states/prova_ic_slots.state"    # com a negociacao ja concluida

b = BizHawkBridge()
ex = Executor(b)
g = Game(b, shot_dir=O)
fase = sys.argv[1]
ALVO = sys.argv[2] if len(sys.argv) > 2 else "EU11"


def snap(tag):
    p = b.screenshot(O / f"{tag}.png")
    img = Image.open(p).convert("RGB")
    print(f"  {tag}: caixa={world.read_cash_k(b)}K regiao={world.detect_region(img)} "
          f"menu={world.at_main_menu_img(img)}", flush=True)
    return p


if fase == "a":
    b.load(EVAL)
    b.advance(90)
    b.speed(400)
    ex._ensure_menu()
    print("caixa inicial:", world.read_cash_k(b), "K", flush=True)
    ok, det = ex.run({"action": "negotiate_slots", "params": {"city": ALVO}})
    print(f"NEGOCIACAO {ALVO}: ok={ok}\n  {det}", flush=True)
    snap("a_final")
    if ok:
        b.save(S_NEG)
        print("savestate:", S_NEG, flush=True)
    b.speed(100)

elif fase == "w":
    b.speed(400)
    for t in range(1, 5):
        antes = world.read_cash_k(b)
        g.end_turn()
        b.advance(120)
        ex._ensure_menu()
        px, shot = ex._staff_px(f"w_staff_t{t}")
        print(f"  turno {t}: caixa {antes}K -> {world.read_cash_k(b)}K | staff={px}px ({shot})",
              flush=True)
        b.save(S_SLOT)
        if px == 0:
            print("  funcionario voltou a base — negociacao encerrada", flush=True)
            break
    b.speed(100)

elif fase == "d":
    # Tela de detalhe da cidade: entra pelo comando de negociacao (mesma tela de
    # mapa), poe o cursor na cidade e aperta A UMA vez. Sai recarregando o
    # savestate — nao ha o que preservar numa leitura.
    b.speed(400)
    b.save("../states/_leitura.state")
    for cid in sys.argv[2:] or ["NA13", ALVO]:
        b.load("../states/_leitura.state")
        b.advance(60)
        ex._ensure_menu()
        g.open_cmd("negotiate")
        seq = []
        for _ in range(2):
            seq += b.seq_press("A", hold=5, wait=25) + b.seq_advance(150)
        b.batch(seq, extra_frames=500)
        reg, pos, verif = world.point_cursor_at_world(b, cid, None)
        b.press("A", hold=5, wait=25)
        b.advance(150)
        world.wait_text(b)
        print(f"  {cid}: regiao={reg} pos={pos} verificada={verif}", flush=True)
        snap(f"d_detalhe_{cid}")
    b.load("../states/_leitura.state")
    b.advance(60)
    ex._ensure_menu()
    b.speed(100)

elif fase == "b":
    b.speed(400)
    ex._ensure_menu()
    idx = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    print("caixa antes:", world.read_cash_k(b), "K", flush=True)
    ok, det = ex.run({"action": "open_route",
                      "params": {"to": ALVO, "aircraft_index": idx,
                                 "flights_week": 1, "fare_level": "mid"}})
    print(f"ROTA NA13->{ALVO} (aviao idx {idx}): ok={ok}\n  {det}", flush=True)
    snap("b_final")
    b.speed(100)

else:
    print(__doc__)
