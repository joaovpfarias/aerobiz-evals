#!/usr/bin/env python3
"""
ETAPA 1a-PartidaLonga: Versao rapida
Avanca ~10 trimestres (em vez de 20) com end_turn, abre rotas, e captura
o estado do ranking regional.

OBJETIVO: verificar se Regional Rankings fica com cores (dados).
"""
import sys
from pathlib import Path
import time
import json

sys.path.insert(0, str(Path(__file__).parent))

from bridge import BizHawkBridge
from executor import Executor
from macros import Game
from world import (
    read_quarter_index, date_label, read_cash_k,
    on_regional_rankings_img, on_quarterly_report_img
)
from PIL import Image

OUTPUT_STATE = Path(__file__).parent.parent / "states" / "eval_2005_rankings.state"
LOG_DIR = Path(__file__).parent.parent / "logs" / "quick_advance"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def log_msg(msg):
    """Print e salva em log."""
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with (LOG_DIR / "run.log").open("a") as f:
        f.write(line + "\n")

def main():
    log_msg("=" * 70)
    log_msg("INICIANDO ETAPA 1a-PartidaLonga (VERSAO RAPIDA)")
    log_msg(f"Output: {OUTPUT_STATE}")
    log_msg("=" * 70)

    # === SETUP ===
    bridge = BizHawkBridge()
    game = Game(bridge, LOG_DIR)
    executor = Executor(bridge)

    # === CHECK CURRENT STATE ===
    quarter_start = read_quarter_index(bridge)
    cash_start = read_cash_k(bridge)
    log_msg(f"Estado atual emulador: {date_label(quarter_start)} (trimestre {quarter_start}), Cash={cash_start}K")

    # === AVANCA 8 TRIMESTRES COM END_TURN ===
    num_turns = 8
    target_quarter = quarter_start + num_turns
    log_msg(f"Objetivo: {date_label(target_quarter)} (trimestre {target_quarter})")
    log_msg("Iniciando loop de end_turn...")

    turns_executed = 0
    turns_failed = 0

    for turn_num in range(num_turns):
        quarter_now = read_quarter_index(bridge)
        if quarter_now >= target_quarter:
            log_msg(f"Alcancou objetivo: {date_label(quarter_now)} (trimestre {quarter_now})")
            break

        log_msg(f"  Turno {turn_num + 1}/{num_turns}: {date_label(quarter_now)} -> ?")

        try:
            ok, detail = game.end_turn()
            if ok:
                quarter_after = read_quarter_index(bridge)
                cash_after = read_cash_k(bridge)
                log_msg(f"    OK -> {date_label(quarter_after)}, Cash={cash_after}K")
                turns_executed += 1
            else:
                log_msg(f"    FALHA: {detail}")
                turns_failed += 1
                if turns_failed > 2:
                    log_msg("ABORTANDO: 2 falhas consecutivas em end_turn")
                    return False
        except Exception as e:
            log_msg(f"    EXCECAO: {e}")
            turns_failed += 1

        time.sleep(0.2)  # Pequeno delay entre turnos

    log_msg(f"\nResumo: {turns_executed} turnos executados, {turns_failed} falhas")

    # === ABRE ROTAS PARA GERAR RANKING ===
    log_msg("\nAbrindo rotas para gerar dados de ranking...")

    routes_to_open = [
        {"to": "London"},      # Europa
        {"to": "Tokyo"},       # SE Asia
        {"to": "Sydney"},      # Oceania
    ]

    for i, route_params in enumerate(routes_to_open):
        log_msg(f"  Rota {i+1}: open_route({route_params['to']})")
        try:
            ok, detail = executor.run({"action": "open_route", "params": route_params})
            if ok:
                log_msg(f"    OK: {detail}")
            else:
                log_msg(f"    FALHA: {detail}")
        except Exception as e:
            log_msg(f"    EXCECAO: {e}")
        time.sleep(0.5)

    # === CAPTURA TELAS DE RELATORIO ===
    log_msg("\nCapturando telas de relatorio...")

    try:
        game.back_to_menu()
        game.open_cmd("info")

        # Navega ate finance (indice 3)
        for _ in range(3):
            bridge.press("Right", hold=3, wait=10)

        bridge.press("A", hold=5, wait=40)
        game.b.advance(200)

        # Primeira tela: Quarterly Report
        quarterly_path = game.shot("quarterly_report_final")
        log_msg(f"  Capturado: Quarterly Report -> {Path(quarterly_path).name}")

        img = Image.open(quarterly_path).convert("RGB")
        if on_quarterly_report_img(img):
            log_msg("    CONFERE: e Quarterly Report")

            # Avanca para Regional Rankings
            bridge.press("A", hold=5, wait=40)
            game.b.advance(200)

            rankings_path = game.shot("regional_rankings_final")
            log_msg(f"  Capturado: Regional Rankings -> {Path(rankings_path).name}")

            img_rankings = Image.open(rankings_path).convert("RGB")
            if on_regional_rankings_img(img_rankings):
                log_msg("    CONFERE: e Regional Rankings")

                # Analisa quais regioes tem cores (dados)
                log_msg("    Analisando caixas de regiao...")
                px = img_rankings.load()

                regions = {
                    "Europe": (24, 40, 88, 68),
                    "N America": (180, 48, 244, 68),
                    "SE Asia": (104, 56, 168, 84),
                    "Mid East": (56, 112, 124, 140),
                    "Oceania": (140, 120, 208, 140),
                    "Africa": (16, 168, 80, 196),
                    "S America": (180, 168, 244, 196),
                }

                regions_with_data = []
                for region, (x0, y0, x1, y1) in regions.items():
                    colored = 0
                    total = (x1 - x0) * (y1 - y0)
                    for x in range(x0, min(x1, img_rankings.width)):
                        for y in range(y0, min(y1, img_rankings.height)):
                            r, g, b = px[x, y]
                            if (r, g, b) != (0, 0, 0):
                                colored += 1

                    frac = colored / total if total > 0 else 0
                    status = "COM COR" if colored > 0 else "PRETA"
                    log_msg(f"      {region:12} -> {colored:4}/{total:4} = {frac:.1%} {status}")

                    if colored > 0:
                        regions_with_data.append(region)

                if regions_with_data:
                    log_msg(f"    RESULTADO: {len(regions_with_data)} regioes com dados: {regions_with_data}")
                else:
                    log_msg(f"    RESULTADO: todas as caixas ainda estao pretas (sem dados)")
            else:
                log_msg("    ERRO: nao conseguiu detectar Regional Rankings")
                log_msg("    Pixel(30,60) sera usado para debug")
                px = img_rankings.load()
                print(f"      Pixel(30,60) = {px[30, 60]}")
        else:
            log_msg("    ERRO: nao conseguiu detectar Quarterly Report")
    except Exception as e:
        log_msg(f"    EXCECAO ao capturar telas: {e}")
        import traceback
        traceback.print_exc()

    # === SALVA SAVESTATE ===
    log_msg("\nSalvando savestate final...")
    try:
        game.back_to_menu()
        time.sleep(1)
        bridge.save(str(OUTPUT_STATE))
        time.sleep(2)

        if OUTPUT_STATE.exists():
            size = OUTPUT_STATE.stat().st_size
            log_msg(f"SUCESSO: Savestate salvo -> {OUTPUT_STATE.name} ({size} bytes)")
        else:
            log_msg(f"ERRO: Savestate nao foi criado")
            return False
    except Exception as e:
        log_msg(f"EXCECAO ao salvar: {e}")

    # === RELATORIO FINAL ===
    quarter_final = read_quarter_index(bridge)
    cash_final = read_cash_k(bridge)

    summary = {
        "start": {"quarter": quarter_start, "date": date_label(quarter_start), "cash": cash_start},
        "end": {"quarter": quarter_final, "date": date_label(quarter_final), "cash": cash_final},
        "turns_executed": turns_executed,
        "turns_failed": turns_failed,
        "quarters_advanced": quarter_final - quarter_start,
        "routes_opened": 3,
        "regions_with_data": regions_with_data if 'regions_with_data' in locals() else None,
    }

    log_msg("\n" + "=" * 70)
    log_msg("RESUMO FINAL")
    log_msg("=" * 70)
    log_msg(f"Inicio:      {summary['start']['date']} (Q{summary['start']['quarter']}), Cash={summary['start']['cash']}K")
    log_msg(f"Fim:         {summary['end']['date']} (Q{summary['end']['quarter']}), Cash={summary['end']['cash']}K")
    log_msg(f"Avanço:      {summary['quarters_advanced']} trimestres")
    log_msg(f"Turnos exec: {summary['turns_executed']}")
    log_msg(f"Turnos fail: {summary['turns_failed']}")
    log_msg(f"Rotas:       {summary['routes_opened']}")
    if summary['regions_with_data']:
        log_msg(f"Rankings:    {len(summary['regions_with_data'])} regioes com dados")
    else:
        log_msg(f"Rankings:    0 regioes com dados")
    log_msg(f"Savestate:   {OUTPUT_STATE.name}")
    log_msg("=" * 70)

    # Salva summary
    (LOG_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        log_msg(f"EXCECAO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
