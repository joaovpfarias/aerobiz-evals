"""Discriminador OFFLINE das baselines (ETAPA 4-Baselines): elas ainda casam
com o action space atual?

Roda as duas politicas contra estados REAIS gravados em `logs/*/turns.jsonl` (o
mesmo objeto que o pilot manda ao modelo) e exige ZERO erro de validacao e ZERO
id de cidade invalido em N sementes. Nao toca no emulador.

    python test_baselines_offline.py [--seeds 100]
"""

import argparse
import json
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import baselines
from schema import validate_turn
from world import WORLD_CITIES

LOGS = pathlib.Path(__file__).resolve().parent.parent / "logs"


def estados():
    out = []
    for tp in sorted(LOGS.glob("*/turns.jsonl")):
        for linha in tp.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(linha)
            except ValueError:
                continue
            st = rec.get("state")
            if isinstance(st, dict) and st.get("company"):
                out.append((f"{tp.parent.name}#t{rec.get('turn')}", st))
    return out


def cidades_invalidas(acoes):
    ruins = []
    for a in acoes:
        for k, v in (a.get("params") or {}).items():
            if k in ("city", "to", "from", "route") and isinstance(v, str) and v not in WORLD_CITIES:
                ruins.append((a.get("action"), k, v))
    return ruins


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=100)
    a = ap.parse_args()
    sts = estados()
    if not sts:
        print("SEM ESTADO GRAVADO em logs/*/turns.jsonl — nada medido")
        return 2
    print("estados reais carregados: %d" % len(sts))
    falhas = 0
    for nome, st in sts:
        for kind, pol in baselines.POLITICAS.items():
            vazios = erros_tot = acoes_tot = 0
            amostra = None
            for s in range(a.seeds):
                acoes, diario = pol(st, random.Random(s))
                valid, errs = validate_turn(acoes, st)
                ruins = cidades_invalidas(acoes)
                acoes_tot += len(acoes)
                erros_tot += len(errs) + len(ruins)
                if errs or ruins:
                    falhas += 1
                    if amostra is None:
                        amostra = (errs, ruins, acoes)
                if not acoes:
                    vazios += 1
                if not diario:
                    falhas += 1
                    print("  FALHA %s/%s: diario VAZIO (congela next_turn_number)" % (nome, kind))
            print("  %-34s %-7s acoes=%3d erros=%d turnos_vazios=%d/%d"
                  % (nome, kind, acoes_tot, erros_tot, vazios, a.seeds))
            if amostra:
                print("    amostra de erro: %s | cidades ruins: %s | acoes: %s"
                      % (amostra[0], amostra[1], json.dumps(amostra[2], ensure_ascii=False)[:300]))
    print("RESULTADO: %s" % ("OK — 0 emissao invalida" if not falhas else "%d emissoes invalidas" % falhas))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
