"""Continua a partir do estado ao vivo (compra de City Hotel ja feita, 1
end_turn ja passado, mesmo processo BizHawk do buy_cityhotel_cont.py):
1) confirma quarter (read_quarter_index)
2) testa r1c1 (ad_campaign) -- ve se recusa "no businesses" ou aceita
3) mais 2 end_turn e reabre facilities -- hoteis podem demorar mais que
   cultural venues (Concert Hall)
"""
import sys

sys.path.insert(0, ".")

from PIL import Image

from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k, read_quarter_index

b = BizHawkBridge()
ex = Executor(b)
g = ex.g

ex._ensure_menu()
q0 = read_quarter_index(b)
cash0 = read_cash_k(b)
print("quarter:", q0, "cash:", cash0)

g.back_to_menu()
g.open_cmd("ad_campaign")
b.advance(120)
shot1 = g.shot("cityhotel_ad_test1")
print("ad_campaign tela 1:", shot1)
ex._ensure_menu()

for i in range(2):
    ok_et, det_et = ex.run({"action": "wait", "params": {}})
    print(f"end_turn extra {i+1}:", ok_et, det_et)

q1 = read_quarter_index(b)
print("quarter apos +2 turnos:", q1)

shot_fac = g.info_screen("facilities", "fac_cityhotel_apos3turnos")
print("facilities apos 3 turnos total:", shot_fac)
ex._ensure_menu()

b.save("../states/_cityhotel_3turnos.state")
print("PARADO")
