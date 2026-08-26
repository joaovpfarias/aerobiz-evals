#!/usr/bin/env python3
"""
Piloto da ETAPA 5c: varrer apenas a Região AF (7 cidades)

Verifica:
1. Cash fica estável
2. Name hashes são todos distintos
3. Nenhuma falha de leitura

Se passar, executar etapa5c_varredura.py em background para as 96 cidades.
"""

import json
import pathlib
import sys
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

# Região AF tem 7 cidades
PILOT_CITIES = world.cities_of_region(3)  # Região 3 = AF


def main():
    print(f"PILOTO - REGIÃO AF ({len(PILOT_CITIES)} cidades): {PILOT_CITIES}\n")

    # Setup
    raw = bridge.BizHawkBridge(timeout=180)
    ex = Executor(raw)
    raw.load(BASE)
    raw.advance(120)

    caixa0 = world.read_cash_k(raw)
    if caixa0 is None:
        print("ERRO: Não conseguiu ler caixa inicial")
        return 1

    print(f"Caixa inicial: {caixa0}K\n")

    # Entrar no fluxo
    ex.g.open_cmd("negotiate")
    world.wait_text(raw)
    for _ in range(5):
        world.wait_text(raw)
        raw.press("A", hold=5, wait=25)
        raw.advance(STEP_SETTLE)
        if world.on_map_screen(Image.open(raw.screenshot()).convert("RGB")):
            break
    else:
        print("ERRO: Não chegou ao mapa")
        return 1

    # Varrer região AF
    intel = {}
    failed = []
    map_region = None

    for i, cid in enumerate(PILOT_CITIES):
        print(f"[{i+1}/{len(PILOT_CITIES)}] {cid}...", end=" ", flush=True)

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

            # Screenshot
            shot = LOG_DIR / f"{cid}_panel.png"
            img = Image.open(raw.screenshot(str(shot))).convert("RGB")

            # Ler caixa DEPOIS
            cash_after = world.read_cash_k(raw)

            # Verificar caixa
            if cash_before is not None and cash_after is not None and cash_after < cash_before:
                print(f"ERRO CAIXA CAIU ({cash_before} -> {cash_after})")
                failed.append(cid)
                break

            # Decodificar
            panel = world.read_city_panel(img)

            if not panel.get("on_panel"):
                print(f"ERRO Guard recusou")
                failed.append(cid)
                raw.press("B", hold=5, wait=25)
                raw.advance(STEP_SETTLE)
                world.wait_text(raw)
                continue

            # Armazenar
            intel[cid] = {
                "pos": pos,
                "region": reg,
                "cursor_verificado": verif,
                **panel
            }

            # Volta
            raw.press("B", hold=5, wait=25)
            raw.advance(STEP_SETTLE)
            world.wait_text(raw)

            # Verificar volta
            volta = Image.open(raw.screenshot()).convert("RGB")
            if not world.on_map_screen(volta):
                print(f"ERRO B não devolveu ao mapa")
                break

            print(f"OK {panel.get('name_ocr', '?')}")

        except Exception as e:
            print(f"ERRO Excecao: {e}")
            failed.append(cid)

    ex.dismiss_to_menu()
    caixa_final = world.read_cash_k(raw)

    # Relatório
    print("\n" + "=" * 60)
    print("RESULTADO DO PILOTO")
    print("=" * 60)

    print(f"\nCidades: {len(intel)}/{len(PILOT_CITIES)} OK")
    print(f"Falhas: {len(failed)}")
    if failed:
        print(f"  {failed}")

    print(f"\nCaixa: {caixa0}K → {caixa_final}K (Δ {caixa_final - caixa0:+,}K)")

    # Verificar hash distintos
    name_hashes = [intel[c].get("name_hash") for c in intel]
    unique_hashes = len(set(h for h in name_hashes if h))
    print(f"Name hashes únicos: {unique_hashes}/{len(intel)}")

    if len(set(name_hashes)) != len(intel):
        print("  AVISO DUPLICATAS DE HASH - possível erro de navegação!")
        return 1

    # Relatório None
    none_counts = defaultdict(int)
    for panel in intel.values():
        for key in ("pop_m", "econ", "trsm", "slots_used", "slots_cap"):
            if panel.get(key) is None:
                none_counts[key] += 1

    if none_counts:
        print(f"\nCampos None (digito 8 falta?):")
        for k, v in sorted(none_counts.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")

    # Verificar caixa
    if abs(caixa_final - caixa0) < 50000:
        print("\nOK Caixa ESTÁVEL - R2 OK")
    else:
        print("\nERRO Caixa VARIOU muito")
        return 1

    # Sucesso
    if len(intel) == len(PILOT_CITIES) and not failed and not none_counts:
        print("\nOKOKOK PILOTO PASSOU - pronto para varredura completa!")
        return 0
    else:
        print("\nERRO Piloto teve problemas - investigar antes da varredura")
        return 1


if __name__ == "__main__":
    sys.exit(main())
