"""SUITE UNICA de testes do harness (ETAPA 2-SuiteTestes).

UM comando roda tudo e diz o que quebrou. Ate aqui as provas estavam espalhadas
em ~20 scripts e ninguem rodava todas — foi assim que a regressao do medidor de
slots (CALIBRATION §36) passou despercebida por duas partidas.

Modos:
  --offline   so leituras sobre PNGs em disco. Sem emulador, segundos.
  --vivo      as 11 acoes de pilot.SUPPORTED, cada uma com efeito verificado
              LENDO O ESTADO DE VOLTA DA TELA (R4), savestate proprio por acao
              e restauracao no fim de cada teste (um teste nao contamina o
              proximo). Caixa medida em volta de cada acao (R2).
  --both      offline e depois vivo.

Saida: tabela (nome | veredito | lido | esperado) + exit code:
  0 = tudo OK
  1 = pelo menos uma FALHA de verdade
  2 = so BLOQUEIOs de infra (ponte morta, savestate/PNG ausente) — NAO e
      regressao, e falta de pre-requisito, e o relatorio tem que separar as duas
      coisas (R5).

REUSO: as 5 provas offline sao CHAMADAS como subprocesso e o veredito delas e o
exit code delas — a logica nao foi reescrita. Os testes vivos chamam
Executor.run() (o mesmo caminho que o piloto usa) e os leitores de world.py.

Uso:
  python test_harness.py --offline
  python test_harness.py --vivo [--only wait,open_route]
  python test_harness.py --both
"""

import argparse
import pathlib
import subprocess
import sys
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
RAIZ = HERE.parent
STATES = RAIZ / "states"
LOGS = RAIZ / "logs"
OUT = LOGS / "suite"

sys.path.insert(0, str(HERE))

OK, FALHA, BLOQUEIO = "OK", "FALHA", "BLOQUEIO"


class Rel:
    """Coletor de linhas do relatorio. Imprime cada linha assim que fecha."""

    def __init__(self):
        self.linhas = []

    def add(self, nome, status, lido, esperado, extra=""):
        self.linhas.append((nome, status, str(lido), str(esperado), extra))
        marca = {OK: "OK   ", FALHA: "FALHA", BLOQUEIO: "BLOQ "}[status]
        print(f"  [{marca}] {nome}: lido={lido!s} | esperado={esperado!s}"
              + (f" | {extra}" if extra else ""), flush=True)
        return status == OK

    def tabela(self):
        larg = max([len(l[0]) for l in self.linhas] + [10])
        print("\n" + "=" * 100)
        print(f"{'TESTE'.ljust(larg)}  {'VEREDITO'.ljust(8)}  LIDO  vs  ESPERADO")
        print("-" * 100)
        for nome, status, lido, esp, extra in self.linhas:
            print(f"{nome.ljust(larg)}  {status.ljust(8)}  {lido}  vs  {esp}"
                  + (f"   [{extra}]" if extra else ""))
        print("=" * 100)
        n_ok = sum(1 for l in self.linhas if l[1] == OK)
        n_f = sum(1 for l in self.linhas if l[1] == FALHA)
        n_b = sum(1 for l in self.linhas if l[1] == BLOQUEIO)
        print(f"TOTAL: {len(self.linhas)} testes | {n_ok} OK | {n_f} FALHA | {n_b} BLOQUEIO")
        if n_f:
            print("FALHAS:")
            for nome, status, lido, esp, extra in self.linhas:
                if status == FALHA:
                    print(f"  - {nome}: lido {lido}, esperado {esp} {extra}")
        if n_b:
            print("BLOQUEIOS (infra/pre-requisito, NAO regressao):")
            for nome, status, lido, esp, extra in self.linhas:
                if status == BLOQUEIO:
                    print(f"  - {nome}: {lido}")
        return 1 if n_f else (2 if n_b else 0)


# =============================================================================
# OFFLINE
# =============================================================================

# As 5 provas que NAO importam bridge.py. Todas verificadas: as 5 tem caminho de
# saida != 0 (sys.exit(1) / return 1) — envolver um script que nao pode falhar e
# imprimir OK seria a mentira do R4 no sentido do sucesso.
PROVAS_OFFLINE = [
    ("prova_tabelas", "read_routes/read_fleet/read_footer_cash_k sobre 3 PNGs"),
    ("prova_slots_qty", "read_slots_qty sobre PNGs da tela 'How many slots?'"),
    ("prova_city_panel", "read_city_panel: 9 paineis + negativos + oraculo + fonte"),
    ("prova_lideres", "read_regional_leaders estavel entre 2 momentos"),
    ("prova_pnl", "read_pnl + guard de Quarterly Report"),
    ("prova_detect_region", "detect_region por forma: 12 mapas reais com rota + "
                            "420 sinteticos nas 7 regioes + negativos"),
]

