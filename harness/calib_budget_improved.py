"""Calibração melhorada do r0c4 (orçamentos): Repair/Ad/Service com malha fechada.

Melhorias em relação a calib_budget_fixed.py:
1. Função para ler qual ordem está destacada na popup (por contraste de cores)
2. Navegação com malha fechada: Down + leitura, até a ordem correta estar destacada
3. Registro de TANTO níveis (0-100 via barra verde) QUANTO valores ($K)
4. Teste primeiro com Ad (coluna 1) que tem mais headroom
5. Teste de aplicação dupla (REDUCE duas vezes) sem reload para verificar semântica

TEORIA: se as 5 ordens são ABSOLUTOS (MAXIMUM=nível 100, REDUCE=nível 30), então
aplicar REDUCE duas vezes não muda (estado idempotente). Se são RELATIVOS (REDUCE=−1
notch), então segunda REDUCE → nível 20.
"""
import sys
from pathlib import Path
from PIL import Image
import json

import world
from bridge import BizHawkBridge
from macros import Game
from executor import Executor

O = Path("../logs/calib_budget_improved")
O.mkdir(parents=True, exist_ok=True)
BASE = "../states/_edit_2rotas.state"
COLS = ["Repair", "Ad", "Service"]
ORDERS = ["MAXIMUM", "RAISE", "MAINTAIN", "REDUCE", "STOP"]

b = BizHawkBridge()
g = Game(b, shot_dir=O)


def read_highlighted_order_popup(img):
    """Lê qual ordem está destacada na popup (contraste de cores).

    A popup tem 5 linhas (uma por ordem) com fundo roxo/escuro.
    A ordem destacada tem fundo mais CLARO (rosa/magenta).

    Amostra: cada linha tem ~15 px de altura, começando em y ~= 120.
    Retorna índice 0-4 ou None se não conseguir ler.
    """
    # Coordenadas aproximadas da popup (achadas olhando screenshots)
    # A popup parece ter as 5 ordens em um retângulo
    # Vamos usar a mediana de brilho (R+G+B) para detectar qual está mais clara

    # Bounding box da popup (estimado a partir de screenshots prévios)
    popup_x0, popup_x1 = 80, 170
    popup_y_start = 120
    popup_line_height = 14

    px = img.load()
    brightnesses = []

    for order_idx in range(5):
        y = popup_y_start + order_idx * popup_line_height
        if y + popup_line_height > 224:  # fora da tela
            brightnesses.append(None)
            continue

        # Amostra o meio da linha (região central)
        x_sample = (popup_x0 + popup_x1) // 2
        y_sample = y + popup_line_height // 2

        try:
            r, g, b = px[x_sample, y_sample][:3]
            brightness = (r + g + b) // 3
            brightnesses.append(brightness)
        except (IndexError, TypeError):
            brightnesses.append(None)

    # A linha destacada tem o brilho MÁXIMO
    valid = [(i, b) for i, b in enumerate(brightnesses) if b is not None]
    if not valid:
        return None

    highlighted_idx = max(valid, key=lambda x: x[1])[0]
    return highlighted_idx


def show(tag, extra=""):
    p = b.screenshot(O / f"{tag}.png")
    img = Image.open(p).convert("RGB")
    col = world.read_budget_col(img)
    lvls = world.read_budget_levels(img)
    labels = world.read_budget_orders(img)
    money = world.read_budget_money(img)
    cash = world.read_cash_k(b)
    highlighted = read_highlighted_order_popup(img)
    msg = f"  {tag}: col={col} lvls={lvls} labels={labels} money={money} highlighted={highlighted} cash={cash}K"
    if extra:
        msg += f" | {extra}"
    print(msg, flush=True)
    return img, {
        "col": col,
        "lvls": lvls,
        "labels": labels,
        "money": money,
        "highlighted": highlighted,
        "cash": cash,
    }


def open_budgets():
    ex = Executor(b)
    ex._ensure_menu()
    g.open_cmd("budgets")
    b.advance(200)
    return ex


