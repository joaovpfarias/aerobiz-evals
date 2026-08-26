#!/usr/bin/env python3
"""ETAPA 1b — terceiro momento AO VIVO, agora pelo caminho CERTO.

MEDIDO 19/08: `Info->finance` mostra o Quarterly Report e um `A` ali NAO
avanca para Regional Rankings (tela identica antes e depois, caixa parada).
A tela de ranking so aparece na CADEIA DE FIM DE TURNO (foi assim que y1/y2
foram capturados em 17/08). Entao aqui: dispara end_turn e atravessa a cadeia
so com B (nunca A, R2), fotografando quando as 7 caixas de regiao aparecerem.
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from PIL import Image
from bridge import BizHawkBridge
from macros import Game
import world

OUT = pathlib.Path(__file__).parent.parent / "logs" / "lideres_19ago"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    b = BizHawkBridge(timeout=60)
    b.load("../states/eval_2005_rankings.state")
    g = Game(b, shot_dir=OUT)
    caixa0 = world.read_cash_k(b)
    q0 = world.read_quarter_index(b)
    print(f"antes: q={q0} ({world.date_label(q0)}) caixa={caixa0}K", flush=True)

    g.back_to_menu()
    g.open_cmd("end_turn")
    b.advance(150)

    achado = None
    for step in range(60):
        img = Image.open(b.screenshot(OUT / "_chain.png")).convert("RGB")
        caixa = world.read_cash_k(b)
        if caixa < caixa0 - 50000:
            print(f"ABORTA: caixa despencou {caixa0} -> {caixa} no passo {step}", flush=True)
            break
        if world.rankings_cells_present(img) and achado is None:
            # MEDIDO 19/08: a tela e detectada ANTES de terminar de desenhar —
            # o primeiro frame veio com as 7 caixas pretas e legenda VAZIA, o
            # que seria lido como "ninguem lidera nada". Entao espera assentar
            # e so aceita frame com legenda legivel.
            for k in range(8):
                p = OUT / f"turno_rankings_{k}.png"
                img.save(p)
                leg = world.read_rankings_legend(img)
                cheias = [r for r in world.REGIONAL_RANKINGS_REGIONS
                          if world._rank_cell_shape(img, *world.REGIONAL_RANKINGS_CELLS[r]) == "com_dado"]
                print(f"  passo {step}.{k}: legenda={len(leg)} caixas_com_dado={cheias}", flush=True)
                if world.rankings_cells_ok(img):
                    achado = p
                    break
                b.advance(150)
                img = Image.open(b.screenshot(OUT / "_chain.png")).convert("RGB")
                if not world.rankings_cells_present(img):
                    print(f"  passo {step}.{k}: saiu da tela de ranking sozinho", flush=True)
                    break
            if achado:
                (OUT / "turno_rankings.png").write_bytes(pathlib.Path(achado).read_bytes())
                print(f"RANKINGS aceito: {achado}", flush=True)
        if world.at_main_menu_img(img):
            print(f"voltei ao menu no passo {step}", flush=True)
            break
        b.press("B", hold=5, wait=25)
        b.advance(90)

    q1 = world.read_quarter_index(b)
    caixa1 = world.read_cash_k(b)
    print(f"depois: q={q1} ({world.date_label(q1)}) caixa={caixa1}K", flush=True)

    if achado is None:
        print("NAO achei a tela de Regional Rankings na cadeia", flush=True)
        return 1

    img = Image.open(achado).convert("RGB")
    nos = None
    nome, cash_rod = world.read_our_company(img), world.read_footer_cash_k(img)
    r = world.read_rivals(img, nos=nos)
    res = {"quarter_antes": q0, "quarter_depois": q1,
           "caixa_antes": caixa0, "caixa_depois": caixa1,
           "legenda": [{"linha": e["linha"], "nome": e["nome"], "cor": list(e["cor"])} for e in r["legenda"]],
           "lideres": r["lideres"], "numeros": r["numeros"],
           "rodape_do_ranking_NAO_E_IDENTIDADE": [nome, cash_rod]}
    print(json.dumps(res, indent=2), flush=True)
    (OUT / "turno_rivals.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