# REGRESSAO §36 (ETAPA 1-RegressaoSlots). O medidor de "How many slots?" tem N
# posicoes e N MUDA POR CIDADE; a tabela antiga assumia 5 sempre e devolvia None
# ("medidor ilegivel") em NA06/NA02, bloqueando partidas.
# Chaveado por CAMINHO RELATIVO, nao por basename: existem dois neg_EU11.png com
# valores esperados DIFERENTES (o de run_f0 e um frame do MEIO do desenho e tem
# que dar None; o de etapa1_slots e o frame completo e tem que dar (1, 5)).
# Sem o caso (1,5) um leitor que devolvesse None para tudo passaria.
REGRESSAO_GAUGE = [
    ("run_f0/neg_semqtd_NA06.png", (1, 2), "cidade com teto 2 (bug: dava None)"),
    ("run_f0/neg_semqtd_NA02.png", (1, 3), "cidade com teto 3 (bug: dava None)"),
    # Toronto tem 11 posicoes e o medidor passa da largura da caixa antiga.
    # Enquanto SLOTS_MAX era 5, NA12 dava None e a baseline gulosa perdeu 10
    # negociacoes seguidas reincidindo na mesma cidade.
    ("run_f0/neg_semqtd_NA12.png", (1, 11), "teto 11 (bug: SLOTS_MAX=5 dava None)"),
    ("run_f0/neg_EU11.png", None, "frame no MEIO do desenho: tem que ser recusado"),
    ("etapa1_slots/neg_EU11.png", (1, 5), "frame completo: teto 5"),
]

# ETAPA 2-OraculosFracos — par ROTULADO do resumo de rota (Washington-San Fran).
# (on_summary, Flts, Fare%). O 2o PNG e a REABERTURA depois de sair ate o menu,
# entao prova persistencia, nao buffer de tela.
REGRESSAO_ETAPA2_RESUMO = [
    ("edit_commit/a_summary.png", (True, 1, 0), "antes do ajuste: Flts 1, Fare $720/0%"),
    ("edit_commit/n_reopen_summary.png", (True, 2, 10),
     "REABERTO apos commit: Flts 2, Fare $792/10%"),
    ("edit_commit/d_after_A.png", (False, None, None),
     "barra de abas NAO e o resumo: guard tem que recusar"),
    ("edit_commit/k_confirm_full.png", (False, None, None),
     "dialogo YES/NO NAO e o resumo: guard tem que recusar"),
    ("edit_commit/m_back_to_menu.png", (False, None, None),
     "menu principal NAO e o resumo: guard tem que recusar"),
]

# As duas corridas em que `return_slots` devolveu ok=True EM CIMA DA RECUSA.
REGRESSAO_ETAPA2_RECUSA = [
    ("return_slots_aceite/return_slots_SA01_confirmado.png", True,
     "corrida 1: 'All of your slots in this city are currently being used'"),
    ("return_slots_debug/return_slots_SA01_confirmado.png", True,
     "corrida 2: mesma recusa, mesmo hash de TEXTBOX"),
    ("return_slots_aceite/return_slots_SA01_mapa.png", False,
     "tela do mapa com 'Havana': NAO e recusa, nao pode dar falso positivo"),
]


def roda_offline(rel):
    print("\n### OFFLINE — leitores sobre PNGs em disco (sem emulador)\n", flush=True)

    print("-- provas existentes (chamadas como subprocesso; veredito = exit code)", flush=True)
    for nome, desc in PROVAS_OFFLINE:
        script = HERE / f"{nome}.py"
        if not script.exists():
            rel.add(nome, BLOQUEIO, "script ausente", "arquivo existe", str(script))
            continue
        t0 = time.time()
        try:
            p = subprocess.run([sys.executable, str(script)], cwd=str(HERE),
                               capture_output=True, text=True, timeout=600,
                               env=_env_utf8())
        except subprocess.TimeoutExpired:
            rel.add(nome, FALHA, "timeout 600s", "exit 0", desc)
            continue
        rc = p.returncode
        ultima = ""
        for ln in reversed((p.stdout or "").splitlines()):
            if ln.strip():
                ultima = ln.strip()[:70]
                break
        if rc == 0:
            rel.add(nome, OK, "exit 0", "exit 0", f"{ultima} ({time.time()-t0:.1f}s)")
        else:
            _dump(nome, p)
            rel.add(nome, FALHA, f"exit {rc}", "exit 0", ultima or "ver log")

    print("\n-- REGRESSAO §36: read_slots_gauge = (escolhidos, N) com N por cidade", flush=True)
    try:
        from PIL import Image
        import world
    except Exception as e:  # noqa: BLE001
        rel.add("regressao_slots_gauge", BLOQUEIO, f"import falhou: {e}", "world importavel")
        return
    for rel_path, esperado, porque in REGRESSAO_GAUGE:
        png = LOGS / rel_path
        nome = f"gauge:{rel_path}"
        if not png.exists():
            # PNG de log e arquivo de trabalho, pode nao estar no clone:
            # ausencia NAO e regressao.
            rel.add(nome, BLOQUEIO, "PNG ausente", esperado, str(png))
            continue
        try:
            lido = world.read_slots_gauge(Image.open(png).convert("RGB"))
        except Exception as e:  # noqa: BLE001
            rel.add(nome, FALHA, f"excecao: {e}", esperado, porque)
            continue
        rel.add(nome, OK if lido == esperado else FALHA, lido, esperado, porque)

    # ETAPA 2-OraculosFracos: os DOIS leitores novos, sobre PNGs ja rotulados
    # que estavam em disco. Sem emulador — se algum deles quebrar, a suite viva
    # nao precisa nem subir.
    print("\n-- ETAPA 2: leitores dos oraculos novos (resumo de rota / recusa de return)",
          flush=True)
    for rel_path, esperado, porque in REGRESSAO_ETAPA2_RESUMO:
        png = LOGS / rel_path
        nome = f"resumo:{rel_path}"
        if not png.exists():
            rel.add(nome, BLOQUEIO, "PNG ausente", str(esperado), str(png))
            continue
        r = world.read_route_summary(Image.open(png).convert("RGB"))
        lido = (r["on_summary"], r["flights"], r["fare_pct"])
        rel.add(nome, OK if lido == esperado else FALHA, lido, esperado, porque)

    for rel_path, espera_recusa, porque in REGRESSAO_ETAPA2_RECUSA:
        png = LOGS / rel_path
        nome = f"recusa:{rel_path}"
        if not png.exists():
            rel.add(nome, BLOQUEIO, "PNG ausente", str(espera_recusa), str(png))
            continue
        txt = world.return_slots_refusal(Image.open(png).convert("RGB"))
        lido = txt is not None
        rel.add(nome, OK if lido == espera_recusa else FALHA,
                (txt[:48] + "...") if txt else "sem recusa",
                "recusa reconhecida" if espera_recusa else "nao e recusa", porque)