def goto_col_order_closedloop(col, orden_idx):
    """Navega para a coluna e ordem com malha fechada (lê após cada toque).

    Retorna dict com dados pré e pós confirmação.
    """
    ex = Executor(b)

    # STEP 1: navegar para a coluna
    print(f"  -> navegando para col={col}, orden={orden_idx}")
    img = Image.open(b.screenshot()).convert("RGB")
    col_atual = world.read_budget_col(img)
    print(f"     col atual = {col_atual}")

    # Navegar a coluna (malha fechada)
    steps_needed = (col - col_atual) % 3
    for step in range(steps_needed):
        b.press("Right", hold=3, wait=14)
        b.advance(40)
        img = Image.open(b.screenshot()).convert("RGB")
        col_novo = world.read_budget_col(img)
        print(f"     pos {step+1}/{steps_needed}: col {col_atual} -> {col_novo}")
        col_atual = col_novo

    # STEP 2: abrir a popup de ordem
    b.press("A", hold=5, wait=25)
    b.advance(200)

    # STEP 3: dentro da popup, navegar para a ordem (malha fechada)
    print(f"     dentro da popup, navegando para orden={orden_idx}")
    img = Image.open(b.screenshot()).convert("RGB")
    orden_atual = read_highlighted_order_popup(img)
    print(f"     orden destacada = {orden_atual}")

    # Down até a ordem correta estar destacada
    max_tries = 2 * 5 + 4  # template do §17.4
    tries = 0
    while orden_atual != orden_idx and tries < max_tries:
        b.press("Down", hold=3, wait=14)
        b.advance(40)
        img = Image.open(b.screenshot()).convert("RGB")
        orden_novo = read_highlighted_order_popup(img)
        print(f"     try {tries+1}: orden {orden_atual} -> {orden_novo}")
        orden_atual = orden_novo
        tries += 1

    if orden_atual != orden_idx:
        print(f"     FALHA: nao consegui navegar para orden {orden_idx} (parei em {orden_atual})")
        return None

    # Capturar antes de confirmar
    img_pre, data_pre = show(f"x_pre_{COLS[col]}_{ORDERS[orden_idx]}", "pre-confirm")

    # STEP 4: confirmar (apertar A até a pergunta mudar x2)
    for _ in range(2):
        ex._step(tries=4)
    b.advance(120)

    # Capturar depois
    img_pos, data_pos = show(f"x_pos_{COLS[col]}_{ORDERS[orden_idx]}", "post-confirm")

    return {
        "col": col,
        "orden": orden_idx,
        "pre": data_pre,
        "pos": data_pos,
    }


def test_double_reduce():
    """Testa aplicar REDUCE duas vezes sem reload (teste semântico)."""
    print("\n=== TESTE: APPLY REDUCE TWICE (sem reload) ===")
    print("Objetivo: detectar se as ordens são ABSOLUTAS ou RELATIVAS")

    b.load(BASE)
    b.advance(120)
    b.speed(400)
    ex = open_budgets()

    # Aplicar REDUCE primeira vez
    print("\nPrimeira REDUCE:")
    result1 = goto_col_order_closedloop(1, 3)  # Ad, REDUCE
    if result1 is None:
        print("  FALHOU na primeira REDUCE")
        return

    # Voltar ao menu e reabrir SEM reload
    print("\nSegunda REDUCE (sem reload):")
    ex.dismiss_to_menu()
    b.advance(120)
    open_budgets()

    result2 = goto_col_order_closedloop(1, 3)  # Ad, REDUCE novamente
    if result2 is None:
        print("  FALHOU na segunda REDUCE")
        return

    # Comparar
    money1_pre = result1["pre"]["money"][1]
    money1_pos = result1["pos"]["money"][1]
    money2_pre = result2["pre"]["money"][1]
    money2_pos = result2["pos"]["money"][1]

    print(f"\nRESULTADO:")
    print(f"  1ª REDUCE: ${money1_pre}K -> ${money1_pos}K")
    print(f"  2ª REDUCE: ${money2_pre}K -> ${money2_pos}K")

    if money1_pos == money2_pos:
        print(f"  CONCLUSÃO: ABSOLUTAS (ambas para ${money2_pos}K)")
    else:
        print(f"  CONCLUSÃO: RELATIVAS (decremento de {money1_pos - money2_pos}K)")

    b.speed(100)


fase = sys.argv[1] if len(sys.argv) > 1 else "sweep"

if fase == "sweep":
    col = int(sys.argv[2]) if len(sys.argv) > 2 else 1  # default = Ad (mais headroom)
    print(f"\n=== SWEEP COLUNA {col} ({COLS[col]}) com MALHA FECHADA ===")

    results = []
    for o in range(5):
        print(f"\nOrdem {o} ({ORDERS[o]}):")
        b.load(BASE)
        b.advance(120)
        b.speed(400)
        open_budgets()
        result = goto_col_order_closedloop(col, o)

        if result:
            print(f"  RESULTADO PRÉ:  lvls={result['pre']['lvls']} money={result['pre']['money']} labels={result['pre']['labels']}")
            print(f"  RESULTADO PÓS:  lvls={result['pos']['lvls']} money={result['pos']['money']} labels={result['pos']['labels']}")
            results.append(result)
        else:
            print(f"  NAVEGAÇÃO FALHOU")

        b.speed(100)

    # Salvar results em JSON
    results_file = O / f"sweep_col{col}_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResultados salvos em {results_file}")

elif fase == "drift":
    col = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    orden = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    n_turns = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    print(f"\n=== DRIFT COLUNA {col} ({COLS[col]}), ORDEM {orden} ({ORDERS[orden]}), {n_turns} TURNOS ===")

    b.load(BASE)
    b.advance(120)
    b.speed(400)
    ex = open_budgets()
    show(f"d0_before", "baseline antes da ação")

    result = goto_col_order_closedloop(col, orden)
    show(f"d0_after", "logo após aplicar ordem")

    # Passar turnos e medir
    for t in range(1, n_turns + 1):
        ex._ensure_menu()
        g.end_turn()
        b.advance(120)
        ex._ensure_menu()
        open_budgets()
        show(f"d{t}_turn{t}", f"após {t} turn(s)")

    b.speed(100)
    print("\n")

elif fase == "double_reduce":
    test_double_reduce()

else:
    print(f"Fase desconhecida: {fase}")
    print("Use: sweep [col] | drift [col] [orden] [n_turns] | double_reduce")
