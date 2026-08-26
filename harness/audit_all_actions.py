#!/usr/bin/env python3
"""
ETAPA 13-Auditoria: Testa cada acao em pilot.SUPPORTED de forma independente.

Para CADA acao:
1. Carrega savestate limpo (eval_single_2000_lv5.state)
2. Executa via Executor.run() com parametros validos
3. Verifica efeito real no jogo (cash, telas, contadores)
4. Registra: funciona / falha / funciona-com-ressalva

Usa savestate limpo antes de cada teste.
"""

import sys
import os
import json
import shutil
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bridge import BizHawkBridge
from executor import Executor
from world import read_cash_k, at_main_menu_img
from macros import Game

# Caminho absoluto do savestate limpo
EVAL_STATE = Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"
AUDIT_LOG = Path(__file__).parent.parent / "AUDITORIA_ACOES.md"

# Acoes a auditar (ordem de pilot.SUPPORTED)
ACTIONS_TO_AUDIT = [
    ("wait", {}),  # Simples, deve sempre funcionar
    ("open_route", {"route": "NA01"}),  # Washington -> NewYork
    ("negotiate_slots", {"city": "Washington"}),  # Negociar na base
    ("buy_aircraft", {"model": 0, "qty": 1}),  # Comprar 1 aircraft modelo 0
    ("open_hub", {"region": 1}),  # Abrir hub America do Sul
    ("adjust_route", {"route": "NA01", "flights_week": 1}),  # Requer rota existente
    ("open_venture", {"city": "Washington", "type_index": 0}),  # Venture em Washington
    ("return_slots", {"city": "Washington"}),  # Devolve slots negociados
    ("ad_campaign", {}),  # Requer venture pronto - vai falhar no estado limpo
    ("close_hub", {"region": 1}),  # Fecha hub - vai falhar se nao tem hub
]

