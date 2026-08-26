#!/usr/bin/env python3
"""
ETAPA 5c - Varredura de todas as 96 cidades do mapa

Objetivo: varrer as 95+ cidades com o leitor read_city_panel e cachear em JSON.

Padrão de navegação: prova_city_panel_vivo.py (3/3 com cash estável).

Contrato: leitor PURO de frame — não navega além do que point_cursor_at_world + A + B fazem.

ENTREGA: harness/city_intel.json com uma entrada por cidade lida + estatísticas.

REGRAS (R2, R3, R4, R5):
- Mede caixa ANTES e DEPOIS de CADA `A` e ABORTA se cair
- Volta ao MAPA com `B`, não ao menu
- Armazena cursor_verificado de point_cursor_at_world (prova de acerto)
- Verifica distinctness de name_hash ao final (detecta regiões erradas)
- Conta None-per-campo (digito 8 falta do mini-atlas)
"""

import json
import pathlib
import sys
import time
from collections import defaultdict

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge
import world
from executor import Executor, STEP_SETTLE

RAIZ = HERE.parent
LOG_DIR = RAIZ / "logs" / "etapa5c"
LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = HERE / "city_intel.json"
BASE = str(RAIZ / "states" / "_e3b_base.state")


def main():
    # Setup
    raw = bridge.BizHawkBridge(timeout=180)
    ex = Executor(raw)
    raw.load(BASE)
    raw.advance(120)

    caixa0 = world.read_cash_k(raw)
    log = []

    def log_msg(msg, level="INFO"):
        print(f"[{level}] {msg}", flush=True)
        log.append((time.time(), level, msg))

    if caixa0 is None:
        log_msg("ERRO: Não conseguiu ler caixa inicial", "ERRO")
        return 1

    log_msg(f"Caixa inicial: {caixa0}K")

    # Carregar dados já processados se houver
    intel = {}
    failed_reads = []
    if OUTPUT_FILE.exists():
        intel = json.loads(OUTPUT_FILE.read_text())
        log_msg(f"Carregadas {len(intel)} cidades já processadas")

    all_cities = sorted(world.WORLD_CITIES.keys())
    remaining = [c for c in all_cities if c not in intel]

    if not remaining:
        log_msg("Varredura já completa!")
        report_final(intel, caixa0, world.read_cash_k(raw), failed_reads, log)
        return 0

    log_msg(f"Cidades a varrer: {len(remaining)} de {len(all_cities)}")

    # Entrar no fluxo de negotiate
    ex.g.open_cmd("negotiate")
    world.wait_text(raw)
    for _ in range(5):
        world.wait_text(raw)
        antes = world.read_cash_k(raw)
        raw.press("A", hold=5, wait=25)
        raw.advance(STEP_SETTLE)
        dep = world.read_cash_k(raw)
        if antes is not None and dep is not None and dep < antes:
            log_msg(f"ABORTO: Caixa caiu no A de entrada ({antes} -> {dep})", "ERRO")
            return 1
        if world.on_map_screen(Image.open(raw.screenshot()).convert("RGB")):
            break
    else:
        log_msg("ABORTO: Não conseguiu chegar ao mapa", "ERRO")
        return 1

    log_msg("Iniciando varredura...")
    start_time = time.time()
    map_region = None
    scanned = 0

    for i, cid in enumerate(remaining):
        elapsed = time.time() - start_time
        eta_per = elapsed / (i + 1) if i > 0 else 0
        eta_remaining = eta_per * len(remaining[i+1:])

        log_msg(f"[{i+1}/{len(remaining)}] ({scanned}OK {len(failed_reads)}ERRO) "
                f"ETA {eta_remaining/60:.1f}min: {cid}")

        try:
            # Posicionar cursor
            reg, pos, verif = world.point_cursor_at_world(raw, cid, map_region)
            map_region = reg
            world.wait_text(raw)

            # Ler caixa ANTES
            cash_before = world.read_cash_k(raw)

            # Aperta A
            raw.press("A", hold=5, wait=25)
            raw.advance(STEP_SETTLE)
            world.wait_text(raw)

            # Capturar screenshot
            shot = LOG_DIR / f"{cid}_panel.png"
            img = Image.open(raw.screenshot(str(shot))).convert("RGB")

            # Ler caixa DEPOIS (R2)
            cash_after = world.read_cash_k(raw)

            # Verificar se caixa caiu (R2)
            if cash_before is not None and cash_after is not None and cash_after < cash_before:
                log_msg(f"ABORTO em {cid}: Caixa caiu ({cash_before} -> {cash_after})", "ERRO")
                break

            # Decodificar painel
            panel = world.read_city_panel(img)

            if not panel.get("on_panel"):
                log_msg(f"  ERRO {cid}: Guard on_city_panel recusou", "WARN")
                failed_reads.append(cid)
                raw.press("B", hold=5, wait=25)
                raw.advance(STEP_SETTLE)
                world.wait_text(raw)
                continue

            # Armazenar
            intel[cid] = {
                "pos": pos,
                "region": reg,
                "cursor_verificado": verif,
                "cash_before": cash_before,
                "cash_after": cash_after,
                "cash_delta": cash_after - cash_before if cash_after else None,
                **panel
            }
            scanned += 1

            # Salvar incrementalmente
            OUTPUT_FILE.write_text(json.dumps(intel, indent=2, ensure_ascii=False))

            # Log
            name = panel.get("name_ocr", "?")
            log_msg(f"  OK {cid}: {name} (Pop {panel.get('pop_m')}M, "
                   f"Slots {panel.get('slots_used')}/{panel.get('slots_cap')})")

            # Voltar ao mapa com B (R2)
            raw.press("B", hold=5, wait=25)
            raw.advance(STEP_SETTLE)
            world.wait_text(raw)

            # Verificar que voltou (R4)
            volta = Image.open(raw.screenshot()).convert("RGB")
            if not world.on_map_screen(volta):
                log_msg(f"  AVISO {cid}: B não devolveu ao mapa (parou em outro lugar)", "WARN")
                break  # Parar a varredura se B não funciona

        except KeyboardInterrupt:
            log_msg("Interrompido pelo usuário", "INFO")
            break
        except Exception as e:
            log_msg(f"  ERRO {cid}: Exceção: {e}", "ERROR")
            failed_reads.append(cid)
            try:
                raw.press("B", hold=5, wait=25)
                raw.advance(STEP_SETTLE)
            except:
                pass

    # Finalizar
    ex.dismiss_to_menu()
    caixa_final = world.read_cash_k(raw)

    log_msg(f"\nVarredura completa: {scanned}/{len(all_cities)} cidades")
    log_msg(f"Caixa final: {caixa_final}K")

    report_final(intel, caixa0, caixa_final, failed_reads, log)

    return 0


