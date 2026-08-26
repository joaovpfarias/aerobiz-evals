"""ETAPA 5a — INVESTIGACAO: onde o jogo mostra Pop/Econ/Rltns/Trsm + slots por companhia.

Nao escreve leitor. So fotografa a tela candidata em VARIAS cidades para saber
QUAIS dos 5 dados existem e quais mudam de cidade para cidade.

Tela candidata unica achada ate agora: o painel de detalhe da cidade que abre
DENTRO do fluxo de negociacao (r0c2 -> funcionario -> A ate o mapa -> cursor na
cidade -> UM A -> "How many slots?"). O painel ocupa y<152; a caixa de dialogo
fica embaixo.

Cada cidade parte de um LOAD do savestate base (nada acumula) e o probe nunca
aperta A depois da tela de quantidade (R2). Mede o caixa na tela e no fim.
"""
import sys, pathlib, json, hashlib
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge, world
from executor import Executor
from probe_slots_lever import goto_qty

RAIZ = HERE.parent
SHOTS = RAIZ / "logs" / "etapa5a"
SHOTS.mkdir(parents=True, exist_ok=True)
BASE = str(RAIZ / "states" / "_e3b_base.state")

# Faixas do painel (medidas visualmente em logs/etapa3b/s00_A1_*.png)
BOX_NOME = (0, 0, 200, 32)     # bandeira + cidade + pais
BOX_POPECON = (0, 32, 200, 48)  # Pop <v>   Econ <v>
BOX_RT = (200, 0, 256, 56)     # chips Rltns/Trsm + icone + numero
BOX_TOTSLOT = (0, 120, 96, 152)  # "Total slots N/ M"
BOX_TABELA = (96, 120, 256, 152)  # Co./Fl/Slot das 4 companhias
BOXES = {"nome": BOX_NOME, "popecon": BOX_POPECON, "rltns_trsm": BOX_RT,
         "total_slots": BOX_TOTSLOT, "tabela_cias": BOX_TABELA}


def h(img, box):
    return hashlib.md5(img.crop(box).tobytes()).hexdigest()[:8]


def main():
    cids = sys.argv[1:] or ["NA13", "NA06", "NA02", "NA14", "NA10"]
    b = bridge.BizHawkBridge()
    ex = Executor(b)
    b.load(BASE); b.advance(120)
    caixa_ini = world.read_cash_k(b)
    out = {"caixa_inicial": caixa_ini, "base": BASE, "cidades": []}
    for cid in cids:
        reg_i = {"cid": cid}
        try:
            livres, reg, pos, verif = goto_qty(b, ex, cid, (0, 0), f"e5a_{cid}")
            img = Image.open(b.screenshot()).convert("RGB")
            p = SHOTS / f"panel_{cid}.png"
            img.save(p)
            # zoom das 3 faixas de numero, para leitura HUMANA
            for nome, box in BOXES.items():
                w, hh = box[2] - box[0], box[3] - box[1]
                img.crop(box).resize((w * 4, hh * 4), Image.NEAREST).save(
                    SHOTS / f"zoom_{cid}_{nome}.png")
            reg_i.update({
                "ok": True, "livres": livres, "regiao": reg, "pos": str(pos),
                "cursor_verificado": verif,
                "medidor_slots": world.read_slots_qty(img),
                "caixa_na_tela": world.read_cash_k(b),
                "hashes": {k: h(img, v) for k, v in BOXES.items()},
                "shot": p.name,
            })
        except Exception as e:
            reg_i.update({"ok": False, "erro": repr(e)})
        out["cidades"].append(reg_i)
        print(json.dumps(reg_i, ensure_ascii=False), flush=True)
    # volta limpo
    b.load(BASE); b.advance(120)
    out["caixa_final"] = world.read_cash_k(b)
    (SHOTS / "panel.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps({"caixa_inicial": caixa_ini, "caixa_final": out["caixa_final"]}))


if __name__ == "__main__":
    main()
