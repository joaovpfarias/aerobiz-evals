"""ETAPA 4-CidadeInvestigar, braco A/B: escolhe UMA sede e mede o estado inicial.

Uso: python _probe_sede_arm.py --region Europe --city 130,46 --tag A
Nao sobrescreve savestate eval_*; grava states/_sede_<tag>.state.
"""
import argparse
import hashlib
import json
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import world  # noqa: E402
import locate  # noqa: E402
from bridge import BizHawkBridge  # noqa: E402
from macros import Game  # noqa: E402

ROOT = pathlib.Path(__file__).parent.parent
SHOTS = ROOT / "logs" / "etapa4_sede"
STATE = str(ROOT / "states" / "eval_players_screen.state")

# hash do recorte do rotulo de regiao (30,126)-(120,144) — medido 24/08
LABEL_BOX = (30, 126, 120, 144)
LABELS = {
    "e1f5ac0fe0": "Europe",
    "6cc4526e02": "MidEast",
    "14416469ee": "SEAsia",
    "53f810e1a1": "NAmerica",
    "2afffee160": "none",
}


def label_of(path):
    im = Image.open(path).convert("RGB").crop(LABEL_BOX)
    h = hashlib.md5(im.tobytes()).hexdigest()[:10]
    return LABELS.get(h, "?" + h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True)
    ap.add_argument("--city", required=True, help="X,Y do blob")
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    cx, cy = (int(v) for v in a.city.split(","))
    SHOTS.mkdir(parents=True, exist_ok=True)
    b = BizHawkBridge()
    b.load(STATE)
    b.advance(60)
    b.speed(400)
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(300), extra_frames=450)

    # 1) regiao: um Right por vez, CONFERINDO o rotulo na tela (R4)
    lab = None
    for i in range(10):
        p = b.screenshot(SHOTS / f"{a.tag}_reg{i}.png")
        lab = label_of(p)
        print(f"  right#{i} rotulo={lab}", flush=True)
        if lab == a.region:
            break
        b.batch(b.seq_press("Right", hold=3, wait=25) + b.seq_advance(150), extra_frames=300)
    if lab != a.region:
        print("ABORT: nao cheguei na regiao", a.region)
        return 1

    # 2) mapa de cidades
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(300), extra_frames=450)
    p_map = b.screenshot(SHOTS / f"{a.tag}_mapa.png")
    print("mapa:", p_map, flush=True)

    # 3) cursor sobre a cidade — foto ANTES do A que compromete
    locate.goto(b, cx + 4, cy + 4)
    p_cur = b.screenshot(SHOTS / f"{a.tag}_cursor.png")
    print("cursor:", p_cur, locate.find_cursor(b), flush=True)

    # 4) confirmar; foto a cada A
    for i in range(4):
        b.batch(b.seq_press("A", hold=6, wait=30) + b.seq_advance(300), extra_frames=600)
        print(f"  A#{i}:", b.screenshot(SHOTS / f"{a.tag}_conf{i}.png"), flush=True)
    b.advance(600)
    p_ini = b.screenshot(SHOTS / f"{a.tag}_ingame.png")
    print("ingame:", p_ini, flush=True)
    out_state = str((ROOT / "states" / f"_sede_{a.tag}.state").resolve())
    b.save(out_state)

    # 5) MEDIDAS
    dados = {"tag": a.tag, "region": a.region, "city_px": [cx, cy],
             "cash_k_ram": world.read_cash_k(b), "state": out_state}
    g = Game(b, shot_dir=SHOTS)
    shots = {}
    for item in ("map", "fleet"):
        shots[item] = g.info_screen(item, f"{a.tag}_info_{item}")
    g.back_to_menu()
    img_map = Image.open(shots["map"]).convert("RGB")
    img_fleet = Image.open(shots["fleet"]).convert("RGB")
    rotas, n_rte = world.read_routes(img_map)
    dados["rotas"] = rotas
    dados["n_rte"] = n_rte
    dados["frota"] = world.read_fleet(img_fleet)
    dados["our_company_map"] = world.read_our_company(img_map)
    dados["our_company_fleet"] = world.read_our_company(img_fleet)
    dados["footer_cash_k_map"] = world.read_footer_cash_k(img_map)
    dados["cash_k_ram_fim"] = world.read_cash_k(b)
    dados["shots"] = shots
    out = SHOTS / f"medida_{a.tag}.json"
    out.write_text(json.dumps(dados, indent=1), encoding="utf-8")
    print(json.dumps(dados, indent=1), flush=True)
    print("json:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