def report_final(intel, cash_init, cash_final, failed_reads, log):
    """Gera relatório final."""

    all_cities = sorted(world.WORLD_CITIES.keys())
    scanned = len(intel)
    total = len(all_cities)
    missing = [c for c in all_cities if c not in intel]

    # Verificar distinctness de name_hash (R4)
    name_hashes = [intel[c].get("name_hash") for c in intel if c in intel]
    hash_duplicates = []
    seen_hashes = {}
    for cid, panel in intel.items():
        h = panel.get("name_hash")
        if h in seen_hashes:
            hash_duplicates.append((seen_hashes[h], cid, h))
        else:
            seen_hashes[h] = cid

    # Contar None por campo (R1)
    none_counts = defaultdict(int)
    for panel in intel.values():
        for key in ("pop_m", "econ", "trsm", "slots_used", "slots_cap", "table", "ours", "our_slots"):
            if panel.get(key) is None:
                none_counts[key] += 1

    # Relatório
    print("\n" + "=" * 80)
    print("ETAPA 5c VARREDURA - RELATÓRIO FINAL")
    print("=" * 80)

    print(f"\nCobertura: {scanned}/{total} cidades ({100*scanned/total:.1f}%)")

    if cash_init and cash_final:
        delta = cash_final - cash_init
        print(f"Caixa: {cash_init}K → {cash_final}K (Δ {delta:+,}K)")
        if abs(delta) < 50000:
            print("  OK Caixa estável (R2 OK)")
        else:
            print(f"  AVISO Variação suspeita!")

    if missing:
        print(f"\nCidades NÃO varridas ({len(missing)}):")
        for r in range(7):
            reg_missing = [c for c in missing if world.city_region(c) == r]
            if reg_missing:
                print(f"  Região {r}: {reg_missing}")

    if failed_reads:
        print(f"\nCidades com falha na leitura ({len(failed_reads)}):")
        for c in failed_reads:
            print(f"  - {c}")

    if hash_duplicates:
        print(f"\nAVISO DUPLICATAS DE name_hash (possível navegação errada, R4):")
        for cid1, cid2, h in hash_duplicates:
            print(f"  {cid1} e {cid2} ambas com hash {h}")

    if none_counts:
        print(f"\nCampos lidos como None (digito 8 falta?):")
        for campo, count in sorted(none_counts.items(), key=lambda x: -x[1]):
            if count > 0:
                pct = 100 * count / len(intel)
                print(f"  {campo}: {count} ({pct:.1f}%)")

    print(f"\nCobertura por região:")
    for r in range(7):
        cities_in_reg = world.cities_of_region(r)
        scanned_in_reg = [c for c in cities_in_reg if c in intel]
        pct = 100 * len(scanned_in_reg) / len(cities_in_reg) if cities_in_reg else 0
        print(f"  Região {r}: {len(scanned_in_reg)}/{len(cities_in_reg)} ({pct:.0f}%)")

    # Salvar metadados
    metadata = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "scanned": scanned,
        "total": total,
        "missing": missing,
        "failed_reads": failed_reads,
        "cash_init": cash_init,
        "cash_final": cash_final,
        "cash_delta": cash_final - cash_init if cash_final else None,
        "duplicates_name_hash": hash_duplicates,
        "none_counts": dict(none_counts),
    }

    meta_file = LOG_DIR / "varredura_metadata.json"
    meta_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

    print(f"\nOK Resultado: {OUTPUT_FILE}")
    print(f"OK Metadados: {meta_file}")
    print(f"OK Painéis: {LOG_DIR}/")


if __name__ == "__main__":
    sys.exit(main())
