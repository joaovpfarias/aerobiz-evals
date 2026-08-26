"""Calibração v3: usar WAIT_TEXT_CHANGE para sincronizar os Downs (template §17.4)."""
import sys
from pathlib import Path
from PIL import Image
import json

import world
from world import wait_text
from bridge import BizHawkBridge
from macros import Game
from executor import Executor

O = Path("../logs/calib_budget_v3")
O.mkdir(parents=True, exist_ok=True)
BASE = "../states/_edit_2rotas.state"
COLS = ["Repair", "Ad", "Service"]
ORDERS = ["MAXIMUM", "RAISE", "MAINTAIN", "REDUCE", "STOP"]

b = BizHawkBridge()
g = Game(b, shot_dir=O)


def show(tag, extra=""):
    """Captura a tela e lê todos os parâmetros."""
    p = b.screenshot(O / f"{tag}.png")
    img = Image.open(p).convert("RGB")
    col = world.read_budget_col(img)
    lvls = world.read_budget_levels(img)
    labels = world.read_budget_orders(img)
    money = world.read_budget_money(img)
    cash = world.read_cash_k(b)
    msg = f"  {tag}: col={col} lvls={lvls} labels={labels} money={money} cash={cash}K"
    if extra:
        msg += f" | {extra}"
    print(msg, flush=True)
    return {
        "col": col,
        "lvls": lvls,
        "labels": labels,
        "money": money,
        "cash": cash,
    }


def open_budgets():
    """Abre o menu de orçamentos."""
    ex = Executor(b)
    ex._ensure_menu()
    g.open_cmd("budgets")
    b.advance(200)
    return ex


def goto_col_order_synceddown(col, orden_idx):
    """Navega para coluna e ordem com Downs sincronizados por wait_text_change.

    Template do §17.4: um toque, uma leitura de sincronização.
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

    # STEP 3: dentro da popup, navegar para a ordem (SINCRONIZADO)
    # A ideia: cada Down muda o destaque/renderização, detectável por hash da
    # tela (textura diferente = mudança no texto/destaque)
    print(f"     dentro da popup, navegando para orden={orden_idx}")

    # Ler o estado inicial da tela
    before_text = wait_text(b, max_polls=3)
    print(f"     text_hash inicial: {before_text}")

    # Fazer Downs até ordenat_idx ter sido atingido (max_tries = 2*5+4 template)
    current_orden = 0  # começamos em MAXIMUM
    max_tries = 2 * 5 + 4
    tries = 0

    while current_orden < orden_idx and tries < max_tries:
        # Pressionar Down e sincronizar
        b.press("Down", hold=3, wait=14)
        b.advance(40)

        # Esperar a tela estabilizar e ler novamente
        after_text = wait_text(b, max_polls=3)
        if after_text != before_text:
            current_orden += 1
            print(f"     try {tries+1}: ordem 0-indexed {current_orden-1} -> {current_orden} (text mudou)")
            before_text = after_text
        else:
            print(f"     try {tries+1}: ordem {current_orden} (text nao mudou, Down engolido?)")

        tries += 1

    if current_orden != orden_idx:
        print(f"     FALHA: nao alcancei orden {orden_idx} (parei em {current_orden})")
        return None

    # Capturar estado pré-confirm
    img_pre = Image.open(b.screenshot()).convert("RGB")
    data_pre = show(f"x_pre_{COLS[col]}_{ORDERS[orden_idx]}", "pre-confirm")

    # STEP 4: confirmar (apertar A até a pergunta mudar x2)
    for _ in range(2):
        ex._step(tries=4)
    b.advance(120)

    # Capturar estado pós-confirm
    img_pos = Image.open(b.screenshot()).convert("RGB")
    data_pos = show(f"x_pos_{COLS[col]}_{ORDERS[orden_idx]}", "post-confirm")

    return {
        "col": col,
        "orden": orden_idx,
        "pre": data_pre,
        "pos": data_pos,
    }


fase = sys.argv[1] if len(sys.argv) > 1 else "sweep"

if fase == "sweep":
    col = int(sys.argv[2]) if len(sys.argv) > 2 else 1  # default = Ad
    print(f"\n=== SWEEP COLUNA {col} ({COLS[col]}) com DOWNS SINCRONIZADOS ===")

    results = []
    for o in range(5):
        print(f"\nOrdem {o} ({ORDERS[o]}):")
        b.load(BASE)
        b.advance(120)
        b.speed(400)
        open_budgets()
        result = goto_col_order_synceddown(col, o)

        if result:
            print(f"  RESULTADO PRÉ:  lvls={result['pre']['lvls']} money={result['pre']['money']} labels={result['pre']['labels']}")
            print(f"  RESULTADO PÓS:  lvls={result['pos']['lvls']} money={result['pos']['money']} labels={result['pos']['labels']}")

            # Calcular deltas
            if result['pre']['money'] and result['pos']['money']:
                money_delta = result['pos']['money'][col] - result['pre']['money'][col]
                lvl_delta = result['pos']['lvls'][col] - result['pre']['lvls'][col]
                print(f"  DELTAS:         lvl {result['pre']['lvls'][col]} -> {result['pos']['lvls'][col]} ({lvl_delta:+d}) | money ${result['pre']['money'][col]}K -> ${result['pos']['money'][col]}K ({money_delta:+d}K)")

            results.append(result)
        else:
            print(f"  NAVEGAÇÃO FALHOU")

        b.speed(100)

    # Salvar resultados
    results_file = O / f"sweep_col{col}_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResultados salvos em {results_file}")

elif fase == "all":
    """Testar todas as 3 colunas."""
    for col in range(3):
        print(f"\n{'='*70}")
        print(f"COLUNA {col} ({COLS[col]})")
        print(f"{'='*70}")
        results = []
        for o in range(5):
            print(f"\nOrdem {o} ({ORDERS[o]}):")
            b.load(BASE)
            b.advance(120)
            b.speed(400)
            open_budgets()
            result = goto_col_order_synceddown(col, o)

            if result:
                print(f"  RESULTADO PRÉ:  lvls={result['pre']['lvls']} money={result['pre']['money']}")
                print(f"  RESULTADO PÓS:  lvls={result['pos']['lvls']} money={result['pos']['money']}")

                if result['pre']['money'] and result['pos']['money']:
                    money_delta = result['pos']['money'][col] - result['pre']['money'][col]
                    lvl_delta = result['pos']['lvls'][col] - result['pre']['lvls'][col]
                    print(f"  DELTAS:         lvl {lvl_delta:+d} | money {money_delta:+d}K")

                results.append(result)
            else:
                print(f"  NAVEGAÇÃO FALHOU")

            b.speed(100)

        # Salvar
        results_file = O / f"sweep_col{col}_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

else:
    print(f"Fase desconhecida: {fase}")
    print("Use: sweep [col] | all")
