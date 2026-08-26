"""ETAPA 5-Venture, retomada 18/08: compra REAL de 1 City Hotel em Vancouver
(NA01), o tipo mais barato encontrado no survey que de fato se chama "City
Hotel" (survey_venture.py achou $54.000K, NAO $72.000K como a tabela antiga
supunha). Verifica: (1) caixa cai exatamente o preco mostrado, (2)
Info->facilities antes/depois de 1 end_turn.

Parte de states/_venture_guard.state (limpo, cash 1.184.900K, sem compras).
"""
import sys

sys.path.insert(0, ".")

from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k

CITY = "NA01"  # Vancouver
TYPE_INDEX = 0  # City Hotel, $54.000K (medido no survey)
GUARD = "../states/_venture_guard.state"


def main():
    b = BizHawkBridge()
    ex = Executor(b)
    g = ex.g

    b.load(GUARD)
    b.advance(90)
    ex._ensure_menu()

    caixa_antes = read_cash_k(b)
    print("caixa antes:", caixa_antes)

    shot_fac_antes = g.info_screen("facilities", "fac_antes_cityhotel")
    print("facilities antes:", shot_fac_antes)
    ex._ensure_menu()

    ok, det = ex.run({"action": "open_venture", "params": {"city": CITY, "type_index": TYPE_INDEX}})
    print("open_venture:", ok, det)

    caixa_depois = read_cash_k(b)
    print("caixa depois:", caixa_depois, "delta:", (caixa_depois - caixa_antes) if (caixa_depois is not None and caixa_antes is not None) else "NA")

    if ok:
        b.save("../states/_cityhotel_comprado.state")
        print("savestate: _cityhotel_comprado.state")

        ex._ensure_menu()
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


if __name__ == "__main__":
    main()
