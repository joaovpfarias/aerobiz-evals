import sys
sys.path.insert(0, ".")
from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k

b = BizHawkBridge()
ex = Executor(b)
g = ex.g
b.load("../states/_venture_comprado.state")
b.advance(90)
ex._ensure_menu()
print("cash:", read_cash_k(b))
shot = g.info_screen("facilities", "venture_facilities_apos_compra_real")
print("facilities:", shot)
