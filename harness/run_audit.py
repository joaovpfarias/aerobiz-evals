#!/usr/bin/env python3
"""
ETAPA 13-Auditoria: Orquestrador de testes

Roda cada teste de acao e compila relatorio em AUDITORIA_ACOES.md
"""

import subprocess
import sys
from pathlib import Path
import time
import json

HARNESS_DIR = Path(__file__).parent
AUDIT_LOG = HARNESS_DIR.parent / "AUDITORIA_ACOES.md"

# Acoes a auditar e seus scripts de teste
AUDIT_TESTS = [
    ("wait", "audit_wait.py"),
    ("negotiate_slots", "audit_negotiate_slots.py"),
    ("open_route", "audit_open_route.py"),
    ("buy_aircraft", "audit_buy_aircraft.py"),
    ("open_hub", "audit_open_hub.py"),
    ("adjust_route", "audit_adjust_route.py"),
    ("open_venture", "audit_open_venture.py"),
    ("return_slots", "audit_return_slots.py"),
    ("ad_campaign", "audit_ad_campaign.py"),
    ("close_hub", "audit_close_hub.py"),
]

def run_test(action_name, script_name):
    """Roda um teste de acao e retorna resultado."""
    print(f"\n{'='*70}")
    print(f"Rodando teste: {action_name}")
    print(f"{'='*70}\n")

    script_path = HARNESS_DIR / script_name
    if not script_path.exists():
        return {
            "action": action_name,
            "status": "SKIPPED",
            "reason": f"Script nao encontrado: {script_name}"
        }

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(HARNESS_DIR),
            capture_output=True,
            text=True,
            timeout=120
        )

        # Parse veredito do output
        output = result.stdout + result.stderr
        print(output)

        if "VEREDITO: FUNCIONA" in output:
            verdict = "FUNCIONA"
        elif "VEREDITO: FUNCIONA-COM-RESSALVA" in output:
            verdict = "FUNCIONA-COM-RESSALVA"
        elif "VEREDITO: FALHA" in output:
            verdict = "FALHA"
        else:
            verdict = "INCONCLUSIVO"

        return {
            "action": action_name,
            "status": "COMPLETED",
            "verdict": verdict,
            "returncode": result.returncode,
            "output_lines": output.split("\n")[-10:]  # Ultimas 10 linhas
        }

    except subprocess.TimeoutExpired:
        return {
            "action": action_name,
            "status": "TIMEOUT",
            "reason": "Teste excedeu tempo limite (120s)"
        }
    except Exception as e:
        return {
            "action": action_name,
            "status": "ERROR",
            "reason": str(e)
        }

def generate_report(results):
    """Gera AUDITORIA_ACOES.md"""
    report = """# AUDITORIA_ACOES.md - ETAPA 13-Auditoria

## Resumo

Auditoria independente de TODAS as acoes em `pilot.SUPPORTED`, testadas uma por uma
a partir do mesmo savestate limpo (`eval_single_2000_lv5.state`).

Cada acao e testada:
1. Carregando savestate limpo
2. Lendo estado inicial (cash, staff, quarter, etc.)
3. Executando via `Executor.run()`
4. Lendo estado final e verificando efeito real no jogo
5. Registrando: FUNCIONA / FUNCIONA-COM-RESSALVA / FALHA

**Data:** 2026-08-18
**Status:** Auditoria em progresso

---

## Resultados por Ação

| Ação | Status | Veredito | Notas |
|------|--------|----------|-------|
"""

    for result in results:
        action = result["action"]
        status = result["status"]
        verdict = result.get("verdict", "?")
        reason = result.get("reason", "")

        if status == "COMPLETED":
            row = f"| {action} | ✓ | {verdict} | - |"
        elif status == "SKIPPED":
            row = f"| {action} | - | - | {reason} |"
        elif status == "TIMEOUT":
            row = f"| {action} | ⏱️ | TIMEOUT | {reason} |"
        else:
            row = f"| {action} | ✗ | ERROR | {reason} |"

        report += row + "\n"

    report += "\n---\n\n## Detalhes\n\n"

    # Seção de detalhes
    for result in results:
        if result["status"] == "COMPLETED":
            action = result["action"]
            verdict = result["verdict"]
            report += f"### {action}\n"
            report += f"- **Veredito:** {verdict}\n"
            report += f"- **Código de retorno:** {result['returncode']}\n"
            report += f"- **Output (últimas linhas):**\n"
            report += "```\n"
            report += "\n".join(result["output_lines"])
            report += "\n```\n\n"

    report += "---\n\n## Próximos Passos\n\n"
    report += "1. Executar todos os testes\n"
    report += "2. Remover acoes com FALHA de `pilot.SUPPORTED`\n"
    report += "3. Investigar acoes com FUNCIONA-COM-RESSALVA\n"
    report += "4. Documentar em ACTION_SPACE.md e CALIBRATION.md\n"

    # Escrever arquivo
    with open(AUDIT_LOG, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n[AUDIT] Relatorio escrito em {AUDIT_LOG}")

if __name__ == "__main__":
    results = []

    for action_name, script_name in AUDIT_TESTS:
        result = run_test(action_name, script_name)
        results.append(result)
        time.sleep(1)  # Pausa entre testes

    generate_report(results)

    print("\n" + "="*70)
    print("AUDITORIA COMPLETADA")
    print("="*70)
