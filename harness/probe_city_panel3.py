"""ETAPA 5a (rodada 3) — INVESTIGACAO: Info->map e um caminho BARATO para o painel?

A rodada 1 achou o painel de cidade DENTRO do fluxo de negociacao (r0c2), que
custa um funcionario e termina numa tela de commit ("How many slots?"). Se a
mesma informacao (ou parte dela) aparecer em `Info->map` — tela de RELATORIO,
sem funcionario e sem commit — o custo e o risco caem para quase zero.

Este probe NAO escreve leitor. Ele:
  F1  abre Info->map e fotografa (0 toques de A no mapa);
  F2  mexe o cursor com as setas e fotografa cada frame (hover-only);
  F3  so se F2 mostrar um cursor: UM `A` sobre a cidade, com caixa medida
      antes/depois e ABORTO se cair (R2).

Conta TOQUES (o entregavel pede toques, nao segundos).
"""
import sys, pathlib, json, hashlib

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bridge, world
from executor import Executor
from macros import Game, INFO, TEXT_SETTLE, READ_SETTLE

RAIZ = HERE.parent
SHOTS = RAIZ / "logs" / "etapa5a"
SHOTS.mkdir(parents=True, exist_ok=True)
BASE = str(RAIZ / "states" / "_e3b_base.state")


def sig(img):
    return hashlib.md5(img.tobytes()).hexdigest()[:8]


def main():
    b = bridge.BizHawkBridge(timeout=120)
    ex = Executor(b)
    g = Game(b)
    b.load(BASE)
    b.advance(120)
    caixa0 = world.read_cash_k(b)
    out = {"caixa0": caixa0, "frames": []}
    toques = 0

    ex.dismiss_to_menu()
    g.open_cmd("info")
    toques += 9  # homing 6+2 + A (contagem do open_cmd)
    for _ in range(INFO["map"]):
        b.press("Right", hold=3, wait=10)
        toques += 1
    b.press("A", hold=5, wait=40)
    toques += 1
    b.advance(READ_SETTLE)
    img = Image.open(b.screenshot(SHOTS / "r3_info_map_00.png")).convert("RGB")
    out["frames"].append({
        "tag": "info_map_00", "toques": toques, "sig": sig(img),
        "land_px": world.land_pixels(img), "on_map": bool(world.on_map_screen(img)),
        "caixa": world.read_cash_k(b),
    })
    print(json.dumps(out["frames"][-1]), flush=True)

    # F2: hover-only. Mexe o cursor e ve se ALGO muda (painel de cidade?).
    for i, botao in enumerate(["Right", "Right", "Down", "Down", "Left", "Up"]):
        b.press(botao, hold=5, wait=25)
        toques += 1
        b.advance(TEXT_SETTLE)
        im2 = Image.open(b.screenshot(SHOTS / f"r3_info_map_hover{i}_{botao}.png")).convert("RGB")
        rec = {"tag": f"hover{i}_{botao}", "toques": toques, "sig": sig(im2),
               "mudou": sig(im2) != out["frames"][-1]["sig"],
               "caixa": world.read_cash_k(b)}
        out["frames"].append(rec)
        print(json.dumps(rec), flush=True)
        if rec["caixa"] is not None and caixa0 is not None and rec["caixa"] < caixa0:
            out["abortado"] = "caixa caiu no hover"
            break

    # F3: UM A, com sentinela de caixa.
    if "abortado" not in out:
        antes = world.read_cash_k(b)
        b.press("A", hold=5, wait=40)
        toques += 1
        b.advance(READ_SETTLE)
        im3 = Image.open(b.screenshot(SHOTS / "r3_info_map_A.png")).convert("RGB")
        depois = world.read_cash_k(b)
        rec = {"tag": "apos_A", "toques": toques, "sig": sig(im3),
               "caixa_antes": antes, "caixa_depois": depois,
               "caiu": (antes is not None and depois is not None and depois < antes)}
        out["frames"].append(rec)
        print(json.dumps(rec), flush=True)

    ex.dismiss_to_menu()
    out["caixa_final"] = world.read_cash_k(b)
    out["toques_total"] = toques
    (SHOTS / "r3_info_map.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps({"caixa0": caixa0, "caixa_final": out["caixa_final"],
                      "toques_total": toques}), flush=True)


if __name__ == "__main__":
    main()
