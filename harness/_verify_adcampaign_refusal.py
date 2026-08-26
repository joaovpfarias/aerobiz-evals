"""Verifica a recusa de ad_campaign sem venture pronto (savestate limpo)."""
from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k

b = BizHawkBridge()
ex = Executor(b)

b.load("../states/eval_single_2000_lv5.state")
b.advance(60)
cash0 = read_cash_k(b)
print("cash antes:", cash0)

ok, det = ex._do_ad_campaign({})
print("ad_campaign result:", ok, det)

cash1 = read_cash_k(b)
print("cash depois:", cash1, "delta:", cash1 - cash0)
