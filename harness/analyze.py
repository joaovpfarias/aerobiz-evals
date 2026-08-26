"""Analisa uma run do piloto: gate do F1 + metricas de trajetoria.

As metricas seguem as 3 camadas do criterio de eval:
  placar     -> caixa final, variacao acumulada, rotas abertas
  trajetoria -> taxa de execucao, acoes invalidas, repeticao de acoes
  custo      -> tokens e latencia por turno

Uso: python analyze.py [--run ../logs/pilot_auto]
"""

import argparse
import json
import pathlib
from collections import Counter


def load(run):
    p = pathlib.Path(run) / "turns.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="../logs/pilot_auto")
    a = ap.parse_args()
    rows = load(a.run)
    if not rows:
        print(f"sem turnos em {a.run}")
        return

    n = len(rows)
    acoes = [x for r in rows for x in r.get("actions_valid", [])]
    invalidas = sum(len(r.get("validation_errors", [])) for r in rows)
    propostas = sum(len(r.get("actions_raw", [])) for r in rows)
    tipos = Counter(x["action"] for x in acoes)

    # resultados de execucao ficam no state do turno seguinte (last_turn_results)
    exec_ok = exec_fail = 0
    for r in rows:
        for res in (r.get("state", {}).get("last_turn_results", {}) or {}).get("acoes_do_turno", []):
            if res.get("ok"):
                exec_ok += 1
            else:
                exec_fail += 1
    total_exec = exec_ok + exec_fail
    taxa = exec_ok / total_exec * 100 if total_exec else 0

    caixas = [r["state"].get("cash_k") for r in rows if r.get("state", {}).get("cash_k")]
    tokens = sum((r.get("usage") or {}).get("completion_tokens", 0) for r in rows)
    lat = [r.get("latency_s") or 0 for r in rows]

    print(f"=== run: {a.run} ===")
    print(f"turnos: {n}")
    print(f"acoes propostas: {propostas} | validas: {len(acoes)} | erros de validacao: {invalidas}")
    print(f"execucao: {exec_ok} ok / {exec_fail} falhas = {taxa:.0f}%  (gate F1: >=90%)")
    print(f"tipos de acao: {dict(tipos)}")
    if caixas:
        print(f"caixa: {caixas[0]}K -> {caixas[-1]}K ({caixas[-1] - caixas[0]:+}K)")
        print(f"  minimo {min(caixas)}K | maximo {max(caixas)}K")
    print(f"tokens de saida: {tokens} | latencia media {sum(lat)/len(lat):.1f}s")

    print("\n--- diario por turno ---")
    for r in rows:
        d = (r.get("diary_update") or "")[:110]
        print(f"  t{r['turn']:02d} [{r['state'].get('cash_k')}K] {d}")


if __name__ == "__main__":
    main()