def _env_utf8():
    import os
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def _dump(nome, p):
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f"{nome}.log"
    f.write_text((p.stdout or "") + "\n--- STDERR ---\n" + (p.stderr or ""),
                 encoding="utf-8", errors="replace")
    print(f"      (saida completa em {f})", flush=True)


# =============================================================================
# VIVO — as 11 acoes de pilot.SUPPORTED
# =============================================================================
#
# Cada teste declara:
#   state    : savestate com o PRE-REQUISITO da acao. Um savestate limpo unico
#              faria adjust_route/return_slots/ad_campaign/close_hub falharem por
#              falta de rota/slot/venture/hub — e a tabela imprimiria FALHA para
#              4 acoes que funcionam.
#   seed     : escrituracao que o Executor precisa ter em memoria (rotas/hubs).
#   params   : parametros da acao.
#   verify   : funcao(ctx) -> (ok, lido, esperado). LE A TELA de volta; nunca
#              usa o `ok` de Executor.run() como prova (R4).
#   caixa    : "cai" | "sobe" | "parada" | "qualquer" — direcao ESPERADA do
#              caixa. Nao e uniforme: close_hub CREDITA, set_budget/wait nao
#              mexem, open_route/buy_aircraft debitam.
#
# Os savestates vem das provas que ja calibraram cada acao (prova_adjust,
# prova_close_hub, prova_return_slots, _verify_adcampaign, prova_etapa1_slots).


def _shot(ctx, tag):
    from PIL import Image
    p = ctx["g"].shot(tag)
    return Image.open(p).convert("RGB")


def _tela_menu(ctx, tag):
    ctx["g"].back_to_menu()
    ctx["b"].advance(90)
    return _shot(ctx, tag)


def _le_rotas(ctx, tag):
    """(lista de rotas, contador 'N Rte' do rodape) lidos da tela Info->map."""
    from PIL import Image
    import world
    ctx["ex"]._ensure_menu()
    p = ctx["g"].info_screen("map", tag)
    img = Image.open(p).convert("RGB")
    ctx["ex"]._ensure_menu()
    rotas, n_rte = world.read_routes(img)
    # R1: leitor pode devolver None (tela nao reconhecida). O teste tem que
    # tratar isso como "nao medi", nunca estourar no meio da suite.
    return (rotas if rotas is not None else []), n_rte


def _le_frota(ctx, tag):
    """Frota lida da tela Info->fleet, com o MESMO cuidado de prova_buy.frota().

    MEDIDO (crosscheck_buy_md100.log / crosscheck_etapa3a_b.log, 24/08):
    `g.back_to_menu()` sozinho em volta do info_screen deixa o jogo num ponto de
    onde a acao SEGUINTE morre ("esperava a tela de quantidade de avioes",
    "painel na tela e d9d87bb8"). As duas provas que certificaram open_route e
    buy_aircraft chamam `ex._ensure_menu()` antes e depois e so aceitam o frame
    quando ele e mesmo o menu (vermelho do menu presente, mapa ausente).
    """
    from PIL import Image
    import world
    ex = ctx["ex"]
    img = None
    for _ in range(3):
        ex._ensure_menu()
        p = ctx["g"].info_screen("fleet", tag)
        img = Image.open(p).convert("RGB")
        if world.menu_red(img) >= 40 and world.land_pixels(img) < 200:
            break
    ex._ensure_menu()
    return world.read_fleet(img) if img is not None else []


