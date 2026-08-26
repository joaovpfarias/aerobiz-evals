"""PROVA de buy_aircraft pelo caminho que o piloto chama (Executor.run).

Fases:
  one <MODELO> [qtd]   compra a partir do savestate do eval e confere caixa+frota
  wrong                pede um modelo com painel trocado (teste do gate de painel)
  deliver <n>          n end_turn e leitura de Info->fleet a cada turno
  route <cidade>       abre rota do savestate pos-entrega (teste do alcance)
  acidx <cid> [n] [dir] calibra aircraft_index na tela de rota
  chain                REGRESSAO: compras e rotas intercaladas, delta x tabela
"""
import sys
from pathlib import Path

from PIL import Image

import world
from bridge import BizHawkBridge
from executor import Executor
from macros import Game

O = Path("../logs/buy")
O.mkdir(parents=True, exist_ok=True)
EVAL = "../states/eval_single_2000_lv5.state"

b = BizHawkBridge()
ex = Executor(b)
g = Game(b, shot_dir=O)
fase = sys.argv[1]


def frota(tag, tries=4):
    """Le Info->fleet com RETRY.

    Depois de um end_turn o jogo intercala mensagens do assessor: a navegacao
    cai numa delas e a captura vira um dialogo, nao a tabela. Assinatura medida:
    as telas de relatorio tem a placa vermelha da companhia (menu_red>=40) e
    NAO tem mapa (land=0); as mensagens do assessor mostram 'CASH' em branco
    (menu_red=0). Mesmo padrao do _staff_px do executor.
    """
    p = None
    for _ in range(tries):
        ex._ensure_menu()
        p = g.info_screen("fleet", tag)
        img = Image.open(p).convert("RGB")
        if world.menu_red(img) >= 40 and world.land_pixels(img) < 200:
            ex._ensure_menu()
            return p
    ex._ensure_menu()
    return p

if fase == "one":
    modelo = sys.argv[2]
    qtd = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    b.load(EVAL)
    b.advance(90)
    b.speed(400)
    ex._ensure_menu()
    antes = world.read_cash_k(b)
    frota_antes = frota(f"frota_antes_{modelo}")
    print(f"caixa antes: {antes}K | frota: {frota_antes}", flush=True)
    ok, det = ex.run({"action": "buy_aircraft", "params": {"model": modelo, "qty": qtd}})
    depois = world.read_cash_k(b)
    esperado = world.AIRCRAFT_CATALOG[modelo.upper()]["price_k"] * qtd
    print(f"COMPRA {qtd}x {modelo}: ok={ok}\n  {det}", flush=True)
    print(f"  caixa {antes}K -> {depois}K = {antes - depois}K "
          f"(preco de tabela x{qtd} = {esperado}K) "
          f"{'CONFERE' if antes - depois == esperado else 'DIVERGE'}", flush=True)
    b.advance(180)
    ex._ensure_menu()
    print("  frota depois:", frota(f"frota_depois_{modelo}"), flush=True)
    b.save(f"../states/_buy_prova_{modelo}.state")
    b.speed(100)

elif fase == "deliver":
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    b.speed(400)
    for t in range(1, n + 1):
        antes = world.read_cash_k(b)
        g.end_turn()
        b.advance(120)
        ex._ensure_menu()
        p = frota(f"frota_turno{t}")
        print(f"  turno {t}: caixa {antes}K -> {world.read_cash_k(b)}K | {p}", flush=True)
        b.save("../states/_buy_entregue.state")
    b.speed(100)

elif fase == "route":
    cid = sys.argv[2]
    b.speed(400)
    ex._ensure_menu()
    antes = world.read_cash_k(b)
    ok, det = ex.run({"action": "open_route", "params": {"to": cid}})
    print(f"ROTA {cid}: ok={ok}\n  {det}\n  caixa {antes}K -> {world.read_cash_k(b)}K",
          flush=True)
    b.speed(100)

elif fase == "wrong":
    b.load(EVAL)
    b.advance(90)
    b.speed(400)
    ex._ensure_menu()
    ok, det = ex.run({"action": "buy_aircraft", "params": {"model": "CONCORDE"}})
    print(f"modelo inexistente: ok={ok}\n  {det}", flush=True)
    ok, det = ex.run({"action": "buy_aircraft", "params": {"model": "B747-400", "qty": 99}})
    print(f"qty invalida: ok={ok}\n  {det}", flush=True)
    ok, det = ex.run({"action": "buy_aircraft", "params": {"model": "B747-400", "qty": 10}})
    print(f"caixa insuficiente (10x135000K): ok={ok}\n  {det}", flush=True)
    b.speed(100)

elif fase == "acidx":
    # aircraft_index na tela de ROTA, com mais de um modelo na frota
    dest = sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    import hashlib
    b.speed(400)
    ex._ensure_menu()
    direc = sys.argv[4] if len(sys.argv) > 4 else "Right"
    ex.g.open_cmd("new_route")
    ex._select_city(dest)
    world.wait_text(b)   # sem isso o 1o toque no seletor e engolido
    b.advance(200)
    for i in range(n + 1):
        p = b.screenshot(O / f"acidx_{dest}_{direc}_{i}.png")
        img = Image.open(p).convert("RGB")
        print(f"  idx {i}: panel={hashlib.md5(img.crop((0, 20, 256, 150)).tobytes()).hexdigest()[:8]}",
              flush=True)
        if i < n:
            b.press(direc, hold=3, wait=14)
            b.advance(60)
    b.speed(100)

elif fase == "chain":
    # REGRESSAO: compras e rotas intercaladas, tudo por Executor.run, com o
    # delta de caixa conferido contra o preco de tabela x quantidade.
    b.load(EVAL)
    b.advance(90)
    b.speed(400)
    ex._ensure_menu()
    plano = [
        {"action": "buy_aircraft", "params": {"model": "MD11", "qty": 1}},
        {"action": "open_route", "params": {"to": "NA06"}},
        {"action": "buy_aircraft", "params": {"model": "B777", "qty": 2}},
        {"action": "buy_aircraft", "params": {"model": "MD100", "qty": 1}},
        {"action": "open_route", "params": {"to": "NA03"}},
    ]
    for a in plano:
        antes = world.read_cash_k(b)
        ok, det = ex.run(a)
        dep = world.read_cash_k(b)
        extra = ""
        if a["action"] == "buy_aircraft":
            esperado = (world.AIRCRAFT_CATALOG[a["params"]["model"]]["price_k"]
                        * a["params"]["qty"])
            extra = f" | tabela {esperado}K {'CONFERE' if antes - dep == esperado else 'DIVERGE'}"
        print(f"{a['action']} {a['params']}: ok={ok} caixa {antes} -> {dep}{extra}")
        print("   ", det, flush=True)
    b.speed(100)
