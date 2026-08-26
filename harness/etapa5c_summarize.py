#!/usr/bin/env python3
"""
Resumir resultados da ETAPA 5c - Varredura de cidades

Lê city_intel.json e gera sumários por região, país, stats
"""

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import world

OUTPUT_FILE = HERE / "city_intel.json"
REPORT_FILE = HERE.parent / "logs" / "etapa5c" / "SUMARIO.md"


def main():
    if not OUTPUT_FILE.exists():
        print(f"Erro: {OUTPUT_FILE} não encontrado")
        return 1

    intel = json.loads(OUTPUT_FILE.read_text())
    print(f"Carregadas {len(intel)} cidades\n")

    # Agrupar por região
    by_region = {}
    for cid, panel in intel.items():
        reg = panel.get("region")
        if reg not in by_region:
            by_region[reg] = []
        by_region[reg].append((cid, panel))

    # Gerar sumário
    lines = []
    lines.append("# ETAPA 5c - SUMÁRIO DE CIDADES")
    lines.append("")
    lines.append(f"**Total:** {len(intel)} cidades de {len(world.WORLD_CITIES)}")
    lines.append("")

    lines.append("## Cobertura por Região")
    lines.append("")
    for r in range(7):
        if r in by_region:
            cities = by_region[r]
            pct = 100 * len(cities) / len(world.cities_of_region(r))
            lines.append(f"### Região {r} ({len(cities)} cidades, {pct:.0f}%)")
            lines.append("")
            for cid, panel in sorted(cities):
                pop = panel.get("pop_m")
                slots = panel.get("slots_used", "?"), panel.get("slots_cap", "?")
                name = panel.get("name_ocr", "?")
                lines.append(f"- **{cid}** {name} | Pop {pop}M | Slots {slots[0]}/{slots[1]}")
            lines.append("")

    lines.append("## Estatísticas de Población")
    lines.append("")
    pops = [p.get("pop_m") for p in intel.values() if p.get("pop_m")]
    if pops:
        lines.append(f"- Média: {sum(pops)/len(pops):.1f}M")
        lines.append(f"- Máxima: {max(pops):.1f}M")
        lines.append(f"- Mínima: {min(pops):.1f}M")
    lines.append("")

    lines.append("## Estatísticas de Slots")
    lines.append("")
    slots_used = [p.get("slots_used") for p in intel.values() if p.get("slots_used")]
    slots_cap = [p.get("slots_cap") for p in intel.values() if p.get("slots_cap")]
    if slots_used:
        lines.append(f"- Slots usados: {sum(slots_used)} em {len(slots_used)} cidades")
        lines.append(f"- Slots disponíveis: {sum(slots_cap)} em {len(slots_cap)} cidades")
        occupancy = 100 * sum(slots_used) / sum(slots_cap) if slots_cap else 0
        lines.append(f"- Ocupação média: {occupancy:.1f}%")
    lines.append("")

    # Salvar
    report = "\n".join(lines)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(report)

    print(report)
    print(f"\n✓ Sumário salvo em {REPORT_FILE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
