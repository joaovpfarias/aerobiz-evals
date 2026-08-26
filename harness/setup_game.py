"""Configura uma partida do zero e grava o savestate inicial.

Config do eval (definida pelo usuario em 11/08/2026):
  cenario 4 = Supersonic Travel (2000-2020)
  nivel 5   = Supersonic (dificuldade maxima dos adversarios)
  jogadores : 1 (single) ou 4 (multi-LLM na mesma partida)

ETAPA 5-CidadeImplementar (24/08): a SEDE virou parametro de linha de comando.
Ela NAO e escolha do modelo — e o eixo do experimento, fixado pelo operador,
para que a diferenca de desempenho entre duas runs seja atribuivel a BASE e nao
a uma escolha que o modelo talvez nem soubesse fazer.

Mecanica MEDIDA (24/08, ETAPA 4-CidadeInvestigar + esta etapa):
  - tela de jogadores --(A)--> menu de regiao (4 atalhos) --(A)--> mapa da regiao
  - o menu de atalhos so nomeia 4 regioes, mas DENTRO do mapa `R` rola para a
    regiao seguinte; a regiao exibida e conferida por `world.detect_region`
    (assinatura de pixels de terra), que vale nesta tela: A_mapa.png da
    ETAPA 4 mede land=2073 => regiao 2 (Europe), o valor do catalogo.
  - o mapa da escolha de sede usa AS MESMAS coordenadas de `world.WORLD_CITIES`:
    os 24 pontos detectados em A_mapa.png batem 24/24 com as coordenadas da
    Europa. Por isso a sede e enderecada por ID (EU10, NA13, ...) e nao por
    pixel na mao.
  - hover: o nome so acende na caixa de texto quando o CENTRO do cursor cai na
    faixa (x+4..+8, y+4..+8) do ponto da cidade. `A` fora de cidade e inerte.
    O nome e LIDO (atlas 8x13), nao adivinhado, e a tela de apresentacao
    confirma a sede uma segunda vez (linha `MAN` do roster).
  - `A` sobre cidade -> "Is <X> OK?" YES/NO -> YES -> telas de apresentacao.

Uso:
  # rapido (parte da tela de jogadores ja salva; cenario/nivel sao os do state)
  python setup_game.py --city EU10
  python setup_game.py --city NA13

  # do zero (exige EmuHawk recem-aberto, na tela de titulo)
  python setup_game.py --city EU10 --boot --dificuldade 5 --ano 2000

Saida: states/eval_<cidade>_<ano>_lv<N>.state + .json (metadados MEDIDOS).
"""

import argparse
import hashlib
import re
import json
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import locate  # noqa: E402
import screen_text as _st  # noqa: E402
import world  # noqa: E402
from bridge import BizHawkBridge  # noqa: E402
from macros import Game  # noqa: E402

SCENARIO_INDEX = 3   # 0-based: 4o cenario = 2000-2020
SKILL_INDEX = 4      # 0-based: 5o nivel = Supersonic (maximo)
ROOT = pathlib.Path(__file__).parent.parent
SHOTS = ROOT / "logs" / "setup"
STATES = ROOT / "states"
PLAYERS_STATE = STATES / "eval_players_screen.state"

# ANO -> indice do cenario. So o 4o cenario foi percorrido e conferido; qualquer
# outro ano seria um indice CHUTADO, entao a lista recusa em vez de adivinhar.
ANO_SCENARIO = {2000: 3}

# Rotulo do menu de atalhos de regiao (hash do recorte, medido 24/08).
LABEL_BOX = (30, 126, 120, 144)
LABELS = {"e1f5ac0fe0": "Europe", "6cc4526e02": "MidEast", "14416469ee": "SEAsia",
          "53f810e1a1": "NAmerica", "2afffee160": "none"}
# id de regiao (world.REGION_NAMES) -> rotulo do atalho. As regioes ausentes
# (1 S America, 3 Africa, 6 Oceania) nao tem atalho: entra-se por qualquer uma
# e rola-se com `R` conferindo por pixels.
REGION_LABEL = {0: "NAmerica", 2: "Europe", 4: "MidEast", 5: "SEAsia"}

