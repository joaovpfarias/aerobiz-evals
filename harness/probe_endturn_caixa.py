"""Por que o detector antigo ("o caixa mudou") falhava — MEDICAO, nao hipotese.

Le caixa e contador em TRES momentos por turno:
  A) no menu, antes de disparar r1c5;
  B) logo apos o disparo, ANTES de atravessar a cadeia de relatorios;
  C) de volta ao menu, depois de dismiss_to_menu.

Se o caixa de (B) ainda for o de (A), quem media "o caixa mudou" cedo demais
concluia "o turno nao passou" e disparava r1c5 DE NOVO — passando um trimestre
extra sem contar. E o modo de falha do enunciado desta etapa.
"""

import pathlib
import sys

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

RAIZ = pathlib.Path(__file__).parent.parent
EVAL = RAIZ / "states" / "eval_single_2000_lv5.state"


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    b = BizHawkBridge(timeout=60)
    g = Game(b)
    ex = Executor(b)
    ex.g = g

    b.load(EVAL)
    b.advance(90)
    b.speed(400)
    ex.dismiss_to_menu()

    for i in range(1, n + 1):
        qa, ca = world.read_quarter_index(b), world.read_cash_k(b)
        g.open_cmd("end_turn")
        b.advance(120)
        qb, cb = world.read_quarter_index(b), world.read_cash_k(b)
        ok = ex.dismiss_to_menu()
        qc, cc = world.read_quarter_index(b), world.read_cash_k(b)
        print(f"[{i}] A(menu) q={qa} caixa={ca}K | "
              f"B(pos-disparo, cadeia aberta) q={qb} caixa={cb}K | "
              f"C(menu de volta, dismiss={ok}) q={qc} caixa={cc}K", flush=True)
        print(f"    contador ja virou em B? {qb == qa + 1} | "
              f"caixa ja mudou em B? {cb != ca} | caixa mudou em C? {cc != ca}",
              flush=True)


if __name__ == "__main__":
    main()
