"""ACEITE ETAPA 1-EndTurn: 6 `end_turn` seguidos, com prova de 6 trimestres.

Sinal de virada: contador absoluto de trimestres da RAM (world.QUARTER_ADDR).
Prova INDEPENDENTE da RAM: a data lida dos PIXELS da barra do menu
(world.read_date_px) apos cada chamada — se a RAM e os pixels concordam nas 7
leituras, o contador nao e "um numero que por acaso anda junto".

Terceira assercao (nao decorativa): a QUEDA DE CAIXA por chamada. A virada
OCT.2000 -> JAN.2001 e a que levanta o "Regional Rankings"; um A cego nessa
tela ja custou $276.000K (CALIBRATION, dismiss_to_menu). Caixa caindo alem da
sentinela = alguma tecla confirmou algo, mesmo que o trimestre tenha virado.

Uso:  python prova_endturn.py [n_turnos] [savestate] [tag]

Sem argumentos: 6 turnos a partir de `states/eval_single_2000_lv5.state`, onde a
ancora e VERIFICADA contra a constante (contador 181 = APR. 2000). Com outro
savestate a ancora e a coerencia RAM x pixels no ponto de partida.
"""

import pathlib
import re
import sys

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

RAIZ = pathlib.Path(__file__).parent.parent
EVAL = RAIZ / "states" / "eval_single_2000_lv5.state"
OUT = RAIZ / "logs" / "etapa1"
OUT.mkdir(parents=True, exist_ok=True)

ANCORA_CONTADOR = 181           # APR. 2000 no savestate do eval
ANCORA_DATA = (2000, 2)         # (ano, trimestre 1..4) = APR
SENTINELA_CAIXA_K = 20_000      # queda por chamada acima disto = tecla confirmou algo


TAG = "aceite"


def le_tela(b, tag):
    """Screenshot + (menu?, data por pixels). Nao aperta nada."""
    p = b.screenshot(OUT / f"{tag}.png")
    img = Image.open(p).convert("RGB")
    return p, world.at_main_menu_img(img), world.read_date_px(img)


def main():
    global TAG
    n_turnos = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    estado = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else EVAL
    TAG = sys.argv[3] if len(sys.argv) > 3 else "aceite"

    b = BizHawkBridge(timeout=60)
    g = Game(b)
    ex = Executor(b)
    ex.g = g

    b.load(estado)
    b.advance(90)
    b.speed(400)
    if not ex.dismiss_to_menu():
        print("ABORTA: nao cheguei ao menu principal a partir do savestate")
        return 1

    q0 = world.read_quarter_index(b)
    caixa0 = world.read_cash_k(b)
    _, menu0, data0 = le_tela(b, f"{TAG}_t0")
    print(f"estado: {estado.name}", flush=True)
    print(f"ancora: contador={q0} ({world.date_label(q0)}) "
          f"data_px={data0} menu={menu0} caixa={caixa0}K", flush=True)
    if data0 != world.quarter_to_date(q0):
        print(f"ABORTA: RAM e pixels discordam na largada "
              f"(RAM diz {world.quarter_to_date(q0)}, tela diz {data0})")
        return 1
    if estado == EVAL and (q0 != ANCORA_CONTADOR or data0 != ANCORA_DATA):
        print(f"ABORTA: ancora divergente (esperado contador={ANCORA_CONTADOR} "
              f"data_px={ANCORA_DATA}) — savestate errado ou epoca errada")
        return 1

    linhas = []
    sucessos = 0
    for i in range(1, n_turnos + 1):
        antes = world.read_quarter_index(b)
        caixa_antes = world.read_cash_k(b)
        ok, det = g.end_turn()
        depois = world.read_quarter_index(b)
        caixa_depois = world.read_cash_k(b)
        _, menu, data_px = le_tela(b, f"{TAG}_t{i}")
        m = re.search(r"(\d+) disparo", det)
        disparos = int(m.group(1)) if m else -1
        delta_caixa = caixa_antes - caixa_depois
        coerente = data_px == world.quarter_to_date(depois)
        sucessos += 1 if ok else 0
        linhas.append({
            "n": i, "ok": ok, "de": antes, "para": depois,
            "rotulo": world.date_label(depois), "data_px": data_px,
            "coerente": coerente, "menu": menu, "disparos": disparos,
            "caixa": caixa_depois, "delta": delta_caixa,
        })
        print(f"[{i}/{n_turnos}] ok={ok} contador {antes}->{depois} "
              f"({world.date_label(antes)} -> {world.date_label(depois)}) "
              f"data_px={data_px} coerente={coerente} menu={menu} "
              f"disparos={disparos} caixa {caixa_antes}K->{caixa_depois}K "
              f"(delta {delta_caixa}K)\n      det: {det}", flush=True)

    q_fim = world.read_quarter_index(b)
    avancou = q_fim - q0
    incoerentes = [l["n"] for l in linhas if not l["coerente"]]
    duplos = [l["n"] for l in linhas if l["para"] - l["de"] != 1]
    caros = [l["n"] for l in linhas if l["delta"] > SENTINELA_CAIXA_K]

    print("\n===== VEREDITO =====")
    print(f"chamadas com sucesso: {sucessos}/{n_turnos}")
    print(f"trimestres avancados: {avancou} (contador {q0} -> {q_fim}; "
          f"{world.date_label(q0)} -> {world.date_label(q_fim)})")
    print(f"RAM x PIXELS: {n_turnos - len(incoerentes)}/{n_turnos} coerentes"
          + (f" — divergem: {incoerentes}" if incoerentes else ""))
    print(f"chamadas que nao andaram exatamente +1: {duplos or 'nenhuma'}")
    print(f"disparos de r1c5 por chamada: {[l['disparos'] for l in linhas]}")
    print(f"quedas de caixa por chamada (K): {[l['delta'] for l in linhas]}")
    print(f"quedas acima da sentinela ({SENTINELA_CAIXA_K}K): {caros or 'nenhuma'}")
    aceite = (sucessos == n_turnos and avancou == n_turnos
              and not incoerentes and not duplos and not caros)
    print("ACEITE:", "OK" if aceite else "FALHOU")
    return 0 if aceite else 1


if __name__ == "__main__":
    sys.exit(main())