def _le_staff(ctx, tag):
    """Funcionarios livres, lidos dos bonecos do menu principal."""
    import world
    return world.free_staff_menu(_tela_menu(ctx, tag))


def _le_orcamento(ctx, tag):
    """Ordens das 3 colunas de orcamento, lidas da tela Budgets."""
    import world
    ctx["g"].back_to_menu()
    ctx["g"].open_cmd("budgets")
    ctx["b"].advance(200)
    img = _shot(ctx, tag)
    if not world.on_budget_screen(img):
        ctx["g"].back_to_menu()
        return None
    o = world.read_budget_orders(img)
    ctx["g"].back_to_menu()
    return o


# --- verificadores -----------------------------------------------------------

def v_wait(ctx):
    import world
    img = _tela_menu(ctx, "wait_depois")
    no_menu = world.at_main_menu_img(img)
    parado = ctx["caixa_depois"] == ctx["caixa_antes"]
    return (no_menu and parado,
            f"menu={no_menu} caixa {ctx['caixa_antes']}K->{ctx['caixa_depois']}K",
            "menu=True e caixa parada")


def pre_rotas(ctx):
    ctx["rotas_antes"] = _le_rotas(ctx, "rotas_antes")


def v_open_route(ctx):
    """Oraculo: `in_use` da frota sobe pelo numero de avioes despachados, e o
    DESTINO pedido aparece na tabela de rotas.

    MEDIDO (crosscheck_etapa3a_b.log, 24/08): ler a tela Info->map ANTES de
    `open_route` fazia a acao seguinte morrer em "esperava a tela de quantidade
    de avioes"; a MESMA rota (NA13->NA06, mesmo savestate) abre normalmente
    quando o pre-estado e lido pela tela de FROTA, que e o que prova_etapa3a.py
    ja fazia. Por isso o "antes" desta acao vem da frota, nao do mapa.
    """
    import world
    antes = ctx.get("frota_antes") or []
    depois = _le_frota(ctx, "frota_depois")
    iu_a = (antes[0] or {}).get("in_use") if antes else None
    iu_d = (depois[0] or {}).get("in_use") if depois else None
    n_planes = int(ctx["params"].get("planes", 1))
    rotas, n_rte = _le_rotas(ctx, "rotas_depois")
    alvo = ctx["params"].get("to")
    entrada = world.WORLD_CITIES.get(alvo)
    nome_alvo = entrada[-1] if entrada else None
    destinos = [r.get("dest") for r in rotas]
    achou = alvo in destinos or (nome_alvo is not None and nome_alvo in destinos)
    ok = (isinstance(iu_a, int) and iu_d == iu_a + n_planes) and achou
    return (ok, f"in_use {iu_a} -> {iu_d}, destinos={destinos} ({n_rte} Rte)",
            f"in_use +{n_planes} e destino {nome_alvo or alvo} na tabela")


def pre_frota(ctx):
    ctx["frota_antes"] = _le_frota(ctx, "frota_antes")


def _total_frota(f):
    if not f:
        return 0
    s = 0
    for l in f:
        for k in ("in_use", "avail", "order"):
            if isinstance(l.get(k), int):
                s += l[k]
    return s


def v_buy_aircraft(ctx):
    antes = ctx.get("frota_antes") or []
    depois = _le_frota(ctx, "frota_depois")
    ta, td = _total_frota(antes), _total_frota(depois)
    return td > ta, f"total frota {ta} -> {td}", "total frota maior (qty=1)"


def pre_staff(ctx):
    ctx["staff_antes"] = _le_staff(ctx, "staff_antes")


def v_negotiate_slots(ctx):
    antes = ctx.get("staff_antes")
    depois = _le_staff(ctx, "staff_depois")
    esperado = (antes - 1) if isinstance(antes, int) else "antes-1"
    return depois == esperado, f"funcionarios livres {antes} -> {depois}", f"{esperado}"


def _le_our_slots(ctx, cid, tag):
    """Nossos slots na cidade, do painel (world.read_city_panel). None = nao medi.

    Leitor INDEPENDENTE do executor no sentido da R4: quem responde e a tela,
    nao a string devolvida pela acao. E o mesmo `city_probe` que serve o modelo.
    """
    import city_probe
    ctx["ex"]._ensure_menu()
    dados, avisos = city_probe.inspect(ctx["b"], ctx["ex"], [cid],
                                       shot_dir=str(OUT / f"slots_{tag}"))
    ctx["ex"]._ensure_menu()
    p = dados.get(cid)
    if not p or not p.get("on_panel"):
        ctx.setdefault("avisos", []).append(f"{tag}: painel de {cid} nao lido ({avisos})")
        return None
    return p.get("our_slots")


def pre_return_slots(ctx):
    ctx["slots_antes"] = _le_our_slots(ctx, ctx["params"]["city"], "antes")
    ctx["staff_antes"] = _le_staff(ctx, "staff_antes")


