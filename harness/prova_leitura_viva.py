"""Leitura AO VIVO das tabelas de rotas e frota (etapas 2 e 3).

Aceite:
  - rotas:  numero de linhas == contador "N Rte" do rodape (divergencia = falha)
  - frota:  a soma das linhas bate com o que o savestate tem, e o caixa lido no
            rodape bate com o caixa lido da RAM (duas fontes independentes)
  - guarda: o caixa nao pode CAIR durante a leitura. Ler e uma operacao de custo
            zero; se o caixa cair, algum A vazou para uma tela de confirmacao —
            ja custou $276.000K uma vez.
"""

import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import world  # noqa: E402
from bridge import BizHawkBridge  # noqa: E402
from macros import Game  # noqa: E402

STATES = pathlib.Path(__file__).parent.parent / "states"
OUT = pathlib.Path(__file__).parent.parent / "logs" / "ler_estado"
OUT.mkdir(parents=True, exist_ok=True)


def varre(g, b, tag):
    caixa_antes = world.read_cash_k(b)
    p_map = g.info_screen("map", f"{tag}_map")
    p_fleet = g.info_screen("fleet", f"{tag}_fleet")
    caixa_depois = world.read_cash_k(b)
    img_map = Image.open(p_map).convert("RGB")
    img_fleet = Image.open(p_fleet).convert("RGB")
    rotas, n_rte = world.read_routes(img_map)
    frota = world.read_fleet(img_fleet)
    return {
        "caixa_ram_antes": caixa_antes,
        "caixa_ram_depois": caixa_depois,
        "caixa_rodape_map": world.read_footer_cash_k(img_map),
        "rotas": rotas,
        "n_rte": n_rte,
        "frota": frota,
        "shots": (str(p_map), str(p_fleet)),
    }


def relata(nome, r):
    print(f"\n=== {nome} ===")
    print(f"  caixa RAM {r['caixa_ram_antes']}K -> {r['caixa_ram_depois']}K"
          f" | rodape da tela: {r['caixa_rodape_map']}K")
    print(f"  contador do rodape: {r['n_rte']} Rte | linhas lidas: {len(r['rotas'])}")
    for x in r["rotas"]:
        print(f"    rota: {x['origin']} -> {x['dest']}  Load {x['load_pct']}%")
    for x in r["frota"]:
        print(f"    frota: {x['model']:<8} InUse {x['in_use']}  Avail {x['avail']}  Order {x['order']}")
    print(f"  shots: {r['shots'][0]}\n         {r['shots'][1]}")
    falhas = []
    if r["caixa_ram_depois"] < r["caixa_ram_antes"]:
        falhas.append(f"CAIXA CAIU durante a leitura ({r['caixa_ram_antes']} -> {r['caixa_ram_depois']})")
    if r["n_rte"] is None:
        falhas.append("contador Rte do rodape ilegivel")
    elif len(r["rotas"]) != r["n_rte"]:
        falhas.append(f"linhas ({len(r['rotas'])}) != contador Rte ({r['n_rte']})")
    if r["caixa_rodape_map"] != r["caixa_ram_antes"]:
        falhas.append(f"caixa do rodape ({r['caixa_rodape_map']}) != caixa da RAM ({r['caixa_ram_antes']})")
    if any(x["model"] is None or "?" in (x["model"] or "") for x in r["frota"]):
        falhas.append("modelo de aviao com glifo fora do atlas")
    if any(x["load_pct"] is None for x in r["rotas"]):
        falhas.append("load_pct ilegivel em alguma rota")
    return falhas


if __name__ == "__main__":
    b = BizHawkBridge()
    g = Game(b, shot_dir=OUT)
    todas = []
    for st_name in (sys.argv[1:] or ["probe_hub_open_sa", "eval_single_2000_lv5"]):
        b.load(str((STATES / f"{st_name}.state").resolve()))
        b.advance(120)
        r = varre(g, b, st_name)
        todas += [f"{st_name}: {x}" for x in relata(st_name, r)]
    print("\nRESULTADO:", "TUDO OK" if not todas else f"{len(todas)} FALHA(S)")
    for x in todas:
        print("  -", x)
    sys.exit(1 if todas else 0)
