"""Calibra flights_week e fare: quantos toques valem uma unidade.

Metodo: do savestate do eval, abre rota para NA06 (Denver — tem slots), avanca ate
a tela de voos/semana, aplica N incrementos e CAPTURA. A leitura do valor efetivo e
feita uma unica vez aqui; producao usa a constante.
"""
import sys
from bridge import BizHawkBridge
from executor import Executor
from probe_icons import montage
from pathlib import Path

ALVO = sys.argv[1] if len(sys.argv) > 1 else "NA06"
INCS = [0, 1, 2, 4]
O = Path("../logs/calib2")
O.mkdir(parents=True, exist_ok=True)

b = BizHawkBridge()
b.speed(400)
ex = Executor(b)
voos, tarifa = [], []

for n in INCS:
    b.load("../states/eval_single_2000_lv5.state")
    b.advance(90)
    ex._ensure_menu()
    ex.g.open_cmd("new_route")
    ex._select_city(ALVO)
    ex._step()                       # -> aviao
    ex._step()                       # -> nº de avioes
    # NAO dar o 3o _step: ele ja leva a TARIFA. A tela de voos/semana vem antes.
    b.batch(ex._bump("Right", n), extra_frames=n * 60 + 80)
    voos.append(b.screenshot(O / f"voos_{n}.png"))  # tela de VOOS/SEMANA
    ex._step()                       # -> tarifa
    b.batch(ex._bump("Right", n), extra_frames=n * 60 + 80)
    tarifa.append(b.screenshot(O / f"tarifa_{n}.png"))
    print(f"incremento {n} capturado", flush=True)

print(montage(voos, O / "cal_voos.png", scale=2, cols=2))
print(montage(tarifa, O / "cal_tarifa.png", scale=2, cols=2))
