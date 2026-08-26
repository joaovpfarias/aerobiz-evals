#!/usr/bin/env python3
"""ETAPA 1b — terceiro momento AO VIVO: Regional Rankings em Q191 (eval_2005_rankings).

Navegacao MEDIDA (17/08): Info->finance cai no Quarterly Report; UM `A` ali
avanca para Regional Rankings. O `A` so e dado se `on_quarterly_report_img`
for verdadeiro (R2: nada de A as cegas), e o caixa e medido antes/depois —
se cair, aborta e diz.
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from PIL import Image
from bridge import BizHawkBridge
from macros import Game, INFO, READ_SETTLE
import world

OUT = pathlib.Path(__file__).parent.parent / "logs" / "lideres_19ago"
OUT.mkdir(parents=True, exist_ok=True)


def tela(b, nome):
    p = b.screenshot(OUT / f"{nome}.png")
    return Image.open(p).convert("RGB"), str(p)


def main():
    b = BizHawkBridge(timeout=60)
    b.load("../states/eval_2005_rankings.state")
    g = Game(b, shot_dir=OUT)
    caixa0 = world.read_cash_k(b)
    q0 = world.read_quarter_index(b)
    print(f"savestate: quarter={q0} ({world.date_label(q0)}) caixa={caixa0}K", flush=True)

    # 1) tela de tabela, para descobrir QUEM SOMOS pelo rodape
    g.back_to_menu()
    p_map = g.info_screen("map", "info_map")
    img_map = Image.open(p_map).convert("RGB")
    nos = world.read_our_company(img_map)
    print("rodape Info->map:", repr(nos), "| on_route_table=", world.on_route_table(img_map), flush=True)

    # 2) Info->finance -> Quarterly Report -> (A medido) -> Regional Rankings
    g.back_to_menu()
    g.open_cmd("info")
    for _ in range(INFO["finance"]):
        b.press("Right", hold=3, wait=10)
    b.press("A", hold=5, wait=40)
    b.advance(READ_SETTLE)
    img_qr, p_qr = tela(b, "finance_00")
    print("finance_00: quarterly2=", world.on_quarterly_report_img2(img_qr),
          "rankings_cells=", world.rankings_cells_ok(img_qr),
          "| detectores antigos:", world.on_quarterly_report_img(img_qr),
          world.on_regional_rankings_img(img_qr), flush=True)

    # O rodape do Quarterly Report traz companhia + caixa. Ele so e aceito como
    # fonte de "quem somos" se o CAIXA lido bater com o da RAM — cheque
    # independente de que aquele rodape e o NOSSO, nao de um adversario.
    cash_rodape = world.read_footer_cash_k(img_qr)
    nome_rodape = world.read_our_company(img_qr)
    print("rodape finance:", repr(nome_rodape), "caixa_rodape=", cash_rodape,
          "caixa_ram=", world.read_cash_k(b), flush=True)

    img_rk = None
    if world.rankings_cells_ok(img_qr):
        img_rk = img_qr
    elif world.on_quarterly_report_img2(img_qr):
        caixa_pre = world.read_cash_k(b)
        b.press("A", hold=5, wait=40)
        b.advance(READ_SETTLE)
        caixa_pos = world.read_cash_k(b)
        if caixa_pos < caixa_pre:
            print(f"ABORTA: caixa caiu {caixa_pre} -> {caixa_pos} apos o A", flush=True)
            return 1
        img_rk, _ = tela(b, "finance_01_rankings")
        print("finance_01: rankings_cells=", world.rankings_cells_ok(img_rk), flush=True)
    else:
        print("nem quarterly nem rankings — nao sei onde caiu; nao aperto nada", flush=True)

    res = None
    if img_rk is not None and world.rankings_cells_ok(img_rk):
        nos = None
        if cash_rodape is not None and cash_rodape == world.read_cash_k(b) and nome_rodape                 and "?" not in nome_rodape:
            nos = nome_rodape
        r = world.read_rivals(img_rk, img_tabela=img_map, nos=nos)
        res = {
            "quarter": q0, "data": world.date_label(q0),
            "nos": r["nos"], "nos_fonte": r["nos_fonte"],
            "legenda": [{"linha": e["linha"], "nome": e["nome"], "cor": list(e["cor"])} for e in r["legenda"]],
            "lideres": r["lideres"], "numeros": r["numeros"],
        }
        print(json.dumps(res, indent=2), flush=True)

    g.back_to_menu()
    caixa1 = world.read_cash_k(b)
    print(f"caixa {caixa0}K -> {caixa1}K (delta {caixa1 - caixa0})", flush=True)
    if res is not None:
        res["caixa_antes"], res["caixa_depois"] = caixa0, caixa1
        (OUT / "q191_rivals.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0 if res is not None and caixa1 >= caixa0 else 1


if __name__ == "__main__":
    sys.exit(main())