NAME_BOX = (20, 150, 150, 168)   # interior da caixa de texto (MEDIDO 24/08)
# Offset centro-do-cursor menos ponto-da-cidade que ACENDE o nome. MEDIDO por
# varredura (`_probe_hover_off.py`, EU10/Berlin, 24/08): a faixa que acende e
# dx=+4..+8, dy=+4..+8; fora dela a caixa fica vazia e `A` e inerte. O (4,11)
# que a ETAPA 4 anotou NAO acende — o braco que "funcionou" chegou na cidade
# pela varredura fina, nao pelo offset.
HOVER_OFF = (4, 4)
HOVER_SCAN = [(0, 0), (2, 0), (0, 2), (2, 2), (4, 0), (0, 4), (4, 2), (2, 4), (4, 4),
              (-2, 0), (0, -2), (-2, -2)]
# O nome da cidade sai da caixa de texto pelo MESMO atlas 8x13 das tabelas
# (MEDIDO: 'Amsterdam', '?Washington', '?erlin' — o '?' e o icone de bandeira
# ou glifo fora do atlas, que por R1 fica '?' e nao vira palpite).
NAME_ROW, NAME_X0, NAME_X1 = 152, 32, 150


def shot(b, name):
    SHOTS.mkdir(parents=True, exist_ok=True)
    return b.screenshot(SHOTS / f"{name}.png")


def boot(b):
    """Do reset ate a tela de titulo."""
    b.batch(b.seq_advance(600) + b.seq_press("Start", hold=5, wait=30) + b.seq_advance(600),
            extra_frames=1400)
    b.batch(b.seq_press("Start", hold=5, wait=30) + b.seq_advance(200), extra_frames=300)
    return shot(b, "01_title")


def choose_scenario(b, idx=SCENARIO_INDEX):
    seq = (b.seq_press("A", hold=5, wait=30) + b.seq_advance(150)          # NEW GAME
           + b.seq_press("Down", hold=3, wait=12, times=idx)
           + b.seq_advance(60))
    b.batch(seq, extra_frames=400)
    p = shot(b, "02_scenario")
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(200), extra_frames=300)  # seleciona
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(200), extra_frames=300)  # confirma resumo
    return p


def choose_skill(b, idx=SKILL_INDEX):
    b.batch(b.seq_press("Down", hold=3, wait=12, times=idx) + b.seq_advance(60),
            extra_frames=300)
    p = shot(b, "03_skill")
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(200), extra_frames=300)
    return p


def choose_players(b, n):
    # A tela abre em 1 jogador; descer (n-1) vezes seleciona n jogadores.
    b.batch(b.seq_press("Down", hold=3, wait=12, times=n - 1) + b.seq_advance(60), extra_frames=300)
    p = shot(b, "04_players")
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(250), extra_frames=350)
    return p


# ---------------------------------------------------------------- sede (cidade)

def _crop_hash(path, box):
    return hashlib.md5(Image.open(path).convert("RGB").crop(box).tobytes()).hexdigest()[:10]


def _label_of(path):
    return LABELS.get(_crop_hash(path, LABEL_BOX), "?" + _crop_hash(path, LABEL_BOX))


def _name_ink(path):
    """Pixels claros na caixa do nome: >0 = a seta esta sobre uma cidade."""
    im = Image.open(path).convert("RGB").crop(NAME_BOX)
    return sum(1 for px in im.getdata() if sum(px) > 500)


def _detect(b, tag):
    p = shot(b, tag)
    img = Image.open(p).convert("RGB")
    return p, world.detect_region(img), world.land_pixels(img)


def enter_region_map(b, reg, tag="05"):
    """Da tela de jogadores ate o mapa da regiao `reg`, CONFERIDO por pixels.

    Devolve (caminho_do_shot, regiao_lida). Levanta se nao chegou.
    """
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(300), extra_frames=450)
    alvo_label = REGION_LABEL.get(reg)
    if alvo_label:
        lab = None
        for i in range(8):
            lab = _label_of(shot(b, f"{tag}_menu{i}"))
            print(f"  atalho#{i} rotulo={lab}", flush=True)
            if lab == alvo_label:
                break
            b.batch(b.seq_press("Right", hold=3, wait=25) + b.seq_advance(150), extra_frames=300)
        if lab != alvo_label:
            raise RuntimeError(f"menu de atalhos nao chegou em {alvo_label} (parou em {lab})")
    # entra no mapa (a partir do atalho corrente, qualquer que seja)
    b.batch(b.seq_press("A", hold=5, wait=30) + b.seq_advance(400), extra_frames=600)
    p, lida, land = _detect(b, f"{tag}_mapa0")
    print(f"  mapa: detect={lida} land={land}", flush=True)
    # rola com R ate a regiao pedida (cobre as 3 sem atalho)
    for k in range(8):
        if lida == reg:
            return p, lida
        b.batch(b.seq_press("R", hold=4, wait=25) + b.seq_advance(250), extra_frames=350)
        p, lida, land = _detect(b, f"{tag}_mapa{k + 1}")
        print(f"  R#{k}: detect={lida} land={land}", flush=True)
    raise RuntimeError(f"nao cheguei na regiao {reg} ({world.REGION_NAMES[reg]}); ultima leitura {lida}")


