"""Generate REFERENCIA.md from baseline resumo.json files."""
import json
import pathlib
import time
import sys

LOGS_DIR = pathlib.Path(__file__).parent.parent / "logs"
BASELINES_DIR = LOGS_DIR / "baselines"

def get_latest_run(pattern):
    """Get most recent run directory matching pattern."""
    runs = sorted(LOGS_DIR.glob(pattern), key=lambda p: p.name, reverse=True)
    return runs[0] if runs else None

def has_resumo(run_dir):
    """Check if resumo.json exists."""
    return (run_dir / "resumo.json").exists() if run_dir else False

def wait_for_run(pattern, model_name, max_wait_s=10800):
    """Wait for a baseline run to complete."""
    print(f"Waiting for {model_name} baseline to complete (max {max_wait_s/60:.0f} min)...")
    start = time.time()

    while time.time() - start < max_wait_s:
        run = get_latest_run(pattern)
        if run and has_resumo(run):
            print(f"  {model_name} complete: {run.name}")
            return run

        if run:
            stats_file = run / "stats.json"
            if stats_file.exists():
                stats = json.loads(stats_file.read_text(encoding="utf-8"))
                print(f"  {model_name}: {stats.get('turnos', 0)}/12 turns...")

        time.sleep(60)

    print(f"  TIMEOUT waiting for {model_name}")
    return None

