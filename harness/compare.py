"""Compara duas runs (modelo fraco vs forte) agrupando pelo modelo que REALMENTE respondeu.

A cadeia de fallback pode responder um turno com outro modelo. Agrupar por
`model_solicitado` produziria uma comparacao entre fantasmas — aqui usamos
`model_respondeu` e marcamos os turnos contaminados.

Uso: python compare.py ../logs/eval_forte_v2 ../logs/eval_fraco
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


def resumo(run):
    rows = load(run)
    if not rows:
        return None
    pedido = Counter(r.get("model_solicitado") for r in rows)
    respondeu = Counter(r.get("model_respondeu") for r in rows)
    contaminados = [
        r["turn"] for r in rows if r.get("model_respondeu") != r.get("model_solicitado")
    ]
    exec_ok = exec_fail = 0
    for r in rows:
        for res in (r.get("state", {}).get("last_turn_results", {}) or {}).get("acoes_do_turno", []):
            exec_ok += 1 if res.get("ok") else 0
            exec_fail += 0 if res.get("ok") else 1
    caixas = [r["state"].get("cash_k") for r in rows if r.get("state", {}).get("cash_k")]
    acoes = Counter(x["action"] for r in rows for x in r.get("actions_valid", []))
    return {
        "run": run,
        "turnos": len(rows),
        "pedido": dict(pedido),
        "respondeu": dict(respondeu),
        "turnos_contaminados": contaminados,
        "exec": (exec_ok, exec_fail),
        "caixa_ini_fim": (caixas[0], caixas[-1]) if caixas else None,
        "acoes": dict(acoes),
        "slots_finais": len(rows[-1]["state"].get("cities_north_america", []) and
                            [c for c in rows[-1]["state"]["cities_north_america"] if c.get("slots_owned")]),
        "rotas_finais": len(rows[-1]["state"]["company"].get("routes_open", [])),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    a = ap.parse_args()
    resumos = [r for r in (resumo(x) for x in a.runs) if r]
    for r in resumos:
        print(f"\n=== {r['run']} ===")
        print(f"turnos: {r['turnos']} | pedido: {r['pedido']} | respondeu: {r['respondeu']}")
        if r["turnos_contaminados"]:
            print(f"  [ALERTA] turnos respondidos por OUTRO modelo (fallback): {r['turnos_contaminados']}")
        ok, fail = r["exec"]
        taxa = ok / (ok + fail) * 100 if (ok + fail) else 0
        print(f"execucao: {ok} ok / {fail} falhas = {taxa:.0f}%")
        print(f"caixa: {r['caixa_ini_fim']} | cidades com slots: {r['slots_finais']} | rotas: {r['rotas_finais']}")
        print(f"acoes: {r['acoes']}")

    if len(resumos) >= 2:
        print("\n--- comparacao ---")
        for campo in ("turnos", "caixa_ini_fim", "slots_finais", "rotas_finais"):
            print(f"{campo}: " + " | ".join(f"{r['run'].split('/')[-1]}={r[campo]}" for r in resumos))
        print("\nNOTA: eval restrito ao subconjunto CALIBRADO de acoes "
              "(destino de rota, cidade de negociacao, wait). Sem sliders de "
              "frequencia/tarifa nem compra de aviao, a companhia e deficitaria "
              "por construcao — isto mede confiabilidade e uso das alavancas "
              "disponiveis, nao qualidade estrategica plena.")


if __name__ == "__main__":
    main()
