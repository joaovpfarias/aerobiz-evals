"""A partir de _cityhotel_3turnos_real.state (City Hotel comprado + 3
end_turn REAIS ja passados, facilities ainda x0 x0 x0), testa r1c1
(ad_campaign): recusa "no businesses" ou aceita? Segundo oraculo
independente da Cultural Facilities screen.
"""
import sys

sys.path.insert(0, ".")

from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k

STATE = "../states/_cityhotel_3turnos_real.state"

b = BizHawkBridge()
ex = Executor(b)
g = ex.g

b.load(STATE)
b.advance(90)
ex._ensure_menu()

print("cash:", read_cash_k(b))
g.back_to_menu()
g.open_cmd("ad_campaign")
b.advance(150)
shot = g.shot("cityhotel_ad_apos3turnos")
print("ad_campaign apos 3 turnos reais:", shot)
ex._ensure_menu()
print("PARADO")
