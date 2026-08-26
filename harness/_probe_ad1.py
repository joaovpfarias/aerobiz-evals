"""Probe: passar 1 turno a partir de _venture_comprado.state e checar
Info->facilities para ver se o venture ja conta."""
from bridge import BizHawkBridge
from macros import Game
from world import read_cash_k

b = BizHawkBridge()
g = Game(b)

b.load("../states/_venture_comprado.state")
b.advance(60)
cash0 = read_cash_k(b)
print("cash antes end_turn:", cash0)

ok, det = g.end_turn()
print("end_turn:", ok, det)
cash1 = read_cash_k(b)
print("cash depois end_turn:", cash1)

g.shot("ad1_pos_endturn_menu")
p = g.info_screen("facilities", "ad1_facilities_pos1turno")
print("facilities shot:", p)
