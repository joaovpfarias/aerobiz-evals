#!/usr/bin/env python3
"""ETAPA 1c-PnL — aceite de `world.read_pnl`. Roda SEM emulador.

Criterio da etapa:
  (a) em `rank_t1.png` (turno 1) TODOS os valores sao 0;
  (b) num savestate com a partida andada, Airline Sales != 0 E pelo menos uma
      linha de custo != 0;
  (c) os rotulos sao LIDOS da tela (nenhum '?' e nenhuma lista chumbada);
  (d) a tela que NAO e Quarterly Report devolve None (guard), porque "tudo
      zero" vindo da tela errada e indistinguivel de turno 1.
"""
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import world  # noqa: E402

RAIZ = pathlib.Path(__file__).parent.parent

# (a) turno 1 e (b) partidas andadas. Os frames de (b) vieram da varredura ao
# vivo `prova_pnl_live.py` (caixa inalterada nos 5 savestates: ler custa zero).
ZERADOS = [
    ("rank_t1 (turno 1)", RAIZ / "logs/logs/rank_t1.png"),
    ("_edit_2rotas (2 rotas com Load 0%, trimestre nao fechado)",
     RAIZ / "logs/pnl_19ago/_edit_2rotas_finance.png"),
]
ANDADOS = [
    ("_cityhotel_3turnos_real (JAN.2001, 2 rotas Load 38/36%)",
     RAIZ / "logs/pnl_19ago/_cityhotel_3turnos_real_finance.png"),
    ("_hub_rota_do_hub (APR.2002, rota Load 51%)",
     RAIZ / "logs/pnl_19ago/_hub_rota_do_hub_finance.png"),
    ("_close_hub_after_turns (APR.2003, rota Load 49%)",
     RAIZ / "logs/pnl_19ago/_close_hub_after_turns_finance.png"),
]
NAO_E_A_TELA = [
    ("Info->map (mapa-mundi)", RAIZ / "logs/lideres_19ago/info_map.png"),
    ("Info->map (tabela de rotas)", RAIZ / "logs/prova_ic/mapa_pos_rota.png"),
    ("Info->fleet (tabela de frota)", RAIZ / "logs/prova_ic/frota_1rota.png"),
    ("Regional Rankings", RAIZ / "logs/rankings_probe/y1_region0_A.png"),
]

CUSTOS = ("Airline Costs", "Business Costs", "Slot Costs", "Hub Costs",
          "Bidding Costs", "Repair Costs", "Ad Costs", "Service Costs")


def mostra(rotulo, pnl):
    print(f"--- {rotulo}")
    if pnl is None:
        print("    read_pnl = None (nao e o Quarterly Report)")
        return
    for k, v in pnl.items():
        print(f"    {k:<16} {v if v is not None else 'None'}")


def main():
    falhas = []

    print("=== (a)/(b') linhas que DEVEM estar zeradas")
    for rotulo, p in ZERADOS:
        img = Image.open(p).convert("RGB")
        pnl = world.read_pnl(img)
        mostra(f"{rotulo}  [{p.name}]", pnl)
        if pnl is None:
            falhas.append(f"{p.name}: guard reprovou uma tela de Quarterly Report")
        elif any(v != 0 for v in pnl.values()):
            falhas.append(f"{p.name}: esperado tudo 0, veio {pnl}")

    print("\n=== (b) partida andada: Airline Sales != 0 e ao menos um custo != 0")
    for rotulo, p in ANDADOS:
        img = Image.open(p).convert("RGB")
        pnl = world.read_pnl(img)
        mostra(f"{rotulo}  [{p.name}]", pnl)
        if pnl is None:
            falhas.append(f"{p.name}: guard reprovou")
            continue
        if not pnl.get("Airline Sales"):
            falhas.append(f"{p.name}: Airline Sales = {pnl.get('Airline Sales')}")
        if not any(pnl.get(c) for c in CUSTOS):
            falhas.append(f"{p.name}: nenhuma linha de custo != 0")

    print("\n=== (c) rotulos legiveis (sem '?') e valores todos parseados")
    for rotulo, p in ZERADOS + ANDADOS:
        img = Image.open(p).convert("RGB")
        linhas = world.pnl_rows(img)
        ruins = [(y, r) for y, r, _ in linhas if not r or "?" in r]
        nulos = [r for _, r, v in linhas if v is None]
        print(f"    {p.name:<40} {len(linhas)} linhas | rotulos ilegiveis={ruins} | valores None={nulos}")
        if ruins:
            falhas.append(f"{p.name}: rotulo ilegivel {ruins}")
        if nulos:
            falhas.append(f"{p.name}: valor nao parseado em {nulos}")

    print("\n=== (d) guard: outras telas devolvem None")
    for rotulo, p in NAO_E_A_TELA:
        img = Image.open(p).convert("RGB")
        pnl = world.read_pnl(img)
        print(f"    {rotulo:<32} read_pnl = {'None' if pnl is None else pnl}")
        if pnl is not None:
            falhas.append(f"{p.name}: guard deixou passar tela que nao e Quarterly Report")

    print("\n=== coerencia semantica (nao e criterio, e evidencia)")
    hotel = world.read_pnl(Image.open(ANDADOS[0][1]).convert("RGB"))
    outros = [world.read_pnl(Image.open(p).convert("RGB")) for _, p in ANDADOS[1:]]
    print("    Business Sales no savestate do city hotel:", hotel.get("Business Sales"))
    print("    Business Sales nos savestates sem venture:",
          [o.get("Business Sales") for o in outros])

    print("\n--- ACEITE")
    if falhas:
        for f in falhas:
            print("  FALHA:", f)
        print("  RESULTADO: FALHA")
        return 1
    print("  RESULTADO: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
