"""Catalogo do mundo do jogo + leitura de estado.

Nomes de cidade nao aparecem no mapa (so ao selecionar), entao o agente trabalha
com IDs estaveis ancorados nas coordenadas dos pontos. Os nomes confirmados no
jogo vao sendo preenchidos conforme visitamos as telas de detalhe.

Enderecos de RAM (SNES WRAM, achados com ramfind.py e validados em 3 savestates):
  0x25F9  caixa em unidades de $10K  (valor*10 = K exibido na tela)
"""

import os
import pathlib

from locate import BLUE, GREEN, find_dots

CASH_ADDR = 0x25F9

# Cursor LOGICO do mapa (o que o jogo consulta para saber a cidade sob o cursor).
# 0x0900/0x0901 tambem seguem o cursor, mas sao apenas a copia de RENDERIZACAO do
# sprite: escrever la move o desenho e nao muda a selecao.
CURSOR_X, CURSOR_Y = 0x257F, 0x2581

# MEDIDO 12/08 no savestate do eval (probe_cursor.py sprite/select/write):
#  - o sprite (13x13) e desenhado com o canto SUPERIOR ESQUERDO exatamente no
#    valor da RAM: RAM(100,100) -> bbox do diff comecou em (100,100);
#  - 1 toque de d-pad = 2px, entao a paridade do valor NUNCA muda por input.
#    O offset antigo (-3,-3) levava a um alvo IMPAR (209,71) — inalcancavel por
#    toque a partir de (128,128). Era a razao de "escrever move mas nao seleciona".
#  - sweep de A por posicao: seleciona com RAM_X em {210,212} e RAM_Y em {71..74}
#    para a cidade em (212,74); falha em X<=208 e em Y=69.
# Logo o alvo correto e a PROPRIA coordenada da cidade.
CURSOR_OFFSET = (0, 0)

# Identificador de tela: 7 no menu principal, 0 nas demais. Substitui o
# reconhecimento do menu por screenshot.
SCREEN_ADDR, SCREEN_MAIN_MENU = 0x0106, 7

DOT_MIN_PX = 20  # pontos de cidade ~28px; os digitos de slot ao lado tem ~8-11px

# Catalogo da America do Norte: id -> (x, y, nome confirmado no jogo ou None).
# Coordenadas medidas no mapa da regiao (256x224).
NA_CITIES = {
    "NA01": (18, 26, None),
    "NA02": (22, 36, "Seattle"),  # confirmado na tabela de rotas (12/08)
    "NA03": (16, 66, "San Francisco"),  # confirmado na tabela de rotas (12/08)
    "NA04": (32, 86, None),
    "NA05": (62, 94, "Phoenix"),  # confirmado na tabela de rotas (12/08)
    "NA06": (90, 72, "Denver"),
    "NA07": (132, 98, None),
    "NA08": (142, 116, None),
    "NA09": (158, 62, None),
    "NA10": (180, 98, "Atlanta"),  # confirmado pela recusa do jogo (12/08)
    "NA11": (192, 132, None),
    "NA12": (194, 54, None),
    "NA13": (204, 84, "Washington"),
    "NA14": (212, 74, "Philadelphia"),   # confirmado pela recusa do jogo (12/08)
    "NA15": (220, 68, None),
    "NA16": (18, 134, None),
}

# Slots iniciais confirmados na tela (numeros ao lado dos pontos no mapa) — F0, cenario 2/1970
START_SLOTS = {"NA13": 27, "NA06": 11, "NA02": 7, "NA03": 7, "NA05": 1, "NA14": 1}

# Savestate do eval (cenario 4 / 2000, nivel 5) — MEDIDO 12/08 pelos digitos do
# mapa (probe_cursor.py slots) e batido com a recusa do jogo em NA10/NA14.
# NAO ha slots em Philadelphia nem em Atlanta neste cenario: o jogo responde
# "We don't have any slots in <cidade>" e a rota NUNCA abre. Essa era a causa
# raiz das rotas "sem efeito", independente do cursor.
EVAL_SLOTS_2000 = {"NA13": 34, "NA06": 12, "NA02": 11, "NA03": 9, "NA05": 2}

# Escala do mapa: o jogo mostrou "1500 MI" para Washington(204,84)->Denver(90,72),
# que distam ~114.6 px. Logo ~13.1 milhas por pixel. E estimativa, nao valor lido.
MILES_PER_PX = 1500 / 114.6

# Frota inicial do cenario 2 / 1970 (F0), lida na tela de selecao de aviao.
FLEET_1970 = [
    {"model": "DC9-30", "count": 4, "range_mi": 1500, "seats": 120, "aircraft_index": 0},
    {"model": "B707-320", "count": 2, "range_mi": 5560, "seats": 160, "aircraft_index": 1},
]

# FROTA DO SAVESTATE DO EVAL (cenario 4 / 2000, nivel 5) — MEDIDA 15/08:
#  - Info->fleet (logs/prova_ic/frota_2000.png): "MD100 | In Use 0 | Avail 6 | Order 0";
#    ha UM UNICO modelo, nao os dois de 1970.
#  - tela de selecao de aviao (logs/prova_ic/fleet_NA06_00.png): MD100, 4680 mi,
#    200 assentos, 6 disponiveis.
# Usar FLEET_1970 aqui foi um erro real: o prompt do piloto anunciava um
# B707-320 de 5560 mi que a companhia NAO tem, e mandava o modelo comparar
# alcance com uma constante inventada.
FLEET_EVAL_2000 = [
    # sem "aircraft_index": nao ha escolha de aeronave (ver CALIBRATION §7)
    {"model": "MD100", "count": 6, "range_mi": 4680, "seats": 200},
]
FLEET_START = FLEET_EVAL_2000

# Distancias REAIS lidas no cabecalho da tela de aviao ("Washington <| N MI |> X").
# E a unica fonte exata: a estimativa por pixel erra ~40% e nao atravessa
# continentes (cada regiao tem projecao propria).
MEASURED_DIST_FROM_HOME = {"NA06": 1500, "NA14": 120, "SA01": 1180}

HOME = "NA13"


