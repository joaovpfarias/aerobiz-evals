"""Calibracao das ferramentas de acao — o pedido tem que virar o valor real.

PRINCIPIO: nenhuma macro entra no eval sem uma medicao que prove que
"o modelo pediu X" resulta em "o jogo ficou com X". Sem isso o eval mede o ruido
do harness, nao a estrategia do modelo.

Cada calibracao aplica N incrementos e captura a tela resultante; a leitura do
valor e feita UMA VEZ (aqui), e o mapeamento fica gravado em CALIBRATION.md.
Em producao as macros usam o mapeamento e nao tiram screenshot.

Uso:
  python calibrate.py route_sliders --dest NA14
"""

import argparse
import pathlib

from bridge import BizHawkBridge
from executor import STEP_SETTLE, Executor
from probe_icons import montage

OUT = pathlib.Path(__file__).parent.parent / "logs" / "calib"


def route_sliders(b, dest, increments=(0, 1, 2, 4)):
    """Abre a tela de rota e captura cada slider com N incrementos aplicados.

    Gera 3 montagens (aviao/qtd, voos por semana, tarifa) para leitura manual
    unica. O objetivo e descobrir quantos toques valem uma unidade.
    """
    ex = Executor(b)
    OUT.mkdir(parents=True, exist_ok=True)
    shots = {"planes": [], "flights": [], "fare": []}

    for n in increments:
        b.load("../states/f0_t02_route.state")
        b.advance(60)
        ex.g.back_to_menu(8)
        ex.g.open_cmd("new_route")
        ex._select_city(dest)
        # passo 1: tela de aviao -> confirma para chegar em "quantos avioes"
        b.batch(ex._confirm(), extra_frames=STEP_SETTLE + 60)
        b.batch(ex._bump("Right", n), extra_frames=n * 40 + 60)
        shots["planes"].append(b.screenshot(OUT / f"planes_{n}.png"))
        # passo 2: confirma -> "voos por semana"
        b.batch(ex._confirm(), extra_frames=STEP_SETTLE + 60)
        b.batch(ex._bump("Right", n), extra_frames=n * 40 + 60)
        shots["flights"].append(b.screenshot(OUT / f"flights_{n}.png"))
        # passo 3: confirma -> "tarifa"
        b.batch(ex._confirm(), extra_frames=STEP_SETTLE + 60)
        b.batch(ex._bump("Right", n), extra_frames=n * 40 + 60)
        shots["fare"].append(b.screenshot(OUT / f"fare_{n}.png"))
        print(f"incremento {n}: capturado", flush=True)

    for nome, paths in shots.items():
        print(montage(paths, OUT / f"montagem_{nome}.png", scale=2, cols=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["route_sliders"])
    ap.add_argument("--dest", default="NA14")
    a = ap.parse_args()
    b = BizHawkBridge()
    b.speed(400)
    if a.what == "route_sliders":
        route_sliders(b, a.dest)


if __name__ == "__main__":
    main()
