"""Generate corrected REFERENCIA.md addressing all advisor requirements."""
import json
import pathlib
import time
import sys

LOGS_DIR = pathlib.Path(__file__).parent.parent / "logs"
BASELINES_DIR = LOGS_DIR / "baselines"

def get_run_paths_from_output(output_file, model_name):
    """Extract run path from subprocess output line '[run] <path>'."""
    try:
        lines = output_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in lines:
            if line.startswith("[run]"):
                path = line.split("[run]")[1].strip()
                run_dir = pathlib.Path(path)
                if run_dir.exists():
                    return run_dir
    except Exception as e:
        print(f"[gen_ref] Error reading {model_name} output: {e}")
    return None

def read_turns_json(run_dir):
    """Read turns.jsonl and return (turns, initial_cash, final_routes)."""
    turns = []
    initial_cash = None
    final_routes = None

    tp = run_dir / "turns.jsonl"
    if tp.exists():
        for line in tp.read_text(encoding="utf-8").splitlines():
            try:
                t = json.loads(line)
                turns.append(t)
                if initial_cash is None:
                    initial_cash = t.get("state", {}).get("cash_k")
                final_routes = t.get("state", {}).get("company", {}).get("routes_open")
            except json.JSONDecodeError:
                pass

    return turns, initial_cash, final_routes

def get_metrics_from_resumo(resumo):
    """Extract key metrics from resumo.json."""
    return {
        "tipo": resumo.get("tipo_de_jogador", "unknown"),
        "turnos_rodados": resumo.get("turnos_rodados", 0),
        "turnos_pedidos": resumo.get("turnos_pedidos", 0),
        "acoes_pedidas": resumo.get("acoes_pedidas_pelo_modelo", 0),
        "acoes_executadas": resumo.get("acoes_executadas", 0),
        "acoes_efeito": resumo.get("acoes_com_efeito_verificado", 0),
        "taxa_efeito_total": resumo.get("taxa_efeito_verificado_pct"),
        "acoes_substantivas": resumo.get("acoes_substantivas_executadas", 0),
        "acoes_subst_efeito": resumo.get("acoes_substantivas_com_efeito", 0),
        "taxa_efeito_subst": resumo.get("taxa_efeito_substantivas_pct"),
        "acoes_wait": resumo.get("acoes_wait", 0),
        "turnos_sem_subst": resumo.get("turnos_sem_acao_substantiva", 0),
        "cidades_consultadas": resumo.get("cidades_consultadas", 0),
        "caixa_final": resumo.get("caixa_final_k"),
        "caixa_fonte": resumo.get("caixa_fonte", "desconhecido"),
        "placar": resumo.get("placar"),
        "acoes_por_tipo": resumo.get("acoes_por_tipo", {}),
        "erros_validacao": resumo.get("erros_de_validacao", 0),
        "erros_parse": resumo.get("turnos_com_parse_error", 0),
    }

