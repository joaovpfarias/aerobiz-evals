"""ACEITE AO VIVO da ETAPA 5b — `read_city_panel` em REGIOES NUNCA VISTAS.

Por que existe, se `prova_city_panel.py` ja passa offline: os 9 paineis do §33
cobrem 2 regioes do jogo (NA e EU) e 4 paises. O aceite pede 3 REGIOES. Aqui
visito cidades de South America, Middle East e Southeast Asia — dados que o
leitor nunca viu, com Rltns provavelmente novo e capacidades novas (chance de
finalmente aparecer o digito "8", que falta no mini-atlas).

Sentinelas (R2): mede o caixa antes e depois de CADA `A` e ABORTA se cair; nunca
aperta `A` depois da tela "How many slots?"; volta pelo `B` (§33.3, 5/5) e
termina com `dismiss_to_menu` + recarga do savestate.

Prova (R4): o veredito NAO e o retorno da funcao. Para cada cidade o script
grava o PNG e confere o ORACULO (soma das colunas Slot == Total slots usados),
que cruza dois leitores independentes do mesmo frame.

Uso: python prova_city_panel_vivo.py [CID ...]
"""

import json
import pathlib
import sys
import time

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge  # noqa: E402
import world  # noqa: E402
from executor import Executor, STEP_SETTLE  # noqa: E402
from probe_city_panel4 import Contador  # noqa: E402

RAIZ = HERE.parent
SHOTS = RAIZ / "logs" / "etapa5b"
SHOTS.mkdir(parents=True, exist_ok=True)
BASE = str(RAIZ / "states" / "_e3b_base.state")

# Uma cidade em cada regiao ainda NAO coberta pelos PNGs do §33.
PADRAO = ["SA02", "ME02", "AS03"]


def main():
    cids = sys.argv[1:] or PADRAO
    raw = bridge.BizHawkBridge(timeout=180)
    b = Contador(raw)
    ex = Executor(b)
    b.load(BASE)
    b.advance(120)
    caixa0 = world.read_cash_k(b)
    out = {"base": BASE, "caixa0": caixa0, "cidades": []}
    print(json.dumps({"caixa0": caixa0}), flush=True)

    ex.g.open_cmd("negotiate")
    world.wait_text(b)
    for _ in range(5):
        world.wait_text(b)
        antes = world.read_cash_k(b)
        b.press("A", hold=5, wait=25)
        b.advance(STEP_SETTLE)
        dep = world.read_cash_k(b)
        if antes is not None and dep is not None and dep < antes:
            print(json.dumps({"ABORTO": "caixa caiu no A de entrada",
                              "antes": antes, "depois": dep}), flush=True)
            return 1
        if world.on_map_screen(Image.open(b.screenshot()).convert("RGB")):
            break
    else:
        print(json.dumps({"erro": "nao chegou ao mapa"}), flush=True)
        return 1

    falhas = []
    for cid in cids:
        t0, n0 = time.time(), b.n
        rec = {"cid": cid, "regiao_esperada": world.REGION_NAMES[world.city_region(cid)]}
        try:
            reg, pos, verif = world.point_cursor_at_world(b, cid, None)
            world.wait_text(b)
            antes = world.read_cash_k(b)
            b.press("A", hold=5, wait=25)
            b.advance(STEP_SETTLE)
            world.wait_text(b)
            shot = SHOTS / ("panel_%s.png" % cid)
            img = Image.open(b.screenshot(shot)).convert("RGB")
            dep = world.read_cash_k(b)
            rec.update({"caixa_antes_A": antes, "caixa_depois_A": dep,
                        "regiao_lida": reg, "cursor_verificado": verif,
                        "toques": b.n - n0, "shot": shot.name})
            if antes is not None and dep is not None and dep < antes:
                rec["ABORTO"] = "caixa caiu ao abrir o painel"
                out["cidades"].append(rec)
                print(json.dumps(rec, ensure_ascii=False), flush=True)
                break
            r = world.read_city_panel(img)
            rec["painel"] = r
            if not r["on_panel"]:
                falhas.append("%s: guard on_city_panel recusou o frame" % cid)
            elif r["soma_confere"] is not True:
                falhas.append("%s: oraculo da soma falhou (%s)" % (cid, r["soma_confere"]))
            # O oraculo da soma NAO cobre capacidade, Pop, Econ nem Trsm: um
            # desses vindo None (glifo fora do atlas, ex. o "8" que falta) faria
            # o script imprimir PASSOU com campo silenciosamente nao lido.
            # Campo None aqui e FALHA explicita — e ainda assim confira o PNG.
            if r["on_panel"]:
                for campo in ("pop_m", "econ", "trsm", "slots_used", "slots_cap"):
                    if r[campo] is None:
                        falhas.append("%s: campo %s veio None (glifo fora do atlas?)"
                                      % (cid, campo))
            # zoom para conferencia A OLHO
            for nome, box in (("total_slots", (0, 120, 96, 152)),
                              ("tabela_cias", (96, 120, 256, 152)),
                              ("popecon", (0, 0, 256, 48))):
                w, hh = box[2] - box[0], box[3] - box[1]
                img.crop(box).resize((w * 4, hh * 4), Image.NEAREST).save(
                    SHOTS / ("zoom_%s_%s.png" % (cid, nome)))
            b.press("B", hold=5, wait=25)
            b.advance(STEP_SETTLE)
            world.wait_text(b)
            volta = Image.open(b.screenshot()).convert("RGB")
            rec["B_volta_ao_mapa"] = bool(world.on_map_screen(volta))
            rec["seg"] = round(time.time() - t0, 1)
        except Exception as e:  # noqa: BLE001
            rec.update({"erro": repr(e), "seg": round(time.time() - t0, 1)})
            falhas.append("%s: %r" % (cid, e))
        out["cidades"].append(rec)
        print(json.dumps(rec, ensure_ascii=False, default=str), flush=True)
        if not rec.get("B_volta_ao_mapa"):
            print(json.dumps({"parou": "B nao devolveu o mapa — nao insisto (R2)"}),
                  flush=True)
            break

    ex.dismiss_to_menu()
    out["caixa_final"] = world.read_cash_k(b)
    out["toques_total"] = b.n
    out["falhas"] = falhas
    if caixa0 is not None and out["caixa_final"] is not None \
            and out["caixa_final"] < caixa0:
        falhas.append("CAIXA CAIU: %s -> %s" % (caixa0, out["caixa_final"]))
    b.load(BASE)
    b.advance(120)
    (SHOTS / "vivo.json").write_text(json.dumps(out, indent=2, ensure_ascii=False,
                                                default=str), encoding="utf-8")
    print(json.dumps({"caixa0": caixa0, "caixa_final": out["caixa_final"],
                      "toques_total": b.n,
                      "ACEITE": "PASSOU" if not falhas else "FALHOU",
                      "falhas": falhas}, ensure_ascii=False), flush=True)
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())
