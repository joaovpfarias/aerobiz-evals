"""Verificacao ao vivo de _do_ad_campaign (ETAPA 10-Marketing).
1) A partir de _venture_pronto.state (venture pronto): espera sucesso, -1800K.
2) Guarda estado antes; roda a macro; imprime resultado; salva screenshot final.
"""
from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k

b = BizHawkBridge()
ex = Executor(b)

b.load("../states/_venture_pronto.state")
b.advance(60)
cash0 = read_cash_k(b)
print("cash antes:", cash0)

ok, det = ex._do_ad_campaign({})
print("ad_campaign result:", ok, det)

cash1 = read_cash_k(b)
print("cash depois:", cash1, "delta:", cash1 - cash0)
