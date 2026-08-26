"""ETAPA 2-MetricaEfeito: recalcula metricas de baselines existentes.

Lê acoes.jsonl de cada run de baseline e recomputa taxa de efeito separando
wait (nao-substantiva) de acoes substantivas.

    python recompute_baselines_metrics.py
"""

import json
import pathlib
import sys

# Importa a funcao de calculo de metricas
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from run_eval import calcular_metricas_acoes

LOGS = pathlib.Path(__file__).resolve().parent.parent / "logs"


def recomputa_run(resumo_path):
    """Recomputa metricas de uma run existente."""
    run_dir = resumo_path.parent
    old_data = json.loads(resumo_path.read_text(encoding="utf-8"))

    # Calcula novas metricas
    metricas = calcular_metricas_acoes(run_dir)

    # Monta novo resumo preservando caixa e placar (nao toca na ponte)
    new_data = old_data.copy()
    new_data.update({
        "acoes_executadas": metricas["acoes_executadas"],
        "acoes_com_efeito_verificado": metricas["acoes_com_efeito_verificado"],
        "taxa_efeito_verificado_pct": metricas["taxa_efeito_verificado_pct"],
        "taxa_fonte_inclui_wait": "metricas acima incluem acoes `wait` (nao-substantivas). Ver campos _substantivas_ abaixo.",
        "acoes_substantivas_executadas": metricas["acoes_substantivas_executadas"],
        "acoes_substantivas_com_efeito": metricas["acoes_substantivas_com_efeito"],
        "taxa_efeito_substantivas_pct": metricas["taxa_efeito_substantivas_pct"],
        "taxa_efeito_substantivas_fonte": "veredito do ORACULO DO EXECUTOR (executor.run), nao-substantivas (wait) excluidas",
        "acoes_wait": metricas["acoes_wait"],
        "turnos_sem_acao_substantiva": metricas["turnos_sem_acao_substantiva"],
    })

    # Preserva caixa, placar, fonte (nao refazemos leitura da ponte)
    # Apenas taxa_sobre_pedidas_pct pode mudar se metricas_acoes mudou
    if old_data.get("acoes_pedidas_pelo_modelo"):
        new_data["taxa_sobre_pedidas_pct"] = (
            round(metricas["acoes_com_efeito_verificado"] /
                  old_data["acoes_pedidas_pelo_modelo"] * 100, 1)
        )

    return old_data, new_data


def main():
    results = []

    for resumo_path in sorted(LOGS.glob("eval_*_NA13_*/resumo.json")):
        # Filtra apenas baselines (random, greedy)
        try:
            data = json.loads(resumo_path.read_text(encoding="utf-8"))
            baseline = data.get("baseline")
        except Exception as e:
            print(f"[SKIP] {resumo_path}: erro ao ler JSON: {e}")
            continue
        if baseline not in ("random", "greedy"):
            continue

        run_dir = resumo_path.parent.name
        old_data, new_data = recomputa_run(resumo_path)

        # Salva o novo resumo
        resumo_path.write_text(json.dumps(new_data, indent=1, ensure_ascii=False),
                               encoding="utf-8")

        results.append({
            "run": run_dir,
            "baseline": baseline,
            "old": old_data,
            "new": new_data,
        })
        print(f"[OK] {run_dir}")

    # Relatorio de antes/depois
    print("\n" + "=" * 120)
    print("COMPARACAO ANTES/DEPOIS")
    print("=" * 120)

    for r in results:
        old = r["old"]
        new = r["new"]

        print(f"\n{r['run']}")
        print(f"  baseline: {r['baseline']}")
        print(f"  acoes_executadas: {old['acoes_executadas']} -> {new['acoes_executadas']}")
        print(f"    com_efeito: {old['acoes_com_efeito_verificado']} -> {new['acoes_com_efeito_verificado']}")
        print(f"    taxa_total (inclui wait): {old['taxa_efeito_verificado_pct']}% -> {new['taxa_efeito_verificado_pct']}%")
        print(f"  SUBSTANTIVAS:")
        print(f"    executadas: {new['acoes_substantivas_executadas']}")
        print(f"    com_efeito: {new['acoes_substantivas_com_efeito']}")
        print(f"    taxa: {new['taxa_efeito_substantivas_pct']}%")
        print(f"    wait: {new['acoes_wait']} (nao-substantivas)")
        print(f"    turnos_sem_subst: {new['turnos_sem_acao_substantiva']}")

    # Resumo por baseline
    print("\n" + "=" * 120)
    print("RESUMO POR BASELINE")
    print("=" * 120)

    random_results = [r for r in results if r["baseline"] == "random"]
    greedy_results = [r for r in results if r["baseline"] == "greedy"]

    print("\nRANDOM:")
    for r in random_results:
        new = r["new"]
        print(f"  {r['run']}: "
              f"taxa_total={new['taxa_efeito_verificado_pct']}% "
              f"taxa_subst={new['taxa_efeito_substantivas_pct']}% "
              f"wait={new['acoes_wait']}")

    print("\nGREEDY:")
    for r in greedy_results:
        new = r["new"]
        print(f"  {r['run']}: "
              f"taxa_total={new['taxa_efeito_verificado_pct']}% "
              f"taxa_subst={new['taxa_efeito_substantivas_pct']}% "
              f"wait={new['acoes_wait']}")

    print("\n" + "=" * 120)
    print(f"TOTAL: {len(results)} runs recomputadas")
    print("=" * 120)


if __name__ == "__main__":
    main()