def v_return_slots(ctx):
    """ORACULO NOVO (ETAPA 2): nossos slots NA CIDADE, nao funcionarios livres.

    O oraculo antigo ("livres +1") era falso por construcao — devolver slot nao
    despacha nem recruta funcionario; quem mexe nesse contador e
    `negotiate_slots` (§17.2). Ele mediu 3->3 (+0) porque nao media a acao.
    """
    cid = ctx["params"]["city"]
    antes = ctx.get("slots_antes")
    depois = _le_our_slots(ctx, cid, "depois")
    if antes is None or depois is None:
        return False, f"nossos slots em {cid} NAO MEDIDOS ({antes} -> {depois})", "leitura do painel"
    return depois < antes, f"nossos slots em {cid}: {antes} -> {depois}", "menos slots nossos"


def v_caixa_caiu(ctx):
    d = ctx["caixa_depois"] - ctx["caixa_antes"]
    return d < 0, f"caixa {ctx['caixa_antes']}K -> {ctx['caixa_depois']}K ({d:+d}K)", "caixa MENOR"


def v_close_hub(ctx):
    # Fechar hub CREDITA caixa (pilot.py / ACTION_SPACE r1c0). Exigir queda aqui
    # foi o bug que desfazia fechamentos que tinham funcionado.
    d = ctx["caixa_depois"] - ctx["caixa_antes"]
    return d > 0, f"caixa {ctx['caixa_antes']}K -> {ctx['caixa_depois']}K ({d:+d}K)", "caixa MAIOR (credito)"


def v_ad_campaign(ctx):
    d = ctx["caixa_depois"] - ctx["caixa_antes"]
    return d == -1800, f"delta {d:+d}K", "-1800K exatos"


def pre_budget(ctx):
    ctx["orc_antes"] = _le_orcamento(ctx, "orc_antes")


def v_set_budget(ctx):
    import world
    depois = _le_orcamento(ctx, "orc_depois")
    antes = ctx.get("orc_antes")
    col = world.BUDGET_COLS.index("ad")
    alvo = world.BUDGET_ORDERS[ctx["params"]["level"]]
    if not depois:
        return False, "tela de orcamento ilegivel", f"coluna ad = {alvo}"
    vizinhas_ok = True
    if antes:
        vizinhas_ok = all(antes[j] == depois[j]
                          for j in range(len(world.BUDGET_COLS)) if j != col)
    ok = depois[col] == alvo and vizinhas_ok and ctx["caixa_depois"] >= ctx["caixa_antes"]
    return ok, f"ordens {antes} -> {depois}", f"coluna ad = {alvo}, vizinhas intactas, caixa nao cai"


def _le_resumo_rota(ctx, tag):
    """Flts e Fare(%) lidos do RESUMO da rota (r0c1). Mesma forma de `_le_orcamento`.

    Reabre a tela do zero — a leitura nao aproveita nenhum frame que a acao
    tenha deixado para tras.
    """
    import world
    ctx["g"].back_to_menu()
    ctx["g"].open_cmd("route_edit")
    ctx["b"].advance(200)
    world.wait_text(ctx["b"])
    img = _shot(ctx, tag)
    r = world.read_route_summary(img)
    ctx["g"].back_to_menu()
    ctx["ex"]._ensure_menu()
    return r


def v_adjust_route(ctx):
    """ORACULO NOVO (ETAPA 2): le Flts e Fare DE VOLTA da tela de resumo.

    O oraculo antigo so conferia "1 Rte antes e 1 Rte depois" — passava mesmo
    quando o Flts pedido 1->3 batia no TETO da rota e ficava em 1, porque
    ninguem lia o campo. Agora:
      - Flts lido == pedido  -> passa;
      - Flts lido  < pedido  -> so passa se o executor DECLAROU teto ("TETO" na
        mensagem) E o valor lido for o que ele declarou ter alcancado. Bater no
        teto nao e falha; ESCONDER o teto e.
      - campo ilegivel       -> NAO MEDIDO, reprova (R1/R5).
    A contagem de rotas continua sendo conferida: editar nao pode sumir com a rota.
    """
    import world
    depois, n_depois = _le_rotas(ctx, "rotas_depois")
    antes_rotas, n_antes = ctx.get("rotas_antes", ([], None))
    rotas_ok = n_depois == n_antes and n_depois is not None

    r = _le_resumo_rota(ctx, "resumo_depois")
    det = str(ctx.get("det", ""))
    p = ctx["params"]
    if not r["on_summary"]:
        return False, "resumo da rota ilegivel — NAO MEDI Flts/Fare", "resumo legivel"

    partes = [f"Flts={r['flights']}", f"Fare={r['fare_pct']}% ({r['fare_segs']} seg)",
              f"{n_depois} Rte"]
    esperado = []
    campo_ok = True

    if p.get("flights_week") is not None:
        alvo = int(p["flights_week"])
        esperado.append(f"Flts={alvo} ou teto declarado")
        lido = r["flights"]
        if lido is None:
            campo_ok = False
            partes.append("Flts NAO MEDIDO")
        elif lido == alvo:
            pass
        elif lido < alvo and "TETO" in det and f"TETO em {lido}" in det:
            partes.append(f"TETO em {lido} declarado pelo executor e confirmado na tela")
        else:
            campo_ok = False

    if p.get("fare_level") is not None:
        pct_alvo = world.FARE_STEPS_PCT[p["fare_level"]] if hasattr(world, "FARE_STEPS_PCT") \
            else {"low": -10, "mid": 0, "high": 10}[p["fare_level"]]
        esperado.append(f"Fare={pct_alvo}%")
        if r["fare_pct"] is None:
            campo_ok = False
            partes.append("Fare NAO MEDIDO")
        elif r["fare_pct"] != pct_alvo and "TETO" not in det:
            campo_ok = False

    return (campo_ok and rotas_ok), "; ".join(partes), \
        "; ".join(esperado + [f"{n_antes} Rte (rota preservada)"])


