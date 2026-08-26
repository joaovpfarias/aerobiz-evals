"""Bake-off dos modelos free do OpenCode Go — escolhe o jogador do F1 por teste.

Criterios: (1) JSON valido, (2) decisao economicamente correta no cenario-armadilha,
(3) latencia, (4) tokens. Roda 2 prompts x N modelos e escreve logs/probe_report.json.

Uso: python probe_models.py [--models a,b,c]
"""

import argparse
import json
import pathlib
import time

from opencode_client import FREE_MODELS, chat, extract_json

LOGS = pathlib.Path(__file__).parent.parent / "logs"

SYSTEM = (
    "Voce e o CEO de uma companhia aerea em um jogo de estrategia por turnos. "
    "Responda SOMENTE com JSON valido, sem markdown, no formato "
    '{"action": "...", "params": {...}, "rationale": "..."}'
)

# P1: armadilha de orcamento — resposta correta evita o 747 (nao cabe no caixa)
P1 = (
    'Caixa: $40M. Slots livres: Nova York (trafego alto), Lima (trafego baixo). '
    'Aviao novo Boeing 747: $180M. DC-8 usado: $30M. Acoes possiveis: '
    '"buy_aircraft" (params: model, qty), "wait". Escolha UMA acao.'
)

# P2: trade-off de rota — dominancia simples (mesma distancia, trafego maior)
P2 = (
    'Voce tem 1 aviao ocioso (DC-8, alcance 9000km). Rotas possiveis a partir do seu hub: '
    'A) hub->Toquio, 8000km, demanda 900 pax/sem, sem concorrente; '
    'B) hub->Sydney, 8000km, demanda 400 pax/sem, 2 concorrentes. '
    'Acoes: "open_route" (params: destination). Escolha UMA acao.'
)


def check_p1(obj):
    p = json.dumps(obj).lower()
    return ("dc-8" in p or "dc8" in p or obj.get("action") == "wait") and "747" not in json.dumps(
        obj.get("params", {})
    )


def check_p2(obj):
    return "toquio" in json.dumps(obj, ensure_ascii=False).lower() or "tokyo" in json.dumps(obj).lower()


def probe(model):
    row = {"model": model, "ok_json": 0, "ok_answer": 0, "latency": [], "tokens_out": [], "errors": []}
    for prompt, check in [(P1, check_p1), (P2, check_p2)]:
        try:
            r = chat(
                [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                model=model,
                max_tokens=2000,
                retries=2,
                fallbacks=False,  # medir ESTE modelo; com fallback a resposta de outro seria creditada a ele
            )
            row["latency"].append(r["latency_s"])
            row["tokens_out"].append(r["usage"].get("completion_tokens"))
            obj = extract_json(r["content"])
            row["ok_json"] += 1
            row["ok_answer"] += 1 if check(obj) else 0
        except Exception as e:  # noqa: BLE001
            row["errors"].append(str(e)[:200])
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(FREE_MODELS))
    args = ap.parse_args()
    LOGS.mkdir(parents=True, exist_ok=True)
    rows = []
    for m in args.models.split(","):
        m = m.strip()
        print(f"[probe] {m} ...", flush=True)
        t0 = time.time()
        row = probe(m)
        rows.append(row)
        lat = ",".join(f"{x:.0f}s" for x in row["latency"]) or "-"
        print(
            f"  json {row['ok_json']}/2 | resposta certa {row['ok_answer']}/2 | lat {lat}"
            + (f" | ERR {row['errors'][:1]}" if row["errors"] else ""),
            flush=True,
        )
        _ = t0
    report = sorted(rows, key=lambda r: (-r["ok_answer"], -r["ok_json"], sum(r["latency"] or [999])))
    out = LOGS / "probe_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nranking: {[r['model'] for r in report]}")
    print(f"relatorio: {out}")


if __name__ == "__main__":
    main()
