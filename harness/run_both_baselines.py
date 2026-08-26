"""Run both baselines sequentially and generate REFERENCIA.md."""
import subprocess
import json
import pathlib
import time
import sys
import os

AQUI = pathlib.Path(__file__).resolve().parent
LOGS_DIR = AQUI.parent / "logs"
BASELINES_DIR = LOGS_DIR / "baselines"
PY = sys.executable

def run_baseline(model, city="NA13", turns=12, seed=0):
    """Run a single baseline evaluation."""
    print(f"\n[run_baselines] Starting {model} baseline...")

    cmd = [
        PY, str(AQUI / "run_eval.py"),
        "--model", model,
        "--city", city,
        "--turns", str(turns),
        "--seed", str(seed)
    ]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(cmd, cwd=str(AQUI), env=env)

    if result.returncode != 0:
        print(f"[run_baselines] {model} baseline failed with exit code {result.returncode}")
        return False

    print(f"[run_baselines] {model} baseline completed")
    return True

def get_latest_run(pattern):
    """Get most recent run directory matching pattern."""
    runs = sorted(LOGS_DIR.glob(pattern), key=lambda p: p.name, reverse=True)
    return runs[0] if runs else None

def has_resumo(run_dir):
    """Check if resumo.json exists."""
    return (run_dir / "resumo.json").exists() if run_dir else False

def wait_for_resumo(pattern, timeout_s=10800):
    """Wait for resumo.json to appear."""
    start = time.time()
    while time.time() - start < timeout_s:
        run = get_latest_run(pattern)
        if run and has_resumo(run):
            return run
        time.sleep(10)
    return None