VIVOS = [
    dict(nome="wait", state="eval_single_2000_lv5",
         action="wait", params={}, caixa="parada", verify=v_wait),

    # `open_route` so e aceita para cidade onde JA temos slots. O savestate do
    # eval tem slots em NA13/NA06/NA02/NA03/NA05 (world.EVAL_SLOTS_2000) e o
    # Executor precisa ter essa escrituracao em memoria — sem `seed_slots` a
    # macro recusa antes de tocar no jogo, como prova_etapa3a ja documentava.
    dict(nome="open_route", state="eval_single_2000_lv5",
         action="open_route", params={"from": "NA13", "to": "NA06",
                                      "planes": 1, "flights_week": 1},
         caixa="cai", seed_slots="EVAL_SLOTS_2000",
         pre=pre_frota, verify=v_open_route),

    dict(nome="negotiate_slots", state="eval_single_2000_lv5",
         action="negotiate_slots", params={"city": "NA06", "slots": 2}, caixa="qualquer",
         pre=pre_staff, verify=v_negotiate_slots),

    dict(nome="negotiate_slots_guard_teto", state="eval_single_2000_lv5",
         action="negotiate_slots", params={"city": "NA06", "slots": 5}, caixa="qualquer",
         espera_recusa=True, pre=pre_staff, verify=None,
         nota="REGRESSAO §36 ao vivo: NA06 tem teto 2; pedir 5 tem que ser RECUSADO "
              "com o teto lido da tela e sem gastar funcionario"),

    dict(nome="buy_aircraft", state="eval_single_2000_lv5",
         # `model` e o NOME do modelo, nao um indice (a macro devolve a lista de
         # modelos disponiveis quando nao reconhece) — audit_all_actions.py
         # passava 0 e por isso registrava falha.
         action="buy_aircraft", params={"model": "MD100", "qty": 1}, caixa="cai",
         pre=pre_frota, verify=v_buy_aircraft),

    dict(nome="open_hub", state="prova_ic_rota_sa",
         action="open_hub", params={"region": 1}, caixa="cai", verify=v_caixa_caiu),

    dict(nome="adjust_route", state="probe_hub_open_sa",
         action="adjust_route", params={"route": "SA01", "flights_week": 3, "fare_level": "high"},
         caixa="qualquer", seed_routes=[{"from": "NA13", "to": "SA01", "flights": 1,
                                         "fare_level": "mid"}],
         pre=pre_rotas, verify=v_adjust_route),

    # ACEITE: cidade onde temos slots LIVRES. NA06/Denver tem 12 slots nossos no
    # savestate do eval (world.EVAL_SLOTS_2000, medido) e NENHUMA rota aberta.
    # FORA DO ACTION SPACE desde 24/08 (ETAPA 2-OraculosFracos) — ver pilot.py.
    # NA06/Denver: 12 slots nossos, zero rotas. Duas cadeias de confirmacao
    # diferentes, duas corridas: nossos slots 12 -> 12 no painel, caixa parada.
    # O que este caso guarda agora e o COMPORTAMENTO GUARDADO: sem queda medida
    # a acao tem que devolver ok=False e restaurar o estado. Se um dia alguem
    # calibrar a cadeia de verdade, este caso vira aceite de novo (verify=
    # v_return_slots) e `return_slots` volta a pilot.SUPPORTED.
    dict(nome="return_slots_sem_efeito", state="eval_single_2000_lv5",
         action="return_slots", params={"city": "NA06"}, caixa="parada",
         espera_recusa=True, recusa_contem="travou no passo",
         pre=pre_return_slots, verify=None,
         nota="acao SEM EFEITO MEDIDO (12 -> 12 nossos slots, 2 corridas); ok=True "
              "aqui seria a mentira que a ETAPA 2 veio matar"),

    # REGRESSAO DA MENTIRA (ETAPA 2-OraculosFracos): em probe_hub_open_sa o
    # slot de SA01/Havana esta EM USO pela rota NA13->SA01 e o jogo responde
    # "All of your slots in this city are currently being used. It's impossible
    # to return them at this time." — capturado em logs/return_slots_aceite/ e
    # logs/return_slots_debug/ (2 corridas). O harness devolvia ok=True em cima
    # dessa tela. Agora tem que RECUSAR.
    dict(nome="return_slots_recusa_em_uso", state="probe_hub_open_sa",
         action="return_slots", params={"city": "SA01"}, caixa="qualquer",
         espera_recusa=True, recusa_contem="NAO MEDIDO",
         pre=pre_staff, verify=None,
         seed_routes=[{"from": "NA13", "to": "SA01", "flights": 1, "fare_level": "mid"}],
         nota="LIMITE HONESTO: nas 3 corridas de 24/08 este caso NUNCA chegou a tela "
              "de recusa do jogo — o painel de SA01 nao abriu e o executor abortou "
              "ANTES de tocar no jogo (R1). Quem exercita `world.return_slots_refusal` "
              "e a regressao OFFLINE REGRESSAO_ETAPA2_RECUSA (--offline), sobre os PNGs "
              "em disco. Aqui o que esta medido e o guard R1. "
              "slot ocupado por rota nao pode ser devolvido; ok=True aqui e a mentira "
              "que a ETAPA 2 veio matar"),

    # close_hub exige hub CONFIRMADO na escrituracao do Executor (nao basta o
    # savestate ter o hub na tela) — mesmo setup de _verify_close_hub_final.py.
    dict(nome="close_hub", state="_hub_rota_do_hub",
         action="close_hub", params={"region": 1}, caixa="sobe",
         seed_hubs=("HOME", "SA01"), verify=v_close_hub),

    # `city` e o ID do catalogo (NA13), nunca o nome humano — audit_open_venture.py
    # passava "Washington" e a macro recusa antes de tocar no jogo.
    dict(nome="open_venture", state="eval_single_2000_lv5",
         action="open_venture", params={"city": "NA13", "type_index": 0},
         caixa="cai", verify=v_caixa_caiu),

    dict(nome="ad_campaign", state="_venture_pronto",
         action="ad_campaign", params={}, caixa="cai", verify=v_ad_campaign),

    dict(nome="set_budget", state="eval_single_2000_lv5",
         action="set_budget", params={"category": "ad", "level": 1}, caixa="parada",
         pre=pre_budget, verify=v_set_budget),
]


