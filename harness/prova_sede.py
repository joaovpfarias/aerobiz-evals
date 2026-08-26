"""ACEITE da ETAPA 5-CidadeImplementar: dois savestates, dois MUNDOS.

Carrega cada savestate gerado por `setup_game.py --city ...` e le do JOGO
(nao do retorno da ferramenta, nao do JSON de metadados) o que identifica
aquele mundo: nome da nossa companhia, caixa e frota, via Info->map/fleet.
Depois exige que os dois difiram.

R3: nada de nome/cor/quantidade de companhia chumbado — tudo sai da tela.
R4: a fonte e a tela relida DEPOIS de carregar o state.

Uso:
  python prova_sede.py ../states/eval_NA13_2000_lv5.state ../states/eval_EU10_2000_lv5.state
"""
import argparse
import json
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import world  # noqa: E402
from bridge import BizHawkBridge  # noqa: E402
from macros import Game  # noqa: E402

ROOT = pathlib.Path(__file__).parent.parent
OUT = ROOT / "logs" / "prova_sede"


def ler(b, state):
    nome = pathlib.Path(state).stem
    b.load(str(pathlib.Path(state).resolve()))
    b.advance(120)
    g = Game(b, shot_dir=OUT)
    shots = {k: g.info_screen(k, f"{nome}_{k}") for k in ("map", "fleet")}
    g.back_to_menu()
    img_map = Image.open(shots["map"]).convert("RGB")
    img_fleet = Image.open(shots["fleet"]).convert("RGB")
    rotas, n_rte = world.read_routes(img_map)
    frota = world.read_fleet(img_fleet)
    return {
        "state": nome,
        "companhia_map": world.read_our_company(img_map),
        "companhia_fleet": world.read_our_company(img_fleet),
        "caixa_k_ram": world.read_cash_k(b),
        "caixa_k_rodape": world.read_footer_cash_k(img_map),
        "frota": [(f["model"], f["avail"]) for f in frota],
        "rotas": rotas, "n_rotas": n_rte,
        "quarter": world.read_quarter_index(b),
        "shots": {k: str(v) for k, v in shots.items()},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("states", nargs=2)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    b = BizHawkBridge()
    b.speed(400)
    lidos = [ler(b, s) for s in a.states]
    for r in lidos:
        print(json.dumps(r, indent=1), flush=True)

    x, y = lidos
    campos = {
        "companhia_fleet": (x["companhia_fleet"], y["companhia_fleet"]),
        "caixa_k_ram": (x["caixa_k_ram"], y["caixa_k_ram"]),
        "frota": (x["frota"], y["frota"]),
    }
    difere = {k: v for k, v in campos.items() if v[0] != v[1] and None not in v}
    iguais = {k: v for k, v in campos.items() if v[0] == v[1]}
    print("\nDIFEREM:", json.dumps(difere, indent=1), flush=True)
    print("IGUAIS :", json.dumps(iguais, indent=1), flush=True)
    veredito = bool(difere)
    print("\nVEREDITO:", "MUNDOS DISTINTOS" if veredito else "NAO PROVEI DISTINCAO", flush=True)
    (OUT / "prova.json").write_text(
        json.dumps({"lidos": lidos, "difere": difere, "iguais": iguais,
                    "veredito": veredito}, indent=1), encoding="utf-8")
    print("json:", OUT / "prova.json")
    return 0 if veredito else 1


if __name__ == "__main__":
    sys.exit(main())