def distance_mi(a, b):
    """Distancia estimada entre dois IDs, a partir dos pixels do mapa."""
    ax, ay, _ = NA_CITIES[a]
    bx, by, _ = NA_CITIES[b]
    return round((((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5) * MILES_PER_PX)


def read_cash_k(bridge):
    """Caixa em $K, como aparece na tela."""
    raw = bridge.read_ram(CASH_ADDR, 4)
    return (int.from_bytes(raw, "little") & 0xFFFFFF) * 10


def at_main_menu(bridge):
    return bridge.read_ram(SCREEN_ADDR, 1)[0] == SCREEN_MAIN_MENU


# --- RELOGIO DO JOGO: trimestre absoluto -------------------------------------
# ACHADO 17/08 (ramdiff sobre 3 viradas medidas: JUL2000 -> OCT2000 -> JAN2001).
# 0x259F e um contador de 16 bits little-endian de TRIMESTRES DESDE JAN/1955
# (a epoca e o cenario mais antigo do jogo). E a UNICA leitura confiavel de
# "o turno passou": +1 exatamente por trimestre, sem depender de o caixa variar.
#
# Por que substituiu o detector antigo: `end_turn` usava "o caixa mudou", que
# NAO muda em todo trimestre. MEDIDO no enunciado desta etapa: 4 chamadas,
# caixa 1218240 -> 1218240 -> 1216420 -> 1216420 — metade das chamadas parecia
# nao ter avancado (e o retry cego podia passar turnos a mais sem ninguem ver).
#
# EVIDENCIA (5 pontos independentes + prova de escrita):
#   1. savestate eval_single_2000_lv5 -> 181 e a barra do menu diz "APR. 2000"
#      (1955 + 181//4 = 2000; 181%4 = 1 = APR)         logs/etapa1/menu_inicial.png
#   2. savestate probe_hub_open_sa    -> 186 e a barra diz "JUL. 2001"
#                                        logs/etapa1/epoch_probe_hub_open_sa.png
#   3. tres viradas ao vivo: 182/183/184 <-> JUL.2000 / OCT.2000 / JAN.2001
#                                        logs/etapa1/date_oct2000.png, date_jan2001.png
#   4. ESCREVER o contador muda a data na tela (write X -> tela mostra X), em 12
#      valores: n=192 -> JAN.2003 ... n=241 -> APR.2015    logs/etapa1/wr_*.png
#   5. n=256/260/263 -> JAN.2019 / JAN.2020 / OCT.2020 confirmam que 0x25A0 e
#      mesmo o byte ALTO — sem isso o contador estouraria em 2018 Q4 (255) e o
#      eval 2000-2020 (que chega a 263) leria a data errada no fim da partida.
QUARTER_ADDR = 0x259F
QUARTER_EPOCH_YEAR = 1955  # trimestre 0 = JAN/1955
QUARTER_NAMES = ("JAN", "APR", "JUL", "OCT")


def quarter_to_date(n):
    """Contador absoluto -> (ano, trimestre 1..4)."""
    return QUARTER_EPOCH_YEAR + n // 4, (n % 4) + 1


def date_to_quarter(year, quarter):
    """(ano, trimestre 1..4) -> contador absoluto."""
    return (year - QUARTER_EPOCH_YEAR) * 4 + (quarter - 1)


def read_quarter_index(bridge):
    """Trimestre absoluto lido da RAM. +1 a cada virada de turno."""
    return int.from_bytes(bridge.read_ram(QUARTER_ADDR, 2), "little")


def read_date(bridge):
    """(ano, trimestre 1..4) lidos da RAM."""
    return quarter_to_date(read_quarter_index(bridge))


def date_label(n):
    """Rotulo igual ao da barra do menu: 'JUL. 2001'."""
    year, q = quarter_to_date(n)
    return f"{QUARTER_NAMES[q - 1]}. {year}"


# --- a MESMA data lida dos PIXELS, para conferir a RAM ------------------------
# A barra do menu principal escreve "MES.AAAA" em 8 celulas de 8px comecando em
# x=8, linha y=167..173 (medido pelo bounding box dos pixels de texto puro
# (255,251,255) em 5 capturas). A celula 3 e sempre o ponto, a 4-7 sao o ano.
# Os hashes de digito 3..9 vieram da prova de escrita (item 4 acima): sao os
# mesmos glifos que o jogo desenha, so que alcancados sem jogar 60 turnos.
DATE_CELL_Y = (167, 174)
DATE_CELL_X0 = 8
DATE_CELL_W = 8
DATE_DIGITS = {
    "d1c22dc1": "0", "14ec3d73": "1", "06ec893e": "2", "f6a5a81e": "3",
    "e1ef0a1c": "4", "0a256794": "5", "53894d20": "6", "b36e38a2": "7",
    "26c6bda5": "8", "f18e18e0": "9",
}
DATE_MONTHS = {
    ("2fe56ff5", "b6b1cf73", "2c1c835d"): 1,  # JAN
    ("b6b1cf73", "19eb03e9", "26c572aa"): 2,  # APR
    ("2fe56ff5", "09f81a13", "4c009ac6"): 3,  # JUL
    ("a9d9d2e6", "525bc714", "98bcea9c"): 4,  # OCT
}


def date_cell_hashes(img):
    """Os 8 hashes de glifo da barra de data (util para catalogar um glifo novo)."""
    y0, y1 = DATE_CELL_Y
    return [
        _bin_md5(img, (DATE_CELL_X0 + DATE_CELL_W * i, y0,
                       DATE_CELL_X0 + DATE_CELL_W * i + 7, y1))
        for i in range(8)
    ]


def read_date_px(img):
    """(ano, trimestre) lidos da BARRA DO MENU, ou None.

    Sinal INDEPENDENTE da RAM: e ele que prova que 0x259F e mesmo a data, e nao
    um contador qualquer que por acaso anda junto. Devolve None (nunca um
    palpite) se algum glifo nao estiver catalogado ou se a tela nao for o menu.
    """
    cells = date_cell_hashes(img)
    q = DATE_MONTHS.get(tuple(cells[:3]))
    if q is None:
        return None
    digitos = [DATE_DIGITS.get(c) for c in cells[4:8]]
    if any(d is None for d in digitos):
        return None
    return int("".join(digitos)), q


# Recorte da caixa de texto: so a pergunta/mensagem, sem as setinhas dos sliders
# nem o retrato do funcionario — ambos ANIMADOS, o que envenena qualquer hash.
TEXTBOX = (62, 152, 232, 188)


def text_hash(bridge):
    import hashlib

    from PIL import Image

    img = Image.open(bridge.screenshot()).convert("RGB").crop(TEXTBOX)
    return hashlib.md5(img.tobytes()).digest()


def wait_text(bridge, max_polls=10, settle=40):
    """Espera a datilografia terminar: duas leituras iguais seguidas.

    Espera fixa NAO serve. Medido ao vivo: 220 frames depois de abrir o comando
    de nova rota, a mensagem ainda estava em "The new route will depart from W".
    Como o jogo IGNORA input enquanto digita, o A de reconhecimento se perdia e
    a acao seguinte a uma rota aberta falhava de forma intermitente.
    """
    prev = text_hash(bridge)
    for _ in range(max_polls):
        bridge.advance(settle)
        cur = text_hash(bridge)
        if cur == prev:
            return cur
        prev = cur
    return prev


def read_cursor(bridge):
    """Posicao logica do cursor do mapa (x, y)."""
    r = bridge.read_ram(CURSOR_X, 3)
    return r[0], r[2]


def _tap(bridge, button="Right"):
    bridge.batch(bridge.seq_press(button, hold=1, wait=6) + bridge.seq_advance(15), extra_frames=60)


def activate_cursor(bridge, rounds=4):
    """Garante que o cursor do mapa esta VIVO — ou seja, que responde ao d-pad.

    Descoberto em 12/08 (probe_cursor.py taps): ao entrar na tela de mapa o
    cursor fica parado em (128,128) e NENHUM toque o move enquanto a mensagem
    ("The new route will depart from Washington...") nao for reconhecida com A.
    Depois do A, o PRIMEIRO toque ainda e engolido pela transicao — so o segundo
    mexe na RAM.

    O teste e adaptativo (so aperta A quando o toque NAO moveu a RAM) porque nem
    toda tela de mapa tem mensagem a reconhecer, e um A a toa numa tela ja ativa
    selecionaria a cidade sob o cursor. Tentamos as duas direcoes antes de
    concluir que esta travado: se o cursor estiver encostado numa borda, um dos
    lados nao anda.

    Atencao: depois de uma rota aberta o cursor NAO volta para (128,128) — fica
    na ultima cidade selecionada. Por isso a deteccao compara com a posicao lida
    na hora, nunca com um valor fixo.
    """
    wait_text(bridge)  # a datilografia ignora input; sem isso o A se perde
    before = read_cursor(bridge)
    for _ in range(rounds):
        for direction in ("Right", "Left"):
            _tap(bridge, direction)
            if read_cursor(bridge) != before:
                return True
        bridge.batch(
            bridge.seq_press("A", hold=5, wait=25) + bridge.seq_advance(60), extra_frames=150
        )
        wait_text(bridge)
    return False


def point_cursor_at(bridge, cid):
    """Posiciona o cursor do mapa sobre uma cidade e devolve a posicao efetiva.

    Escrever a posicao na RAM e EXATO e sem drift — ao contrario de andar por
    toques, que erra +-1px porque o passo e de 2px e a malha fechada nao fecha
    em delta impar. Mas so funciona com o cursor ATIVO (ver activate_cursor):
    o teste antigo que "provou" que escrever nao seleciona dava um unico toque,
    justamente o que a transicao engole, e ainda mirava um alvo impar.
    """
    x, y = city_xy(cid)
    if not activate_cursor(bridge):
        raise RuntimeError("cursor do mapa nao respondeu ao d-pad — tela errada?")
    bridge.batch(
        bridge.seq_write(CURSOR_X, max(0, x + CURSOR_OFFSET[0]))
        + bridge.seq_write(CURSOR_Y, max(0, y + CURSOR_OFFSET[1]))
        + bridge.seq_advance(15)
    )
    return read_cursor(bridge)


def land_pixels(img, step=3):
    """Amostra de pixels de TERRA (verde) na faixa do mapa."""
    px = img.load()
    return sum(
        1
        for y in range(0, 140, step)
        for x in range(0, 256, step)
        if px[x, y][1] > px[x, y][0] + 30 and px[x, y][1] > px[x, y][2] + 10
    )


def menu_red(img):
    """Pixels vermelhos da caixa do nome da companhia, no rodape do menu."""
    px = img.load()
    return sum(
        1
        for y in range(183, 200)
        for x in range(4, 71)
        if px[x, y][0] > 150 and px[x, y][1] < 90 and px[x, y][2] < 90
    )


def at_main_menu_img(img, min_red=40):
    """True se estamos no MENU PRINCIPAL (o hub do turno).

    Assinatura: a caixa vermelha com o nome da companhia ("Federal") no rodape.
    MEDIDO: 108 pixels no menu, 0 no mapa de rota, na tela de recusa, na tela de
    aviao e na lista de rotas. O byte 0x0106 nao serve (varia entre turnos) e
    apertar B as cegas nao garante o retorno — era assim que uma acao quebrada
    contaminava a seguinte.

    CORRIGIDO 15/08 — o teste de vermelho SOZINHO da FALSO POSITIVO no fluxo
    de compra de aviao. A tela de showroom com o pedido montado ("Cost: 1 /
    $110000K") desenha a placa vermelha da companhia deslocada para a esquerda e
    marca **77 pixels** na mesma janela (>= 40). Consequencia medida ao vivo: o
    executor deu a compra por encerrada ainda DENTRO do showroom; a leitura
    seguinte de Info->fleet mandou "Left x6, Up x2, Down, Right x3" para o
    SELETOR DE FABRICANTE e reabriu a Airbus, e a captura da "frota depois"
    era a tela do showroom.
    Discriminador medido: o menu principal E o mapa da regiao, entao tem TERRA;
    o showroom nao tem nenhuma (land_pixels: 2266 no menu, 0 em 5 telas do
    fluxo de compra). O teste passa a ser vermelho E terra.
    """
    return menu_red(img) >= min_red and land_pixels(img) >= 200


# --- caixa de decisao (YES NO) --------------------------------------------
# MEDIDO 17/08 (ETAPA 1): a cadeia de fim de turno pode parar numa PERGUNTA com
# dinheiro em jogo — "Rep. of EC ... $372000K is requested. Will you back this
# Project? (YES NO)" (logs/etapa1/aceite_sa_t1.png). E a tela mais cara do jogo
# para se atravessar as cegas: um A ali entrega $372.000K, um terco do caixa.
#
# Assinatura medida no rodape: os dois rotulos tem FUNDO CHAPADO de cor pura —
# a opcao selecionada em vermelho (255,0,0) e a outra em azul (0,2,255).
# Na captura: YES ocupa x 65..88 (vermelho = selecionado), NO x 88..110 (azul).
YESNO_BAND = (0, 195, 256, 220)
YESNO_RED = (255, 0, 0)
YESNO_BLUE = (0, 2, 255)


def yesno_prompt(img, minimo=20):
    """Ha uma caixa (YES NO) no rodape? Devolve 'YES', 'NO' (o SELECIONADO) ou None.

    O selecionado e o que esta sobre o fundo VERMELHO; o outro fica no azul.
    Decide-se pela posicao horizontal media de cada cor: YES fica a esquerda de
    NO. Devolve None — nunca um palpite — se faltar uma das duas cores.
    """
    x0, y0, x1, y1 = YESNO_BAND
    px = img.load()
    vermelhos, azuis = [], []
    for y in range(y0, min(y1, img.size[1])):
        for x in range(x0, min(x1, img.size[0])):
            c = px[x, y]
            if c == YESNO_RED:
                vermelhos.append(x)
            elif c == YESNO_BLUE:
                azuis.append(x)
    if len(vermelhos) < minimo or len(azuis) < minimo:
        return None
    return "YES" if sum(vermelhos) / len(vermelhos) < sum(azuis) / len(azuis) else "NO"


def on_map_screen(img, min_land=200):
    """True se ainda estamos vendo o mapa da regiao.

    Usado para detectar a RECUSA do jogo: quando nao temos slots na cidade
    escolhida ele responde "We don't have any slots in X" e continua no mapa,
    em vez de abrir a tela de escolha de aviao.

    Contar "pontos de cidade" NAO serve: o aviao branco da tela de selecao cai
    na cor BLUE do detector e rendia 40 falsos positivos. A massa de terra verde
    separa as duas telas sem ambiguidade — MEDIDO: 2266 no mapa, 0 em todas as
    telas do fluxo de rota (logs/probe12).
    """
    return land_pixels(img) >= min_land


def detect_cities(img):
    """Pontos de cidade visiveis no mapa (filtra os digitos de slot pelo tamanho)."""
    dots = [d for d in find_dots(img, GREEN) + find_dots(img, BLUE) if d[2] >= DOT_MIN_PX]
    return sorted(dots, key=lambda d: (d[0], d[1]))


def cities_with_slots(img, cursor=None, region=0):
    """IDs das cidades onde POSSUIMOS slots, lido do mapa.

    O jogo desenha o numero de slots logo abaixo/ao lado do ponto da cidade.
    Esses digitos aparecem como blobs pequenos (8-11px) contra os 28px do ponto,
    entao a presenca de um blob pequeno perto de uma cidade = temos slots la.

    E o unico jeito verificavel de saber que uma NEGOCIACAO CONCLUIU: o harness
    so sabe o que disparou, nao o que o jogo concedeu.
    """
    small = [d for d in find_dots(img, GREEN) + find_dots(img, BLUE) if d[2] < DOT_MIN_PX]
    if cursor:  # o sprite do cursor tambem vira blob pequeno — excluir sua vizinhanca
        cx0, cy0 = cursor
        small = [d for d in small if abs(d[0] - cx0) > 10 or abs(d[1] - cy0) > 10]
    out = set()
    # So as cidades da regiao EXIBIDA: com o mapa em outro continente as
    # coordenadas da America do Norte casariam com pontos alheios (ou com
    # nenhum), e o piloto substituia a lista de slots por vazio.
    for cid, (cx, cy) in ((c, (v[0], v[1])) for c, v in WORLD_CITIES.items() if v[2] == region):
        for sx, sy, _ in small:
            # o digito fica logo ABAIXO e quase alinhado com o ponto; sem essa
            # restricao o proprio sprite do cursor conta como slot (2 falsos positivos)
            if abs(sx - cx) <= 6 and 4 <= (sy - cy) <= 12:
                out.add(cid)
                break
    return sorted(out)


def city_xy(cid):
    x, y, _ = NA_CITIES[cid]
    return x, y


def catalog_for_prompt(owned_slots, routes):
    """Catalogo enxuto para o prompt: so o que o agente precisa decidir.

    Inclui a distancia estimada ate a base — sem ela o modelo escolhe destinos
    fora do alcance do aviao e o jogo recusa a rota.
    """
    out = []
    for cid, (x, y, name) in NA_CITIES.items():
        entry = {
            "id": cid,
            "slots_owned": owned_slots.get(cid, 0),
            "dist_from_home_mi_est": distance_mi(HOME, cid) if cid != HOME else 0,
            "connected": any(cid in r for r in routes),
        }
        if name:
            entry["name"] = name
        out.append(entry)
    return out


# --- Placar do eval: tela Info->victory ---------------------------------
# As 7 regioes ocupam linhas de altura 8 a partir de y=111; o status fica na
# coluna da direita. Medido em logs/run_f0/placar_t1.png.
VICTORY_REGIONS = [
    "Europe", "Africa", "Middle East", "Southeast Asia",
    "Oceania", "North America", "South America",
]
VICTORY_ROW0, VICTORY_ROW_H = 111, 8
VICTORY_STATUS_BOX = (168, 0, 214, 7)  # x0,_,x1,altura — o y vem da linha


def read_victory(img, na_ref=None):
    """Status por regiao na tela de vitoria.

    Retorna {regiao: 'N/A' | 'com_valor'}. A distincao e feita por assinatura de
    pixels contra a referencia 'N/A' — evita OCR e basta para o placar: uma
    regiao deixa de ser N/A quando passamos a ter presenca nela.
    """
    import hashlib

    x0, _, x1, h = VICTORY_STATUS_BOX
    out = {}
    for i, reg in enumerate(VICTORY_REGIONS):
        y = VICTORY_ROW0 + i * VICTORY_ROW_H
        cell = img.crop((x0, y, x1, y + h))
        sig = hashlib.md5(cell.tobytes()).hexdigest()[:8]
        out[reg] = {"sig": sig}
        if na_ref:
            out[reg]["status"] = "N/A" if sig == na_ref else "com_valor"
    return out


def victory_na_signature(img):
    """Assinatura da celula 'N/A' — capturada de um placar no turno 1."""
    sigs = [v["sig"] for v in read_victory(img).values()]
    return max(set(sigs), key=sigs.count)

# ==== CATALOGO GLOBAL: 7 regioes ====
# id -> (x, y, indice_da_regiao, nome_confirmado_ou_None)
# O indice e quantos "R" a partir da America do Norte (0). MEDIDO percorrendo o
# ciclo com R durante a criacao de rota (catalog_regions.py): NA -> SA -> Europa
# -> Africa -> Oriente Medio -> Sudeste Asiatico -> Oceania, fechando em 7.
#
# CORRECAO 13/08 (o catalogo anterior estava ERRADO e teria trocado as cidades):
#  - a regiao 0 vinha da deteccao automatica e usava os MESMOS ids de NA_CITIES
#    para cidades DIFERENTES (NA03 = (194,54) la, (16,66)=San Francisco aqui).
#    Como EVAL_SLOTS_2000, HOME e os nomes confirmados sao chaveados por
#    NA_CITIES, usar aquele catalogo faria toda acao na America do Norte mirar
#    outra cidade — e algumas ainda "dariam certo". Agora a regiao 0 E derivada
#    de NA_CITIES, entao as duas nao podem mais divergir.
#  - Washington (204,84) FALTAVA na regiao 0: o cursor estava em cima dela na
#    captura e o detector nao ve o ponto sob o sprite. Por simetria, cada regiao
#    de 1 a 6 pode estar faltando UMA cidade ocluida pelo cursor (que ficou em
#    (204,84) durante todo o percurso). Buraco conhecido, nao corrigido.
#  - o ponto (135,137) aparecia nas 7 regioes na MESMA posicao: e a caixa de
#    rotulo do rodape, nao uma cidade. Removido (95 -> 89 cidades).
REGION_NAMES = {0: 'North America', 1: 'South America', 2: 'Europe', 3: 'Africa',
                4: 'Middle East', 5: 'Southeast Asia', 6: 'Oceania'}

WORLD_CITIES = {cid: (x, y, 0, nome) for cid, (x, y, nome) in NA_CITIES.items()}
WORLD_CITIES.update({
    "SA01": (78, 12, 1, "Havana"),     # confirmado na tela de detalhe (15/08)
    "SA02": (28, 16, 1, None),
    "SA03": (96, 28, 1, None),
    "SA04": (88, 94, 1, None),
    "SA05": (206, 106, 1, None),
    "SA06": (196, 108, 1, None),
    "SA07": (112, 130, 1, None),
    "SA08": (166, 130, 1, None),
    "EU01": (122, 12, 2, None),
    "EU02": (164, 12, 2, None),
    "EU03": (146, 18, 2, None),
    "EU04": (130, 28, 2, None),
    "EU05": (74, 30, 2, None),
    "EU06": (204, 34, 2, None),
    "EU07": (104, 40, 2, None),
    "EU08": (170, 40, 2, None),
    "EU09": (84, 44, 2, None),
    "EU10": (130, 46, 2, None),
    "EU11": (96, 56, 2, "Brussels"),   # confirmado na tela de detalhe (15/08)
    "EU12": (110, 58, 2, None),
    "EU13": (86, 66, 2, None),
    "EU14": (194, 72, 2, None),
    "EU15": (230, 72, 2, None),
    "EU16": (134, 74, 2, None),
    "EU17": (156, 76, 2, None),
    "EU18": (116, 84, 2, None),
    "EU19": (124, 100, 2, None),
    "EU20": (114, 108, 2, None),
    "EU21": (94, 116, 2, None),
    "EU22": (58, 118, 2, None),
    "EU23": (138, 122, 2, None),
    "EU24": (188, 132, 2, None),
    "AF01": (90, 22, 3, None),
    "AF02": (112, 24, 3, None),
    "AF03": (122, 38, 3, None),
    "AF04": (174, 48, 3, None),
    "AF05": (198, 92, 3, None),
    "AF06": (80, 102, 3, None),
    "AF07": (194, 116, 3, None),
    # Nome LIDO da tela de detalhe em 16/08 (logs/neg_multi/neg_ME01.png):
    # "Tashkent / Uzbekistan / Pop 2.4M / Econ 68 / Total slots 0/57".
    "ME01": (154, 14, 4, "Tashkent"),
    "ME02": (84, 36, 4, None),
    "ME03": (56, 62, 4, None),
    "ME04": (160, 62, 4, None),
    "ME05": (176, 94, 4, None),
    "ME06": (142, 106, 4, None),
    "ME07": (234, 108, 4, None),
    "ME08": (160, 132, 4, None),
    "AS01": (142, 12, 5, None),
    "AS02": (168, 24, 5, None),
    "AS03": (78, 32, 5, None),
    "AS04": (118, 36, 5, None),
    "AS05": (164, 48, 5, None),
    "AS06": (148, 50, 5, None),
    "AS07": (128, 52, 5, None),
    "AS08": (96, 58, 5, None),
    "AS09": (216, 68, 5, None),
    "AS10": (104, 72, 5, None),
    "AS11": (84, 84, 5, None),
    "AS12": (200, 84, 5, None),
    "AS13": (38, 94, 5, None),
    "AS14": (94, 104, 5, None),
    "AS15": (106, 114, 5, None),
    "AS16": (40, 126, 5, None),
    "AS17": (52, 132, 5, None),
    "OC01": (226, 34, 6, None),
    "OC02": (198, 48, 6, None),
    "OC03": (230, 72, 6, None),
    "OC04": (170, 84, 6, None),
    "OC05": (164, 110, 6, None),
    "OC06": (30, 114, 6, None),
    "OC07": (220, 118, 6, None),
    "OC08": (118, 120, 6, None),
    "OC09": (140, 128, 6, None),
})

# Quantas cidades por regiao (para conferencia rapida)
REGION_COUNTS = {r: sum(1 for v in WORLD_CITIES.values() if v[2] == r) for r in REGION_NAMES}


def city_region(cid):
    return WORLD_CITIES[cid][2]


def city_xy_world(cid):
    x, y, _, _ = WORLD_CITIES[cid]
    return x, y


def cities_of_region(reg):
    return sorted(c for c, v in WORLD_CITIES.items() if v[2] == reg)


# Assinatura de REGIAO por FORMA (mascara de terra), nao por contagem global.
#
# A contagem global (`REGION_LAND` abaixo, mantida so como referencia historica)
# NAO sobrevive ao jogo pintar o mapa: MEDIDO em logs/run_f0/map_t*.png que 2
# rotas desenhadas derrubam a regiao 0 de 2265 para 2183 pixels, e como
# REGION_LAND[0]=2262 dista so 189 do vizinho REGION_LAND[2]=2073, a leitura
# virava None a partir do turno 3 — o harness ficava CEGO justamente quanto mais
# o modelo jogava. Pior: de t5 em diante o vizinho mais proximo era a regiao 2,
# ou seja um fallback "pega o mais perto" chutaria a regiao ERRADA em silencio.
#
# A propriedade que conserta isso: rotas, sprites de aviao, pontos de cidade e
# o cursor so TAPAM verde — nunca pintam verde FORA da massa de terra da regiao.
# Logo a mascara observada e (aproximadamente) um SUBCONJUNTO da mascara de
# referencia da regiao certa, e a PRECISAO
#     |obs & ref| / |obs|
# e invariante ao desenho, enquanto a REVOCACAO |obs & ref| / |ref| e a unica
# que cai. Por isso o ranking e por precisao e a revocacao so serve de piso
# largo (para recusar tela que nao e mapa), nunca de criterio de desempate.
REGION_MASKS = None  # {regiao: frozenset(indice linear)}; carregado de JSON
_MASK_STEP = 3
_MASK_YMAX = 140
_MASK_XMAX = 256


def _load_region_masks():
    """Carrega harness/region_masks.json (gerado por gen_region_masks.py)."""
    global REGION_MASKS, _MASK_STEP, _MASK_YMAX, _MASK_XMAX
    if REGION_MASKS is not None:
        return REGION_MASKS
    import json
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "region_masks.json")
    with open(caminho) as f:
        d = json.load(f)
    _MASK_STEP = d["step"]
    _MASK_YMAX = d["ymax"]
    _MASK_XMAX = d["xmax"]
    REGION_MASKS = {int(r): frozenset(v) for r, v in d["regioes"].items()}
    return REGION_MASKS


def land_mask(img):
    """Mascara de terra como indices lineares, na mesma malha de land_pixels."""
    _load_region_masks()
    step, ymax, xmax = _MASK_STEP, _MASK_YMAX, _MASK_XMAX
    largura = (xmax + step - 1) // step
    px = img.load()
    out = set()
    for y in range(0, ymax, step):
        base = (y // step) * largura
        for x in range(0, xmax, step):
            p = px[x, y]
            if p[1] > p[0] + 30 and p[1] > p[2] + 10:
                out.add(base + x // step)
    return out


# Contagem global antiga. NAO e mais usada por detect_region; fica documentada
# porque outros probes a citam e porque e o numero que a etapa 1 refutou.
REGION_LAND = {0: 2262, 1: 1016, 2: 2073, 3: 877, 4: 1128, 5: 326, 6: 613}

# Limiares MEDIDOS (ver CALIBRATION, "ETAPA 1-VerRegiao"):
#  - precisao da regiao certa: 0.999 nos 12 map_t*.png reais; 1.000 em 420
#    mapas sinteticos com 2/6/12 rotas nas 7 regioes.
#  - maior precisao de regiao ERRADA em mapa limpo: 0.774 (r1 observada contra
#    a referencia r0 — o caso "pequena dentro da grande").
#  - revocacao da regiao certa no pior caso sintetico: 0.874 (r5, 12 rotas).
#    O piso e 0.60, largo de proposito: um piso apertado em 0.85, calibrado na
#    regiao 0 (2262 px), recusaria a regiao 5 (326 px) assim que ela ganhasse
#    rotas, porque a MESMA perda absoluta de pixels pesa 7x mais la.
#  - dialogo tapando >=60% da faixa do mapa cai para revocacao 0.525 -> None.
REGION_PREC_MIN = 0.90     # precisao minima do melhor palpite
REGION_PREC_2ND_MAX = 0.80  # precisao maxima tolerada para o 2o colocado
REGION_REC_MIN = 0.60      # piso largo de revocacao (recusa tela nao-mapa)
REGION_N_MIN = 200         # verde de menos para ser mapa de qualquer regiao


def region_scores(img):
    """[(precisao, revocacao, regiao)] ordenado por precisao. Para diagnostico."""
    masks = _load_region_masks()
    m = land_mask(img)
    n = len(m)
    out = []
    for r, ref in masks.items():
        i = len(m & ref)
        out.append((i / n if n else 0.0, i / len(ref), r))
    out.sort(reverse=True)
    return out


def detect_region(img, margin=None):
    """Regiao exibida no mapa, ou None se a leitura nao for confiavel.

    `margin` e ACEITO E IGNORADO — sobra da assinatura antiga por contagem
    global, mantida para nao quebrar os probes que a passavam.

    Recusa (devolve None) quando: ha verde de menos para ser mapa; a precisao
    do melhor palpite fica abaixo de REGION_PREC_MIN; a revocacao fica abaixo
    de REGION_REC_MIN (mapa muito tapado, p.ex. dialogo por cima); ou o
    segundo colocado tambem passa de REGION_PREC_2ND_MAX (ambiguo).
    """
    m = land_mask(img)
    if len(m) < REGION_N_MIN:
        return None
    masks = _load_region_masks()
    n = len(m)
    out = []
    for r, ref in masks.items():
        i = len(m & ref)
        out.append((i / n, i / len(ref), r))
    out.sort(reverse=True)
    prec, rec, reg = out[0]
    if prec < REGION_PREC_MIN or rec < REGION_REC_MIN:
        return None
    if len(out) > 1 and out[1][0] > REGION_PREC_2ND_MAX:
        return None
    return reg


HOME_REGION = WORLD_CITIES[HOME][2]


def read_region(bridge):
    from PIL import Image
    return detect_region(Image.open(bridge.screenshot()).convert("RGB"))


def switch_to_region(bridge, alvo, atual=None, total=7, tries=None):
    """Troca a regiao exibida no mapa apertando R e CONFIRMA por pixels.

    MEDIDO 12/08: durante a criacao de rota, R avanca a regiao e MANTEM a origem
    (o rotulo segue 'Washington'). Sem isto o agente so alcanca a America do
    Norte — e a vitoria exige hub em TODA regiao, tanto para ROTA quanto para
    NEGOCIACAO de slots.

    UM R POR VEZ, com leitura entre eles. MEDIDO 16/08 (probe_regiao4.py, mapa
    da negociacao): **os dois primeiros R sao engolidos** e so a partir do
    terceiro cada tecla anda uma regiao —

        R x0..x2: land=2266 regiao 0 | R x3: 1018 r1 | R x4: 2073 r2
        R x5: 879 r3 | R x6: 1128 r4 | R x7: 326 r5 | R x8: 613 r6

    A versao antiga mandava `passos` R's em LOTE e relia so no fim. Com teclas
    engolidas ela ficava atras do alvo e cada nova tentativa perdia mais uma:
    pedir a regiao 4 (Oriente Medio) parava na 3 (Africa) e a acao morria com
    "mapa ficou na regiao 3, esperado 4" (aceite B, 16/08). Com malha fechada a
    tecla engolida custa uma iteracao, nao a acao inteira.

    `atual` e apenas um palpite: a regiao real e LIDA da tela. Devolve
    (regiao_final, verificado: bool) — `verificado` False significa que alguma
    leitura saiu ambigua e a contagem entrou no lugar dela.
    """
    wait_text(bridge)  # o jogo ignora R durante a datilografia (medido 13/08)
    if tries is None:
        tries = 2 * total + 4
    lido = read_region(bridge)
    atual = lido if lido is not None else (HOME_REGION if atual is None else atual)
    cego = lido is None
    for _ in range(tries):
        if atual == alvo:
            return alvo, not cego
        lido = _press_r_until_read(bridge, atual)
        if lido is None:
            cego = True
            atual = (atual + 1) % total  # palpite: o R andou
        else:
            # lido == atual significa tecla ENGOLIDA: nao avancamos o palpite e a
            # proxima iteracao aperta de novo. E exatamente o caso que a versao
            # em lote nao sabia distinguir.
            atual = lido
    return atual, (not cego) and atual == alvo


# MEDIDO 16/08 (probe_regiao_tempo.py, mapa da negociacao): depois de um R que
# o jogo ACEITA, a nova regiao ja e legivel em **20-40 frames** (8 trocas: uma
# em 20, sete em 40, estaveis nas 4 leituras seguintes). Dai a leitura por
# POLLING, que sai assim que a regiao muda em vez de gastar 150 frames fixos —
# este caminho roda depois de TODA acao (invariante de regiao).
#
# ARMADILHA MEDIDA no mesmo dia: com orcamento de 120 frames o aceite A
# REGREDIU — `negotiate_slots SA01` (1 tecla de distancia) terminou na regiao 4.
# "Nao mudou dentro do orcamento" NAO e prova de tecla engolida: em outras telas
# o redesenho passa dos 120 frames, o codigo concluia "engolida", apertava de
# novo e passava do alvo. Duas defesas, as duas necessarias:
#   1. orcamento FOLGADO (300 frames = 7,5x o pior caso medido) antes de
#      declarar que a tecla nao pegou;
#   2. a regiao nova so e aceita com DUAS leituras iguais seguidas — uma leitura
#      unica pode cair num frame de transicao e casar com a assinatura de outra
#      regiao.
R_SETTLE_CHUNK = 20
R_SETTLE_BUDGET = 300


def _press_r_until_read(bridge, antes):
    """Aperta R e le ate a regiao MUDAR e ESTABILIZAR.

    Devolve a nova regiao, `antes` (nada mudou dentro do orcamento = tecla
    provavelmente engolida) ou None (leitura ambigua).
    """
    bridge.press("R", hold=4, wait=25)
    lido = None
    candidato = None
    for _ in range(R_SETTLE_BUDGET // R_SETTLE_CHUNK):
        bridge.advance(R_SETTLE_CHUNK)
        lido = read_region(bridge)
        if lido is not None and lido != antes:
            if candidato == lido:
                return lido
            candidato = lido
        else:
            candidato = None
    return lido


def settle_cursor_on(bridge, x, y, approach=6, taps=8):
    """Leva o cursor ate (x,y) TERMINANDO por movimento REAL de d-pad.

    MEDIDO 13/08 no mapa de negociacao: escrever a posicao na RAM desenha o
    sprite no lugar certo, mas o A NAO seleciona nada — seis A's seguidos sobre
    Washington nao abriram a tela da cidade. Depois de UM toque real de d-pad
    (Right+Left), o mesmo A abriu "Washington / United States / Total slots
    34/116". Ou seja: o jogo guarda a cidade sob o cursor no momento em que
    PROCESSA o movimento; a escrita na RAM nao dispara esse recalculo.

    Por isso teleportamos para perto (escrita, exata e barata) e fazemos os
    ultimos pixels por toque real, terminando EM CIMA do alvo.

    O passo do d-pad tambem NAO e o mesmo em todo mapa: 2px no mapa de rota,
    **3px** no mapa de negociacao (medido: 128->131->134->137->140). O laco
    fecha por leitura da RAM, entao serve para os dois.
    """
    bridge.batch(
        bridge.seq_write(CURSOR_X, min(255, x + approach))
        + bridge.seq_write(CURSOR_Y, min(255, y + approach))
        + bridge.seq_advance(15)
    )
    for eixo, botao, alvo, idx in (("x", "Left", x, 0), ("y", "Up", y, 1)):
        for _ in range(taps):
            pos = read_cursor(bridge)
            if pos[idx] <= alvo:
                break
            bridge.batch(
                bridge.seq_press(botao, hold=2, wait=12) + bridge.seq_advance(20), extra_frames=120
            )
    return read_cursor(bridge)


def point_cursor_at_world(bridge, cid, atual=None):
    """Seleciona uma cidade em QUALQUER regiao: troca de mapa e posiciona.

    Devolve (regiao_atual, posicao_do_cursor, regiao_verificada) para o chamador
    rastrear onde o mapa ficou — o jogo NAO volta sozinho para a regiao da base,
    e a acao seguinte comeca de onde a anterior parou.
    """
    x, y, reg, _ = WORLD_CITIES[cid]
    # ATIVAR ANTES DE TROCAR DE REGIAO. MEDIDO 13/08: com a mensagem ainda
    # datilografando o jogo ignora tambem o R — os apertos se perdem, a leitura
    # de regiao sai errada e o laco de correcao ACUMULA apertos (pedi Europa=2 e
    # o mapa parou no Sudeste Asiatico=5). O A de reconhecimento resolve os dois
    # problemas de uma vez.
    if not activate_cursor(bridge):
        raise RuntimeError("cursor do mapa nao respondeu — tela errada?")
    atual, ok = switch_to_region(bridge, reg, atual)
    if atual != reg:
        raise RuntimeError(f"mapa ficou na regiao {atual}, esperado {reg} ({cid})")
    # segunda ativacao: barata e sem efeito colateral num mapa ja vivo (o teste
    # e um toque de d-pad; so aperta A se o toque NAO mover a RAM)
    if not activate_cursor(bridge):
        raise RuntimeError(f"cursor nao respondeu na regiao {REGION_NAMES[reg]}")
    pos = settle_cursor_on(bridge, x + CURSOR_OFFSET[0], y + CURSOR_OFFSET[1])
    return atual, pos, ok


def catalog_for_prompt_world(owned_slots, routes, regions=None):
    """Catalogo GLOBAL para o prompt, agrupado por regiao.

    Distancia: o mapa de cada regiao tem projecao propria, entao pixel-para-milha
    NAO atravessa continentes. Para destinos fora da regiao da base a distancia
    sai `None` com uma nota — numero inventado aqui e pior que numero ausente,
    porque a regra do prompt manda comparar com o alcance do aviao.
    """
    out = {}
    for reg, nome in REGION_NAMES.items():
        if regions and reg not in regions:
            continue
        linhas = []
        for cid in cities_of_region(reg):
            x, y, _, cname = WORLD_CITIES[cid]
            e = {
                "id": cid,
                "slots_owned": owned_slots.get(cid, 0),
                "connected": any(cid in r for r in routes),
                "dist_from_home_mi_est": (
                    0 if cid == HOME else
                    distance_mi(HOME, cid) if reg == HOME_REGION else None
                ),
                # distancia LIDA do jogo (exata); ausente = nunca medimos
                "dist_from_home_mi_real": MEASURED_DIST_FROM_HOME.get(cid),
            }
            if cname:
                e["name"] = cname
            linhas.append(e)
        out[f"{reg} {nome}"] = linhas
    return out


# --- Painel Area/Type/Wait da tela Info->staff -------------------------------
# MEDIDO 13/08 (logs/negeu/00_staff_antes.png x 11_staff_depois.png): antes da
# negociacao o painel esta VAZIO (0 pixels de texto); depois mostra
# "Brussels / Airport Slots / 6 months" (517 pixels de texto). E o sinal de
# efeito de negotiate_slots — o lance NAO debita o caixa na hora, entao o gate
# de caixa nao serve para essa acao.
# Limitacao: o painel descreve o funcionario DESTACADO. A macro sempre envia o
# primeiro, entao a leitura vale para o fluxo atual; com escolha de funcionario
# (nao implementada) sera preciso ler os quatro.
STAFF_PANEL = (2, 66, 110, 140)
TEXT_RGB = (255, 251, 255)


def staff_panel_px(img):
    """Pixels de texto no painel Area/Type/Wait (0 = funcionario ocioso)."""
    px = img.load()
    return sum(
        1
        for y in range(STAFF_PANEL[1], STAFF_PANEL[3])
        for x in range(STAFF_PANEL[0], STAFF_PANEL[2])
        if px[x, y] == TEXT_RGB
    )


# Assinatura da TELA Info->staff: a moldura dos campos Area/Type/Wait usa a cor
# (99,99,165). MEDIDO: 750-751 pixels nas duas capturas da tela de staff, 0 numa
# mensagem do assessor e 0 no mapa. Sem esta checagem o harness leu "painel 0px"
# de uma tela que NAO era a de staff e concluiu que a negociacao tinha acabado.
STAFF_FRAME_RGB = (99, 99, 165)


# --- Tela "What type of plane" x tela de RECUSA ------------------------------
# MEDIDO 15/08 no recorte (8,24)-(248,120): na tela do aviao o painel cinza
# (123,123,140) ocupa 5552 px; na tela de recusa ("We don't have any aircraft
# capable of flying such a great distance") a area e 100% azul (57,75,173),
# 23040 px, zero cinza. Sem este detector o executor seguia apertando A na tela
# de recusa e reportava "fluxo travou na tela de voos/semana" — um sintoma tres
# telas depois da causa.
PLANE_PANEL_BOX = (8, 24, 248, 120)
PLANE_PANEL_RGB = (123, 123, 140)


def on_plane_screen(img, minimo=2000):
    px = img.load()
    return (
        sum(
            1
            for y in range(PLANE_PANEL_BOX[1], PLANE_PANEL_BOX[3])
            for x in range(PLANE_PANEL_BOX[0], PLANE_PANEL_BOX[2])
            if px[x, y] == PLANE_PANEL_RGB
        )
        >= minimo
    )


def on_staff_screen(img, minimo=400):
    px = img.load()
    return (
        sum(
            1
            for y in range(STAFF_PANEL[1], STAFF_PANEL[3])
            for x in range(STAFF_PANEL[0], STAFF_PANEL[2])
            if px[x, y] == STAFF_FRAME_RGB
        )
        >= minimo
    )


# --- RANKING REGIONAL (Info->finance, indice 3) ------------------------------
# MEDIDO 17/08 (ACTION_SPACE.md) e CONFIRMADO AO VIVO 17/08 (probe_rankings.py,
# eval_single_2000_lv5.state, trimestres 181/182 = Apr2000/Jul2000):
#
# Abrir Info->finance NAO cai direto no ranking regional: cai primeiro no
# "Quarterly Report <mes><ano>" (grafico de barras por companhia, $ do
# trimestre) — MESMA paleta de fundo do ranking, dai a falha do primeiro
# detector ingenuo (so cor de fundo) confundir as duas telas. Um toque de A
# no Quarterly Report avanca para "Regional Rankings <ano>": mapa-mundi com
# 7 caixas (Europe/N America/SE Asia/Mid East/Oceania/Africa/S America) e a
# legenda das 4 companhias (Federal/MetLink/AirRoma/Aussie) coloridas por
# ORDEM DE COLOCACAO daquele instante (a ordem da legenda mudou entre os dois
# momentos capturados — e o sinal de que e ranking de verdade, nao estatico).
# So caixas com dado already-computed mostram numero+marcador; as demais
# ficam PRETAS ("sem dados ainda" — bate com ACTION_SPACE.md linha 280).
#
# Evidencia (logs/rankings_probe/):
#   y1_00_map.png        Quarterly Report Apr2000 (Federal $00K | MetLink $17720K | AirRoma $00K | Aussie $1460K)
#   y1_region0_A.png      Regional Rankings 2000, trimestre Apr2000: N America 17280# | Oceania 1848# | demais 5 caixas pretas
#   y2_00_map.png        Quarterly Report Jul2000
#   y2_region0_A.png      Regional Rankings 2000, trimestre Jul2000: N America 34560# | Oceania 9048# | legenda reordenada (Aussie subiu para 2o)
#
# O pixel (30,60) e o teste que distingue as duas telas: preto (0,0,0) no
# ranking regional (caixa de regiao vazia), teal (41,123,173) no Quarterly
# Report (nao ha caixa ali, e o grafico de barras).
#
# PENDENTE (nao calibrado ainda): recorte exato de cada uma das 7 caixas e
# OCR do numero de passageiros/marcador de cor por caixa — as coordenadas
# tentadas (grade 30/95/140 x 45/95/140) nao bateram com as caixas reais
# (leram fundo do mapa, nao a caixa). Por ora so o DETECTOR de tela e a
# leitura qualitativa (quais regioes tem dado vs pretas) estao prontos.
QUARTERLY_REPORT_TITLE_PT = (10, 40)
QUARTERLY_REPORT_TEAL = (41, 123, 173)
REGIONAL_RANKINGS_TITLE_PT = (0, 0)
REGIONAL_RANKINGS_BG = (57, 75, 173)
REGIONAL_RANKINGS_BOX_PT = (30, 60)  # caixa da Europa: preta se sem dado


def on_regional_rankings_img(img):
    """Tela 'Regional Rankings <ano>' (Info->finance, apos 1x A no Quarterly Report).

    Distingue do Quarterly Report (mesma paleta de fundo) pelo pixel da
    caixa da Europa: so o ranking tem caixa DESENHADA ali (preta), o
    relatorio trimestral tem o gradiente teal do grafico de barras.
    """
    px = img.load()
    return (
        px[REGIONAL_RANKINGS_TITLE_PT] == REGIONAL_RANKINGS_BG
        and px[REGIONAL_RANKINGS_BOX_PT] == (0, 0, 0)
    )


def on_quarterly_report_img(img):
    """Tela 'Quarterly Report <mes><ano>' — 1o relatorio da cadeia de fim de turno."""
    px = img.load()
    return px[QUARTERLY_REPORT_TITLE_PT] == QUARTERLY_REPORT_TEAL


REGIONAL_RANKINGS_REGIONS = (
    "Europe", "N America", "SE Asia", "Mid East", "Oceania", "Africa", "S America",
)

# Bounding boxes aproximadas das 7 caixas, medidas por deteccao de retangulo
# preto em y1_region0_A.png (grade de amostragem 4px). NAO CALIBRADO: uma
# tentativa de classificar "caixa com dado vs caixa vazia" por fracao de
# pixel preto (limiar 0.8/0.9) foi testada contra os 2 momentos capturados e
# NAO bateu de forma estavel — mesmo N America e Oceania, que tem numero
# visivel ("17280#"/"1848#" -> "34560#"/"9048#"), ficam ~85-90% pretos porque
# o numero e o marcador ocupam pouca area da caixa. Fica so o bounding box
# medido; leitura de conteudo por caixa (numero + cor do lider) e PENDENTE —
# precisa recorte fino em volta do numero/marcador (nao no centro da caixa) e
# OCR dos digitos, nao feito nesta sessao.
REGIONAL_RANKINGS_BOXES = {
    "Europe": (24, 40, 88, 68),
    "N America": (180, 48, 244, 68),
    "SE Asia": (104, 56, 168, 84),
    "Mid East": (56, 112, 124, 140),
    "Oceania": (140, 120, 208, 140),
    "Africa": (16, 168, 80, 196),
    "S America": (180, 168, 244, 196),
}

# CALIBRADO 18/08 (ETAPA 8-LerRanking) — OCR do numero por regiao, POR
# COLUNA-DE-PIXEL-BRANCO (255,251,255), sem drill-down.
#
# ACHADO que corrige o texto do CALIBRATION.md (que descrevia offset positivo
# "para baixo" a partir do topo da caixa): a faixa do numero fica ACIMA do
# REGIONAL_RANKINGS_BOXES[regiao][1] (y0), nao abaixo. Medido nas 2 unicas
# regioes com dado nos 2 momentos capturados (y1/y2_region0_A.png):
#   N America: box y0=48, digitos em y=40..46 (offset -8)
#   Oceania:   box y0=120, digitos em y=111..117 (offset -9)
# Ambos com banda de 7px de altura. As outras 5 regioes NUNCA tiveram dado
# visivel nos savestates disponiveis — offset delas e DESCONHECIDO, nao
# assumido (decodificar so roda pras 2 regioes abaixo; as outras 5 sempre
# devolvem None ate alguem capturar um momento com hub+rota ativa la).
RANKING_ROW_OFFSET = {"N America": -8, "Oceania": -9}
RANKING_ROW_HEIGHT = 7

# O glifo do MESMO digito NAO produz o mesmo hash entre N America e Oceania
# (subpixel/alinhamento de fonte difere por posicao de tela — verificado
# vivo: '1' em NA e '1' em OC tem hashes diferentes). Por isso o catalogo e
# POR REGIAO, construido a partir dos 4 numeros reais ja capturados:
#   N America: "17280#" (y1_region0_A.png, Apr2000) -> "34560#" (y2, Jul2000)
#   Oceania:   "1848#"  (y1_region0_A.png, Apr2000) -> "9048#"  (y2, Jul2000)
# Cobrem os 10 digitos + "#" sem nenhum conflito de hash dentro da mesma
# regiao. Regiao fora do catalogo -> decodifica None (falha segura, nunca
# adivinha digito). Fonte: harness/world.py, construido inline a partir de
# logs/rankings_probe/{y1,y2}_region0_A.png (ver CALIBRATION.md ETAPA 8).
RANKING_GLYPHS = {
    "N America": {
        "7912227295": "1", "459e7b67f4": "7", "3008d6e7e6": "2",
        "a89fcb5381": "8", "8dfa56e73d": "0", "ddf0bfefff": "#",
        "3248d9c2b2": "3", "97cada40a8": "4", "ee9365a705": "5",
        "5ac520739d": "6",
    },
    "Oceania": {
        "3205cfe8d0": "1", "a82397a719": "8", "01e9e60b34": "4",
        "085c396590": "#", "c3e488b85e": "9", "83138401d3": "0",
    },
}

RANKING_WHITE = (255, 251, 255)


def _ranking_digit_hash(img, gx0, gx1, y0, y1):
    import hashlib
    px = img.load()
    bits = []
    for y in range(y0, y1):
        for x in range(gx0, gx1):
            bits.append("1" if px[x, y] == RANKING_WHITE else "0")
    return hashlib.md5("".join(bits).encode()).hexdigest()[:10]


def _ranking_col_groups(img, x0, x1, y0, y1):
    px = img.load()
    cols = [any(px[x, y] == RANKING_WHITE for y in range(y0, y1)) for x in range(x0, x1)]
    groups = []
    cur = None
    for i, has in enumerate(cols):
        if has and cur is None:
            cur = [i, i]
        elif has:
            cur[1] = i
        elif cur is not None:
            groups.append((x0 + cur[0], x0 + cur[1] + 1))
            cur = None
    if cur is not None:
        groups.append((x0 + cur[0], x0 + cur[1] + 1))
    return groups


def read_regional_rankings(img):
    """Decodifica o numero do lider por regiao na tela 'Regional Rankings'.

    Devolve {regiao: int|None}. None = caixa sem dado (preta) OU regiao/
    glifo fora do catalogo (RANKING_GLYPHS so tem N America/Oceania hoje) —
    NUNCA adivinha digito. `img` deve ser um frame com `on_regional_rankings_img`
    verdadeiro (chamador responsavel por navegar ate la).
    """
    out = {}
    for region in REGIONAL_RANKINGS_REGIONS:
        glyphs = RANKING_GLYPHS.get(region)
        offset = RANKING_ROW_OFFSET.get(region)
        if not glyphs or offset is None:
            out[region] = None
            continue
        x0, y0, x1, _ = REGIONAL_RANKINGS_BOXES[region]
        row0 = y0 + offset
        row1 = row0 + RANKING_ROW_HEIGHT
        groups = _ranking_col_groups(img, x0, x1, row0, row1)
        digits = []
        ok = True
        for gx0, gx1 in groups:
            h = _ranking_digit_hash(img, gx0, gx1, row0, row1)
            ch = glyphs.get(h)
            if ch is None:
                ok = False
                break
            digits.append(ch)
        if not ok or not digits or digits[-1] != "#":
            out[region] = None
            continue
        try:
            out[region] = int("".join(digits[:-1]))
        except ValueError:
            out[region] = None
    return out


# --- Fluxo de COMPRA DE AVIAO (comando r0c3) ---------------------------------
# MEDIDO 15/08 (probe_buy.py, savestate do eval). A caixa de dialogo deste fluxo
# fica no TOPO da tela, NAO no rodape: a constante TEXTBOX (62,152,232,188) usada
# no fluxo de rota cai em cima da linha "Price $..." e fica CONSTANTE durante o
# fluxo inteiro (medido: hash 1cf2b866 identico em 8 telas seguidas). Usar _step()
# aqui devolveria False sempre. Recortes deste fluxo:
BUY_TEXT = (60, 20, 250, 64)     # fala da vendedora / pergunta (exclui o retrato)
BUY_PANEL = (8, 82, 150, 148)    # SO o desenho + o nome do modelo (ver nota abaixo)
BUY_PRICE = (0, 148, 256, 178)   # "Start of Production" + "Price" / "Cost: N"

# CALIBRADO 17/08 (probe_venture9/10, live): linha "<Nome> $<preco>K" da tela
# de business venture (r0c5), logo abaixo dos icones da cidade e acima da
# caixa de dialogo (TEXTBOX comeca em y=152). NAO temos OCR — o hash serve so
# para detectar SE Right mudou de tipo, nunca para ler o preco. Confirmado
# 17/08: muda entre Concert Hall/Grand Hotel/Commuter Airline (Washington) e
# fica IDENTICO quando Right nao tem mais tipo pra oferecer (sem wrap) — por
# isso vira o sinal de "acabaram os tipos desta cidade" no executor.
VENTURE_TYPE_BOX = (0, 130, 256, 150)


def venture_type_hash(img):
    return _crop_md5(img, VENTURE_TYPE_BOX)


def _crop_md5(img, box):
    import hashlib

    return hashlib.md5(img.crop(box).tobytes()).hexdigest()[:8]


def buy_panel_hash(img):
    """Assinatura do modelo na tela do showroom.

    O recorte para na coluna x=150 DE PROPOSITO. A metade direita do painel
    (alcance/assentos/combustivel/reparo/estrelas/UNIDADES QUE POSSUIMOS) tem
    um campo DINAMICO: as unidades em estoque. Medido: o mesmo MD100 hasheia
    672bf7ee com 6 unidades e 645ceac3 com 5 (uma ja alocada numa rota), o que
    fez a compra de MD100 abortar dizendo que a tela era de outro aviao — com a
    captura mostrando "MD100" em letras garrafais. Com o recorte a esquerda
    (desenho + nome) o hash e invariante: bate entre a referencia de 6 unidades
    e a tela ao vivo de 5, e os 8 modelos continuam distintos.
    """
    return _crop_md5(img, BUY_PANEL)


def buy_text_hash(bridge):
    """Hash do dialogo do fluxo de compra — as DUAS caixas, nao uma.

    MEDIDO: o fluxo troca de layout no meio. A tela do mapa de fabricantes usa a
    caixa de RODAPE (a mesma TEXTBOX do fluxo de rota: "Which manufacturer would
    you like to visit?"); as telas de showroom usam a caixa do TOPO
    (BUY_TEXT: "Nice to meet you...", "You can order a maximum of 10 planes...").
    Hashear so o topo fazia wait_buy_text() devolver na hora no mapa de
    fabricantes — a area estava vazia e constante — e o executor bumpava o
    seletor durante a datilografia. Sintoma real: pedir A340 e chegar na tela do
    MD11 (o gate de painel pegou: 'painel na tela e d174fcd9, esperado c664bbf5').
    """
    import hashlib

    from PIL import Image

    img = Image.open(bridge.screenshot()).convert("RGB")
    return hashlib.md5(img.crop(BUY_TEXT).tobytes() + img.crop(TEXTBOX).tobytes()).hexdigest()[:8]


def wait_buy_text(bridge, max_polls=10, settle=40):
    """Espera a datilografia da fala da vendedora terminar (2 leituras iguais).

    MEDIDO: sem esperar, o PRIMEIRO toque no seletor de fabricante e engolido —
    o mesmo padrao do cursor do mapa. Com advance(60) a sequencia 0..7 toques
    devolvia MDC,MDC,Boeing,...; com advance(240) devolve MDC,Boeing,World
    Lease,Airbus,Tupolev,Ilyushin,MDC (ver CALIBRATION §12).
    """
    prev = buy_text_hash(bridge)
    for _ in range(max_polls):
        bridge.advance(settle)
        cur = buy_text_hash(bridge)
        if cur == prev:
            return cur
        prev = cur
    return prev


# Seletor de FABRICANTE na tela "Which manufacturer would you like to visit?":
# 1 toque Right = proximo fabricante, ciclo de 6. MEDIDO com espera da
# datilografia (probe_buy.py mk Right 6, logs/buy/mk_labels.png).
MAKERS = ["MDC", "Boeing", "World Lease", "Airbus", "Tupolev", "Ilyushin"]
# ATENCAO: indice 2 ("World Lease") NAO vende avioes novos — a tela pergunta
# "Which model are you trying to sell?" e mostra a NOSSA frota (MD100 por
# $20.880K). E o canal de VENDA. Nao usar em buy_aircraft.
MAKER_SELL = 2

# Seletor de MODELO dentro do fabricante: 1 toque DOWN = proximo modelo.
# MEDIDO: Right/L NAO fazem nada nessa tela (7 capturas com hash identico);
# Down alterna os modelos e da a volta.
# Alcance, assentos, preco e ano lidos DA TELA (logs/buy/md*_Down_*.png).
# "panel" = md5[:8] do recorte BUY_PANEL — assinatura para PROVAR, antes de
# confirmar a compra, que o modelo na tela e o que o agente pediu.
AIRCRAFT_CATALOG = {
    "MD11":     {"maker_idx": 0, "model_idx": 0, "range_mi": 7750, "seats": 360,
                 "price_k": 81600,  "prod": 1991, "panel": "3b61c2c4"},
    "MD12":     {"maker_idx": 0, "model_idx": 1, "range_mi": 8000, "seats": 400,
                 "price_k": 96000,  "prod": 1995, "panel": "6d47e58f"},
    "MD100":    {"maker_idx": 0, "model_idx": 2, "range_mi": 4680, "seats": 200,
                 "price_k": 28800,  "prod": 1998, "panel": "8030bace"},
    "B747-400": {"maker_idx": 1, "model_idx": 0, "range_mi": 7180, "seats": 550,
                 "price_k": 135000, "prod": 1989, "panel": "c9418b1f"},
    "B777":     {"maker_idx": 1, "model_idx": 1, "range_mi": 5500, "seats": 360,
                 "price_k": 54000,  "prod": 1995, "panel": "31752f2a"},
    "A340":     {"maker_idx": 3, "model_idx": 0, "range_mi": 8870, "seats": 330,
                 "price_k": 110000, "prod": 1993, "panel": "35321d23"},
    "TU204":    {"maker_idx": 4, "model_idx": 0, "range_mi": 2870, "seats": 210,
                 "price_k": 28600,  "prod": 1989, "panel": "973a264d"},
    "IL96-300": {"maker_idx": 5, "model_idx": 0, "range_mi": 6870, "seats": 300,
                 "price_k": 49500,  "prod": 1988, "panel": "13a21801"},
}
for _m in AIRCRAFT_CATALOG.values():
    _m["maker"] = MAKERS[_m["maker_idx"]]

# Quantidade: 1 toque Right = +1 aviao, base 1, teto 10 ("You can order a maximum
# of 10 planes"). MEDIDO em 5 pontos: 0->1, 1->2, 2->3, 3->4, 4->5
# (logs/buy/qty_right.png).
BUY_QTY_BASE = 1
BUY_QTY_MAX = 10


# O SELETOR DE FABRICANTE E "PEGAJOSO" — MEDIDO 15/08, do jeito caro.
# Ele NAO volta para MDC ao reabrir o comando: fica no fabricante da ultima
# visita, exatamente como o cursor de icones do menu. Uma sequencia que assumia
# inicio em MDC e dava "Right x2" para chegar ao World Lease caiu na Airbus e
# comprou 5 A340 por $550.000K (frota: A340 Order 5; caixa 1.123.880K ->
# 573.880K). Por isso o executor LE o fabricante na tela antes de andar.
# Recorte do rotulo (so o nome, sem a caixa "Maker" nem as setas) e md5[:8]
# medidos com a datilografia ja encerrada (logs/buy/mk_Right_*.png); o indice 2
# foi confirmado por uma captura independente (logs/buy/sell_00.png).
MAKER_LABEL_BOX = (60, 124, 162, 148)
MAKER_LABEL_MD5 = {
    "ef998f36": 0,  # MDC
    "7975a58a": 1,  # Boeing
    "d196c072": 2,  # World Lease
    "442d8155": 3,  # Airbus
    "711b6f90": 4,  # Tupolev
    "89fe6489": 5,  # Ilyushin
}


def read_maker_idx(img):
    """Indice do fabricante exibido, ou None se o rotulo nao for reconhecido.

    Duas armadilhas MEDIDAS, as duas do mesmo tipo (hashear pixels que nao sao
    o dado):
    1. As SETAS do seletor so aparecem depois do primeiro movimento. Colunas de
       texto branco em MDC: com seta [26,27,28, 64..86, 163..165, ...]; sem seta
       [64..86, ...]. Um recorte que comecasse antes de x=60 dava hash diferente
       para o MESMO fabricante — foi o que fez a 2a compra de uma cadeia falhar
       com "nao consegui LER o fabricante" (logs/run_f0/buy_maker_ilegivel_B777.png,
       tela mostrando "Maker MDC" perfeitamente legivel).
    2. O FUNDO da faixa e um degrade de ceu que muda entre telas. Por isso o
       hash e da MASCARA binaria do texto branco (255,251,255), nao dos pixels.
    Validado: MDC bate com e sem seta; World Lease bate em 3 capturas
    independentes (mk_Right_02, sell_00, eu2_maker).
    """
    import hashlib

    x0, y0, x1, y1 = MAKER_LABEL_BOX
    px = img.crop(MAKER_LABEL_BOX).load()
    bits = bytes(
        1 if px[x, y] == TEXT_RGB else 0
        for y in range(y1 - y0)
        for x in range(x1 - x0)
    )
    return MAKER_LABEL_MD5.get(hashlib.md5(bits).hexdigest()[:8])


# =====================================================================
# ORCAMENTOS — comando r0c4 (MEDIDO 15/08, probe_edit.py / calib_budget.py)
# =====================================================================
# A tela mostra 3 colunas (Repair / Ad / Service), cada uma com:
#   - o gasto do trimestre em $K  ("$110K")   <- MUDA NO ATO ao confirmar a ordem
#   - o NIVEL atual (0-100), em numero grande e como BARRA VERDE
#   - a ORDEM vigente (MAXIMUM / RAISE / MAINTAIN / REDUCE / STOP)
# Fluxo: "Change which budget?" (Right = proxima coluna, ciclo 3)
#        -> A -> "What are your orders?" (Down = proxima ordem, ciclo 5)
#        -> A -> "Are you sure...?" -> A -> aplica e volta para a 1a tela.
BUDGET_COLS = ("repair", "ad", "service")
BUDGET_ORDERS = ("maximum", "raise", "maintain", "reduce", "stop")

# Cabecalho da coluna SELECIONADA fica laranja (198,130,66); as outras cinza
# (140,138,140). MEDIDO em bsel_00/01/02.
BUDGET_HDR_X = ((8, 78), (92, 162), (176, 246))
BUDGET_HDR_Y = (14, 26)
BUDGET_HDR_SEL_RGB = (198, 130, 66)

# Barra de nivel: y=106, 64px de largura por coluna, verde = nivel.
BUDGET_BAR_Y = 106
BUDGET_BAR_X0 = (24, 96, 168)
BUDGET_BAR_W = 64

# Rotulo da ordem: caixa de 52x14 por coluna, pitch 72.
BUDGET_LABEL_BOX = (34, 128, 86, 142)
BUDGET_LABEL_PITCH = 72
# md5 do recorte BINARIZADO (branco vs resto) — o fundo muda de cor por coluna
# e por estado (confirmada = esmaecida), entao hashear o pixel cru nao serve.
BUDGET_LABEL_MD5 = {
    "e20921e8": "maximum", "140c2105": "raise", "76fc5a47": "maintain",
    "d0001cb3": "reduce", "4fbd5c08": "stop",
}

# Valor em $K: fonte pequena, celulas de 8px, texto ALINHADO A DIREITA
# terminando no 'K'. O 'K' da coluna i comeca em x = 73 + 72*i.
BUDGET_MONEY_KX = (73, 145, 217)
BUDGET_MONEY_Y = (78, 88)
BUDGET_GLYPHS = {
    "a798c2fc": "K", "6f0e30d3": "$",
    "b8018869": "0", "70b3c357": "1", "4512183a": "4",
    "2a1564a7": "6", "c2b231ed": "9",
    # colhidos 19/08 das capturas de calib_budget_19ago (render ASCII do recorte
    # binarizado). AINDA FALTAM "3" e "8": nao apareceram em nenhuma tela ate
    # agora, entao valor que os contenha sai como None — falha visivel, nunca
    # numero adivinhado.
    "3371d46f": "5", "e1259348": "2", "357a988a": "7",
}

# NUMEROS DE NIVEL (fonte grande, pretos, 90/6/48 em capturas atuais)
# Colhidos 19/08 em harvest_budget_level_digits.py: cada hash e o numero INTEIRO.
BUDGET_LEVEL_GLYPHS = {
    "4404c620": "90",
    "52f419b5": "6",
    "ab5c753a": "48",
}


def _bin_md5(img, box):
    """md5 do recorte binarizado (>200 = tinta). Imune a cor de fundo."""
    import hashlib

    c = img.crop(box).point(lambda v: 255 if v > 200 else 0).convert("L")
    return hashlib.md5(c.tobytes()).hexdigest()[:8]


def read_budget_col(img):
    """Indice da coluna selecionada na tela de orcamentos (0/1/2), ou None."""
    px = img.load()
    y0, y1 = BUDGET_HDR_Y
    best, melhor = None, 0
    for i, (x0, x1) in enumerate(BUDGET_HDR_X):
        n = sum(1 for y in range(y0, y1) for x in range(x0, x1)
                if px[x, y] == BUDGET_HDR_SEL_RGB)
        if n > melhor:
            best, melhor = i, n
    return best if melhor > 50 else None


def read_budget_levels(img):
    """Comprimento em px da barra verde de cada coluna (0..64).

    O nivel 0-100 exibido em numero grande e ~ px/64*100 (MEDIDO: Service
    nivel 48 -> 30px = 46,9; Repair nivel 90 -> 58px = 90,6; Ad nivel 6 -> 2px
    = 3,1 — o extremo baixo tem erro de arredondamento de alguns pontos).
    A barra e o sinal AUTOMATIZAVEL do nivel; o numero exato exigiria OCR da
    fonte grande, NAO implementado.
    """
    px = img.load()
    out = []
    for x0 in BUDGET_BAR_X0:
        out.append(sum(1 for x in range(x0, x0 + BUDGET_BAR_W)
                       if px[x, BUDGET_BAR_Y][1] > 150
                       and px[x, BUDGET_BAR_Y][0] < 100 and px[x, BUDGET_BAR_Y][2] < 100))
    return out


def read_budget_orders(img):
    """Ordem vigente em cada coluna, lida do rotulo. None onde o hash e novo."""
    x0, y0, x1, y1 = BUDGET_LABEL_BOX
    out = []
    for i in range(3):
        dx = BUDGET_LABEL_PITCH * i
        out.append(BUDGET_LABEL_MD5.get(_bin_md5(img, (x0 + dx, y0, x1 + dx, y1))))
    return out


def read_budget_money(img, col=None, debug=False):
    """Gasto em $K de cada coluna (lido do texto '$NNNK'). None se ilegivel."""
    cols = range(3) if col is None else [col]
    out = []
    for i in cols:
        kx = BUDGET_MONEY_KX[i]
        y0, y1 = BUDGET_MONEY_Y
        digitos = ""
        val = None
        for k in range(5):
            x = kx - 8 * k
            g = BUDGET_GLYPHS.get(_bin_md5(img, (x - 1, y0, x + 7, y1)))
            if debug and g is None:
                print("   glifo novo em col%d k%d: %s"
                      % (i, k, _bin_md5(img, (x - 1, y0, x + 7, y1))))
            if k == 0:
                if g != "K":
                    break
                continue
            if g == "$":
                val = int(digitos[::-1]) if digitos else None
                break
            if g is None or not g.isdigit():
                break
            digitos += g
        out.append(val)
    return out if col is None else out[0]


def on_budget_screen(img):
    """True se a tela de orcamentos esta aberta (as 3 barras de nivel existem)."""
    return read_budget_col(img) is not None


def on_budget_orders_prompt(img):
    """True na caixa "What are your orders?" da tela de orcamentos.

    MEDIDO 19/08 (`probe_budget_popup.py`): enquanto essa caixa esta ativa o
    realce do CABECALHO some, entao `read_budget_col` devolve None e
    `on_budget_screen` da False — com a tela de orcamentos inteira na frente.
    Era isso que fazia o guard de `set_budget` recusar o proprio A de
    confirmacao ("deixei a tela de orcamento no confirm A#1").

    A assinatura usada e a que sobrevive a caixa: os TRES rotulos de ordem
    continuam legiveis e continuam mudando com Up/Down. Exigir os tres (e nao
    "algum texto na tela") mantem o guard util — uma tela de noticia ou a caixa
    YES/NO de patrocinio nao tem os tres rotulos.
    """
    if read_budget_col(img) is not None:
        return False
    ordens = read_budget_orders(img)
    return bool(ordens) and len(ordens) == 3 and all(o in BUDGET_ORDERS for o in ordens)


def on_budget_family(img):
    """Tela de orcamentos, com ou sem a caixa de ordens aberta."""
    return on_budget_screen(img) or on_budget_orders_prompt(img)


def wait_budget_col(bridge, tries=8, settle=20):
    """Le a coluna selecionada insistindo — o destaque do cabecalho PISCA.

    MEDIDO: `bconf_3.png` (logo apos aplicar uma ordem) tem os TRES cabecalhos
    cinza, enquanto `w_budgets_00.png`, da mesma tela, tem o Repair laranja.
    Uma leitura unica devolve None em ~metade dos frames — e andar com o
    seletor a partir de "nao sei" e exatamente o erro que custou $550.000K no
    seletor de fabricante (CALIBRATION §15b).
    """
    from PIL import Image

    for _ in range(tries):
        img = Image.open(bridge.screenshot()).convert("RGB")
        c = read_budget_col(img)
        if c is not None:
            return c
        bridge.advance(settle)
    return None


def read_budget_numbers(img):
    """Le os numeros EXATOS de orcamento (custo $K + nivel 0-100).

    Devolve {repair: {custo_k, nivel}, ad: {...}, service: {...}}.
    Custos e niveis veem como None se ilegivel; nunca ha palpite.

    ETAPA 4: substitui `read_budget_levels` (pixel-level) pelo numero real de
    nivel (0-100), sem conversao de pixel.
    """
    out = {}

    # Le os custos em $K
    custos = read_budget_money(img)  # lista [repair, ad, service]

    # Le os numeros de nivel usando a banda y=35-65 com tinta ESCURA
    for col in range(3):
        kx = BUDGET_MONEY_KX[col]
        y0, y1 = 35, 65
        x0 = kx - 40
        x1 = kx + 20

        # Acha o hash do numero inteiro (agrupando colunas de tinta escura)
        px = img.load()
        cols = []
        for x in range(x0, x1):
            has_ink = False
            for y in range(y0, y1):
                c = img.getpixel((x, y))
                avg = (c[0] + c[1] + c[2]) // 3
                if avg < 150:
                    has_ink = True
                    break
            cols.append(has_ink)

        # Agrupa colunas consecutivas com tinta
        groups = []
        cur = None
        for i, has in enumerate(cols):
            if has and cur is None:
                cur = [i, i]
            elif has:
                cur[1] = i
            elif cur is not None:
                groups.append((x0 + cur[0], x0 + cur[1] + 1))
                cur = None
        if cur is not None:
            groups.append((x0 + cur[0], x0 + cur[1] + 1))

        # Se ha um unico grupo (numero inteiro), hasha e procura no catalogo
        nivel = None
        if len(groups) == 1:
            gx0, gx1 = groups[0]
            bits = ""
            for y in range(y0, y1):
                for x in range(gx0, gx1):
                    c = img.getpixel((x, y))
                    avg = (c[0] + c[1] + c[2]) // 3
                    bits += "1" if avg < 150 else "0"

            import hashlib
            h = hashlib.md5(bits.encode()).hexdigest()[:8]
            nivel = BUDGET_LEVEL_GLYPHS.get(h)

        col_name = BUDGET_COLS[col]
        out[col_name] = {"custo_k": custos[col], "nivel": nivel}

    return out


# --- Tela de NEGOCIACAO (r0c2): grade de funcionarios --------------------------
# MEDIDO 16/08 (probe_staff_pick*.py, savestates eval_single_2000_lv5 e
# _neg1_feita). CAUSA RAIZ da falha "a 2a negociacao do turno nao acontece":
# a macro apertava A as cegas com o destaque parado no funcionario 0. Depois da
# 1a negociacao ESSE funcionario esta em missao e o jogo responde
# "Sorry, I'm busy making a bid for some airport slots" e NAO sai da tela
# (logs/neg2/03_apos_A3.png, 04_apos_A4.png). Os A's seguintes se perdiam ali e
# o erro so aparecia tres passos depois, como "cursor do mapa nao respondeu".
#
# Geometria medida pelo bbox do destaque (vermelho puro 255,0,0 — 448 px, NAO
# pisca: 8 leituras seguidas identicas em logs/staffpick/blink_*.png):
STAFF_SEL_RGB = (255, 0, 0)
STAFF_CELL_X = (98, 146, 194)
STAFF_CELL_Y = (9, 73)
# As celulas de FUNCIONARIO sao as 4 do bloco 2x2. A celula (1,2) NAO e
# funcionario: ao pousar nela o jogo troca a acao de Bid para **Return** e o A
# abre "Return which city's slots?" (logs/staffpick/c_celula5.png e
# c_celula5_apos_A.png). Selecionar essa celula por engano DEVOLVERIA slots.
STAFF_CELLS = ((0, 0), (0, 1), (1, 0), (1, 1))
STAFF_RETURN_CELL = (1, 2)
# Movimento MEDIDO: 1 toque = 1 celula, SEM wrap (satura na borda):
#   Right a partir de (0,0) -> (0,1) e para (6 toques, 1 movimento);
#   Down  a partir de (0,0) -> (1,0) e para;
#   na linha de baixo Right chega ate a coluna 2 (a celula de Return).
# O seletor NAO e pegajoso: reabrir o comando devolve o destaque a (0,0)
# (logs/staffpick/b_reabre.png). Ainda assim lemos a posicao antes de andar —
# assumir o inicio do seletor de fabricante ja custou $550.000K (CALIBRATION §15b).

# Cracha do funcionario: figurinha vermelha (189,0,41) desenhada no canto
# inferior direito da celula QUANDO ELE ESTA NA BASE. Ao ser despachado o
# cracha SAI da celula e reaparece sobre o mini-mapa, marcando o destino
# (medido: 23 px por cracha, 4 crachas na base, e apos negociar em Bruxelas o
# cracha da celula (0,0) migrou para (35..39, 23..30), sobre a Europa).
STAFF_BADGE_RGB = (189, 0, 41)
STAFF_BADGE_PX = 23

# Bid / Return: o item destacado fica LARANJA (198,97,66); o outro, cinza.
# Medido: Bid destacado = 359 px na caixa de Bid; Return destacado = 297 px.
BID_BOX = (198, 20, 248, 36)
RETURN_BOX = (198, 36, 248, 52)
BID_ON_RGB = (198, 97, 66)

# Contador de funcionarios LIVRES lido do MENU PRINCIPAL, sem navegar: os
# "bonecos" da barra inferior. MEDIDO: 92 px com 4 livres, 69 px com 3 livres
# (logs/staffpick/c_menu_zero_neg.png x c_menu_uma_neg.png) — 23 px por boneco,
# desenhados da esquerda para a direita. E o sinal de efeito da negociacao:
# cumulativo, por acao, e de graca (o menu principal ja e fotografado).
MENU_STAFF_BAR = (72, 170, 115, 190)


def count_rgb(img, box, rgb):
    px = img.load()
    return sum(
        1
        for y in range(box[1], box[3])
        for x in range(box[0], box[2])
        if px[x, y] == rgb
    )


def staff_cell_box(row, col):
    x, y = STAFF_CELL_X[col], STAFF_CELL_Y[row]
    return (x, y, x + 51, y + 67)


def staff_badge_box(row, col):
    x, y = STAFF_CELL_X[col], STAFF_CELL_Y[row]
    return (x + 38, y + 50, x + 48, y + 66)


def staff_sel_cell(img):
    """Celula (linha, coluna) sob o destaque vermelho, ou None se nao houver."""
    px = img.load()
    pts = [
        (x, y)
        for y in range(0, 150)
        for x in range(0, 256)
        if px[x, y] == STAFF_SEL_RGB
    ]
    if not pts:
        return None
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    if x0 not in STAFF_CELL_X or y0 not in STAFF_CELL_Y:
        return None
    return STAFF_CELL_Y.index(y0), STAFF_CELL_X.index(x0)


def staff_free_cells(img, minimo=10):
    """Celulas de funcionario com cracha = quem esta na base e pode ser enviado."""
    return [
        c for c in STAFF_CELLS
        if count_rgb(img, staff_badge_box(*c), STAFF_BADGE_RGB) >= minimo
    ]


# --- Tela "How many slots?" (r0c2, depois de escolher a cidade) --------------
# CALIBRADO 19/08 (ETAPA 3b-a). A quantidade E ESCOLHIVEL — ate 18/08 a macro
# apertava A e ficava com o padrao (1 slot) sem nunca ter olhado a tela.
# O widget e um MEDIDOR de 5 bonequinhos dentro da caixa de texto: os N
# escolhidos aparecem inteiros, os demais como toco.
#
#   toques de Right | rotulo lido na tela      | px brancos no medidor
#   0               | "1 slot"                 | 215
#   1               | "2 slots"                | 237
#   2               | "3 slots"                | 259
#   3               | "4 slots"                | 281
#   4               | "5 slots"                | 303
#   5,6,7,8         | "5 slots" (NAO da volta) | 303
#
# Evidencia: logs/etapa3b/qR_qty_0..4.png (rotulos lidos a olho, um por um) e
# qR8_qty_0..8.png (teto: hash da TEXTBOX 890f8672 identico nos toques 4..8).
# O hash da TEXTBOX foi conferido ESTAVEL (mesma tela fotografada 2x =
# c43ce532 nas duas), entao "hash mudou" aqui e sinal, nao piscada de seta.
#
# Por que PIXEL e nao OCR: o texto de DIALOGO nao esta na grade 8x13 do §24 —
# screen_text.read_text devolve '??????' na caixa (medido nesta mesma tela).
# O medidor tem geometria fixa e nao depende de letra nenhuma.
SLOTS_GAUGE_BOX = (24, 168, 68, 194)
SLOTS_GAUGE_PX = {215: 1, 237: 2, 259: 3, 281: 4, 303: 5}
SLOTS_MIN = 1
# MEDIDO 25/08: o medidor NAO para em 5. Toronto (NA12) tem 11 posicoes, e a
# tela desenha alem da largura de SLOTS_GAUGE_BOX. Enquanto isto era 5, toda
# negociacao em NA12 falhava com "medidor ilegivel" — 10 recusas seguidas na
# baseline gulosa, que reincidia na mesma cidade.
SLOTS_MAX = 16

# --- ETAPA 1-RegressaoSlots (23/08): a tabela acima ESTAVA ERRADA -----------
# BUG MEDIDO: `negotiate_slots` falhava com "medidor ilegivel" em NA06 (Denver)
# e NA02, mas passava em NA05/NA10/NA14. Causa levantada dos proprios PNGs
# (logs/run_f0/neg_semqtd_NA06.png = 152 px, neg_semqtd_NA02.png = 173 px,
# neg_qtd_NA05_1.png = 215 px), com dump ASCII pixel a pixel:
#
#   O medidor NAO tem 5 posicoes sempre. Ele tem N posicoes, e N MUDA POR
#   CIDADE. Cada posicao e um boneco INTEIRO (escolhido) ou um TOCO (disponivel
#   e nao escolhido). NA05/NA14 -> N=5; NA02 -> N=3; NA06 (Denver) -> N=2.
#
# Como SLOTS_GAUGE_PX so tem a soma total de pixels brancos e foi levantada
# numa unica cidade de N=5, ela e na verdade a formula
#       total = 43*escolhidos + 21*tocos + 88   (88 = as duas molduras)
# avaliada apenas em escolhidos+tocos == 5. Qualquer cidade com N != 5 cai fora
# da tabela e vira None -> "medidor ilegivel". Confere nas 5 telas:
#   NA05_1 (1 inteiro,4 tocos) 43+84+88=215 | NA05_2 (2,3) 86+63+88=237
#   NA14_3 (3,2) 129+42+88=259 | NA02 (1,2) 43+42+88=173 | NA06 (1,1) 43+21+88=152
#
# O QUE FIXA N NAO FOI MEDIDO. Nao e "slots livres no aeroporto": Denver mostra
# "Total slots 24/94" (70 livres) com N=2 e Phoenix "5/53" (48 livres) com N=5.
# Por isso a recusa fala em POSICOES DO MEDIDOR, nunca em "a cidade so oferece
# 2 slots" — descrever o que foi lido, nao inventar a causa (R1).
#
# ARMADILHA MEDIDA (neg_EU11.png = 105 px): o medidor e desenhado de CIMA PARA
# BAIXO, e um frame pego no meio do desenho mostra o primeiro boneco cortado na
# linha 182 e NENHUMA outra posicao. Ler N ai daria N=0/N=1 numa cidade de N=5 —
# sub-leitura silenciosa, exatamente o erro que esta correcao existe para matar.
# Por isso: (a) o leitor exige o boneco/toco INTEIRO, casando o desenho contra
# um gabarito exato, e (b) quem chama exige DUAS leituras iguais consecutivas
# (read_slots_gauge_stable) antes de acreditar.
#
# Geometria (indices absolutos de tela, medidos nos dumps):
#   posicao i: boneco inteiro em x 25+8i..29+8i, linhas 175..190
#              toco       em x 26+8i..30+8i, linhas 185..190
#   moldura da caixa de dialogo: linhas 169,170,194,195 brancas em x 20..79
SLOTS_GAUGE_PITCH = 8
SLOTS_GAUGE_TALL_XY = (25, 175)   # canto do boneco inteiro na posicao 0
SLOTS_GAUGE_STUB_XY = (26, 185)   # canto do toco na posicao 0
SLOTS_GAUGE_FRAME_ROWS = (169, 170, 194, 195)
SLOTS_GAUGE_FRAME_X = (20, 80)
SLOTS_GAUGE_TALL_PX = 43
SLOTS_GAUGE_STUB_PX = 21
SLOTS_GAUGE_FRAME_PX = 88          # pixels brancos da moldura dentro de _BOX

# Gabaritos exatos (dx, dy) a partir do canto de cada figura.
SLOTS_GAUGE_TALL_TPL = frozenset(
    (dx, dy)
    for dy, dxs in enumerate((
        (2, 3), (1, 4), (1, 4), (2, 3), (),
        (1, 2, 3), (1, 3, 4), (1, 3, 4), (1, 3, 4), (2,),
        (0, 1, 3, 4), (0, 1, 2, 3, 4), (0, 1, 2, 3, 4), (0, 1, 2, 3, 4),
        (2,), (2, 3),
    ))
    for dx in dxs
)
SLOTS_GAUGE_STUB_TPL = frozenset(
    (dx, dy)
    for dy, dxs in enumerate((
        (2,), (1, 3), (0, 1, 2, 3, 4), (0, 1, 3, 4), (0, 1, 3, 4),
        (0, 1, 2, 3, 4),
    ))
    for dx in dxs
)


def _slots_gauge_cell(px, i):
    """Classifica a posicao i do medidor: 'tall', 'stub', 'empty' ou None.

    None = nao bate com nenhum gabarito (frame no meio do desenho, tela errada,
    figura nova). NUNCA vira palpite.
    """
    x0 = SLOTS_GAUGE_TALL_XY[0] + SLOTS_GAUGE_PITCH * i
    brancos = {
        (x, y)
        for x in range(x0 - 1, x0 + 6)
        for y in range(SLOTS_GAUGE_TALL_XY[1], SLOTS_GAUGE_STUB_XY[1] + 6)
        if px[x, y] == TEXT_RGB
    }
    if not brancos:
        return "empty"
    tall = {(x0 + dx, SLOTS_GAUGE_TALL_XY[1] + dy) for dx, dy in SLOTS_GAUGE_TALL_TPL}
    if brancos == tall:
        return "tall"
    sx = SLOTS_GAUGE_STUB_XY[0] + SLOTS_GAUGE_PITCH * i
    stub = {(sx + dx, SLOTS_GAUGE_STUB_XY[1] + dy) for dx, dy in SLOTS_GAUGE_STUB_TPL}
    if brancos == stub:
        return "stub"
    return None


def read_slots_gauge(img):
    """(escolhidos, posicoes) do medidor da tela "How many slots?", ou None.

    `posicoes` e o TETO daquela cidade lido da tela — o modelo nao pode pedir
    mais que isso. None = nao reconheci a tela (R1: nunca palpite).
    """
    px = img.load()
    for y in SLOTS_GAUGE_FRAME_ROWS:
        for x in range(*SLOTS_GAUGE_FRAME_X):
            if px[x, y] != TEXT_RGB:
                return None
    # Para na PRIMEIRA posicao vazia: o medidor termina ali, e a direita dele vem
    # o texto "N slot" do dialogo. Varrer alem disso classificava esse texto como
    # figura desconhecida (None) e derrubava a leitura inteira.
    largura = img.size[0]
    celulas = []
    for i in range(SLOTS_MAX):
        if SLOTS_GAUGE_TALL_XY[0] + SLOTS_GAUGE_PITCH * i + 6 >= largura:
            break
        c = _slots_gauge_cell(px, i)
        if c == "empty":
            break
        if c is None:
            return None
        celulas.append(c)
    if not celulas:
        return None
    tall = celulas.count("tall")
    stub = celulas.count("stub")
    # As figuras sao desenhadas da esquerda para a direita: inteiros, depois
    # tocos, depois vazio. Qualquer outra ordem = leitura suspeita.
    if celulas != ["tall"] * tall + ["stub"] * stub:
        return None
    if tall < 1:
        return None
    # Cruzamento independente. A versao anterior somava os pixels de uma CAIXA de
    # largura fixa (44 px, o bastante para 5 posicoes) — com 11 posicoes a soma
    # nunca batia e a tela virava "ilegivel". Aqui a checagem e equivalente mas
    # nao depende da largura: NENHUM pixel branco pode existir na faixa do
    # medidor fora dos gabaritos que casaram. Pega a mesma classe de erro
    # ("tem coisa a mais desenhada") em qualquer numero de posicoes.
    y_ini = SLOTS_GAUGE_TALL_XY[1]
    y_fim = SLOTS_GAUGE_STUB_XY[1] + 6
    x_ini = SLOTS_GAUGE_TALL_XY[0] - 1
    # Ate a ultima posicao OCUPADA, nao ate a ultima varrida: a direita do
    # medidor vem o texto "N slot" do dialogo, branco e na mesma faixa de y.
    x_fim = SLOTS_GAUGE_TALL_XY[0] + SLOTS_GAUGE_PITCH * (tall + stub) + 6
    x_fim = min(x_fim, img.size[0])
    vistos = {(x, y) for x in range(x_ini, x_fim) for y in range(y_ini, y_fim)
              if px[x, y] == TEXT_RGB}
    esperados = set()
    for i, c in enumerate(celulas):
        if c == "tall":
            bx = SLOTS_GAUGE_TALL_XY[0] + SLOTS_GAUGE_PITCH * i
            esperados |= {(bx + dx, SLOTS_GAUGE_TALL_XY[1] + dy)
                          for dx, dy in SLOTS_GAUGE_TALL_TPL}
        elif c == "stub":
            bx = SLOTS_GAUGE_STUB_XY[0] + SLOTS_GAUGE_PITCH * i
            esperados |= {(bx + dx, SLOTS_GAUGE_STUB_XY[1] + dy)
                          for dx, dy in SLOTS_GAUGE_STUB_TPL}
    if vistos != esperados:
        return None
    return tall, tall + stub


def read_slots_qty(img):
    """Quantos slots a tela "How many slots?" esta pedindo, ou None.

    None significa "nao reconheci" — NUNCA um palpite (R1). Serve tambem como
    detector da tela.
    """
    lido = read_slots_gauge(img)
    return None if lido is None else lido[0]


def staff_action_is_bid(img, minimo=100):
    """True = acao de CIMA destacada; False = a de BAIXO; None = ambiguo.

    Serve para as DUAS telas de despacho de funcionario, que compartilham a
    geometria inteira (MEDIDO 17/08, logs/hub2/p2_hub_staff.png):

      | comando            | acao de cima (BID_BOX) | acao de baixo (RETURN_BOX) |
      |--------------------|------------------------|----------------------------|
      | r0c2 negociar      | **Bid** (pedir slots)  | Return (devolver slots)    |
      | r1c0 hub regional  | **Open** (abrir hub)   | Close (fechar hub)         |

    Na tela do hub, recem-aberta: BID_BOX = 343 px de laranja (Open destacado)
    contra 66 px na RETURN_BOX — os mesmos limiares da negociacao valem.
    Em ambas, a acao de baixo e DESTRUTIVA (devolver slots / fechar hub), entao
    quem chama deve abortar quando isto nao for True.
    """
    bid = count_rgb(img, BID_BOX, BID_ON_RGB)
    ret = count_rgb(img, RETURN_BOX, BID_ON_RGB)
    if bid >= minimo and ret < minimo:
        return True
    if ret >= minimo and bid < minimo:
        return False
    return None


# --- HUB REGIONAL (comando r1c0) --------------------------------------------
# MEDIDO 17/08 (probe_hub3.py, de `prova_ic_rota_sa.state`): a tela "Hub Set-up"
# que aparece depois de escolher o funcionario lista o CUSTO na propria tela —
# "Maintenance Expense $1760K / Construction Costs $28800K" — e abaixo a lista
# de cidades candidatas da regiao (as que ja recebem uma rota nossa; com uma
# unica candidata a lista tem so ela, "Havana").
# O caixa cai EXATAMENTE Construction Costs no A que responde a pergunta
# "Shall we open [a hub here]?": 1.166.820K -> 1.138.020K (-28.800K), e o
# numero de funcionarios livres cai de 4 para 3 no mesmo passo.
# A Maintenance Expense e RECORRENTE (linha "Hub Costs" do P&L) — nunca foi
# medida por trimestre, so lida da tela.
HUB_CONSTRUCTION_K = 28800
HUB_MAINTENANCE_K = 1760

# Recusas MEDIDAS do comando (mensagem exata; em todas o jogo fica numa tela de
# MENSAGEM, nao de selecao — sair por tecla e traicoeiro, recarregar e barato):
#   regiao da base        -> "Our home base is here in North America. We don't
#                            need a regional hub."            (logs/hub/hub_NA.png)
#   regiao sem rota nossa -> "We can't open a regional hub in South America. We
#                            don't have any flights going there." (hub_SA2.png)
#   hub ja em negociacao  -> "In South America, preparations for a regional hub
#                            are already underway in Havana."
#                            (logs/action_space_map/r1c0_msgfull.png)

# --- de qual HUB a rota vai partir: lido da propria tela ---------------------
# A caixa de rodape da tela de rota (a mesma TEXTBOX) tem DOIS conteudos
# possiveis, e distingui-los por hash e mais barato e mais seguro que inferir:
#
#   "We don't have a regional hub here."  -> md5 11d9dcad
#       Nao ha hub nosso na regiao EXIBIDA. E uma MENSAGEM: o cursor fica morto
#       e nenhum toque de d-pad passa (foi a causa raiz do "menu inacessivel").
#       Hash MEDIDO em 4 capturas independentes, de regioes diferentes e de
#       sessoes diferentes: logs/run_f0/rota_travada_NA02/NA06/NA14.png (esta
#       ultima na Europa) e logs/hub2/p1_r0c0_regiao1.png (America do Sul,
#       17/08, com a negociacao de hub JA PAGA e em andamento — ou seja, hub
#       pendente ainda NAO abre rota).
#
#   banner com bandeira + nome da cidade de ORIGEM -> md5 b06ced83 para
#       Washington (logs/run_f0/rota_recusada_SA01.png, rota_recusada_EU11.png e
#       logs/action_space_map/rota_recusada_SA01.png — 3 capturas, 2 sessoes).
#       O nome na caixa E a origem escolhida pelo jogo, entao o hash confirma de
#       qual hub a rota parte em vez de deduzir da regiao.
ROUTE_NO_HUB_MD5 = "11d9dcad"
ROUTE_ORIGIN_MD5 = {"b06ced83": "NA13"}  # hash -> cidade de origem (medidos)


def route_banner_md5(img):
    import hashlib

    return hashlib.md5(img.crop(TEXTBOX).tobytes()).hexdigest()[:8]


def route_screen_kind(img):
    """Le a caixa de rodape da tela de rota.

    Devolve ('sem_hub', md5) | ('origem', cidade) | ('desconhecido', md5).
    'desconhecido' NAO e erro: e um banner de origem cujo hash ainda nao foi
    catalogado (cada hub novo traz um). Quem chama decide se isso basta.
    """
    h = route_banner_md5(img)
    if h == ROUTE_NO_HUB_MD5:
        return "sem_hub", h
    if h in ROUTE_ORIGIN_MD5:
        return "origem", ROUTE_ORIGIN_MD5[h]
    return "desconhecido", h


def free_staff_menu(img):
    """Funcionarios livres, lidos dos bonecos do MENU PRINCIPAL."""
    return count_rgb(img, MENU_STAFF_BAR, STAFF_BADGE_RGB) // STAFF_BADGE_PX


# =============================================================================
# ETAPA 1 (OCR-Infra): leitor generico de TABELA para telas de relatorio
# (submenu Info: macros.INFO). Duas telas calibradas OFFLINE a partir de
# logs/prova_ic/{mapa_pos_rota,frota_1rota,frota_2000}.png — nenhuma delas
# tinha 2+ linhas de dado disponivel, entao a geometria vertical ALEM da
# linha 1 (o passo entre linha N e N+1, e quantas linhas cabem na tela) NAO
# foi verificada ao vivo; read_table_rows() nunca finge saber alem do medido:
# para na primeira banda sem nenhum pixel branco.
#
# Duas famílias de campo, no molde ja usado por _ranking_digit_hash/
# RANKING_GLYPHS (Regional Rankings, acima) e por _crop_md5/BUY_PANEL/
# venture_type_hash (identidade de recorte):
#   - "digits"/"digits_pct": hash de glifo por digito (0-9, + '%' como
#     terminador opcional). Digito fora do catalogo -> valor None, NUNCA um
#     palpite (R1).
#   - "name": hash md5 do recorte INTEIRO da celula (largura fixa da coluna,
#     preenchido com fundo se o texto for curto) contra um catalogo
#     AUTO-POPULADO em disco (name_hashes.json). Hash desconhecido -> None +
#     o proprio hash, para quem chamou aprender via learn_table_name() assim
#     que souber o nome verdadeiro por outra via (ex.: acabou de abrir rota
#     para Havana).
# =============================================================================

TABLE_WHITE = RANKING_WHITE  # mesma cor de texto (255, 251, 255), confirmada
                              # nos 3 PNGs desta etapa (mesmo pipeline de fonte)

# Banda vertical (y0,y1) de uma linha de tabela, MEDIDA em mapa_pos_rota.png e
# frota_1rota.png/frota_2000.png (as 3 telas concordam pixel a pixel quando a
# banda usada e a MESMA altura nas duas tabelas — usar alturas diferentes por
# tabela fez o mesmo digito '0' hashear DIFERENTE e foi o primeiro erro desta
# etapa, documentado aqui para nao repetir):
#   cabecalho: y=8..20  (13px)   -> TABLE_HEADER_Y
#   linha 1:   y=24..36 (13px)   -> TABLE_ROW0_Y
#   passo cabecalho->linha1: 24-8 = 16px -> TABLE_ROW_STEP
TABLE_HEADER_Y = (8, 21)
TABLE_ROW0_Y = (24, 37)
TABLE_ROW_STEP = 16
# ATUALIZADO apos varredura em todo logs/ por hash de cabecalho (ver
# _sweep_table_headers no fim do arquivo/CALIBRATION notes): achamos
# logs/probe12/72_rotas_final.png, uma tela real com 4 linhas de dado
# ("NEW Washington San Fran/Seattle/Denver/Phoenix 0%", rodape "4 Rtes").
# read_table_rows() sobre ela devolveu exatamente 4 linhas com o load_pct=0
# batendo nas 4 -> TABLE_ROW_STEP=16 esta CONFIRMADO para linha 2, 3 e 4, nao
# so para header->linha1. As colunas origin/destination continuaram None
# (esperado: linhas nao selecionadas tem hash de fundo diferente do usado
# para calibrar Washington/Havana — ver nota abaixo sobre o catalogo de
# nomes ser implicitamente por ESTADO DE SELECAO, nao so por cidade).
#
# Teto de linhas: DERIVADO da posicao do rodape (footer comeca por volta de
# y=197 nos PNGs desta etapa: "N Rte(s)"/"Plane|Federal" fica em y=200..212),
# nao mais um numero chutado. n tal que TABLE_ROW0_Y[0] + n*TABLE_ROW_STEP +
# (TABLE_ROW0_Y[1]-TABLE_ROW0_Y[0]) <= 197 -> n <= 10 -> 11 linhas (0..10).
# Ainda NAO vimos uma tela com mais de 4 linhas preenchidas, entao linhas
# 5-11 continuam teoricas; read_table_rows() para sozinho na 1a linha vazia
# de qualquer forma, e loga quando o teto e atingido SEM achar linha vazia
# (sinal de possivel truncamento, nunca silencioso).
TABLE_FOOTER_Y0 = 197
TABLE_ROWS_MAX = (TABLE_FOOTER_Y0 - TABLE_ROW0_Y[0]) // TABLE_ROW_STEP + 1  # = 11

# Geometria horizontal das colunas, medida nos PNGs desta etapa (fronteira =
# ponto medio entre o fim de um dado e o inicio do proximo, nao a largura do
# rotulo do cabecalho — nomes de cidade sao mais largos que a palavra "Origin"
# e vazam para dentro do espaco do cabecalho seguinte).
#
# CAVEAT (origin/destination, x=123): a fronteira 123 e o PONTO MEDIO entre
# "Washington" (termina x=118) e "Havana" (comeca x=128) numa unica amostra —
# NAO e uma borda de coluna medida do motor do jogo (o cabecalho "Destination"
# comeca em x=112, mais cedo que 123, entao rotulo de cabecalho e inicio de
# coluna de dado NAO sao a mesma coisa aqui). Um nome de origem mais longo que
# "Washington" (ex. "Los Angeles", "San Francisco") pode ultrapassar x=123 e
# corromper o recorte de AMBAS as colunas (origin fica largo demais, destination
# perde a borda esquerda). 72_rotas_final.png tem "San Fran"/"Seattle" como
# destino e nao deu pra confirmar overflow porque o catalogo de nomes so tem
# Washington/Havana SELECIONADOS (ver caveat de selecao abaixo) — as 4 linhas
# vieram None e os 4 hashes de destination saem DISTINTOS entre si (nenhuma
# colisao observada), o que e evidencia fraca a favor mas nao prova a borda.
TABLE_SPECS = {
    # macros.INFO["map"]==0: "Origin Destination Load"
    # (mapa_pos_rota.png: "NEW Washington Havana 0%", rodape "1 Rte")
    "map": [
        {"name": "origin", "x": (38, 123), "kind": "name"},
        {"name": "destination", "x": (123, 206), "kind": "name"},
        {"name": "load_pct", "x": (206, 250), "kind": "digits_pct"},
    ],
    # macros.INFO["fleet"]==2: "Plane In Use Avail Order"
    # (frota_1rota.png: "MD100 1 5 0"; frota_2000.png: "MD100 0 6 0")
    "fleet": [
        {"name": "plane", "x": (20, 92), "kind": "name"},
        {"name": "in_use", "x": (92, 147), "kind": "digits"},
        {"name": "avail", "x": (147, 195), "kind": "digits"},
        {"name": "order", "x": (195, 250), "kind": "digits"},
    ],
}

# CAVEAT DE SELECAO (name cells): o catalogo hasheia o recorte CRU (RGB, via
# _crop_md5), incluindo o FUNDO da celula. As 3 amostras usadas para semear
# Washington/Havana/MD100 (mapa_pos_rota.png, frota_1rota.png, frota_2000.png)
# tem a UNICA linha em destaque (fundo de "linha selecionada"/cursor). Em
# logs/probe12/72_rotas_final.png (4 linhas, NENHUMA selecionada) os hashes de
# origin/destination saem TODOS diferentes dos catalogados -> value=None nas 4
# linhas, mesmo a primeira sendo "Washington" de novo. Isso falha FECHADO (nunca
# devolve nome errado, R1) mas significa que o catalogo esta implicitamente
# indexado por (nome, estado-de-selecao), nao so por nome. Etapa 2/3 vao
# precisar chamar learn_table_name() de novo para o hash "nao selecionada" de
# cada nome ja visto, na primeira vez que aparecer fora de destaque.

# Catalogo de digitos por hash de glifo (mesmo molde de RANKING_GLYPHS, mas
# NAO compartilha hashes com ele — fonte e posicao de tela sao outras).
# MEDIDO em 4 telas: as 3 desta etapa + logs/probe12/72_rotas_final.png
# (rodape "4 Rtes" deu o digito '4'). Cobre 0, 1, 4, 5, 6 e '%'. Os digitos
# 2,3,7,8,9 NUNCA apareceram numa captura real destas tabelas -> decodificam
# None (R1: nenhum digito e adivinhado). Complete assim que uma captura ao
# vivo trouxer um deles (ver _table_glyph_hash para gerar o hash a incluir).
TABLE_DIGIT_GLYPHS = {
    "f5a9603a1a": "0",
    "769d49eacd": "1",
    "6bd56ac90f": "4",
    "1212981af0": "5",
    "298792a906": "6",
    "3237e7245a": "%",
}

# Rodape "N Rte"/"N Rtes" da tela "map" (fora de TABLE_SPECS — e um contador,
# nao uma tabela). MEDIDO em mapa_pos_rota.png ("1 Rte", digito comeca em
# x=18) e 72_rotas_final.png ("4 Rtes", digito comeca em x=16, largura maior
# pq '4' e mais largo que '1'). O rotulo "Rte(s)" comeca em x=32 nas duas
# amostras -> a banda (0,30) cobre com folga tanto alinhamento a esquerda
# (confirmado nas 2 amostras) quanto um eventual numero de 2 digitos, sem
# tocar no "R" de "Rte".
MAP_FOOTER_Y = (200, 213)
MAP_FOOTER_RTE_X = (0, 30)


def read_map_route_count(img):
    """Le o contador 'N Rte'/'N Rtes' do rodape da tela 'map' (Origin
    Destination Load). Devolve (valor:int|None, hashes:list[str]) — mesmo
    contrato de _decode_table_digits. `img` deve ja estar na tela 'map'."""
    x0, x1 = MAP_FOOTER_RTE_X
    y0, y1 = MAP_FOOTER_Y
    return _decode_table_digits(img, x0, x1, y0, y1)

NAME_HASHES_PATH = pathlib.Path(__file__).parent / "name_hashes.json"


def _table_glyph_hash(img, gx0, gx1, y0, y1):
    """Hash de glifo de digito — mesmo algoritmo de _ranking_digit_hash,
    exposto com nome proprio para quem for calibrar TABLE_DIGIT_GLYPHS."""
    return _ranking_digit_hash(img, gx0, gx1, y0, y1)


def _decode_table_digits(img, x0, x1, y0, y1):
    """Decodifica uma sequencia de digitos (+ '%' opcional, que so serve de
    terminador e nunca entra no valor) na banda (x0,x1,y0,y1).

    Devolve (valor:int|None, hashes:list[str]). valor=None se a banda nao
    tinha nenhum digito OU se qualquer glifo bateu fora de TABLE_DIGIT_GLYPHS
    (glifo novo) — nunca um palpite parcial. `hashes` sempre vem preenchido
    (mesmo com valor None) para depurar/calibrar glifos novos.
    """
    groups = _ranking_col_groups(img, x0, x1, y0, y1)
    digits = []
    hashes = []
    ok = True
    for gx0, gx1 in groups:
        h = _table_glyph_hash(img, gx0, gx1, y0, y1)
        hashes.append(h)
        ch = TABLE_DIGIT_GLYPHS.get(h)
        if ch is None:
            ok = False
            continue
        if ch == "%":
            break
        digits.append(ch)
    if not ok or not digits:
        return None, hashes
    try:
        return int("".join(digits)), hashes
    except ValueError:
        return None, hashes


def _load_name_catalog():
    import json

    if NAME_HASHES_PATH.exists():
        return json.loads(NAME_HASHES_PATH.read_text(encoding="utf-8"))
    return {}


def _save_name_catalog(cat):
    import json

    NAME_HASHES_PATH.write_text(
        json.dumps(cat, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )


def learn_table_name(table, column, name, h):
    """Ensina catalogo hash->nome para TABLE_SPECS[table][coluna==column] e
    PERSISTE em name_hashes.json. `h` e o hash (string) — ja calculado, tipicamente
    lido do campo {"value": None, "hash": h} devolvido por read_table_rows()
    quando o harness, por outra via, sabe o nome verdadeiro daquela celula
    (ex.: acabou de confirmar abertura de rota para "Havana").

    Nunca sobrescreve silenciosamente: hash ja catalogado com OUTRO nome
    levanta ValueError (colisao — investigar antes de aceitar, nunca a
    ultima gravacao vence por acidente)."""
    cat = _load_name_catalog()
    cat.setdefault(table, {}).setdefault(column, {})
    existing = cat[table][column].get(h)
    if existing is not None and existing != name:
        raise ValueError(
            f"colisao de hash em {table}.{column}: catalogo tinha {existing!r}, "
            f"tentando gravar {name!r} para o mesmo hash {h}"
        )
    cat[table][column][h] = name
    _save_name_catalog(cat)
    return cat


def _table_row_y(row_index):
    y0, y1 = TABLE_ROW0_Y
    off = row_index * TABLE_ROW_STEP
    return y0 + off, y1 + off


def read_table_rows(img, table, name_catalog=None):
    """Le uma tela de relatorio tabular (spec em TABLE_SPECS[table]).

    `img` deve ja estar na tela certa (chamador responsavel por navegar,
    tipicamente via macros.Game.info_screen(macros.INFO[table])).

    Devolve uma lista de dicts, uma por linha de dado detectada, na ordem em
    que aparecem na tela. Para de ler na primeira linha cuja banda nao tem
    NENHUM pixel branco (fim da tabela) — ver nota de geometria no topo desta
    secao sobre por que isso e mais honesto que confiar num TABLE_ROWS_MAX.

    Cada campo "digits"/"digits_pct" vem como {"value": int|None, "hashes":
    [...]}. Cada campo "name" vem como {"value": str|None, "hash": "..."} —
    value=None quando o hash da celula nao esta (ainda) no catalogo.

    `name_catalog`: passe um dict ja carregado para evitar reler o disco em
    loop (ex.: lendo N telas seguidas); por padrao le name_hashes.json a
    cada chamada.
    """
    if table not in TABLE_SPECS:
        raise ValueError(f"tabela desconhecida: {table!r} (esperado um de {list(TABLE_SPECS)})")
    cols = TABLE_SPECS[table]
    catalog = name_catalog if name_catalog is not None else _load_name_catalog()
    table_x0 = min(c["x"][0] for c in cols)
    table_x1 = max(c["x"][1] for c in cols)
    px = img.load()
    img_h = img.size[1]

    rows = []
    for row_index in range(TABLE_ROWS_MAX):
        y0, y1 = _table_row_y(row_index)
        if y1 > img_h:
            break
        has_any = any(
            px[x, y] == TABLE_WHITE
            for y in range(y0, y1)
            for x in range(table_x0, table_x1)
        )
        if not has_any:
            break
        row = {}
        for col in cols:
            x0, x1 = col["x"]
            if col["kind"] in ("digits", "digits_pct"):
                value, hashes = _decode_table_digits(img, x0, x1, y0, y1)
                row[col["name"]] = {"value": value, "hashes": hashes}
            elif col["kind"] == "name":
                h = _crop_md5(img, (x0, y0, x1, y1))
                value = catalog.get(table, {}).get(col["name"], {}).get(h)
                row[col["name"]] = {"value": value, "hash": h}
            else:
                raise ValueError(f"kind desconhecido: {col['kind']!r}")
        rows.append(row)
    else:
        # o for esgotou TABLE_ROWS_MAX sem NUNCA achar uma linha vazia —
        # ou a tabela tem mais linhas do que cabem na tela medida (rolagem
        # nao contemplada) ou a geometria esta errada. Nao inventa um corte
        # silencioso: avisa alto, porque quem chama pode estar contando
        # linhas (ex.: Etapa 2/3 comparando com read_map_route_count()).
        import warnings

        warnings.warn(
            f"read_table_rows({table!r}): atingiu TABLE_ROWS_MAX={TABLE_ROWS_MAX} "
            "sem achar linha vazia — resultado pode estar truncado (rolagem de "
            "tela nao suportada nesta etapa)."
        )
    return rows


# --- TABELAS DE RELATORIO (Info->map, Info->fleet) ---------------------------
# Geometria MEDIDA 18/08 nos PNGs ja em disco (logs/prova_ic/mapa_pos_rota.png e
# frota_1rota.png, mais logs/buy/frota_depois_A340.png para a 2a linha):
# celula de 8x13 alinhada a grade, linhas em y = 8 + 16*i. Ver screen_text.py.
#
# ROTA vs RAM: a etapa anterior tentou achar frota na RAM e travou (In Use ficou
# com 156 candidatos). Estas tabelas mostram tudo na tela; le-se a tela.

import screen_text as _st

# Info->map: | Origin | Destination | Load |
ROUTE_COL_ORIGIN = (40, 120)
ROUTE_COL_DEST = (120, 208)
ROUTE_COL_LOAD = (208, 248)
# Info->fleet: | Plane | In Use | Avail | Order |
FLEET_COL_NAME = (16, 96)
FLEET_COL_IN_USE = (96, 152)
FLEET_COL_AVAIL = (152, 200)
FLEET_COL_ORDER = (200, 248)
# Rodape comum: "<N> Rte" a esquerda, "<Empresa>" e "$<caixa>K" a direita.
FOOTER_ROW = 200
FOOTER_COL_RTE = (16, 32)
FOOTER_COL_CASH = (176, 248)
MAX_TABLE_ROWS = 11          # (FOOTER_ROW - primeira linha) // ROW_PITCH


def _table_rows(img, cols, max_rows=MAX_TABLE_ROWS):
    """Itera as linhas de dados ate a primeira VAZIA.

    Parar na primeira vazia (e nao varrer as 11) evita inventar linha a partir
    de resto de render; o chamador confere o total contra o contador do rodape.
    """
    out = []
    for i in range(1, max_rows + 1):
        y = _st.row_y(i)
        if y + _st.CELL_H > FOOTER_ROW:
            break
        campos = {k: _st.read_text(img, y, a, b) for k, (a, b) in cols.items()}
        if not any(campos.values()):
            break
        out.append((y, campos))
    return out


def read_footer_rte(img):
    """Quantas rotas o JOGO diz que existem — o cheque de sanidade da leitura."""
    return _st.read_int(img, FOOTER_ROW, *FOOTER_COL_RTE)


def read_footer_cash_k(img):
    return _st.read_int(img, FOOTER_ROW, *FOOTER_COL_CASH)


ROUTE_TABLE_HEADER = "OriginDestinationLoad"


def on_route_table(img):
    """A tela mostrada e a TABELA de rotas (e nao o mapa-mundi)?

    MEDIDO 18/08: `Info->map` tem DUAS telas. Com rotas abertas aparece a tabela
    `Origin | Destination | Load`; com ZERO rotas aparece o mapa-mundi com os
    slots por cidade. A mesma navegacao leva a telas diferentes, entao o leitor
    precisa saber onde caiu — senao ele leria o mapa e reportaria "0 rotas",
    que e indistinguivel de "abri a tela errada".
    """
    h = _st.read_text(img, _st.row_y(0), 0, 256).replace(" ", "")
    return ROUTE_TABLE_HEADER in h


def read_routes(img):
    """Tabela de rotas de Info->map.

    Devolve (rotas, n_rte). Cada rota: {origin, dest, load_pct}. `load_pct` e
    None quando a celula nao decodifica (glifo fora do atlas) — nunca chuta.
    `n_rte` e o contador do rodape: se len(rotas) != n_rte a LEITURA esta errada
    (linha perdida ou linha inventada) e o chamador deve tratar como falha, nao
    como "achei menos rotas".

    Devolve `(None, None)` quando a tela exibida NAO e a tabela — ver
    `on_route_table`. Isso e diferente de `([], 0)`, que seria "a tabela existe e
    esta vazia". NAO FOI MEDIDO ainda se a tabela chega a existir vazia; ate la,
    tratar `(None, None)` como "nao lido" e nao como "sem rotas".
    """
    if not on_route_table(img):
        return None, None
    rotas = []
    for y, campos in _table_rows(img, {"origin": ROUTE_COL_ORIGIN, "dest": ROUTE_COL_DEST}):
        rotas.append({
            "origin": campos["origin"] or None,
            "dest": campos["dest"] or None,
            "load_pct": _st.read_int(img, y, *ROUTE_COL_LOAD),
        })
    return rotas, read_footer_rte(img)


def read_fleet(img):
    """Tabela de frota de Info->fleet.

    Devolve lista de {model, in_use, avail, order}. A ORDEM das linhas importa:
    foi medido (INVENTARIO §14.7) que ela e a mesma ordem do `aircraft_index` na
    tela de criacao de rota — quem escolher aviao por indice depende disso.
    """
    frota = []
    for y, campos in _table_rows(img, {"model": FLEET_COL_NAME}):
        frota.append({
            "model": campos["model"] or None,
            "in_use": _st.read_int(img, y, *FLEET_COL_IN_USE),
            "avail": _st.read_int(img, y, *FLEET_COL_AVAIL),
            "order": _st.read_int(img, y, *FLEET_COL_ORDER),
        })
    return frota


# --- ADVERSARIOS: legenda de companhias na tela Regional Rankings ------------
# REGRA DE PROJETO (19/08, apontada pelo usuario): os nomes e as cores das
# companhias NAO sao fixos. Mudam com o cenario, e a companhia do jogador e
# escolhida no inicio da partida. Portanto:
#   - nunca chumbar "Federal/MetLink/AirRoma/Aussie" nem a paleta;
#   - nunca assumir QUANTAS companhias existem;
#   - nunca assumir que a posicao na legenda identifica a companhia (a ordem
#     muda entre trimestres — ela e DADO, provavelmente colocacao, nao rotulo).
# O que e estavel: a estrutura (uma linha por companhia, nome + cor propria) e o
# RODAPE das telas de tabela, que traz o nome da NOSSA companhia. E por ele que
# se descobre quem somos, em vez de supor.

FOOTER_COL_COMPANY = (64, 176)
LEGEND_X = (96, 184)
RANK_BG = {(57, 75, 173), (41, 40, 74), (0, 0, 0)}


def read_our_company(img):
    """Nome da NOSSA companhia, lido do rodape. None se ilegivel."""
    nome = _st.read_text(img, FOOTER_ROW, *FOOTER_COL_COMPANY)
    return nome or None


def _dominant_color(img, y0, x0, x1, ignorar=()):
    from collections import Counter
    px = img.load()
    c = Counter(px[x, y] for x in range(x0, x1) for y in range(y0, y0 + _st.CELL_H)
                if px[x, y] not in RANK_BG and px[x, y] not in ignorar)
    return c.most_common(1)[0][0] if c else None


def read_rankings_legend(img):
    """Legenda da tela Regional Rankings: [{nome, cor, linha}] na ordem exibida.

    O nome sai do REALCE BRANCO do texto (o mesmo atlas das tabelas — medido
    19/08: `Federal`/`MetLink`/`AirRoma`/`Aussie` decodificam assim), e a cor e
    a dominante da linha excluindo o branco e o fundo. Assim o mapa
    companhia->cor vem DO PROPRIO FRAME, sem paleta chumbada — que e o unico
    jeito de sobreviver a cenarios com outros nomes e outras cores.

    A ordem e devolvida como veio: `linha` e o indice exibido, nao identidade.
    """
    x0, x1 = LEGEND_X
    out = []
    for i, y0 in enumerate(range(_st.GRID_Y0, FOOTER_ROW + _st.ROW_PITCH, _st.ROW_PITCH)):
        if y0 + _st.CELL_H > img.size[1]:
            break
        nome = _st.read_text(img, y0, x0, x1)
        if not nome or _st.UNKNOWN in nome:
            continue
        cor = _dominant_color(img, y0, x0, x1, ignorar=(_st.WHITE,))
        if cor is None:
            continue
        out.append({"nome": nome, "cor": cor, "linha": i})
    # O TITULO da tela ("Regional Rankings <ano>") atravessa a faixa x da legenda
    # e entrava na lista como se fosse companhia. O filtro e ESTRUTURAL, nao por
    # nome: a legenda e um bloco de linhas CONSECUTIVAS no rodape da tela, e o
    # titulo fica isolado la em cima. Filtrar por texto ("ignore 'Rankings'")
    # quebraria no primeiro cenario com outro idioma ou outro titulo.
    if not out:
        return out
    blocos, atual = [], [out[0]]
    for item in out[1:]:
        if item["linha"] == atual[-1]["linha"] + 1:
            atual.append(item)
        else:
            blocos.append(atual)
            atual = [item]
    blocos.append(atual)
    return max(blocos, key=lambda b: (len(b), b[-1]["linha"]))


# --- ADVERSARIOS: quem lidera cada regiao ------------------------------------
# MEDIDO 19/08 (ETAPA 1b-Adversarios) nos DOIS unicos frames de Regional
# Rankings existentes (logs/rankings_probe/y1_region0_A.png = Apr2000 e
# y2_region0_A.png = Jul2000), por deteccao de retangulo PRETO (sem palpite de
# grade): as 7 caixas de regiao sao 64x32 px, nas MESMAS coordenadas nos dois
# frames. A estrutura de cada caixa:
#
#   linhas  0..7   faixa de cabecalho: PREENCHIDA com a cor da companhia que
#                  lidera a regiao, com os digitos brancos por cima
#   linhas  8..31  corpo, sempre preto
#
# Caixa SEM dado = 32 linhas pretas (nao existe faixa colorida). Foi assim que
# as 5 regioes sem trafego apareceram nos dois frames.
#
# Isto tambem explica o `RANKING_ROW_OFFSET` do §ETAPA 8 (-8 e -9): a faixa de
# digitos e o cabecalho da caixa, e os "offsets negativos" eram a distancia da
# aproximacao antiga (`REGIONAL_RANKINGS_BOXES`, medida em grade de 4px) ate o
# topo real da celula. As coordenadas abaixo sao as reais.
#
# NAO CHUMBAR COR (R3): a cor da faixa so vira nome via `read_rankings_legend`,
# lida do MESMO frame. Cor que nao case EXATAMENTE com nenhuma da legenda vira
# None — nunca a mais parecida.
REGIONAL_RANKINGS_CELLS = {
    "Europe": (24, 39),
    "N America": (168, 39),
    "SE Asia": (96, 55),
    "Mid East": (56, 111),
    "Oceania": (136, 111),
    "Africa": (16, 167),
    "S America": (176, 167),
}
RANK_CELL_W, RANK_CELL_H = 64, 32
RANK_HEADER_H = 8           # altura da faixa colorida (o resto do corpo e preto)
RANK_FILL_MIN = 0.5         # fracao minima da faixa na cor do lider


def _rank_cell_shape(img, x0, y0):
    """Classifica a caixa de uma regiao pela ESTRUTURA, nao pela cor.

    Devolve 'vazia' (32 linhas pretas = sem dado), 'com_dado' (faixa de 8
    linhas + 24 linhas pretas) ou None (nao e uma caixa de ranking — serve
    tambem como cheque de "abri a tela errada").
    """
    px = img.load()
    if x0 + RANK_CELL_W > img.size[0] or y0 + RANK_CELL_H > img.size[1]:
        return None
    pretas = [
        all(px[x, y] == (0, 0, 0) for x in range(x0, x0 + RANK_CELL_W))
        for y in range(y0, y0 + RANK_CELL_H)
    ]
    if all(pretas):
        return "vazia"
    if not any(pretas[:RANK_HEADER_H]) and all(pretas[RANK_HEADER_H:]):
        return "com_dado"
    return None


def _rank_header_fill(img, x0, y0):
    """Cor dominante da faixa de cabecalho, ignorando SO o branco dos digitos.

    Ignorar tambem o fundo (como `_dominant_color` faz) seria perigoso aqui:
    uma faixa que fosse quase toda fundo devolveria a 4a cor mais comum, que
    poderia casar com a legenda por acidente. Ignorando so o branco, faixa sem
    preenchimento devolve a cor de fundo, que nao casa com companhia nenhuma —
    a resposta honesta.

    Devolve (cor, fracao) ou (None, 0.0).
    """
    from collections import Counter
    px = img.load()
    c = Counter(
        px[x, y]
        for y in range(y0, y0 + RANK_HEADER_H)
        for x in range(x0, x0 + RANK_CELL_W)
        if px[x, y] != _st.WHITE
    )
    if not c:
        return None, 0.0
    cor, n = c.most_common(1)[0]
    return cor, n / float(sum(c.values()))


def read_regional_leaders(img, legenda=None):
    """{regiao: nome_da_companhia | None} — quem lidera cada regiao.

    None significa SEMPRE "nao sei", nunca "ninguem": caixa sem dado, caixa com
    estrutura inesperada, faixa sem cor dominante clara, ou cor que nao casa
    EXATAMENTE com uma (e so uma) entrada da legenda do proprio frame.

    Se duas companhias da legenda tiverem a mesma cor, o casamento seria
    ambiguo e TUDO devolve None — preferivel a atribuir lider errado.
    """
    if legenda is None:
        legenda = read_rankings_legend(img)
    por_cor = {}
    for e in legenda:
        por_cor.setdefault(e["cor"], []).append(e["nome"])
    ambiguo = any(len(v) > 1 for v in por_cor.values())
    out = {}
    for regiao in REGIONAL_RANKINGS_REGIONS:
        x0, y0 = REGIONAL_RANKINGS_CELLS[regiao]
        forma = _rank_cell_shape(img, x0, y0)
        if forma != "com_dado" or ambiguo:
            out[regiao] = None
            continue
        cor, frac = _rank_header_fill(img, x0, y0)
        if cor is None or frac < RANK_FILL_MIN:
            out[regiao] = None
            continue
        nomes = por_cor.get(cor)
        out[regiao] = nomes[0] if nomes and len(nomes) == 1 else None
    return out


def read_rivals(img, img_tabela=None, nos=None):
    """Retrato dos adversarios a partir do frame de Regional Rankings.

    - `legenda`: [{nome, cor, linha}] na ordem exibida (posicao = DADO, nao
      identidade — a ordem muda entre trimestres).
    - `lideres`: {regiao: nome|None} (ver `read_regional_leaders`).
    - `numeros`: {regiao: int|None} (`read_regional_rankings`; so N America e
      Oceania tem catalogo de digitos hoje).
    - `nos`: nome da NOSSA companhia. MEDIDO 19/08: NAO da para tira-lo do
      frame de ranking. `read_our_company` le a linha y=200, que nessa tela e a
      ULTIMA LINHA DA LEGENDA — nos dois frames capturados ela devolveu nomes
      DIFERENTES (AirRoma em Apr2000, Federal em Jul2000) porque a legenda
      reordena. Ela so e valida em tela de TABELA (Info->map / Info->fleet),
      onde o rodape traz mesmo a nossa companhia (verificado: 'Federal' em
      logs/prova_ic/mapa_pos_rota.png e frota_1rota.png). Por isso: passe
      `nos=` ou um `img_tabela` de tela de tabela. Sem isso, `nos` vem None e
      `nos_fonte` diz o porque — jamais a ultima linha da legenda.
    """
    legenda = read_rankings_legend(img)
    fonte = "argumento"
    if nos is None and img_tabela is not None:
        lido = read_our_company(img_tabela)
        if lido and _st.UNKNOWN not in lido:
            nos, fonte = lido, "rodape_tabela"
        else:
            fonte = "indisponivel: rodape da img_tabela ilegivel"
    elif nos is None:
        fonte = "indisponivel: sem img_tabela nem nos= (o rodape do ranking e legenda, nao identidade)"
    return {
        "legenda": legenda,
        "lideres": read_regional_leaders(img, legenda),
        "numeros": read_regional_rankings(img),
        "nos": nos,
        "nos_fonte": fonte,
    }


# --- DETECTOR ESTRUTURAL das duas telas do Info->finance (19/08) --------------
# MEDIDO 19/08 AO VIVO: `on_quarterly_report_img` (pixel (10,40) teal) devolveu
# False num Quarterly Report REAL (`logs/lideres_19ago/finance_00.png`, Q191) —
# aquele pixel cai sobre as BARRAS do grafico, cuja altura muda com o resultado
# do trimestre. Detector por pixel de barra e detector por sorte.
#
# O que e estrutural: a tela de Regional Rankings tem as 7 caixas de regiao
# (64x32, coordenadas de REGIONAL_RANKINGS_CELLS) e o Quarterly Report nao tem
# NENHUMA. Testado nos 4 frames disponiveis (2 de cada) — ver §29.
def rankings_cells_present(img):
    """Gate FROUXO: as 7 caixas existem, mas a tela pode ainda estar desenhando.

    Serve so para "candidato a tela de ranking" durante a cadeia de fim de
    turno: quem varre a cadeia precisa PARAR ali e esperar assentar. Ler com
    este gate e proibido — use `rankings_cells_ok` (que tambem exige legenda).
    """
    # O fundo importa: MEDIDO 19/08, a cadeia de fim de turno passa por um
    # frame 100% PRETO (57344 px) e nele TODAS as 7 caixas classificam como
    # "vazia" — tela preta virava "tela de ranking sem lider nenhum". O fundo
    # azul do relatorio e o que separa a tela real do fade.
    # O teste e por VOLUME de fundo, nao por um pixel: (0,0) e justamente a
    # linha do titulo, e detector de um pixel so foi o que quebrou em §29.1.
    # Medido: y1/y2 tem dezenas de milhares de px de fundo entre as caixas; o
    # frame do fade tem ZERO.
    px = img.load()
    fundo = sum(1 for y in range(0, img.size[1], 2) for x in range(0, img.size[0], 2)
                if px[x, y] == REGIONAL_RANKINGS_BG)
    if fundo < 500:
        return False
    return all(_rank_cell_shape(img, *REGIONAL_RANKINGS_CELLS[r]) in ("vazia", "com_dado")
               for r in REGIONAL_RANKINGS_REGIONS)


def rankings_cells_ok(img):
    """Gate da tela de Regional Rankings: as 7 caixas + a legenda DESENHADAS.

    A clausula da legenda nao e enfeite — e correcao de um falso positivo
    MEDIDO 19/08 ao vivo: no passo 6 da cadeia de fim de turno a tela ja tinha
    as 7 caixas (todas pretas) e legenda VAZIA, porque ainda nao terminara de
    desenhar. So as caixas bastariam para `read_regional_leaders` devolver
    tudo `None`, que se le como "ninguem lidera nada" quando a verdade e "a
    tela nao estava pronta" (o mesmo modo de falha do §25).
    """
    if not rankings_cells_present(img):
        return False
    return bool(read_rankings_legend(img))


import re as _re

QR_MONEY_RE = _re.compile(r"^\$\d+K$")


def on_quarterly_report_img2(img):
    """Quarterly Report pela ESTRUTURA, sem usar altura de barra.

    Tres condicoes, todas medidas: fundo de tela de relatorio; NAO tem as 7
    caixas de regiao (senao seria o ranking); e pelo menos 2 linhas de dados
    (fora o rodape) sao rotulos de dinheiro `$NNNK` das barras. A terceira
    condicao existe porque sem ela as telas de TABELA (Info->map/fleet), que
    tem o mesmo fundo, davam falso positivo — e falso positivo aqui autoriza um
    `A` na tela errada, exatamente o que custou $276.000K (R2).
    """
    if img.load()[(0, 0)] != REGIONAL_RANKINGS_BG or rankings_cells_ok(img):
        return False
    n = sum(1 for i in range(12)
            if QR_MONEY_RE.match(_st.read_text(img, _st.row_y(i), 0, 256).replace(" ", "")))
    return n >= 2


import hashlib as _hashlib
import json as _json
import pathlib as _pathlib

# ===================== P&L trimestral (ETAPA 1c) ==========================
# A tela "Quarterly Report" (Info->finance, a PRIMEIRA, antes do Regional
# Rankings) usa DUAS fontes diferentes, e essa e a descoberta que a etapa
# custou (medida 19/08 em logs/logs/rank_t1.png e logs/lideres_19ago/
# finance_00.png):
#
#   * os VALORES ($NNNK) sao a fonte de tabela do §24 — celula 8x13 na grade,
#     tinta branca (255,251,255). O leitor generico ja servia.
#   * os ROTULOS ("Airline Sales", ...) NAO estao nessa grade: sao uma fonte
#     PROPORCIONAL de 1..7 px de largura, ~10 px de altura, tinta
#     (239,235,239), comecando em x=10 e fora de qualquer multiplo de 8.
#     A premissa "as linhas estao na grade 8x13 do atlas" so vale para a
#     metade direita da tela.
#
# Por isso existe um SEGUNDO atlas (`glyphs_label.json`), com sua propria
# segmentacao. Ele NAO compartilha namespace com `glyphs.json`: os hashes aqui
# sao sobre segmentos de largura variavel, os de la sobre celulas de 8 px.
LABEL_INK = (239, 235, 239)     # medido: tinta dos rotulos (o valor usa 255,251,255)
LABEL_BAND_H = 16               # a linha inteira; cobre o descendente de 'g'/'p' (medido y0+13)
LABEL_MIN_GAP_SPACE = 3         # medido: entre letras o vao e 1 ou 2 px; entre palavras, 6
PNL_LABEL_X = (0, 96)           # medido: rotulo comeca em x=10 e termina antes do valor
PNL_VALUE_X = 96                # medido: o '$' do valor cai exatamente em x=96 nos 2 frames

LABEL_ATLAS_PATH = _pathlib.Path(__file__).parent / "glyphs_label.json"


def _load_label_atlas():
    if LABEL_ATLAS_PATH.exists():
        return _json.loads(LABEL_ATLAS_PATH.read_text(encoding="utf-8"))
    return {}


LABEL_GLYPHS = _load_label_atlas()


def _label_segments(img, y0, x0=PNL_LABEL_X[0], x1=PNL_LABEL_X[1]):
    """Colunas com tinta de rotulo agrupadas em segmentos contiguos.

    Fonte proporcional: nao da para fatiar por celula fixa. O vao entre letras
    e de 1-2 px e entre palavras de 6 px (medido nas 10 linhas dos 2 frames),
    entao `LABEL_MIN_GAP_SPACE` separa palavra de letra.
    """
    px = img.load()
    tinta = [any(px[x, y] == LABEL_INK for y in range(y0, y0 + LABEL_BAND_H))
             for x in range(x0, x1)]
    segs, i = [], 0
    while i < len(tinta):
        if tinta[i]:
            j = i
            while j < len(tinta) and tinta[j]:
                j += 1
            segs.append((x0 + i, x0 + j))
            i = j
        else:
            i += 1
    return segs


def _label_glyph_hash(img, a, b, y0):
    px = img.load()
    bits = "".join("1" if px[x, y] == LABEL_INK else "0"
                   for y in range(y0, y0 + LABEL_BAND_H) for x in range(a, b))
    # a largura entra no hash: sem ela dois glifos de larguras diferentes
    # poderiam colidir por acidente de bits.
    return _hashlib.md5(f"{b - a}:{bits}".encode()).hexdigest()[:10]


def read_label(img, y0, x0=PNL_LABEL_X[0], x1=PNL_LABEL_X[1], atlas=None):
    """Texto do rotulo da linha que comeca em y0. Glifo fora do atlas vira '?'.

    Nunca adivinha (R1): um rotulo errado faria o modelo atribuir o dinheiro a
    outra rubrica. Falha visivel ('?') e melhor que numero bem-arrumado na
    linha errada.
    """
    atlas = atlas if atlas is not None else LABEL_GLYPHS
    segs = _label_segments(img, y0, x0, x1)
    if not segs:
        return ""
    out = []
    anterior = None
    for (a, b) in segs:
        if anterior is not None and a - anterior >= LABEL_MIN_GAP_SPACE:
            out.append(" ")
        out.append(atlas.get(_label_glyph_hash(img, a, b, y0), _st.UNKNOWN))
        anterior = b
    return "".join(out).strip()


def label_unknown_glyphs(img, y0, x0=PNL_LABEL_X[0], x1=PNL_LABEL_X[1]):
    """Segmentos cujo glifo nao esta no atlas de rotulo — alimenta o rotulador."""
    fora = {}
    for (a, b) in _label_segments(img, y0, x0, x1):
        h = _label_glyph_hash(img, a, b, y0)
        if h not in LABEL_GLYPHS:
            fora[h] = (a, b, y0)
    return fora


def _pnl_value_k(img, y0):
    """Valor da linha, ou None. Exige o '$' EXATAMENTE em x=PNL_VALUE_X.

    Sem essa exigencia o RODAPE entra na varredura: ele tambem casa `$NNNK`,
    so que com o dinheiro alinhado a direita. Confundir caixa total com uma
    rubrica do trimestre seria o pior erro possivel nesta tela.
    """
    px = img.load()
    if _st.read_cell(px, PNL_VALUE_X, y0) != "$":
        return None, None
    bruto = _st.read_text(img, y0, PNL_VALUE_X, img.size[0])
    if not _PNL_MONEY_RE.match(bruto.replace(" ", "")):
        return None, bruto
    return _st.read_int(img, y0, PNL_VALUE_X, img.size[0]), bruto


_PNL_MONEY_RE = _re.compile(r"^\$\d+K$")


def pnl_rows(img):
    """Linhas de dinheiro da tela, DERIVADAS do frame (nao de uma lista de y fixa).

    Devolve [(y, rotulo, valor_k)] de cima para baixo. As 10 linhas dos frames
    conhecidos caem em y = 8,24,48,64,88,104,120,144,160,176 — os vaos de 8 px
    entre os grupos sao por isso que a varredura anda de 8 em 8 e nao de 16.
    Chumbar essa lista faria o leitor errar caladamente num cenario com outro
    numero de rubricas.
    """
    out = []
    for y in range(0, img.size[1] - _st.CELL_H, 8):
        valor, bruto = _pnl_value_k(img, y)
        if bruto is None:
            continue
        out.append((y, read_label(img, y), valor))
    return out


def read_pnl(img):
    """P&L do trimestre: {rotulo_lido: valor_k|None}. `None` se nao for a tela.

    Diferenca proposital entre os dois "nada":
      * `None`  = nao estamos no Quarterly Report (guard reprovou);
      * `{}`    = e a tela, mas nenhuma linha de dinheiro foi lida.
    "Tudo zero" DEPOIS de rotas operando seria sinal de leitura errada, nao de
    empresa parada — por isso o guard estrutural (§29.1) vem antes.
    """
    if not on_quarterly_report_img2(img):
        return None
    return {rot: val for _, rot, val in pnl_rows(img)}


# --- ETAPA 3a: as DUAS telas do fluxo de rota que o executor bumpava as cegas --
# (aircraft_index e planes). Tudo aqui foi MEDIDO em 19/08 no savestate
# eval_single_2000_lv5 (frota: MD100 x6 disponiveis) e em _buy_entregue
# (MD100 x6 + A340 x1). Logs: logs/etapa3a/.
#
# TELA 1 — "What type of plane will you use on the route?"
#   O atlas PRINCIPAL (glyphs.json) le esta tela: o NOME do modelo esta na
#   linha y=80, x=8..64 ("MD100"), o alcance em y=32 (4680) e os assentos em
#   y=48 (200). PREMISSA DA ETAPA DERRUBADA: `buy_panel_hash`/AIRCRAFT_CATALOG
#   NAO identificam o modelo aqui — o recorte BUY_PANEL e do SHOWROOM e nesta
#   tela hasheia 72406d20, que nao existe no catalogo. Ler o nome (e conferir o
#   alcance contra AIRCRAFT_CATALOG[modelo]["range_mi"]) e o caminho medido.
PLANE_MODEL_ROW = 80
PLANE_MODEL_COL = (8, 64)
PLANE_RANGE_ROW = 32
PLANE_SEATS_ROW = 48
PLANE_NUM_COL = (200, 248)


def read_route_plane(img):
    """(nome_bruto, alcance_mi, assentos) da tela de escolha de aviao.

    `nome_bruto` sai do atlas principal e pode conter '?': MEDIDO 19/08 que o
    jogo desenha um SIMBOLO grafico (um circulo, hash 0982a68abb) logo depois
    do nome — "A340" e lido como "A340?". Truncar no '?' seria palpite sobre
    onde o nome acaba (B747-400 tem 8 caracteres), entao o bruto vai como esta
    e quem identifica o modelo e `identify_route_plane`, por NUMERO.
    """
    return (_st.read_text(img, PLANE_MODEL_ROW, *PLANE_MODEL_COL) or None,
            _st.read_int(img, PLANE_RANGE_ROW, *PLANE_NUM_COL),
            _st.read_int(img, PLANE_SEATS_ROW, *PLANE_NUM_COL))


def identify_route_plane(img):
    """Modelo do catalogo exibido na tela de aviao, ou None. Identidade por NUMERO.

    Casa alcance E assentos contra AIRCRAFT_CATALOG (digitos vem do atlas ja
    provado). Se dois modelos casassem, devolve None em vez de escolher um —
    hoje o par (alcance, assentos) e unico nos 8 do catalogo. O nome escrito
    serve de confirmacao quando legivel, nunca de identidade sozinho: o simbolo
    grafico ao lado dele quebra a comparacao por string.
    """
    nome, alcance, assentos = read_route_plane(img)
    if alcance is None or assentos is None:
        return None
    cand = [m for m, d in AIRCRAFT_CATALOG.items()
            if d["range_mi"] == alcance and d["seats"] == assentos]
    return cand[0] if len(cand) == 1 else None


# TELA 2 — "How many planes will be used on this route?"
#   A quantidade aparece como "x N" ao lado do modelo, numa fonte PEQUENA de 7
#   linhas que NAO esta no atlas principal (o atlas e de celula 8x13 alinhada a
#   grade; este texto fica em y=95, fora da grade de 16). Por isso um segundo
#   mini-atlas, rotulado a MAO a partir da arte ASCII dos glifos
#   (logs/etapa3a/planes_right_*.png e seq_qty_*.png).
#   O "x" (multiplicacao) tem hash proprio e serve de guard: sem ele, a tela
#   exibida nao e a da quantidade e a leitura devolve None em vez de chutar.
QTY_GLYPH_Y = 95
QTY_GLYPH_H = 7
QTY_MULT_X = 112
QTY_DIGIT_X = 120
QTY_MULT_MD5 = "8d85d3c671"
QTY_DIGIT_MD5 = {
    "77d927b0ef": 1,
    "bf8ccc55dc": 2,
    "46b0d4a5c9": 3,
    "514f44595a": 4,
    "379f6230c5": 5,
    "94b46c2aa2": 6,
}
# LIMITE HONESTO: so foram OBSERVADOS os digitos 1..6, porque o teto medido da
# tela e o numero de unidades DISPONIVEIS do modelo (6 MD100 no savestate).
# Numero de dois digitos nunca apareceu; se aparecer, o leitor devolve None.

# A "piscina" de avioes livres do modelo aparece na caixinha a esquerda, essa
# sim na fonte grande do atlas principal: y=128, x=32..56. MEDIDO: ela e
# `disponiveis - selecionados` (6->5 com 1 aviao, 0 com 6).
QTY_POOL_ROW = 128
QTY_POOL_COL = (32, 56)


def _small_cell_md5(img, cx, y0=QTY_GLYPH_Y, h=QTY_GLYPH_H, w=_st.CELL_W):
    import hashlib
    px = img.load()
    bits = "".join("1" if px[x, y] == _st.WHITE else "0"
                   for y in range(y0, y0 + h) for x in range(cx, cx + w))
    if bits.count("1") < _st.MIN_INK:
        return None
    return hashlib.md5(bits.encode()).hexdigest()[:10]


def on_route_qty_screen(img):
    """True quando a tela exibida e a da QUANTIDADE de avioes da rota."""
    return _small_cell_md5(img, QTY_MULT_X) == QTY_MULT_MD5


def read_route_planes(img):
    """Quantos avioes a tela mostra ("x N"). None se nao der para LER.

    None cobre tres casos diferentes de proposito — nenhum deles vira palpite:
    nao e a tela da quantidade, o digito esta fora do mini-atlas, ou o numero
    tem mais de um digito (nunca observado).
    """
    if not on_route_qty_screen(img):
        return None
    return QTY_DIGIT_MD5.get(_small_cell_md5(img, QTY_DIGIT_X))


def read_route_planes_pool(img):
    """Avioes do modelo que sobram fora da rota (sinal independente do "x N")."""
    return _st.read_int(img, QTY_POOL_ROW, *QTY_POOL_COL)


# ======================================================================
# ETAPA 5b — PAINEL DE CIDADE (fluxo de negociacao r0c2)  [CALIBRATION §33/§34]
# ======================================================================
# A tela e o painel de detalhe que aparece depois de UM `A` com o cursor sobre a
# cidade, dentro do fluxo `negotiate` (r0c2), com a caixa "How many slots?"
# embaixo. E a UNICA tela do jogo com Pop/Econ/Rltns/Trsm + slots por companhia
# juntos (§33.1). Este modulo so LE o frame: nao navega, nao aperta nada.
#
# Duas fontes convivem no mesmo frame:
#   - fonte GRANDE (celula 8x13 da grade do §24, `screen_text`) -> Pop/Econ/Trsm;
#   - fonte PEQUENA (celula 8x7, a MESMA da tela de quantidade de avioes,
#     `QTY_DIGIT_MD5`) -> "Total slots N/ M" e a tabela por companhia.
# A fonte pequena e binarizada por LUMINANCIA (>200) e nao por igualdade com
# `_st.WHITE`: os digitos da tabela ficam sobre 4 fundos coloridos diferentes e
# o jogo usa DOIS tons de branco no painel ((255,251,255) e (239,235,239)).
# Conferido: o mesmo digito em colunas de cores diferentes gera o MESMO hash.

CITY_PANEL_ROW = 24                 # linha grande com Pop / Econ / Trsm
CITY_POP_COL = (40, 96)
CITY_ECON_COL = (136, 176)
CITY_TRSM_COL = (200, 256)
CITY_NAME_BOX = (0, 0, 200, 32)     # bandeira + nome + pais (fonte NAO no atlas)
CITY_RLTNS_BOX = (224, 2, 254, 23)  # Rltns e PICTOGRAMA: nao ha numero (§33.2)

# Tabela por companhia: 4 faixas coloridas de 32px (§33.1). A ordem de exibicao
# e DADO, nao identidade (R3) — a unica cor com dono MEDIDO e a carmim, que e a
# NOSSA (§33.8, medida por acao propria).
CITY_COL_KEYS = ("carmim", "azul", "laranja", "verde")
CITY_COL_X = {"carmim": (119, 151), "azul": (151, 183),
              "laranja": (183, 216), "verde": (216, 248)}
CITY_COL_RGB = {"carmim": (189, 0, 41), "azul": (57, 58, 255),
                "laranja": (255, 97, 57), "verde": (0, 178, 0)}
CITY_OURS_COL = "carmim"            # MEDIDO §33.8

CITY_TABLE_Y = {"fl": 119, "slot": 135}   # topo da celula de 7px de cada linha
CITY_DIGIT_X0 = 136                 # x da celula MAIS A DIREITA da 1a coluna
CITY_COL_PITCH = 32
CITY_MAX_DIGITS = 3

# "Total slots N/ M": grade de 8px ancorada em x=0. O numero usado termina na
# celula x=24, a barra fica sempre em x=32 e a capacidade termina em x=56.
CITY_TOTAL_Y = 135
CITY_TOTAL_USED_X = 24
CITY_TOTAL_SLASH_X = 32
CITY_TOTAL_CAP_X = 56

CITY_BAND_Y = (118, 146)
CITY_BAND_MIN_PX = 400              # positivos 660-692, negativos 0-23 (medido)

# Mini-atlas da fonte de 7px. Os digitos 1..6 sao IDENTICOS aos ja calibrados em
# `QTY_DIGIT_MD5` (tela de quantidade de avioes) — confirmacao independente do
# rotulo. 0, 7, 9 e a barra "/" foram colhidos aqui.
# FALTA "8": nunca apareceu em nenhum dos 9 paineis. Numero que o contenha sai
# como None (R1) — falha visivel, nunca palpite.
CITY_SMALL_GLYPHS = {
    "e52c0cf178": "0",
    "77d927b0ef": "1",
    "bf8ccc55dc": "2",
    "46b0d4a5c9": "3",
    "514f44595a": "4",
    "379f6230c5": "5",
    "94b46c2aa2": "6",
    "27aa151025": "7",
    "4bdb05f531": "9",
    "1384aba1f7": "/",
}
CITY_SMALL_H = 7


def _city_bin(img):
    """Frame binarizado por luminancia (>200 = tinta). Imune a cor de fundo."""
    return img.convert("L").point(lambda v: 255 if v > 200 else 0)


def _city_small_cell(gp, cx, y0):
    """Char da celula 8x7 em (cx, y0). None = vazia; UNKNOWN = glifo novo."""
    import hashlib
    bits = "".join("1" if gp[x, y] else "0"
                   for y in range(y0, y0 + CITY_SMALL_H)
                   for x in range(cx, cx + _st.CELL_W))
    if bits.count("1") < _st.MIN_INK:
        return None
    h = hashlib.md5(bits.encode()).hexdigest()[:10]
    return CITY_SMALL_GLYPHS.get(h, _st.UNKNOWN)


def _city_small_number(gp, x_right, y0, max_digits=CITY_MAX_DIGITS):
    """Numero alinhado a DIREITA terminando na celula `x_right`.

    Le da direita para a esquerda ate a primeira celula vazia. Devolve None se
    nao houver digito nenhum ou se aparecer qualquer caractere que nao seja
    digito (glifo fora do mini-atlas, a barra "/", lixo) — nunca um numero
    parcialmente adivinhado.
    """
    digitos = ""
    for k in range(max_digits):
        cx = x_right - _st.CELL_W * k
        if cx < 0:
            break
        c = _city_small_cell(gp, cx, y0)
        if c is None:
            break
        if not c.isdigit():
            return None
        digitos += c
    if not digitos:
        return None
    return int(digitos[::-1])


def city_panel_bands(img):
    """Pixels da cor exata de cada uma das 4 faixas da tabela. Assinatura da tela."""
    px = img.load()
    y0, y1 = CITY_BAND_Y
    out = {}
    for k in CITY_COL_KEYS:
        x0, x1 = CITY_COL_X[k]
        rgb = CITY_COL_RGB[k]
        out[k] = sum(1 for y in range(y0, y1) for x in range(x0, x1)
                     if px[x, y] == rgb)
    return out


def on_city_panel(img):
    """True so no painel de cidade do fluxo de negociacao.

    Assinatura = as 4 faixas coloridas da tabela por companhia nas posicoes
    medidas. MEDIDO: 660-692 px em cada faixa nos 9 paineis; 0 px em frames de
    outras telas (mapa, hover, Info->map, escolha de aviao, staff, orcamento,
    menu...), com um unico frame chegando a 23 px numa faixa so.
    """
    if img.size != (256, 224):
        return False
    b = city_panel_bands(img)
    return all(v >= CITY_BAND_MIN_PX for v in b.values())


def read_city_pop_m(img):
    """Populacao em MILHOES (float), do texto "N.NM". None se ilegivel.

    Devolve a unidade declarada no nome porque a tela nao mostra habitantes: ela
    mostra "9.6M". Arredondar para int aqui seria inventar precisao.
    """
    s = _st.read_text(img, CITY_PANEL_ROW, *CITY_POP_COL)
    if not s.endswith("M"):
        return None
    s = s[:-1].strip()
    if not s or _st.UNKNOWN in s or any(c not in "0123456789." for c in s):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def read_city_table(img):
    """Linhas `Fl` e `Slot` por coluna colorida. Valor ilegivel vira None."""
    gp = _city_bin(img).load()
    out = {}
    for linha, y0 in CITY_TABLE_Y.items():
        out[linha] = {
            k: _city_small_number(gp, CITY_DIGIT_X0 + CITY_COL_PITCH * i, y0)
            for i, k in enumerate(CITY_COL_KEYS)
        }
    return out


def read_city_total_slots(img):
    """(usados, capacidade) do "Total slots N/ M". Campo ilegivel vira None."""
    gp = _city_bin(img).load()
    if _city_small_cell(gp, CITY_TOTAL_SLASH_X, CITY_TOTAL_Y) != "/":
        return (None, None)
    return (_city_small_number(gp, CITY_TOTAL_USED_X, CITY_TOTAL_Y),
            _city_small_number(gp, CITY_TOTAL_CAP_X, CITY_TOTAL_Y))


def read_city_panel(img):
    """Le o painel de cidade INTEIRO de um frame. Nunca navega, nunca aperta nada.

    Devolve dict; TODO campo que nao decodifica vem None (R1). Chaves:

      on_panel      bool  — a tela e mesmo o painel (guard `on_city_panel`)
      name          None  — SEMPRE None hoje: os glifos MINUSCULOS do nome/pais
                            nao estao no atlas do §24 (falha visivel, `name_ocr`)
      name_ocr      str   — o que o atlas leu, com '?' onde nao sabe (diagnostico)
      name_hash     str   — md5 do recorte do nome+pais+bandeira; e o campo util:
                            deixa o chamador conferir que o painel e o da cidade
                            para onde ele apontou o cursor
      pop_m         float — populacao em MILHOES (a tela mostra "9.6M")
      econ          int
      trsm          int   — MEDIDO que o NUMERO e Trsm e o ICONE e Rltns (§33.2)
      rltns_icon    str   — hash do pictograma. NAO ha numero e NAO ha ranking
                            calibrado: virar "bom/ruim" seria palpite (§33.6.2)
      slots_used    int
      slots_cap     int
      table         dict  — {"fl": {cor: n}, "slot": {cor: n}}
      ours          str   — "carmim", a UNICA cor com dono MEDIDO (§33.8)
      our_slots     int   — atalho para table["slot"]["carmim"]
      soma_confere  bool  — soma das 4 colunas de `slot` == slots_used.
                            None quando algum dos termos e None.

    NAO MEDIDO e por isso ausente: nome da companhia das outras 3 cores (ordem
    de exibicao e dado, nao identidade, R3); o que a linha `Fl` significa (era 0
    nos 9 paineis observados); se o icone de Rltns tem mais de 3 estados.
    """
    import hashlib
    ok = on_city_panel(img)
    out = {"on_panel": ok, "name": None, "name_ocr": None, "name_hash": None,
           "pop_m": None, "econ": None, "trsm": None, "rltns_icon": None,
           "slots_used": None, "slots_cap": None, "table": None,
           "ours": CITY_OURS_COL, "our_slots": None, "soma_confere": None}
    if not ok:
        return out
    out["name_ocr"] = _st.read_text(img, 8, 40, 200)
    out["name_hash"] = hashlib.md5(img.crop(CITY_NAME_BOX).tobytes()).hexdigest()[:8]
    out["rltns_icon"] = hashlib.md5(
        img.crop(CITY_RLTNS_BOX).tobytes()).hexdigest()[:8]
    out["pop_m"] = read_city_pop_m(img)
    out["econ"] = _st.read_int(img, CITY_PANEL_ROW, *CITY_ECON_COL)
    out["trsm"] = _st.read_int(img, CITY_PANEL_ROW, *CITY_TRSM_COL)
    usados, cap = read_city_total_slots(img)
    out["slots_used"], out["slots_cap"] = usados, cap
    tab = read_city_table(img)
    out["table"] = tab
    out["our_slots"] = tab["slot"][CITY_OURS_COL]
    vals = list(tab["slot"].values())
    if usados is not None and all(v is not None for v in vals):
        out["soma_confere"] = (sum(vals) == usados)
    return out


# =============================================================================
# ETAPA 2-OraculosFracos — leitura DE VOLTA do RESUMO DE ROTA (r0c1 route_edit)
# =============================================================================
# O oraculo antigo de `adjust_route` era "1 Rte antes e 1 Rte depois": nao lia
# NADA do que a acao muda. Aqui se le da TELA os dois campos que a acao mexe.
#
# CALIBRADO OFFLINE no par ROTULADO que ja estava em disco:
#   logs/edit_commit/a_summary.png        -> Flts 1, Fare $720 / 0%
#   logs/edit_commit/n_reopen_summary.png -> Flts 2, Fare $792 / 10%
# (o segundo e a REABERTURA depois de sair ate o menu, entao e persistencia
#  real, nao buffer de tela.)
#
# Flts: digito na fonte de 8x13 do atlas principal, celula x=224 y=200. O
# recorte vai de 208 para caber ate 3 digitos; celula vazia le ''.
#
# Fare: o PRECO ($720) e o PERCENTUAL (0%) sao desenhados numa fonte MINUSCULA
# de 7 linhas que NAO esta no atlas (mesma familia do QTY_GLYPH_Y). Em vez de
# adivinhar glifos com 2 amostras, le-se a BARRA: segmentos de 3 px da cor
# (57,91,173) com passo 4 a partir de x=161. Medido 10 segmentos em 0% e 12 em
# +10% — bate com FARE_PCT_PER_STEP=5% ja calibrado (2 toques = 10%).
ROUTE_SUM_LABEL_BOX = (128, 183, 160, 210)   # rotulos "Fare"/"Flts" da direita
ROUTE_SUM_LABEL_HASH = "1aed410b"            # identico nas 2 capturas de resumo
ROUTE_SUM_FLTS_ROW = 200
ROUTE_SUM_FLTS_COL = (208, 232)
FARE_GAUGE_RGB = (57, 91, 173)
FARE_GAUGE_X0 = 161
FARE_GAUGE_PITCH = 4
FARE_GAUGE_Y = 195
FARE_GAUGE_MAX = 20
FARE_GAUGE_MID = 10          # segmentos cheios quando a tela diz "0%" (media)
FARE_PCT_PER_SEG = 5         # 1 segmento = 5% (== FARE_PCT_PER_STEP)


def on_route_summary(img):
    """True so na tela de RESUMO da rota (a que mostra Sales/Load/Fare/Flts).

    Guard por hash do bloco de rotulos, como `on_budget_screen`. MEDIDO: as
    outras 4 telas do fluxo de edicao em logs/edit_commit (d_after_A,
    j_after_set, k_confirm_full, m_back_to_menu) dao hashes DIFERENTES, entao
    o guard separa mesmo.
    """
    return _hashlib.md5(img.crop(ROUTE_SUM_LABEL_BOX).tobytes()).hexdigest()[:8] \
        == ROUTE_SUM_LABEL_HASH


def read_route_flights(img):
    """Voos/semana (Flts) exibidos no resumo. None se nao decodificar (R1)."""
    return _st.read_int(img, ROUTE_SUM_FLTS_ROW, *ROUTE_SUM_FLTS_COL)


def read_fare_gauge(img):
    """Segmentos CHEIOS da barra de tarifa. None nunca — a contagem e pixel."""
    px = img.load()
    n = 0
    for i in range(FARE_GAUGE_MAX):
        x = FARE_GAUGE_X0 + FARE_GAUGE_PITCH * i
        if x + 3 > img.size[0]:
            break
        if all(px[x + d, FARE_GAUGE_Y] == FARE_GAUGE_RGB for d in range(3)):
            n += 1
        else:
            break          # a barra e contigua; parar no 1o vazio evita contar
    return n               # os tracinhos soltos do trilho vazio


def fare_pct_from_gauge(segs):
    """Percentual sobre a tarifa media, a partir da contagem de segmentos.

    ANCORA MEDIDA: 10 segmentos = 0% (a propria tela escreve "0%"), 12 = 10%.
    Fora disso e extrapolacao linear pelo passo ja calibrado de 5%.
    """
    if segs is None:
        return None
    return (segs - FARE_GAUGE_MID) * FARE_PCT_PER_SEG


def read_route_summary(img):
    """{'on_summary','flights','fare_segs','fare_pct'} — campo ilegivel = None."""
    ok = on_route_summary(img)
    if not ok:
        return {"on_summary": False, "flights": None,
                "fare_segs": None, "fare_pct": None}
    segs = read_fare_gauge(img)
    return {"on_summary": True, "flights": read_route_flights(img),
            "fare_segs": segs, "fare_pct": fare_pct_from_gauge(segs)}


# =============================================================================
# ETAPA 2-OraculosFracos — RECUSA de `return_slots`
# =============================================================================
# MEDIDO: as DUAS corridas de aceite que estavam em disco
# (logs/return_slots_aceite/ e logs/return_slots_debug/,
#  return_slots_SA01_confirmado.png) mostram a MESMA tela de recusa:
#   "All of your slots in this city are currently being used.
#    It's impossible to return them at this time."
# O harness respondia ok=True em cima disso — era essa a mentira do §17.1.
# A fonte da caixa e a minuscula (o atlas devolve '?????'), entao a leitura e
# por HASH da TEXTBOX, mesma tecnica ja usada para a recusa de rota.
RETURN_REFUSAL_HASHES = {
    "e7e0ae54": "All of your slots in this city are currently being used. "
                "It's impossible to return them at this time.",
}


def return_slots_refusal(img):
    """Texto da recusa se a tela for uma recusa conhecida de Return, senao None."""
    h = _hashlib.md5(img.crop(TEXTBOX).tobytes()).hexdigest()[:8]
    return RETURN_REFUSAL_HASHES.get(h)