def aim_city(b, cid, tag="06"):
    """Poe o cursor sobre `cid` e PROVA o hover. Devolve dict da mira."""
    x, y, reg, nome = world.WORLD_CITIES[cid]
    alvo = (x + HOVER_OFF[0], y + HOVER_OFF[1])
    # 1o toque: apaga o texto "Choose a city..." (senao a tinta dele e falso
    # positivo do detector de nome). Down+Up = deslocamento liquido zero.
    b.press("Down", hold=1, wait=8)
    b.press("Up", hold=1, wait=8)
    b.advance(150)
    tentativas = []
    for dx, dy in HOVER_SCAN:
        pos = locate.goto(b, alvo[0] + dx, alvo[1] + dy, tol=1)
        p = shot(b, f"{tag}_hover")
        ink = _name_ink(p)
        tentativas.append({"offset": [dx, dy], "cursor": list(pos), "ink": ink})
        print(f"  mira {cid} alvo={(alvo[0] + dx, alvo[1] + dy)} cursor={pos} ink={ink}", flush=True)
        if ink > 0:
            lido = _st.read_text(Image.open(p).convert("RGB"), NAME_ROW, NAME_X0, NAME_X1)
            lido = (lido or "").strip()
            print(f"  nome LIDO da caixa: {lido!r}", flush=True)
            return {"city": cid, "city_px": [x, y], "region": reg, "region_nome": world.REGION_NAMES[reg],
                    "nome_catalogo": nome, "nome_lido_da_tela": lido,
                    "alvo": [alvo[0] + dx, alvo[1] + dy],
                    "cursor_verificado": list(pos), "desvio_px": [dx, dy],
                    "name_box_hash": _crop_hash(p, NAME_BOX), "name_ink": ink,
                    "shot": str(p), "tentativas": tentativas}
    raise RuntimeError(f"sem hover em {cid}: a caixa de nome ficou vazia em "
                       f"{len(HOVER_SCAN)} miras {tentativas}")


def read_roster(path):
    """Linhas OCR da tela de apresentacao das companhias.

    MEDIDO 24/08: a tela lista as 4 companhias (`MAN` = a nossa, `COM` = as do
    computador) com a CIDADE-SEDE de cada uma, e no canto direito o cenario e o
    nivel ("4", "Lv 5"). Serve de duas provas ao mesmo tempo: que a sede e a que
    pedimos, e que cenario/nivel sao os declarados.

    OBSERVADO: os adversarios MUDAM entre execucoes da mesma cidade (Air LA /
    Air Mex / UK Air numa passada; Air LA / UK Air / Sunrise na seguinte). Por
    isso adversario diferente NAO prova cidade diferente — R3.
    """
    im = Image.open(path).convert("RGB")
    linhas = []
    for y in range(8, 88, 8):
        t = _st.read_text(im, y, 8, 248)
        if t and t.replace("?", "").strip():
            linhas.append(t.strip())
    return linhas


def read_roster_config(path):
    """Cenario e nivel LIDOS da coluna direita da tela de apresentacao.

    MEDIDO 24/08 nas duas cidades: a coluna x=190..250 traz "Scen" (y=24), o
    NUMERO do cenario (y=40) e "Lv N" (y=64). E a unica leitura de tela que
    confere a config da partida — sem ela `--from-state` poderia carimbar
    `lv5` num savestate que foi criado em outro nivel.
    Devolve (cenario, nivel), cada um int ou None quando ilegivel (R1).
    """
    im = Image.open(path).convert("RGB")
    col = {y: (_st.read_text(im, y, 190, 250) or "") for y in (24, 40, 64)}
    cen = re.search(r"(\d)", col[40])
    lv = re.search(r"Lv\s*(\d)", col[64])
    return (int(cen.group(1)) if cen else None,
            int(lv.group(1)) if lv else None), col