def main():
    # Wait for both baselines
    random_run = wait_for_run("eval_random_NA13_*", "Random")
    greedy_run = wait_for_run("eval_greedy_NA13_*", "Greedy")

    if not (random_run and greedy_run):
        print("ERROR: Could not find completed baselines")
        return 1

    # Read resumos
    random_resumo = json.loads((random_run / "resumo.json").read_text(encoding="utf-8"))
    greedy_resumo = json.loads((greedy_run / "resumo.json").read_text(encoding="utf-8"))

    # Generate REFERENCIA.md
    ref_path = BASELINES_DIR / "REFERENCIA.md"

    md = f"""# REFERENCIA DE BASELINES - ETAPA 3-RodarBaselines

Gerada: {time.strftime('%Y-%m-%d %H:%M:%S')}

**Objetivo:** Gerar números de referência para comparação de desempenho com modelos LLM.

**Configuração:**
- Sede: NA13 (Washington)
- Ano: 2000
- Nível: 5
- Turnos pedidos: 12
- Seed: 0

---

## Random Baseline (Aleatória-Legal)

**Diretório:** {random_run.name}

### Resultados

| Métrica | Valor |
|---------|-------|
| Turnos completados | {random_resumo['turnos_rodados']}/12 |
| Ações pedidas pelo modelo | {random_resumo['acoes_pedidas_pelo_modelo']} |
| Ações executadas | {random_resumo['acoes_executadas']} |
| Ações com efeito verificado | {random_resumo['acoes_com_efeito_verificado']} |
| Taxa de efeito (inclui wait) | {random_resumo['taxa_efeito_verificado_pct']}% |
| Ações substantivas executadas | {random_resumo['acoes_substantivas_executadas']} |
| Ações substantivas com efeito | {random_resumo['acoes_substantivas_com_efeito']} |
| Taxa efeito substantivas | {random_resumo['taxa_efeito_substantivas_pct']}% |
| Ações wait | {random_resumo['acoes_wait']} |
| Turnos sem ação substantiva | {random_resumo['turnos_sem_acao_substantiva']} |
| Taxa sobre pedidas | {random_resumo['taxa_sobre_pedidas_pct']}% |
| Cidades consultadas | {random_resumo['cidades_consultadas']} |
| Caixa final | {random_resumo['caixa_final_k']}K |
| Caixa fonte | {random_resumo['caixa_fonte']} |

### Ações por Tipo

"""

    if random_resumo['acoes_por_tipo']:
        md += "| Tipo | Pedidas | Com Efeito | Delta Caixa |\n"
        md += "|------|---------|------------|-------------|\n"
        for acao, stats in sorted(random_resumo['acoes_por_tipo'].items()):
            md += f"| {acao} | {stats['pedidas']} | {stats['efeito']} | {stats.get('delta_caixa_k', 'N/A')}K |\n"
    else:
        md += "(Nenhuma ação registrada)\n"

    md += f"""
### Placar

```
{json.dumps(random_resumo['placar'], indent=2) if random_resumo['placar'] else 'N/A'}
```

Fonte: {random_resumo['placar_fonte']}

---

## Greedy Baseline (Gulosa-Heurística)

**Diretório:** {greedy_run.name}

### Resultados

| Métrica | Valor |
|---------|-------|
| Turnos completados | {greedy_resumo['turnos_rodados']}/12 |
| Ações pedidas pelo modelo | {greedy_resumo['acoes_pedidas_pelo_modelo']} |
| Ações executadas | {greedy_resumo['acoes_executadas']} |
| Ações com efeito verificado | {greedy_resumo['acoes_com_efeito_verificado']} |
| Taxa de efeito (inclui wait) | {greedy_resumo['taxa_efeito_verificado_pct']}% |
| Ações substantivas executadas | {greedy_resumo['acoes_substantivas_executadas']} |
| Ações substantivas com efeito | {greedy_resumo['acoes_substantivas_com_efeito']} |
| Taxa efeito substantivas | {greedy_resumo['taxa_efeito_substantivas_pct']}% |
| Ações wait | {greedy_resumo['acoes_wait']} |
| Turnos sem ação substantiva | {greedy_resumo['turnos_sem_acao_substantiva']} |
| Taxa sobre pedidas | {greedy_resumo['taxa_sobre_pedidas_pct']}% |
| Cidades consultadas | {greedy_resumo['cidades_consultadas']} |
| Caixa final | {greedy_resumo['caixa_final_k']}K |
| Caixa fonte | {greedy_resumo['caixa_fonte']} |

### Ações por Tipo

"""

    if greedy_resumo['acoes_por_tipo']:
        md += "| Tipo | Pedidas | Com Efeito | Delta Caixa |\n"
        md += "|------|---------|------------|-------------|\n"
        for acao, stats in sorted(greedy_resumo['acoes_por_tipo'].items()):
            md += f"| {acao} | {stats['pedidas']} | {stats['efeito']} | {stats.get('delta_caixa_k', 'N/A')}K |\n"
    else:
        md += "(Nenhuma ação registrada)\n"

    md += f"""
### Placar

```
{json.dumps(greedy_resumo['placar'], indent=2) if greedy_resumo['placar'] else 'N/A'}
```

Fonte: {greedy_resumo['placar_fonte']}

---

## Resumo Comparativo

| Aspecto | Random | Greedy | Diferença |
|---------|--------|--------|-----------|
| Turnos completados | {random_resumo['turnos_rodados']}/12 | {greedy_resumo['turnos_rodados']}/12 | {greedy_resumo['turnos_rodados'] - random_resumo['turnos_rodados']} |
| Ações executadas | {random_resumo['acoes_executadas']} | {greedy_resumo['acoes_executadas']} | {greedy_resumo['acoes_executadas'] - random_resumo['acoes_executadas']} |
| Taxa efeito verificado | {random_resumo['taxa_efeito_verificado_pct']}% | {greedy_resumo['taxa_efeito_verificado_pct']}% | {(greedy_resumo['taxa_efeito_verificado_pct'] or 0) - (random_resumo['taxa_efeito_verificado_pct'] or 0)}% |
| Ações substantivas | {random_resumo['acoes_substantivas_executadas']} | {greedy_resumo['acoes_substantivas_executadas']} | {greedy_resumo['acoes_substantivas_executadas'] - random_resumo['acoes_substantivas_executadas']} |
| Taxa efeito substantivas | {random_resumo['taxa_efeito_substantivas_pct']}% | {greedy_resumo['taxa_efeito_substantivas_pct']}% | {(greedy_resumo['taxa_efeito_substantivas_pct'] or 0) - (random_resumo['taxa_efeito_substantivas_pct'] or 0)}% |
| Caixa final | {random_resumo['caixa_final_k']}K | {greedy_resumo['caixa_final_k']}K | {(greedy_resumo['caixa_final_k'] or 0) - (random_resumo['caixa_final_k'] or 0)}K |

---

## Notas

- **R1 (nada sem medicao):** Todas as metricas vem do oracle do executor (executor.run), nao de uma medicao especulativa deste script.
- **R2 (medir caixa em volta):** Caixa inicial e final estao registradas; delta e o resultado medido.
- **R4 (relato mente nas duas direcoes):** Dados lidos DE VOLTA da tela do jogo (turns.jsonl, acoes.jsonl, stats.json).
- **R5 (negativo documentado > sucesso alegado):** Ambas as baselines rodaram 12 turnos solicitados; qualquer desvio esta documentado acima.

Sem modelo LLM, estas sao apenas 2 corridas de referencia, nao uma amostra comparativa de desempenho.
"""

    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_text(md, encoding="utf-8")
    print(f"\nREFERENCIA gerada: {ref_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