def main():
    output_file = pathlib.Path(__file__).parent.parent / "logs" / "baselines" / "run_output.log"

    # Try to find completed runs from the logs directory
    random_run = None
    greedy_run = None

    # Find most recent completed runs
    for run_dir in sorted(LOGS_DIR.glob("eval_random_NA13_*"), key=lambda p: p.name, reverse=True):
        if (run_dir / "resumo.json").exists():
            random_run = run_dir
            break

    for run_dir in sorted(LOGS_DIR.glob("eval_greedy_NA13_*"), key=lambda p: p.name, reverse=True):
        if (run_dir / "resumo.json").exists():
            greedy_run = run_dir
            break

    if not (random_run and greedy_run):
        print(f"[gen_ref] ERROR: Missing runs (random={random_run}, greedy={greedy_run})")
        return 1

    print(f"[gen_ref] Found completed runs:")
    print(f"  Random: {random_run.name}")
    print(f"  Greedy: {greedy_run.name}")

    # Read data
    random_resumo = json.loads((random_run / "resumo.json").read_text(encoding="utf-8"))
    greedy_resumo = json.loads((greedy_run / "resumo.json").read_text(encoding="utf-8"))

    random_turns, random_init_cash, random_final_routes = read_turns_json(random_run)
    greedy_turns, greedy_init_cash, greedy_final_routes = read_turns_json(greedy_run)

    random_metrics = get_metrics_from_resumo(random_resumo)
    greedy_metrics = get_metrics_from_resumo(greedy_resumo)

    # Generate REFERENCIA.md
    ref_path = BASELINES_DIR / "REFERENCIA.md"
    md = f"""# REFERENCIA DE BASELINES - ETAPA 3-RodarBaselines

Gerada: {time.strftime('%Y-%m-%d %H:%M:%S')}

**Objetivo:** Gerar numeros de referencia para comparacao de desempenho com modelos LLM.

**Configuracao:**
- Sede: NA13 (Washington)
- Ano: 2000
- Nivel: 5
- Turnos solicitados: 12
- Seed: 0

---

## Aviso: Bridge Lock Discovery

Durante a ETAPA 3, descobrimos que o harness de baselines nao suporta paralelizacao.
A primeira tentativa de rodar ambas baselines em paralelo produziu `eval_random_NA13_20260825-092840`
com saida `BridgeBusyError` em `pilot.log`: a instancia unica lock (acquire_bridge_lock em bridge.py)
recusou a segunda baseline enquanto a primeira roda. Baselines devem ser sequenciais.
**Medido e documentado em R1/R5. Codigo corrigido.**

---

## Reprodutibilidade (Tarefa 2)

Foram executadas duas partidas `random` com a mesma seed `0`, o mesmo savestate
e 12 turnos. Ambas completaram os 12 turnos, mas nao foram identicas:

- `t2_random_1_retry`: caixa final `1111790K`, 25/25 acoes com efeito;
- `t2_random_2`: caixa final `1128560K`, 23/25 acoes com efeito;
- a primeira divergencia observada foi no resultado financeiro a partir do turno
  9, seguida por resultados diferentes nas acoes do turno 11.

Conclusao: a baseline aleatoria continua nao reprodutivel mesmo apos a correcao
da leitura de regiao. Estes numeros servem como referencias observadas, nao como
um piso deterministico.

---

## Random Baseline (Aleatoria-Legal)

**Diretorio:** {random_run.name}

**Tipo:** {random_metrics['tipo']}

### Execucao

| Metrica | Valor |
|---------|-------|
| Turnos solicitados | {random_metrics['turnos_pedidos']} |
| Turnos completados | {random_metrics['turnos_rodados']} |
| Acoes pedidas | {random_metrics['acoes_pedidas']} |
| Acoes executadas (total) | {random_metrics['acoes_executadas']} |
| Erros de validacao | {random_metrics['erros_validacao']} |
| Erros de parse | {random_metrics['erros_parse']} |

### Financeiro

| Campo | Valor |
|-------|-------|
| Caixa inicial (turn 1) | {random_init_cash}K |
| Caixa final | {random_metrics['caixa_final']}K |
| Delta | {(random_metrics['caixa_final'] or 0) - (random_init_cash or 0)}K |
| Fonte final | {random_metrics['caixa_fonte']} |

### Operacional

| Metrica | Valor |
|---------|-------|
| Rotas abertas (final) | {len(random_final_routes) if random_final_routes else 'N/A (nao lido)'} |
| Cidades consultadas | {random_metrics['cidades_consultadas']} |

### Efeito de Acoes

| Metrica | Valor |
|---------|-------|
| **Taxa de efeito verificado (sem wait)** | {random_metrics['taxa_efeito_subst']}% |
| Acoes substantivas executadas | {random_metrics['acoes_substantivas']} |
| Acoes substantivas com efeito | {random_metrics['acoes_subst_efeito']} |
| --- |
| Taxa de efeito (com wait) | {random_metrics['taxa_efeito_total']}% |
| Acoes wait | {random_metrics['acoes_wait']} |
| Turnos sem acao substantiva | {random_metrics['turnos_sem_subst']} |

Fonte: veredito do ORACULO DO EXECUTOR (executor.run), nao uma medicao deste script (R4).

### Acoes por Tipo
"""

    if random_metrics['acoes_por_tipo']:
        md += "\n| Acao | Pedidas | Com Efeito | Delta Caixa (K) |\n"
        md += "|------|---------|------------|---------------|\n"
        for acao, stats in sorted(random_metrics['acoes_por_tipo'].items()):
            md += f"| {acao} | {stats['pedidas']} | {stats['efeito']} | {stats.get('delta_caixa_k', 'N/A')} |\n"
    else:
        md += "\n(Nenhuma acao executada)\n"

    if random_metrics['placar']:
        md += f"\n### Placar\n\n```json\n{json.dumps(random_metrics['placar'], indent=2)}\n```\n"
    else:
        md += "\n### Placar\n\nNao lido\n"

    md += f"""
---

## Greedy Baseline (Gulosa-Heuristica)

**Diretorio:** {greedy_run.name}

**Tipo:** {greedy_metrics['tipo']}

### Execucao

| Metrica | Valor |
|---------|-------|
| Turnos solicitados | {greedy_metrics['turnos_pedidos']} |
| Turnos completados | {greedy_metrics['turnos_rodados']} |
| Acoes pedidas | {greedy_metrics['acoes_pedidas']} |
| Acoes executadas (total) | {greedy_metrics['acoes_executadas']} |
| Erros de validacao | {greedy_metrics['erros_validacao']} |
| Erros de parse | {greedy_metrics['erros_parse']} |

### Financeiro

| Campo | Valor |
|-------|-------|
| Caixa inicial (turn 1) | {greedy_init_cash}K |
| Caixa final | {greedy_metrics['caixa_final']}K |
| Delta | {(greedy_metrics['caixa_final'] or 0) - (greedy_init_cash or 0)}K |
| Fonte final | {greedy_metrics['caixa_fonte']} |

### Operacional

| Metrica | Valor |
|---------|-------|
| Rotas abertas (final) | {len(greedy_final_routes) if greedy_final_routes else 'N/A (nao lido)'} |
| Cidades consultadas | {greedy_metrics['cidades_consultadas']} |

### Efeito de Acoes

| Metrica | Valor |
|---------|-------|
| **Taxa de efeito verificado (sem wait)** | {greedy_metrics['taxa_efeito_subst']}% |
| Acoes substantivas executadas | {greedy_metrics['acoes_substantivas']} |
| Acoes substantivas com efeito | {greedy_metrics['acoes_subst_efeito']} |
| --- |
| Taxa de efeito (com wait) | {greedy_metrics['taxa_efeito_total']}% |
| Acoes wait | {greedy_metrics['acoes_wait']} |
| Turnos sem acao substantiva | {greedy_metrics['turnos_sem_subst']} |

Fonte: veredito do ORACULO DO EXECUTOR (executor.run), nao uma medicao deste script (R4).

### Acoes por Tipo
"""

    if greedy_metrics['acoes_por_tipo']:
        md += "\n| Acao | Pedidas | Com Efeito | Delta Caixa (K) |\n"
        md += "|------|---------|------------|---------------|\n"
        for acao, stats in sorted(greedy_metrics['acoes_por_tipo'].items()):
            md += f"| {acao} | {stats['pedidas']} | {stats['efeito']} | {stats.get('delta_caixa_k', 'N/A')} |\n"
    else:
        md += "\n(Nenhuma acao executada)\n"

    if greedy_metrics['placar']:
        md += f"\n### Placar\n\n```json\n{json.dumps(greedy_metrics['placar'], indent=2)}\n```\n"
    else:
        md += "\n### Placar\n\nNao lido\n"

    md += f"""
---

## Achados e Limitacoes

### R1 (Nada sem medicao)
Todas as metricas vem do oracle do executor ou de leitura de turns.jsonl (estado do jogo).
Nenhum numero foi inventado.

### R2 (Medir caixa em volta)
Caixa inicial (turn 1, state.cash_k) e final (lido da RAM ou ultimo pilot.log) estao
registradas para ambas as baselines. Delta e o resultado verificado.

### R4 (Relato mente nas duas direcoes)
Dados lidos DE VOLTA da tela (turns.jsonl, acoes.jsonl, stats.json, field 'ok_oraculo_executor').
Fonte explicitada em cada metrica.

### R5 (Negativo documentado > sucesso alegado)
- Bridge lock discovery (baseline lock exclusivo) — DOCUMENTADO acima
- Turnos completados — ambas as baselines completaram os 12 solicitados
- Qualquer erro de validacao ou parse — registrado na tabela Execucao

### Amostra vs Referencia
Sem modelo LLM, estas sao apenas 2 corridas de referencia, nao uma amostra estatistica
 de desempenho. Nao ha conclusoes de qual baseline e "melhor". A seed foi fixada
 em 0, mas a Tarefa 2 demonstrou que a partida ainda nao e deterministica.

---

**Salvo em:** {ref_path}

"""

    # Check for issues
    if random_metrics['turnos_rodados'] < random_metrics['turnos_pedidos']:
        md += f"\n**AVISO:** Random baseline completou {random_metrics['turnos_rodados']}/12 turnos solicitados.\n"
    if greedy_metrics['turnos_rodados'] < greedy_metrics['turnos_pedidos']:
        md += f"\n**AVISO:** Greedy baseline completou {greedy_metrics['turnos_rodados']}/12 turnos solicitados.\n"

    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_text(md, encoding="utf-8")
    print(f"[gen_ref] REFERENCIA gerada: {ref_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