def roda_vivo(rel, only=None):
    print("\n### VIVO — 11 acoes de pilot.SUPPORTED, efeito lido da tela\n", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)

    try:
        from bridge import BizHawkBridge
    except Exception as e:  # noqa: BLE001
        rel.add("ponte", BLOQUEIO, f"import falhou: {e}", "bridge importavel")
        return
    b = BizHawkBridge()
    try:
        b.ping()
    except Exception as e:  # noqa: BLE001
        rel.add("ponte", BLOQUEIO,
                f"ping falhou ({e}) — suba launch.ps1 com a ROM e espere o boot (~40s)",
                "ponte viva")
        for t in VIVOS:
            if only and t["nome"] not in only:
                continue
            rel.add(t["nome"], BLOQUEIO, "ponte morta", "ponte viva")
        return
    rel.add("ponte", OK, "ping respondeu", "ponte viva")

    from executor import Executor
    from macros import Game
    import world

    # Cobertura: a suite tem que cobrir TODAS as acoes de pilot.SUPPORTED. Se
    # alguem adicionar uma acao e esquecer o teste, isto denuncia.
    try:
        import pilot
        cobertas = {t["action"] for t in VIVOS}
        faltando = [a for a in pilot.SUPPORTED if a not in cobertas]
        rel.add("cobertura_SUPPORTED", OK if not faltando else FALHA,
                f"{len(cobertas)}/{len(pilot.SUPPORTED)} acoes cobertas"
                + (f", faltando {faltando}" if faltando else ""),
                "todas as acoes de pilot.SUPPORTED tem teste")
    except Exception as e:  # noqa: BLE001
        rel.add("cobertura_SUPPORTED", BLOQUEIO, f"import pilot falhou: {e}", "pilot importavel")

    for t in VIVOS:
        nome = t["nome"]
        if only and nome not in only:
            continue
        st = STATES / f"{t['state']}.state"
        if not st.exists():
            rel.add(nome, BLOQUEIO, f"savestate ausente: {t['state']}.state",
                    "pre-requisito em disco", t.get("nota", ""))
            continue
        try:
            _um_teste_vivo(rel, b, Executor, Game, world, t, st)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            rel.add(nome, FALHA, f"excecao na suite: {e}", "teste roda ate o fim")
        finally:
            # RESTAURA sempre: um teste nao pode contaminar o proximo. A caixa
            # e MEDIDA depois do reload e impressa — sem isso "restaurei" seria
            # so uma afirmacao (R4). MEDIDO na run 1: `close_hub` comecou com a
            # caixa que `open_hub` deixou, prova de que so chamar b.load() no
            # fim do teste anterior nao basta quando o savestate e OUTRO.
            try:
                b.load(str(st.resolve()))
                b.advance(120)
                print(f"   restaurado {t['state']}: caixa {world.read_cash_k(b)}K",
                      flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"   RESTAURACAO FALHOU ({t['state']}): {e}", flush=True)


