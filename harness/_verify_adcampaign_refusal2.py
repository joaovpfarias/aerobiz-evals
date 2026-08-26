"""Verifica a recusa de ad_campaign via API publica Executor.run (salva GUARD
antes, entao _restore_guard() volta ao estado CORRETO, nao a um guard velho
de outra sessao -- ver achado 18/08 sobre chamar _do_ad_campaign cru direto,
sem passar por Executor.run, em _verify_adcampaign_refusal.py)."""
from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k

b = BizHawkBridge()
ex = Executor(b)

b.load("../states/eval_single_2000_lv5.state")
b.advance(60)
cash0 = read_cash_k(b)
print("cash antes:", cash0)

ok, det = ex.run({"action": "ad_campaign", "params": {}})
print("ad_campaign result:", ok, det)

cash1 = read_cash_k(b)
print("cash depois:", cash1, "delta:", cash1 - cash0)
