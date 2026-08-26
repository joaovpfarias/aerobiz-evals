"""Calibracao do comando r0c4 (orcamentos): Repair / Ad / Service — VERSAO CORRIGIDA.

Fluxo:
  r0c4 -> "Change which budget?"  (leia col atual)
   A   -> "What are your orders?" (leia ordem atual)
   Down -> proxima ordem (1 at a time, com leitura)
   A   -> "Are you sure you want ... ?"
   A   -> aplica e VOLTA para "Change which budget?"

Fases:
  sweep [col]   aplica cada uma das 5 ordens a coluna `col` (0=Rep 1=Ad 2=Svc),
                uma recarga do savestate por ordem, leituras em malha fechada
  drift col ord n   aplica a ordem e passa n trimestres, capturando a tela de
                orcamento a cada trimestre (verifica se o nivel muda no ato ou so apos turn)
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from macros import Game
from executor import Executor

O = Path("../logs/edit_fixed")
O.mkdir(parents=True, exist_ok=True)
BASE = "../states/_edit_2rotas.state"
COLS = ["Repair", "Ad", "Service"]
ORDERS = ["MAXIMUM", "RAISE", "MAINTAIN", "REDUCE", "STOP"]

b = BizHawkBridge()
g = Game(b, shot_dir=O)


def show(tag, extra=""):
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
    return img, (col, lvls, labels, money, cash)


def open_budgets():
    ex = Executor(b)
    ex._ensure_menu()
    g.open_cmd("budgets")
    b.advance(200)
    return ex


def goto_col_order(col, orden_idx):
    """Navega para a coluna `col` (0-2) e abre a popup da ordem `orden_idx` (0-4).

    CORREÇÕES (18/08):
    1. Verificar qual ordem está selecionada ANTES de fazer Downs (via labels)
    2. Só fazer Downs se necessário
    3. Guardar contra overshoot com on_budget_screen() após confirmar
    4. Verificar que a ordem selecionada é correta antes de confirmar
    """
    ex = Executor(b)

    # STEP 1: navegar para a coluna na tela de orcamentos
    print(f"  -> navegando para col={col}, orden={orden_idx}")
    img = Image.open(b.screenshot()).convert("RGB")
    col_atual = world.read_budget_col(img)
    print(f"     col atual = {col_atual}")

    # Navegar a coluna (fechada em malha)
    steps_needed = (col - col_atual) % 3
    for step in range(steps_needed):
        b.press("Right", hold=3, wait=14)
        b.advance(40)
        img = Image.open(b.screenshot()).convert("RGB")
        col_novo = world.read_budget_col(img)
        print(f"     pos {step+1}/{steps_needed}: col {col_atual} -> {col_novo}")
        col_atual = col_novo

    # STEP 2: abrir a popup de ordem (apertar A)
    b.press("A", hold=5, wait=25)
    b.advance(200)

    # STEP 3: dentro da popup, verificar qual ordem está destacada
    # e navegar se necessário (malha fechada)
    img = Image.open(b.screenshot()).convert("RGB")
    labels_atual = world.read_budget_orders(img)
    orden_atual_lido = labels_atual[col] if labels_atual and labels_atual[col] else None
    orden_idx_atual = ORDERS.index(orden_atual_lido.upper()) if orden_atual_lido else 0

    print(f"     dentro da popup, ordem selecionada = {orden_atual_lido} (idx {orden_idx_atual})")
    print(f"     navegando para orden={orden_idx} ({ORDERS[orden_idx]})")

    # Fazer Downs até chegar na ordem desejada (malha fechada)
    tries = 0
    max_tries = 2 * 5 + 4
    while orden_idx_atual < orden_idx and tries < max_tries:
        b.press("Down", hold=3, wait=14)
        b.advance(40)
        img = Image.open(b.screenshot()).convert("RGB")
        labels_atual = world.read_budget_orders(img)
        orden_atual_lido = labels_atual[col] if labels_atual and labels_atual[col] else None
        orden_idx_novo = ORDERS.index(orden_atual_lido.upper()) if orden_atual_lido else orden_idx_atual
        print(f"     try {tries+1}: ordem {orden_idx_atual} -> {orden_idx_novo}")
        orden_idx_atual = orden_idx_novo
        tries += 1

    if orden_idx_atual != orden_idx:
        print(f"     AVISO: nao alcancei a ordem {orden_idx}, parei em {orden_idx_atual}")

    # Capturar antes de confirmar
    img_pre, (col_pre, lvls_pre, labels_pre, money_pre, cash_pre) = show(f"x_pre_{COLS[col]}_{ORDERS[orden_idx]}", "pre-confirm")

    # VERIFICAÇÃO: a ordem selecionada é a correta?
    if labels_pre and labels_pre[col] and labels_pre[col].upper() != ORDERS[orden_idx]:
        print(f"     AVISO: ordem selecionada é {labels_pre[col]}, não {ORDERS[orden_idx]}")

    # STEP 4: confirmar a ordem (apertar A ate a pergunta mudar x2)
    # GUARDA: verificar que ainda estamos na tela de orçamento
    for i in range(2):
        img_check = Image.open(b.screenshot()).convert("RGB")
        if not world.on_budget_screen(img_check):
            print(f"     AVISO: deixei a tela de orçamento no confirm A#{i+1}")
            break
        ex._step(tries=4)
    b.advance(120)

    # Capturar depois
    img_pos, (col_pos, lvls_pos, labels_pos, money_pos, cash_pos) = show(f"x_pos_{COLS[col]}_{ORDERS[orden_idx]}", "post-confirm")

    return {
        "col": col,
        "orden": orden_idx,
        "pre": {"col": col_pre, "lvls": lvls_pre, "labels": labels_pre, "money": money_pre, "cash": cash_pre},
        "pos": {"col": col_pos, "lvls": lvls_pos, "labels": labels_pos, "money": money_pos, "cash": cash_pos},
    }


fase = sys.argv[1] if len(sys.argv) > 1 else "sweep"

if fase == "sweep":
    col = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    print(f"\n=== SWEEP COLUNA {col} ({COLS[col]}) ===")
    for o in range(5):
        print(f"\nOrdem {o} ({ORDERS[o]}):")
        b.load(BASE)
        b.advance(120)
        b.speed(400)
        open_budgets()
        result = goto_col_order(col, o)
        # Resumo
        print(f"  RESULTADO: money {result['pre']['money']} -> {result['pos']['money']} | "
              f"labels {result['pre']['labels']} -> {result['pos']['labels']}")
        b.speed(100)
    print("\n")

elif fase == "drift":
    col = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    orden = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    n_turns = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    print(f"\n=== DRIFT COLUNA {col} ({COLS[col]}), ORDEM {orden} ({ORDERS[orden]}), {n_turns} TURNOS ===")

    b.load(BASE)
    b.advance(120)
    b.speed(400)
    ex = open_budgets()
    show(f"d0_before", "baseline antes da acao")

    result = goto_col_order(col, orden)
    show(f"d0_after", "logo apos aplicar ordem")

    # Passar turnos e medir
    for t in range(1, n_turns + 1):
        ex._ensure_menu()
        g.end_turn()
        b.advance(120)
        ex._ensure_menu()
        open_budgets()
        show(f"d{t}_turn{t}", f"apos {t} turn(s)")

    b.speed(100)
    print("\n")

else:
    print(f"Fase desconhecida: {fase}")
    print("Use: sweep [col] | drift [col] [orden] [n_turns]")
