"""Tarefa 1.4 — mapa TELA A TELA do fluxo de NOVA ROTA, a partir do savestate do eval.

Uma screenshot por TELA (dedupe pelo hash do recorte da caixa de texto), contando
quantos A's cada transicao custou, e seguindo DEPOIS da animacao de pouso ate o
menu principal — que era o unico trecho nunca capturado (probe12 parou em p07).

Uso: python probe_flow14.py walk [DEST]
     python probe_flow14.py tail          (so o rabo, a partir da confirmacao)
"""

import hashlib
import json
import pathlib
import sys

from PIL import Image

from bridge import BizHawkBridge
from macros import Game
import world

EVAL = pathlib.Path(__file__).parent.parent / "states" / "eval_single_2000_lv5.state"
OUT = pathlib.Path(__file__).parent.parent / "logs" / "flow14"
OUT.mkdir(parents=True, exist_ok=True)


def snap(b, name):
    """Screenshot + metricas objetivas da tela (sem OCR)."""
    p = b.screenshot(OUT / f"{name}.png")
    img = Image.open(p).convert("RGB")
    return {
        "file": name,
        "txt": hashlib.md5(img.crop(world.TEXTBOX).tobytes()).hexdigest()[:8],
        "full": hashlib.md5(img.tobytes()).hexdigest()[:8],
        "menu_red": world.menu_red(img),
        "land": world.land_pixels(img),
        "cash": world.read_cash_k(b),
    }


def line(tag, m, extra=""):
    print(
        f"{tag:28s} txt={m['txt']} menu_red={m['menu_red']:4d} "
        f"land={m['land']:5d} caixa={m['cash']}K {extra}"
    )


def walk():
    dest = sys.argv[2] if len(sys.argv) > 2 else "NA06"
    b = BizHawkBridge()
    g = Game(b, shot_dir=OUT)
    b.load(EVAL)
    b.advance(60)
    g.back_to_menu()
    b.advance(60)

    log = []
    m = snap(b, "T0_menu_principal")
    line("T0 menu principal", m)
    log.append(dict(m, etapa="T0 menu principal", teclas="-"))
    cash0 = m["cash"]

    # --- T1: comando de nova rota -> mapa com "Choose destination"
    g.open_cmd("new_route")
    world.wait_text(b)
    m = snap(b, "T1_mapa_choose_dest")
    line("T1 mapa/choose dest", m, "(antes do A de reconhecimento)")
    log.append(dict(m, etapa="T1 mapa Choose destination", teclas="icone r0c0 + A"))

    # --- T1b: cursor ativado (A de reconhecimento) e posicionado no destino
    pos = world.point_cursor_at(b, dest)
    m = snap(b, "T1b_cursor_no_destino")
    line("T1b cursor no destino", m, f"cursor={pos}")
    log.append(dict(m, etapa=f"T1b cursor sobre {dest}", teclas="A (reconhece) + escrita RAM"))

    # --- caminhada: A ate a PERGUNTA mudar, uma screenshot por tela nova
    seen = {m["txt"]}
    cur = world.wait_text(b)
    idx = 1
    total_a = 0
    for _ in range(10):
        antes = cur
        n = 0
        while n < 6:
            b.press("A", hold=5, wait=25)
            n += 1
            total_a += 1
            cur = world.wait_text(b)
            if cur != antes:
                break
        m = snap(b, f"T{idx + 1}_tela{idx}")
        line(f"T{idx + 1} tela {idx}", m, f"<- {n} A")
        log.append(dict(m, etapa=f"tela {idx} do fluxo", teclas=f"{n}x A", a_gastos=n))
        seen.add(m["txt"])
        idx += 1
        if m["cash"] < cash0:
            print(f"  >>> caixa CAIU ({cash0} -> {m['cash']}): a rota foi cobrada aqui")
            break
        if world.at_main_menu_img(Image.open(OUT / f"T{idx}_tela{idx - 1}.png").convert("RGB")):
            print("  >>> voltou ao menu principal")
            break

    print(f"\ntotal de A's do fluxo (apos selecionar a cidade): {total_a}")

    # --- rabo: DEPOIS da confirmacao, so avancando frames (sem tecla nenhuma)
    print("\n--- rabo pos-confirmacao (so ADVANCE, nenhuma tecla) ---")
    prev = None
    for i in range(16):
        b.advance(40)
        m = snap(b, f"R{i:02d}")
        novo = "NOVA" if prev is None or m["full"] != prev else "igual"
        line(f"R{i:02d} +{40 * (i + 1)}f", m, novo)
        log.append(dict(m, etapa=f"rabo +{40 * (i + 1)} frames", teclas="(nenhuma)"))
        prev = m["full"]
        if world.at_main_menu_img(Image.open(OUT / f"R{i:02d}.png").convert("RGB")):
            print("  >>> MENU PRINCIPAL alcancado sem apertar nada")
            break

    (OUT / "walk.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    print("\nlog:", OUT / "walk.json")
    print("caixa final:", world.read_cash_k(b), "K  (inicial", cash0, "K)")


def tail():
    """Quantos FRAMES a animacao de abertura leva ate o menu, sem apertar nada.

    O executor precisa desse numero: se ele devolve o controle cedo demais, o
    `_ensure_menu` comeca a apertar B em cima da animacao e a acao SEGUINTE
    encontra o jogo numa tela inesperada.
    """
    dest = sys.argv[2] if len(sys.argv) > 2 else "NA06"
    b = BizHawkBridge()
    g = Game(b, shot_dir=OUT)
    b.load(EVAL)
    b.advance(60)
    g.back_to_menu()
    b.advance(60)
    cash0 = world.read_cash_k(b)

    g.open_cmd("new_route")
    world.wait_text(b)
    world.point_cursor_at(b, dest)
    # 1 A seleciona a cidade + 4 A's ate a tela de confirmacao (uma por tela)
    for _ in range(5):
        antes = world.wait_text(b)
        for _ in range(6):
            b.press("A", hold=5, wait=25)
            if world.wait_text(b) != antes:
                break
    m = snap(b, "X0_confirmacao")
    line("confirmacao", m)

    b.press("A", hold=5, wait=25)  # YES
    frames = 0
    for i in range(60):
        b.advance(20)
        frames += 20
        img = Image.open(b.screenshot(OUT / "_tail.png")).convert("RGB")
        if world.at_main_menu_img(img):
            print(f">>> menu principal {frames} frames depois do A de confirmacao")
            break
    else:
        print(f">>> NAO voltou ao menu em {frames} frames")
    print("caixa:", cash0, "->", world.read_cash_k(b))


if __name__ == "__main__":
    {"walk": walk, "tail": tail}[sys.argv[1]]()