class CaixaCaiu(RuntimeError):
    """Uma tela da apresentacao cobrou dinheiro. Guarda como reconhece-la."""

    def __init__(self, msg, passo, chave, shot):
        super().__init__(msg)
        self.passo = passo
        self.chave = chave
        self.shot = shot


# Faixa do texto do pedido ("$132000K is requested.") — identidade da tela cara.
COSTLY_BAND = (24, 120, 232, 148)


def _costly_key(img):
    import hashlib as _h
    return _h.md5(img.crop(COSTLY_BAND).tobytes()).hexdigest()[:10]


def commit_city(b, mira, tag="07", recusar=(), config_esperada=None):
    """Confirma a sede (A -> YES) e atravessa a apresentacao medindo o caixa.

    `recusar`: chaves de tela (ou indices de passo) em que a resposta e NO.
    """
    b.press("A", hold=6, wait=40)
    b.advance(400)
    p_perg = shot(b, f"{tag}_pergunta")
    b.press("A", hold=6, wait=40)         # YES e o default
    b.advance(600)
    caixas = []
    p_roster = shot(b, f"{tag}_roster")
    roster = read_roster(p_roster)
    print("  roster LIDO:", roster, flush=True)
    # GATE DE IDENTIDADE (R4): a linha da NOSSA companhia (a marcada MAN) tem de
    # nomear a cidade que a caixa de hover nomeou. Sem isto, mirar o vizinho por
    # 2px produziria um savestate perfeitamente crivel da cidade errada.
    alvo_nome = (mira.get("nome_lido_da_tela") or "").lstrip("?").strip()
    linha_nossa = next((l for l in roster if "MAN" in l or "MA?" in l), None)
    if not alvo_nome or not linha_nossa or alvo_nome not in linha_nossa:
        raise RuntimeError(
            f"a sede confirmada NAO confere com a mirada: hover={alvo_nome!r} "
            f"linha_MAN={linha_nossa!r} roster={roster} tela={p_roster}")
    (cen_lido, lv_lido), col = read_roster_config(p_roster)
    print(f"  config LIDA da tela: cenario={cen_lido} nivel={lv_lido} (bruto {col})", flush=True)
    if config_esperada:
        if (cen_lido, lv_lido) != tuple(config_esperada):
            raise RuntimeError(
                f"CONFIG NAO CONFERE: a tela diz cenario={cen_lido} nivel={lv_lido}, "
                f"o rotulo do savestate diria {tuple(config_esperada)}; tela={p_roster}")
    caixas.append(world.read_cash_k(b))
    # A apresentacao (roster + falas do conselheiro) tem um numero VARIAVEL de
    # telas; ela termina no MENU PRINCIPAL. Apertar um numero fixo de A (5, como
    # a ETAPA 4 fazia) parava no meio das falas e a medicao seguinte lia a tela
    # errada — por isso o criterio de parada e a assinatura do menu, lida da tela.
    no_menu = False
    eventos = []
    for i in range(30):
        p = shot(b, f"{tag}_pos{i}")
        img = Image.open(p).convert("RGB")
        if world.at_main_menu_img(img):
            no_menu = True
            break
        # PERGUNTA COM DINHEIRO EM JOGO (R2). MEDIDO 24/08 em NA13: a cadeia de
        # apresentacao pode trazer um evento ("Rep. of Tunisia ... $132000K is
        # requested"). O `A` cego aceitou e o caixa caiu 1.220.000 -> 1.088.000.
        #
        # Responder NO a TODA pergunta YES/NO tambem esta errado, e foi MEDIDO:
        # a apresentacao tem perguntas estruturais ("Customize each company's
        # name and color?", e a confirmacao seguinte) e o NO nelas DESFEZ a
        # partida inteira — o fluxo voltou para a tela de escolha de cenario
        # (logs/setup/07_pos3.png). Por isso o NO e CIRURGICO: so nas telas que
        # esta ferramenta ja viu custar dinheiro, identificadas pelo recorte do
        # texto do pedido (`_costly_key`) OU pelo indice do passo. A primeira
        # passada descobre; a segunda recusa.
        chave = _costly_key(img)
        sel = world.yesno_prompt(img)
        if sel and (chave in recusar or i in recusar):
            for btn in ("Right", "Down", "Right"):
                if sel == "NO":
                    break
                b.press(btn, hold=4, wait=20)
                b.advance(120)
                img = Image.open(shot(b, f"{tag}_pos{i}_no")).convert("RGB")
                sel = world.yesno_prompt(img)
            if sel != "NO":
                raise RuntimeError(f"pergunta YES/NO com dinheiro em jogo e nao consegui "
                                   f"selecionar NO (selecionado={sel}); tela={p}")
            eventos.append({"passo": i, "resposta": "NO", "chave": chave, "shot": str(p)})
        antes = world.read_cash_k(b)
        b.press("A", hold=6, wait=40)
        b.advance(500)
        depois = world.read_cash_k(b)
        caixas.append(depois)
        if antes and depois and depois < antes:
            raise CaixaCaiu(f"CAIXA CAIU no passo {i} da apresentacao (R2): "
                            f"{antes} -> {depois}; tela={p}", i, chave, str(p))
    print(f"  caixa na apresentacao: {caixas} chegou_ao_menu={no_menu}", flush=True)
    if not no_menu:
        raise RuntimeError("a apresentacao nao terminou no menu principal em 30 toques")
    validos = [c for c in caixas if c]
    if validos and min(validos) < max(validos):
        raise RuntimeError(f"CAIXA CAIU durante a apresentacao (R2): {caixas}")
    return {"pergunta_shot": str(p_perg), "roster_shot": str(p_roster),
            "roster_ocr": roster, "cenario_lido": cen_lido, "nivel_lido": lv_lido,
            "coluna_config_bruta": col, "caixa_apresentacao": caixas,
            "chegou_ao_menu": no_menu, "eventos_recusados": eventos}


