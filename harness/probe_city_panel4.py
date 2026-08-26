"""ETAPA 5a (rodada 4) — INVESTIGACAO do painel de cidade. Nao escreve leitor.

Responde 4 perguntas que a rodada 1 (logs/etapa5a/panel_*.png) deixou abertas:

P1 O painel abre no HOVER (so posicionar o cursor) ou so depois do `A`?
   A rodada 1 nunca fotografou o frame ANTES do `A`, entao nao sabia.

P2 O ICONE e Rltns (do PAIS) e o NUMERO e Trsm (da cidade)? A rodada 1 so viu
   cidades dos EUA — invariante nenhuma prova. Aqui visito cidades de outros
   paises; o painel imprime o pais, entao a atribuicao se verifica sozinha.

P3 `B` na tela "How many slots?" volta ao MAPA? Se voltar, inspecionar N cidades
   custa uma entrada no fluxo, nao N. Isso decide se o painel pode virar campo
   de estado por turno ou se e caro demais.

P4 Quantos TOQUES custa cada cidade (o entregavel pede toques, nao segundos).

Sentinelas: conta toques de verdade (contador embrulhado no bridge), mede caixa
a cada parada e ABORTA se cair (R2). Nunca aperta `A` depois da tela de
quantidade.
"""
import sys, pathlib, json, hashlib, time

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge, world
from executor import Executor, STEP_SETTLE
from world import (wait_text, on_map_screen, staff_free_cells,
                   point_cursor_at_world, read_cash_k)
from probe_city_panel import BOXES, h

RAIZ = HERE.parent
SHOTS = RAIZ / "logs" / "etapa5a"
SHOTS.mkdir(parents=True, exist_ok=True)
BASE = str(RAIZ / "states" / "_e3b_base.state")


class Contador:
    """Embrulha o bridge para CONTAR toques de botao (press e batch/seq_press)."""

    def __init__(self, b):
        self._b = b
        self.n = 0

    def press(self, *bt, **kw):
        self.n += kw.get("times", 1)
        return self._b.press(*bt, **kw)

    def batch(self, cmds, **kw):
        self.n += sum(1 for c in cmds if isinstance(c, str) and c.startswith("PRESS"))
        return self._b.batch(cmds, **kw)

    def __getattr__(self, k):
        return getattr(self._b, k)


def zooms(img, cid, pref):
    for nome, box in BOXES.items():
        w, hh = box[2] - box[0], box[3] - box[1]
        img.crop(box).resize((w * 4, hh * 4), Image.NEAREST).save(
            SHOTS / f"{pref}_zoom_{cid}_{nome}.png")


def main():
    cids = sys.argv[1:] or ["NA01", "NA16", "NA11"]
    raw = bridge.BizHawkBridge(timeout=120)
    b = Contador(raw)
    ex = Executor(b)
    b.load(BASE)
    b.advance(120)
    caixa0 = read_cash_k(b)
    livres0 = staff_free_cells(Image.open(b.screenshot()).convert("RGB"))
    out = {"caixa0": caixa0, "livres0": livres0, "base": BASE, "cidades": []}

    ex.g.open_cmd("negotiate")
    wait_text(b)
    # blind-A ate o mapa, mas com sentinela de caixa (R2)
    for _ in range(5):
        wait_text(b)
        antes = read_cash_k(b)
        b.press("A", hold=5, wait=25)
        b.advance(STEP_SETTLE)
        dep = read_cash_k(b)
        if antes is not None and dep is not None and dep < antes:
            print(json.dumps({"ABORTO": "caixa caiu no A de entrada",
                              "antes": antes, "depois": dep}), flush=True)
            return
        if on_map_screen(Image.open(b.screenshot()).convert("RGB")):
            break
    else:
        print(json.dumps({"erro": "nao chegou ao mapa"}), flush=True)
        return

    out["toques_ate_o_mapa"] = b.n
    print(json.dumps({"toques_ate_o_mapa": b.n}), flush=True)

    for cid in cids:
        t0, n0 = time.time(), b.n
        rec = {"cid": cid}
        try:
            reg, pos, verif = point_cursor_at_world(b, cid, None)
            n_cursor = b.n - n0
            wait_text(b)
            # P1: frame de HOVER, antes de qualquer A
            hov = Image.open(b.screenshot(SHOTS / f"r4_hover_{cid}.png")).convert("RGB")
            rec["hover"] = {"toques": n_cursor, "on_map": bool(on_map_screen(hov)),
                            "hashes": {k: h(hov, v) for k, v in BOXES.items()}}

            antes = read_cash_k(b)
            b.press("A", hold=5, wait=25)
            b.advance(STEP_SETTLE)
            wait_text(b)
            img = Image.open(b.screenshot(SHOTS / f"r4_panel_{cid}.png")).convert("RGB")
            dep = read_cash_k(b)
            zooms(img, cid, "r4")
            rec.update({"ok": True, "regiao": reg, "pos": str(pos),
                        "cursor_verificado": verif,
                        "toques_cidade": b.n - n0, "toques_acumulados": b.n,
                        "medidor_slots": world.read_slots_qty(img),
                        "caixa_antes_A": antes, "caixa_na_tela": dep,
                        "hover_igual_ao_painel":
                            rec["hover"]["hashes"] == {k: h(img, v) for k, v in BOXES.items()},
                        "hashes": {k: h(img, v) for k, v in BOXES.items()}})
            if antes is not None and dep is not None and dep < antes:
                rec["ABORTO"] = "caixa caiu ao abrir o painel"
                out["cidades"].append(rec)
                print(json.dumps(rec, ensure_ascii=False), flush=True)
                break

            # P3: B devolve o mapa?
            b.press("B", hold=5, wait=25)
            b.advance(STEP_SETTLE)
            wait_text(b)
            depois = Image.open(b.screenshot(SHOTS / f"r4_posB_{cid}.png")).convert("RGB")
            rec["B_volta_ao_mapa"] = bool(on_map_screen(depois))
            rec["toques_com_B"] = b.n - n0
            rec["seg"] = round(time.time() - t0, 1)
        except Exception as e:
            rec.update({"ok": False, "erro": repr(e), "seg": round(time.time() - t0, 1)})
        out["cidades"].append(rec)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
        if not rec.get("B_volta_ao_mapa"):
            print(json.dumps({"parou": "B nao devolveu o mapa — nao insisto (R2)"}),
                  flush=True)
            break

    ex.dismiss_to_menu()
    fim = Image.open(b.screenshot()).convert("RGB")
    out["caixa_final"] = read_cash_k(b)
    out["livres_final"] = staff_free_cells(fim)
    out["toques_total"] = b.n
    (SHOTS / "r4_panel.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps({"caixa0": caixa0, "caixa_final": out["caixa_final"],
                      "livres0": livres0, "livres_final": out["livres_final"],
                      "toques_total": b.n}), flush=True)


if __name__ == "__main__":
    main()
