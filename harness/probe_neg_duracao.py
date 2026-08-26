"""ETAPA 3b (b): quantos TRIMESTRES uma negociacao leva, medido de verdade.

Carrega um savestate com a negociacao JA despachada, passa turnos um a um e a
cada turno le:
  - contador de trimestres (RAM, world.read_quarter_index)
  - funcionarios livres na barra do menu (world.free_staff_menu)
  - caixa
Para quando os livres voltam ao valor de antes do despacho, ou no teto.

uso: probe_neg_duracao.py <state> <livres_alvo> <max_turnos> <pref>
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


def main():
    st, alvo, maxt, pref = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    b = bridge.BizHawkBridge()
    ex = Executor(b)
    b.load(st)
    b.advance(120)
    img = Image.open(b.screenshot()).convert("RGB")
    linhas = [{"t": 0, "q": world.read_quarter_index(b), "data": world.read_date(b),
               "livres": world.free_staff_menu(img), "cash": world.read_cash_k(b),
               "menu": world.at_main_menu_img(img)}]
    for t in range(1, maxt + 1):
        ok, det = ex.g.end_turn()
        img = Image.open(b.screenshot()).convert("RGB")
        liv = world.free_staff_menu(img)
        p = b.screenshot(SHOTS / f"{pref}_t{t}.png")
        linhas.append({"t": t, "ok": ok, "det": det, "q": world.read_quarter_index(b),
                       "data": world.read_date(b), "livres": liv,
                       "cash": world.read_cash_k(b),
                       "menu": world.at_main_menu_img(img),
                       "shot": pathlib.Path(p).name})
        print(json.dumps(linhas[-1], default=str), flush=True)
        if liv is not None and liv >= alvo:
            break
    b.save(str(RAIZ / "states" / f"_e3b_{pref}_fim.state"))
    print(json.dumps({"RESULTADO": linhas}, default=str), flush=True)


if __name__ == "__main__":
    main()