def generate_referencia(random_run, greedy_run):
    """Generate REFERENCIA.md from completed runs."""

    if not (random_run and greedy_run):
        print("[run_baselines] ERROR: Missing run directories")
        return False

    # Read resumos
    random_resumo = json.loads((random_run / "resumo.json").read_text(encoding="utf-8"))
    greedy_resumo = json.loads((greedy_run / "resumo.json").read_text(encoding="utf-8"))

    # Generate REFERENCIA.md
    ref_path = BASELINES_DIR / "REFERENCIA.md"

    md = f"""# REFERENCIA DE BASELINES - ETAPA 3-RodarBaselines

Gerada: {time.strftime('%Y-%m-%d %H:%M:%S')}

**Objetivo:** Gerar numeros de referencia para comparacao de desempenho com modelos LLM.

**Configuracao:**
- Sede: NA13 (Washington)
- Ano: 2000
- Nivel: 5
- Turnos pedidos: 12
- Seed: 0

---

## Random Baseline (Aleatoria-Legal)

**Diretorio:** {random_run.name}

### Resultados

| Metrica | Valor |
|---------|-------|
| Turnos completados | {random_resumo['turnos_rodados']}/12 |
| Acoes pedidas pelo modelo | {random_resumo['acoes_pedidas_pelo_modelo']} |
| Acoes executadas | {random_resumo['acoes_executadas']} |
| Acoes com efeito verificado | {random_resumo['acoes_com_efeito_verificado']} |
| Taxa de efeito (inclui wait) | {random_resumo['taxa_efeito_verificado_pct']}% |
| Acoes substantivas executadas | {random_resumo['acoes_substantivas_executadas']} |
| Acoes substantivas com efeito | {random_resumo['acoes_substantivas_com_efeito']} |
| Taxa efeito substantivas | {random_resumo['taxa_efeito_substantivas_pct']}% |
| Acoes wait | {random_resumo['acoes_wait']} |
| Turnos sem acao substantiva | {random_resumo['turnos_sem_acao_substantiva']} |
| Taxa sobre pedidas | {random_resumo['taxa_sobre_pedidas_pct']}% |
| Cidades consultadas | {random_resumo['cidades_consultadas']} |
| Caixa final | {random_resumo['caixa_final_k']}K |
| Caixa fonte | {random_resumo['caixa_fonte']} |

### Acoes por Tipo
"""

    if random_resumo['acoes_por_tipo']:
        md += "\n| Tipo | Pedidas | Com Efeito | Delta Caixa |\n"
        md += "|------|---------|------------|-------------|\n"
        for acao, stats in sorted(random_resumo['acoes_por_tipo'].items()):
            md += f"| {acao} | {stats['pedidas']} | {stats['efeito']} | {stats.get('delta_caixa_k', 'N/A')}K |\n"
    else:
        md += "\n(Nenhuma acao registrada)\n"

    if random_resumo['placar']:
        md += f"\n### Placar\n\n{json.dumps(random_resumo['placar'], indent=2)}\n"
    else:
        md += "\n### Placar\n\nN/A\n"

    md += f"""
Fonte: {random_resumo['placar_fonte']}

---

## Greedy Baseline (Gulosa-Heuristica)

**Diretorio:** {greedy_run.name}

### Resultados

| Metrica | Valor |
|---------|-------|
| Turnos completados | {greedy_resumo['turnos_rodados']}/12 |
| Acoes pedidas pelo modelo | {greedy_resumo['acoes_pedidas_pelo_modelo']} |
| Acoes executadas | {greedy_resumo['acoes_executadas']} |
| Acoes com efeito verificado | {greedy_resumo['acoes_com_efeito_verificado']} |
| Taxa de efeito (inclui wait) | {greedy_resumo['taxa_efeito_verificado_pct']}% |
| Acoes substantivas executadas | {greedy_resumo['acoes_substantivas_executadas']} |
| Acoes substantivas com efeito | {greedy_resumo['acoes_substantivas_com_efeito']} |
| Taxa efeito substantivas | {greedy_resumo['taxa_efeito_substantivas_pct']}% |
| Acoes wait | {greedy_resumo['acoes_wait']} |
| Turnos sem acao substantiva | {greedy_resumo['turnos_sem_acao_substantiva']} |
| Taxa sobre pedidas | {greedy_resumo['taxa_sobre_pedidas_pct']}% |
| Cidades consultadas | {greedy_resumo['cidades_consultadas']} |
| Caixa final | {greedy_resumo['caixa_final_k']}K |
| Caixa fonte | {greedy_resumo['caixa_fonte']} |

### Acoes por Tipo
"""

    if greedy_resumo['acoes_por_tipo']:
        md += "\n| Tipo | Pedidas | Com Efeito | Delta Caixa |\n"
        md += "|------|---------|------------|-------------|\n"
        for acao, stats in sorted(greedy_resumo['acoes_por_tipo'].items()):
            md += f"| {acao} | {stats['pedidas']} | {stats['efeito']} | {stats.get('delta_caixa_k', 'N/A')}K |\n"
    else:
        md += "\n(Nenhuma acao registrada)\n"

    if greedy_resumo['placar']:
        md += f"\n### Placar\n\n{json.dumps(greedy_resumo['placar'], indent=2)}\n"
    else:
        md += "\n### Placar\n\nN/A\n"

    md += f"""
Fonte: {greedy_resumo['placar_fonte']}

---

## Resumo Comparativo

| Aspecto | Random | Greedy | Diferenca |
|---------|--------|--------|-----------|
| Turnos completados | {random_resumo['turnos_rodados']}/12 | {greedy_resumo['turnos_rodados']}/12 | {greedy_resumo['turnos_rodados'] - random_resumo['turnos_rodados']} |
| Acoes executadas | {random_resumo['acoes_executadas']} | {greedy_resumo['acoes_executadas']} | {greedy_resumo['acoes_executadas'] - random_resumo['acoes_executadas']} |
| Taxa efeito verificado | {random_resumo['taxa_efeito_verificado_pct']}% | {greedy_resumo['taxa_efeito_verificado_pct']}% | {(greedy_resumo['taxa_efeito_verificado_pct'] or 0) - (random_resumo['taxa_efeito_verificado_pct'] or 0)}% |
| Acoes substantivas | {random_resumo['acoes_substantivas_executadas']} | {greedy_resumo['acoes_substantivas_executadas']} | {greedy_resumo['acoes_substantivas_executadas'] - random_resumo['acoes_substantivas_executadas']} |
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
    print(f"[run_baselines] REFERENCIA gerada: {ref_path}")
    return True

def main():
    print("[run_baselines] ETAPA 3-RodarBaselines — Executando ambas baselines sequencialmente")

    # Run random baseline
    if not run_baseline("random"):
        print("[run_baselines] Falha ao rodar random baseline")
        return 1

    # Wait for random resumo.json
    random_run = wait_for_resumo("eval_random_NA13_*")
    if not random_run:
        print("[run_baselines] Random baseline nao completou (timeout)")
        return 1

    print(f"[run_baselines] Random baseline completado: {random_run.name}")

    # Run greedy baseline
    if not run_baseline("greedy"):
        print("[run_baselines] Falha ao rodar greedy baseline")
        return 1

    # Wait for greedy resumo.json
    greedy_run = wait_for_resumo("eval_greedy_NA13_*")
    if not greedy_run:
        print("[run_baselines] Greedy baseline nao completou (timeout)")
        return 1

    print(f"[run_baselines] Greedy baseline completado: {greedy_run.name}")

    # Generate REFERENCIA.md
    if not generate_referencia(random_run, greedy_run):
        print("[run_baselines] Falha ao gerar REFERENCIA.md")
        return 1

    print("[run_baselines] SUCESSO — Ambas baselines rodadas, REFERENCIA.md gerada")
    return 0

if __name__ == "__main__":
    sys.exit(main())