def measure(b, tag="08"):
    """Le de VOLTA do jogo o que identifica este mundo (R4)."""
    g = Game(b, shot_dir=SHOTS)
    shots = {}
    for item in ("map", "fleet"):
        shots[item] = g.info_screen(item, f"{tag}_info_{item}")
    g.back_to_menu()
    img_map = Image.open(shots["map"]).convert("RGB")
    img_fleet = Image.open(shots["fleet"]).convert("RGB")
    rotas, n_rte = world.read_routes(img_map)
    return {
        "our_company_map": world.read_our_company(img_map),
        "our_company_fleet": world.read_our_company(img_fleet),
        "footer_cash_k_map": world.read_footer_cash_k(img_map),
        "cash_k_ram": world.read_cash_k(b),
        "frota": world.read_fleet(img_fleet),
        "rotas": rotas, "n_rotas": n_rte,
        "shots": {k: str(v) for k, v in shots.items()},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", help="ID da sede (ex.: EU10, NA13). Sem ele para na tela de jogadores.")
    ap.add_argument("--dificuldade", type=int, default=5, choices=[1, 2, 3, 4, 5])
    ap.add_argument("--ano", type=int, default=2000)
    ap.add_argument("--players", type=int, default=1)
    ap.add_argument("--boot", action="store_true",
                    help="percorre os menus do zero (exige EmuHawk na tela de titulo)")
    ap.add_argument("--from-state", default=str(PLAYERS_STATE),
                    help="savestate da tela de jogadores (usado quando nao ha --boot)")
    ap.add_argument("--out", help="caminho do savestate (default: states/eval_<city>_<ano>_lv<N>.state)")
    ap.add_argument("--step", choices=["boot", "scenario", "skill", "players", "regiao", "mira"],
                    help="parar apos")
    a = ap.parse_args()
    if a.ano not in ANO_SCENARIO:
        print(f"ABORT: ano {a.ano} nao tem indice de cenario MEDIDO; conhecidos: "
              f"{sorted(ANO_SCENARIO)}. Nao vou chutar posicao de menu.")
        return 2
    if a.city and a.city not in world.WORLD_CITIES:
        print(f"ABORT: cidade {a.city} nao esta no catalogo world.WORLD_CITIES")
        return 2

    global SHOTS
    if a.city:
        SHOTS = SHOTS / a.city          # artefatos por braco, sem sobrescrever
    b = BizHawkBridge()
    b.speed(400)
    proveniencia = {}

    if a.boot:
        print(boot(b), flush=True)
        if a.step == "boot":
            return 0
        print(choose_scenario(b, ANO_SCENARIO[a.ano]), flush=True)
        if a.step == "scenario":
            return 0
        print(choose_skill(b, a.dificuldade - 1), flush=True)
        if a.step == "skill":
            return 0
        print(choose_players(b, a.players), flush=True)
        proveniencia = {"origem": "boot completo", "cenario_index": ANO_SCENARIO[a.ano],
                        "skill_index": a.dificuldade - 1, "players": a.players,
                        "config_conferida_na_tela": "na tela de apresentacao (ver confirmacao.cenario_lido/nivel_lido)"}
    else:
        # O state da tela de jogadores foi gravado com cenario 2000-2020 / nivel 5
        # / 1 jogador. Isso e DECLARADO (veio do --step players desta ferramenta),
        # nao lido da tela — por isso qualquer pedido diferente e recusado em vez
        # de gravar um savestate rotulado com uma config que nao configuramos.
        if (a.ano, a.dificuldade, a.players) != (2000, 5, 1):
            print("ABORT: sem --boot a partida vem de "
                  f"{a.from_state} (2000 / lv5 / 1 jogador). Pedido: "
                  f"{a.ano} / lv{a.dificuldade} / {a.players} jogador(es). Use --boot.")
            return 2
        b.load(a.from_state)
        b.advance(60)
        proveniencia = {"origem": pathlib.Path(a.from_state).name,
                        "cenario_ano": a.ano, "dificuldade": a.dificuldade,
                        "players": a.players,
                        "config_conferida_na_tela": "cenario e nivel sao CONFERIDOS na tela de "
                                                    "apresentacao; numero de jogadores nao e lido",
                        "nota": "cenario/nivel/jogadores sao os gravados no state; declarados, nao lidos"}
    if a.step == "players" or not a.city:
        p = shot(b, "05_after_players")
        print(f"parei na tela de jogadores: {p}")
        return 0

    # Ponto de retorno para o replay: a tela de jogadores, exatamente como esta
    # agora. Sem ele uma tela cara descoberta no meio da apresentacao so poderia
    # ser evitada relancando o emulador.
    volta = str((STATES / "_setup_players_tmp.state").resolve())
    b.save(volta)

    reg = world.WORLD_CITIES[a.city][2]
    recusar = set()
    conf = mira = None
    for tentativa in range(3):
        if tentativa:
            b.load(volta)
            b.advance(60)
        p_map, lida = enter_region_map(b, reg)
        print(f"regiao no mapa: {lida} ({world.REGION_NAMES[lida]}) {p_map}", flush=True)
        if a.step == "regiao":
            return 0
        mira = aim_city(b, a.city)
        print("mira OK:", json.dumps(mira["cursor_verificado"]),
              "hash_nome", mira["name_box_hash"], flush=True)
        if a.step == "mira":
            return 0
        try:
            conf = commit_city(b, mira, recusar=recusar,
                               config_esperada=(ANO_SCENARIO[a.ano] + 1, a.dificuldade))
            break
        except CaixaCaiu as e:
            # R2: o dinheiro ja saiu nesta passada, entao ESTA passada esta
            # queimada — volta ao ponto de retorno e refaz recusando a tela.
            print(f"[tentativa {tentativa}] {e} -> vou repetir recusando "
                  f"(chave={e.chave}, passo={e.passo})", flush=True)
            recusar |= {e.chave, e.passo}
    if conf is None:
        print("ABORT: nao consegui atravessar a apresentacao sem perder caixa em 3 tentativas")
        return 1
    out = a.out or str(STATES / f"eval_{a.city}_{a.ano}_lv{a.dificuldade}.state")
    b.save(str(pathlib.Path(out).resolve()))
    med = measure(b)
    meta = {"city": a.city, "ano": a.ano, "dificuldade": a.dificuldade, "players": a.players,
            "state": str(pathlib.Path(out).resolve()), "proveniencia": proveniencia,
            "mira": mira, "confirmacao": conf, "medido_do_jogo": med,
            "telas_recusadas": sorted(str(x) for x in recusar)}
    meta_path = pathlib.Path(out).with_suffix(".json")
    meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(json.dumps(med, indent=1), flush=True)
    print("state:", out)
    print("meta:", meta_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
