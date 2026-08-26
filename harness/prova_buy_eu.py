"""Prova do desbloqueio: com o A340 comprado, a Europa deixa de ser inalcancavel.

Parte de ../states/_buy_entregue.state (A340 entregue, Avail 1).
  neg    negotiate_slots EU11
  wait N end_turn ate o funcionario voltar
  rota   open_route EU11 com aircraft_index=1 (A340)
"""
import sys
import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

b = BizHawkBridge(); ex = Executor(b); g = Game(b, shot_dir="../logs/buy")
fase = sys.argv[1]
b.speed(400)

if fase == "neg":
    b.load("../states/_buy_entregue.state"); b.advance(90)
    ex._ensure_menu()
    ok, det = ex.run({"action": "negotiate_slots", "params": {"city": "EU11"}})
    print("NEG EU11:", ok, "|", det, flush=True)
    b.save("../states/_buy_eu_neg.state")

elif fase == "wait":
    n = int(sys.argv[2])
    for t in range(1, n + 1):
        g.end_turn(); b.advance(120); ex._ensure_menu()
        px, shot = ex._staff_px(f"eu_staff_t{t}")
        print(f"  turno {t}: caixa={world.read_cash_k(b)}K staff={px}px", flush=True)
        b.save("../states/_buy_eu_slot.state")
        if px == 0:
            print("  negociacao encerrada", flush=True); break

elif fase == "rota":
    idx = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    ex._ensure_menu()
    antes = world.read_cash_k(b)
    ok, det = ex.run({"action": "open_route",
                      "params": {"to": "EU11", "aircraft_index": idx}})
    print(f"ROTA EU11 (aircraft_index={idx}): ok={ok}\n  {det}\n"
          f"  caixa {antes}K -> {world.read_cash_k(b)}K", flush=True)
b.speed(100)
