"""ETAPA 3b: prova AO VIVO da alavanca `slots` + duracao real da negociacao.

1) A partir de `_e3b_base`, executa a acao do action space
   {"action":"negotiate_slots","params":{"city":"NA14","slots":3}}
   pelo Executor (mesmo caminho do piloto), e exige que o detalhe traga
   "LIDOS DE VOLTA=3" — ou seja, a tela confirmou a quantidade.
2) Passa turnos ate os funcionarios livres voltarem a 4, contando trimestres
   pelo contador da RAM. Esse e o numero que a etapa pede.
Este script NAO le os slots concedidos. Essa leitura e um passo SEPARADO,
feito depois, por `probe_slots_lever.py NA14 0 0 0 Right <pref> <state>`:
ele reabre a tela de negociacao (cujo cabecalho traz "Total slots N/75"),
fotografa e ABORTA com B — custo zero, medido nas quatro corridas da bateria
de meses (caixa 1.220.000K intacta e 4 funcionarios livres no fim de todas).
"""
import sys, pathlib, json
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge, world
from executor import Executor

RAIZ = HERE.parent
SHOTS = RAIZ / "logs" / "etapa3b"
SHOTS.mkdir(parents=True, exist_ok=True)
BASE = str(RAIZ / "states" / "_e3b_base.state")

SLOTS = int(sys.argv[1]) if len(sys.argv) > 1 else 3
CID = sys.argv[2] if len(sys.argv) > 2 else "NA14"
PREF = sys.argv[3] if len(sys.argv) > 3 else f"vivo_s{SLOTS}"
MAXT = int(sys.argv[4]) if len(sys.argv) > 4 else 6

b = bridge.BizHawkBridge()
ex = Executor(b)
b.load(BASE)
b.advance(120)
img = Image.open(b.screenshot()).convert("RGB")
livres0 = world.free_staff_menu(img)
cash0 = world.read_cash_k(b)
q0 = world.read_quarter_index(b)
print(json.dumps({"passo": "antes", "livres": livres0, "cash": cash0,
                  "q": q0, "data": world.read_date(b)}, default=str), flush=True)

ok, det = ex.run({"action": "negotiate_slots",
                  "params": {"city": CID, "slots": SLOTS}})
print(json.dumps({"passo": "acao", "ok": ok, "detalhe": det}, default=str), flush=True)
if not ok:
    sys.exit(1)
b.save(str(RAIZ / "states" / f"_e3b_{PREF}_despachado.state"))

linhas = []
for t in range(1, MAXT + 1):
    okt, dett = ex.g.end_turn()
    img = Image.open(b.screenshot()).convert("RGB")
    liv = world.free_staff_menu(img)
    p = b.screenshot(SHOTS / f"{PREF}_t{t}.png")
    l = {"t": t, "ok": okt, "det": dett, "q": world.read_quarter_index(b),
         "data": world.read_date(b), "livres": liv, "cash": world.read_cash_k(b),
         "menu": world.at_main_menu_img(img), "shot": pathlib.Path(p).name}
    linhas.append(l)
    print(json.dumps({"passo": "turno", **l}, default=str), flush=True)
    if liv is not None and liv >= livres0:
        break

b.save(str(RAIZ / "states" / f"_e3b_{PREF}_concluido.state"))
print(json.dumps({"passo": "fim", "turnos": linhas,
                  "trimestres_ate_voltar": (linhas[-1]["q"] - q0) if linhas else None},
                 default=str), flush=True)
