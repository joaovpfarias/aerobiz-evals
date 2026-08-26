"""Correcao: 'wait' (ex.run action) e NO-OP no executor (_do_wait so retorna
True sem fazer nada) -- NAO avanca o trimestre. O jogo so avanca via
g.end_turn() (r1c5, macro dedicada). Recarrega _cityhotel_comprado.state
(City Hotel ja comprado em Vancouver, caixa 1.130.900K, ANTES de qualquer
end_turn) e usa g.end_turn() de verdade, lendo o quarter antes/depois.
"""
import sys

sys.path.insert(0, ".")

from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k, read_quarter_index

STATE = "../states/_cityhotel_comprado.state"

b = BizHawkBridge()
ex = Executor(b)
g = ex.g

b.load(STATE)
b.advance(90)
ex._ensure_menu()

q0 = read_quarter_index(b)
cash0 = read_cash_k(b)
print("ANTES end_turn: quarter", q0, "cash", cash0)

shot0 = g.info_screen("facilities", "rt_facilities_0turnos")
print("facilities 0 turnos:", shot0)
ex._ensure_menu()

for i in range(3):
    ok, det = g.end_turn()
    q = read_quarter_index(b)
    cash = read_cash_k(b)
    print(f"end_turn #{i+1}: ok={ok} det={det} quarter={q} cash={cash}")
    ex._ensure_menu()
    shot = g.info_screen("facilities", f"rt_facilities_{i+1}turnos")
    print(f"facilities apos {i+1} turno(s):", shot)
    ex._ensure_menu()

b.save("../states/_cityhotel_3turnos_real.state")
print("PARADO")