def _um_teste_vivo(rel, b, Executor, Game, world, t, st):
    nome = t["nome"]
    print(f"\n-- {nome} (savestate {t['state']})", flush=True)
    b.load(str(st.resolve()))
    b.advance(120)
    g = Game(b, shot_dir=OUT / nome)
    ex = Executor(b)
    ex.g = g
    # ordem importa: reset_world_state zera a escrituracao, entao vem ANTES das
    # rotas semeadas a mao.
    if t.get("seed_slots"):
        ex.reset_world_state(owned_slots=dict(getattr(world, t["seed_slots"])))
    if t.get("seed_hubs"):
        ex.reset_world_state(hubs={world.HOME if h == "HOME" else h
                                   for h in t["seed_hubs"]})
    if t.get("seed_routes"):
        ex.routes = list(t["seed_routes"])
    ex._ensure_menu()

    ctx = {"b": b, "g": g, "ex": ex, "params": t["params"]}
    if t.get("pre"):
        t["pre"](ctx)
        ex._ensure_menu()

    ctx["caixa_antes"] = world.read_cash_k(b)
    t0 = time.time()
    ok, det = ex.run({"action": t["action"], "params": t["params"]})
    ctx["caixa_depois"] = world.read_cash_k(b)
    dt = time.time() - t0
    det = str(det)
    ctx["ok"], ctx["det"] = ok, det
    det = det[:200]
    print(f"   executor: ok={ok} | {det} | {dt:.0f}s", flush=True)

    # (a) GUARDA que devia RECUSAR: sucesso aqui e o bug, nao o aceite.
    if t.get("espera_recusa"):
        staff_depois = _le_staff(ctx, "staff_depois")
        staff_antes = ctx.get("staff_antes")
        gastou = isinstance(staff_antes, int) and staff_depois != staff_antes
        caiu = ctx["caixa_depois"] < ctx["caixa_antes"]
        # `ok=False` sozinho e um oraculo FRACO: abortar antes de tocar no jogo
        # e abortar depois de executar e nao ter efeito dao os dois ok=False.
        # `recusa_contem` (opcional) fixa QUAL recusa e esperada, lida da string
        # de detalhe do executor. Sem isso os dois casos de `return_slots`
        # passariam ate se o motivo mudasse por baixo.
        alvo_txt = t.get("recusa_contem")
        det_txt = str(ctx.get("det", ""))
        txt_ok = (alvo_txt is None) or (alvo_txt in det_txt)
        bom = (not ok) and (not gastou) and (not caiu) and txt_ok
        rel.add(nome, OK if bom else FALHA,
                f"executor ok={ok}, funcionarios {staff_antes}->{staff_depois}, "
                f"caixa {ctx['caixa_antes']}K->{ctx['caixa_depois']}K"
                + (f", motivo{'' if txt_ok else ' NAO'} contem \"{alvo_txt}\""
                   if alvo_txt else ""),
                "recusa (ok=False), funcionarios e caixa intactos"
                + (f", motivo contendo \"{alvo_txt}\"" if alvo_txt else ""),
                t.get("nota", ""))
        return

    # (b) R2: caixa medida em volta de TODA acao, na direcao certa por acao.
    d = ctx["caixa_depois"] - ctx["caixa_antes"]
    direcao = t["caixa"]
    caixa_ok = {"cai": d < 0, "sobe": d > 0, "parada": d == 0, "qualquer": True}[direcao]

    # (c) R4: prova = ler o estado DE VOLTA da tela.
    if t.get("verify"):
        vok, lido, esperado = t["verify"](ctx)
    else:
        vok, lido, esperado = ok, f"executor ok={ok}", "ok=True"

    status = OK if (ok and vok and caixa_ok) else FALHA
    extra = det
    if not caixa_ok:
        extra = f"CAIXA {d:+d}K contraria '{direcao}' | " + det
    if not ok:
        extra = "EXECUTOR RECUSOU | " + det
    rel.add(nome, status, lido, f"{esperado} (caixa {direcao})", extra)


def main():
    ap = argparse.ArgumentParser(description="Suite unica de testes do harness Aerobiz")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--vivo", action="store_true")
    ap.add_argument("--both", action="store_true")
    ap.add_argument("--only", default="", help="lista separada por virgula de testes vivos")
    a = ap.parse_args()
    if not (a.offline or a.vivo or a.both):
        ap.error("escolha --offline, --vivo ou --both")

    only = set(x.strip() for x in a.only.split(",") if x.strip()) or None
    rel = Rel()
    t0 = time.time()
    if a.offline or a.both:
        roda_offline(rel)
    if a.vivo or a.both:
        roda_vivo(rel, only)
    code = rel.tabela()
    print(f"tempo total: {time.time() - t0:.1f}s | exit={code}"
          " (0=tudo OK, 1=FALHA real, 2=so BLOQUEIO de infra)")
    return code


if __name__ == "__main__":
    sys.exit(main())