class AuditRunner:
    def __init__(self):
        self.bridge = None
        self.executor = None
        self.results = []
        self.start_cash = 1220000  # Caixa inicial do estado

    def setup(self):
        """Inicia BizHawk e conecta."""
        print("[AUDIT] Iniciando BizHawk...")
        # Assumir que EmuHawk ja esta rodando com a ROM carregada
        self.bridge = BizHawkBridge(config_path="bridge_config.json")
        self.executor = Executor(self.bridge)
        time.sleep(1)

    def load_savestate(self):
        """Carrega savestate limpo."""
        print(f"[AUDIT] Carregando savestate: {EVAL_STATE}")
        assert EVAL_STATE.exists(), f"Savestate nao encontrado: {EVAL_STATE}"
        self.bridge.load_state(str(EVAL_STATE))
        time.sleep(2)  # Aguardar carregamento

        # Verificar que estamos no menu principal
        for i in range(5):
            if at_main_menu_img(self.bridge):
                print("[AUDIT] Savestate carregado, estamos no menu principal")
                return True
            time.sleep(0.5)

        print("[AUDIT] AVISO: Pode nao estar no menu principal apos carga")
        return False

    def read_state_snapshot(self):
        """Le snapshot do estado do jogo."""
        try:
            cash = read_cash_k(self.bridge)
            at_menu = at_main_menu_img(self.bridge)
            return {"cash": cash, "at_menu": at_menu}
        except Exception as e:
            print(f"[AUDIT] Erro ao ler estado: {e}")
            return None

    def test_action(self, action_name, params):
        """Testa UMA acao completa."""
        print(f"\n{'='*70}")
        print(f"[AUDIT] Testando: {action_name}")
        print(f"[AUDIT] Parametros: {params}")
        print(f"{'='*70}")

        # 1. Carregar savestate limpo
        self.load_savestate()
        time.sleep(1)

        # 2. Ler estado inicial
        state_before = self.read_state_snapshot()
        if not state_before:
            return {
                "action": action_name,
                "params": params,
                "verdict": "FALHA - nao conseguiu ler estado inicial",
                "cash_before": None,
                "cash_after": None,
                "evidence": "Erro de conexao com BizHawk"
            }

        print(f"[AUDIT] Cash antes: {state_before['cash']}K")

        # 3. Executar acao via Executor.run()
        try:
            print(f"[AUDIT] Executando Executor.run()...")
            success, message = self.executor.run({
                "action": action_name,
                **params
            })
            print(f"[AUDIT] Resultado: {success}, Mensagem: {message}")
        except Exception as e:
            print(f"[AUDIT] EXCECAO ao executar: {e}")
            return {
                "action": action_name,
                "params": params,
                "verdict": "FALHA - excecao na execucao",
                "cash_before": state_before.get("cash"),
                "cash_after": None,
                "evidence": str(e)
            }

        # 4. Aguardar um pouco para estabilizar
        time.sleep(1)

        # 5. Ler estado final
        state_after = self.read_state_snapshot()
        if not state_after:
            return {
                "action": action_name,
                "params": params,
                "verdict": "INCONCLUSIVO - nao conseguiu ler estado final",
                "cash_before": state_before.get("cash"),
                "cash_after": None,
                "evidence": "Erro ao ler estado apos acao"
            }

        print(f"[AUDIT] Cash depois: {state_after['cash']}K")

        # 6. Analisar resultado
        cash_before = state_before.get("cash", 0)
        cash_after = state_after.get("cash", 0)
        cash_delta = cash_after - cash_before

        # Determinar veredito baseado no tipo de acao
        verdict = self._analyze_verdict(action_name, success, cash_delta, message)

        result = {
            "action": action_name,
            "params": params,
            "success": success,
            "message": message,
            "cash_before": cash_before,
            "cash_after": cash_after,
            "cash_delta": cash_delta,
            "verdict": verdict,
            "evidence": f"Cash: {cash_before}K -> {cash_after}K (delta {cash_delta}K)"
        }

        print(f"[AUDIT] Veredito: {verdict}")
        return result

    def _analyze_verdict(self, action_name, success, cash_delta, message):
        """Analisa e classifica o resultado."""

        # Acoes que debitam sempre
        debit_actions = ["open_route", "negotiate_slots", "buy_aircraft", "open_hub",
                        "open_venture", "ad_campaign"]

        # Acoes que creditam
        credit_actions = ["close_hub", "return_slots"]

        # Acoes neutras (cash nao muda)
        neutral_actions = ["wait", "adjust_route"]

        if success:
            if action_name in debit_actions:
                if cash_delta < 0:
                    return "FUNCIONA - cash debitado como esperado"
                else:
                    return "FUNCIONA-COM-RESSALVA - reporta sucesso mas cash nao mudou"
            elif action_name in credit_actions:
                if cash_delta > 0:
                    return "FUNCIONA - cash creditado como esperado"
                else:
                    return "FUNCIONA-COM-RESSALVA - reporta sucesso mas cash nao mudou"
            elif action_name in neutral_actions:
                return "FUNCIONA - execucao confirmada"
        else:
            # Falhou - pode ser recusa esperada ou bug
            if "sem efeito" in message.lower() or "cash inalterado" in message.lower():
                return "FALHA - nao teve efeito no jogo"
            elif "recusado" in message.lower() or "recusa" in message.lower():
                return "FALHA - acao foi recusada pelo jogo"
            else:
                return f"FALHA - {message}"

    def run_all(self):
        """Roda todos os testes."""
        print("\n" + "="*70)
        print("ETAPA 13-AUDITORIA - Testando todas as acoes de pilot.SUPPORTED")
        print("="*70 + "\n")

        self.setup()

        for action_name, params in ACTIONS_TO_AUDIT:
            result = self.test_action(action_name, params)
            self.results.append(result)
            time.sleep(1)  # Pausa entre testes

        self.generate_report()
        print("\n" + "="*70)
        print("AUDITORIA COMPLETA")
        print("="*70)

    def generate_report(self):
        """Gera AUDITORIA_ACOES.md com os resultados."""
        print(f"\n[AUDIT] Gerando relatorio em {AUDIT_LOG}...")

        report = """# AUDITORIA_ACOES.md - Etapa 13

## Resumo Executivo

Auditoria independente de TODAS as acoes em `pilot.SUPPORTED`, testadas uma por uma
a partir do mesmo savestate limpo (`eval_single_2000_lv5.state`).

**Data:** 2026-08-18 (sessão de auditoria)

| Ação | Parâmetros | Veredito | Cash Δ | Evidência |
|------|-----------|---------|--------|-----------|
"""

        # Tabela de resultados
        for result in self.results:
            action = result["action"]
            params = json.dumps(result["params"]) if result["params"] else "{}"
            verdict = result["verdict"]
            cash_delta = result.get("cash_delta", "?")
            evidence = result["evidence"]

            # Truncar para caber na tabela
            if len(evidence) > 50:
                evidence = evidence[:47] + "..."

            report += f"| {action} | {params} | {verdict} | {cash_delta}K | {evidence} |\n"

        report += "\n## Detalhes por Ação\n\n"

        # Detalhes completos
        for result in self.results:
            action = result["action"]
            report += f"### {action}\n\n"
            report += f"- **Parâmetros:** {json.dumps(result['params'])}\n"
            report += f"- **Sucesso reportado:** {result.get('success', '?')}\n"
            report += f"- **Mensagem:** {result.get('message', 'N/A')}\n"
            report += f"- **Cash antes:** {result.get('cash_before')}K\n"
            report += f"- **Cash depois:** {result.get('cash_after')}K\n"
            report += f"- **Delta:** {result.get('cash_delta')}K\n"
            report += f"- **Veredito:** {result['verdict']}\n"
            report += f"- **Evidência:** {result['evidence']}\n\n"

        report += "\n## Ações a Remover de pilot.SUPPORTED\n\n"
        report += "Ações que falharam na auditoria independente:\n\n"

        failed_actions = [r for r in self.results if "FALHA" in r["verdict"]]
        if failed_actions:
            for result in failed_actions:
                report += f"- **{result['action']}**: {result['verdict']}\n"
        else:
            report += "Nenhuma ação falhou (todas passaram na auditoria).\n"

        report += "\n## Ações a Manter\n\n"
        report += "Ações com veredito positivo:\n\n"

        passed_actions = [r for r in self.results if "FUNCIONA" in r["verdict"]]
        if passed_actions:
            for result in passed_actions:
                report += f"- **{result['action']}**: {result['verdict']}\n"

        # Escrever arquivo
        with open(AUDIT_LOG, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"[AUDIT] Relatorio escrito em {AUDIT_LOG}")

if __name__ == "__main__":
    runner = AuditRunner()
    try:
        runner.run_all()
    except KeyboardInterrupt:
        print("\n[AUDIT] Auditoria interrompida pelo usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n[AUDIT] Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
