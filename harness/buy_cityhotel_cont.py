"""Continuacao de buy_cityhotel.py apos o crash em b.saveas (typo, corrigido
para b.save). NAO recarrega savestate -- o emulador ja esta com o City Hotel
comprado em Vancouver (NA01), caixa 1.130.900K, de volta ao menu principal.
"""
import sys

sys.path.insert(0, ".")

from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k

b = BizHawkBridge()
ex = Executor(b)
g = ex.g

ex._ensure_menu()
print("caixa:", read_cash_k(b))

b.save("../states/_cityhotel_comprado.state")
print("savestate: _cityhotel_comprado.state")

shot_fac_depois_imediato = g.info_screen("facilities", "fac_depois_cityhotel_imediato")
print("facilities imediato pos-compra:", shot_fac_depois_imediato)
ex._ensure_menu()

ok_et, det_et = ex.run({"action": "wait", "params": {}})
print("end_turn:", ok_et, det_et)

shot_fac_depois_turno = g.info_screen("facilities", "fac_depois_cityhotel_1turno")
print("facilities apos 1 end_turn:", shot_fac_depois_turno)
ex._ensure_menu()
b.save("../states/_cityhotel_pronto.state")
print("savestate: _cityhotel_pronto.state")

print("PARADO")
