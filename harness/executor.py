"""Traduz acoes semanticas do agente em sequencias de menu do jogo.

Cada acao segue o padrao anti-fragilidade: savestate antes, executa, verifica
que voltamos ao menu principal; se nao voltou, recarrega o savestate e marca a
acao como falha. Assim uma acao quebrada nunca contamina o resto do turno.
"""

import pathlib

from PIL import Image

from macros import Game
from world import (REGION_NAMES, WORLD_CITIES, point_cursor_at_world, switch_to_region,
                   wait_text, read_budget_money, read_budget_col, BUDGET_ORDERS, at_main_menu_img,
                   city_region, on_map_screen, staff_action_is_bid, buy_panel_hash)
import world
GUARD = pathlib.Path(__file__).parent.parent / "states" / "_guard.state"
STEP_SETTLE = 90   # frames entre teclas de um fluxo
TYPE_SETTLE = 150  # frames para a datilografia terminar antes de aceitar input

# Acoes cujo efeito no jogo tem custo imediato — usadas para verificar que a
# acao ACONTECEU, e nao apenas que a macro rodou sem quebrar.
# MEDIDO 12/08: abrir rota debita o caixa NA HORA (-16.200K / -18.900K), mas o
# LANCE por slots NAO — ele so e cobrado no fechamento do trimestre. Verificar
# negotiate_slots por caixa reprovava acoes que funcionaram (run EVAL_single_fraco:
# 3 negociacoes marcadas SEM EFEITO com o caixa parado em 1.220.000K).
# O sinal correto para a negociacao e o funcionario sair da base (tela Info->staff),
# ainda NAO implementado — por isso ela fica fora do gate por enquanto.
# MEDIDO 15/08 (probe_buy.py): comprar aviao DEBITA O CAIXA NA HORA, no A que
# responde YES ao "1 plane will cost $81600K. Is this OK?" — 1.220.000K ->
# 1.138.400K, exatamente os $81.600K do MD11 mostrados na tela. A entrega e que
# demora ("Please wait about 3 months for delivery"), o pagamento nao.
EFEITO_CUSTA_CAIXA = {"open_route", "buy_aircraft"}

# CALIBRADO 12/08 (logs/calib/cal_voos.png, rota Washington-Denver):
# 1 toque = 5% sobre a tarifa media, linear e verificado em 4 pontos.
#   0 toques -> "average fare"     $490
#   1 toque  -> "5% above avg."    $514
#   2 toques -> "10% above avg."   $538
#   4 toques -> "20% above avg."   $586
# CALIBRADO 12/08 (logs/calib2/cal_voos.png): 1 toque = +1 voo/semana, base 1.
# ATENCAO: cada voo/semana consome 1 SLOT EM CADA PONTA da rota (medido:
# 1 voo -> SLOTS 1/34 e 1/12; 5 voos -> 5/34 e 5/12). Frequencia alta com
# poucos slots inviabiliza rotas futuras — e um trade-off real do jogo.
FLIGHTS_PER_STEP = 1
FLIGHTS_BASE = 1
SLOTS_POR_VOO = 1

FARE_PCT_PER_STEP = 5
FARE_STEPS = {"low": -2, "mid": 0, "high": 2}  # -10% / media / +10%

# MEDIDO (probe_flow14.py, rota NA06): do A de confirmacao ate o jogo voltar
# sozinho ao menu passam-se 420 frames sem apertar tecla nenhuma.
OPEN_ANIM_FRAMES = 420

# CALIBRADO 17/08 (route_edit, r0c1): a barra de abas do editor tem 7 celulas
# FIXAS — Susp/Close/Model/Planes/Flts/Fare/SET — navegadas so com Right/Left
# (sem wrap constatado: parado em SET nao voltou a Susp em 2 toques extras,
# logs/action_space_map/r0c1_tab4..6_zoom.png). 'SET' e o botao de commit, NAO
# uma lista de rotas — a antiga leitura "SEL(ECT) volta a lista" no
# ACTION_SPACE.md era hipotese, nao medicao; a celula testada abre "Is it OK
# to change this flight as shown?" (YES/NO).
#
# Bounds nativos (256x224), lidos pixel a pixel na linha y=8 (divisorias
# escuras entre celulas, ver logs/tabguard/susp_tab2.png).
# ARMADILHA MEDIDA 17/08: a 1a versao destes bounds (guess a partir de um
# zoom em escala, sem medir os divisores) e a 1a heuristica de leitura (soma
# R+G+B media na faixa y=2..16) pareciam calibradas (5/5) porque o teste NUNCA
# tinha cobrido Susp/Close nem qualquer frame com 'SET' NAO destacado. Ao vivo:
# (a) os bounds antigos cortavam Susp/Close no meio, e um Left real (Susp
#     destacada, confirmado por olho — logs/tabguard/susp_zoom.png) foi lido
#     como Close; (b) a celula SET tem letras BRANCAS ("S/E/T" empilhadas) que
#     sozinhas erguem a soma R+G+B mesmo SEM destaque, entao qualquer aba
#     genuinamente destacada com brilho proximo perdia para SET no argmax
#     (medido: Flts e Fare destacados foram lidos como 'set').
# Correcao: bounds exatos por divisor + amostra de UMA linha (y=8, acima do
# texto) do canal G, que separa destacado (~103-107) de nao-destacado
# (~41-52, inclusive o proprio SET fora de foco) com folga grande. Validado
# 7/7 contra as 7 celulas com destaque conhecido — incluindo Susp e Close,
# que a versao anterior nunca tinha testado.
ROUTE_TAB_BOUNDS = (8, 40, 72, 136, 168, 200, 240, 247)
ROUTE_TAB_NAMES = ("susp", "close", "model", "planes", "flts", "fare", "set")
ROUTE_TAB_ROW_Y = 8

# Recorte do VALOR mostrado no painel (nao do rotulo) de cada campo editavel —
# so para detectar SE um toque mudou algo (hash), NUNCA para ler o numero: o
# harness nao tem OCR. Capturado em logs/edit_commit/flts_box_zoom2.png e
# fare_box_zoom.png.
# ARMADILHA MEDIDA 17/08 (prova_adjust.py, 1a versao): a caixa do Flts INCLUI
# a borda pontilhada do topo do overlay, que PISCA — igual as setinhas do
# slider que ja tinham quebrado o hash de tela inteira em `_step()`. Com essa
# borda dentro do recorte, o hash mudava a CADA screenshot mesmo sem nenhum
# toque, e a deteccao de teto reportou "Flts: 1 -> 3 (2 toques)" quando a tela
# seguia mostrando "1" (logs/adjust_aceite/z_final_summary.png contra o
# resultado do run — falso positivo). Recorte reduzido para SO o digito,
# testado 3x parado (hash identico) + 2x com Right no teto real (hash
# identico, correto) em logs/adjust_aceite/stable*.png.
FLTS_VALUE_BOX = (218, 124, 233, 136)
FARE_VALUE_BOX = (193, 100, 247, 120)


class Executor:
    def __init__(self, bridge):
        self.b = bridge
        self.g = Game(bridge)
        # Regiao em que o mapa ficou. O jogo NAO volta sozinho para a regiao da
        # base: se a acao anterior terminou na Europa, a proxima tela de mapa
        # abre na Europa. E so um PALPITE — switch_to_region le a regiao real da
        # tela antes de agir e corrige este valor.
        self.map_region = None
        # Quantas vezes o retry de "cursor travado" precisou entrar. Se um
        # aceite passa com isto > 0, quem passou foi o retry, nao a correcao.
        self.retries_fired = 0
        # --- ESCRITURACAO DE MUNDO (instancia, NUNCA classe) -----------------
        # HUB_REGIONS era um atributo de CLASSE: um `self.HUB_REGIONS.add(1)`
        # mutaria o conjunto do processo inteiro e sobreviveria a um
        # `_restore_guard()` — o harness continuaria dizendo ao modelo que ha um
        # hub que o jogo desfez. Tudo que descreve o mundo mora na instancia e e
        # revertido junto com o savestate (ver _snapshot/_restore_snapshot).
        self.reset_world_state()

    # --- escrituracao: hubs, rotas e slots que o HARNESS acredita ------------
    def reset_world_state(self, hubs=None, hubs_pending=None, routes=None, owned_slots=None):
        """Zera/define o que o harness acredita sobre o mundo.

        Deve ser chamada depois de todo `b.load()` feito FORA do executor — os
        hubs e rotas do savestate nao sao lidos do jogo, sao declarados por quem
        carrega o estado. Declaracao errada aqui vira recusa errada la na frente,
        por isso toda mensagem que usa estes campos diz "o harness acredita".
        """
        from world import HOME

        # A BASE e hub por definicao (medido: na regiao dela o jogo responde
        # "Our home base is here... We don't need a regional hub").
        self.hubs = set(hubs) if hubs is not None else {HOME}
        # regiao -> cidade cuja negociacao de hub esta EM ANDAMENTO. Um hub
        # pendente NAO e origem valida: medido 17/08 (probe_hub1.py) que o jogo
        # ainda responde "We don't have a regional hub here." com a negociacao
        # em curso.
        self.hubs_pending = dict(hubs_pending or {})
        # [{"from": cid, "to": cid, "flights": n}] — so entram rotas cujo efeito
        # foi verificado (queda de caixa).
        self.routes = list(routes or [])
        # cid -> slots que o harness acredita possuir (o pilot atualiza pelo mapa)
        self.owned_slots = dict(owned_slots or {})

    def _snapshot(self):
        return (set(self.hubs), dict(self.hubs_pending),
                [dict(r) for r in self.routes], dict(self.owned_slots))

    def _restore_snapshot(self, snap):
        self.hubs, self.hubs_pending, self.routes, self.owned_slots = (
            set(snap[0]), dict(snap[1]), [dict(r) for r in snap[2]], dict(snap[3])
        )

    @property
    def hub_regions(self):
        """Regioes onde temos hub CONFIRMADO (pendente nao conta)."""
        from world import city_region

        return {city_region(c) for c in self.hubs}

    def _restore_guard(self):
        """Recarrega o savestate de guarda E ESQUECE a regiao do mapa.

        O GUARD foi salvo ANTES da troca de continente, entao depois do load o
        mapa esta de volta na regiao antiga enquanto self.map_region ainda
        aponta para o destino. switch_to_region normalmente se corrige lendo a
        tela, mas quando a leitura sai ambigua ela cai no palpite — e o palpite
        errado poe o cursor na coordenada certa do continente errado, sem erro
        nenhum. None = "nao sei", que forca a leitura.

        Reverte TAMBEM a escrituracao (hubs/rotas/slots): se a macro chegou a
        anotar um hub e o savestate volta atras, manter a anotacao seria
        exatamente a mentira que o gate de efeito existe para impedir.
        """
        self.b.load(GUARD)
        self.b.advance(60)
        self.map_region = None
        if getattr(self, "_snap", None) is not None:
            self._restore_snapshot(self._snap)

    def _ensure_menu(self, tries=10):
        """Volta ao menu principal e CONFIRMA que chegou.

        Antes isso apertava B as cegas e devolvia True sempre. Resultado: quando
        uma acao era recusada, a seguinte comecava numa tela qualquer, o 'homing'
        dos icones acabava movendo o cursor DO MAPA e a acao seguinte falhava por
        um motivo que nada tinha a ver com ela (visto ao vivo: NA06 falhou logo
        depois da recusa de NA14, e funcionou sozinho).
        """
        from world import at_main_menu_img

        for i in range(tries):
            if at_main_menu_img(Image.open(self.b.screenshot()).convert("RGB")):
                return True
            # SO B, de proposito. Cheguei a escalar para "A + B" porque na tela
            # de RECUSA de rota 6 B's seguidos nao saem (probe_recusa.py: so
            # A + 4 B voltaram ao menu) — mas o A REENTRA no fluxo e deixa o jogo
            # num estado que quebrava a acao SEGUINTE (visto ao vivo duas vezes).
            # A tela de recusa e tratada na origem, recarregando o savestate de
            # guarda, entao esse ramo nao e mais necessario aqui.
            self.b.batch(
                self.b.seq_press("B", hold=5, wait=25) + self.b.seq_advance(90), extra_frames=200
            )
        return False

    def run(self, action, _retry=True):
        """Executa uma acao; devolve (ok, detalhe)."""
        name = action.get("action")
        params = action.get("params", {}) or {}
        fn = getattr(self, f"_do_{name}", None)
        if fn is None:
            return False, f"acao sem macro implementada: {name}"
        from world import read_cash_k

        self.b.save(GUARD)
        # Escrituracao no mesmo ponto do savestate: se o GUARD for recarregado,
        # hubs/rotas anotados pela macro voltam atras junto.
        self._snap = self._snapshot()
        cash_antes = read_cash_k(self.b)
        try:
            ok, detail = fn(params)
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"excecao: {e}"
        # VERIFICACAO DE EFEITO: abrir rota e negociar custam dinheiro. Se o
        # caixa nao mudou, a macro rodou mas o jogo nao fez nada — reportar
        # sucesso ai foi o que produziu uma run inteira de numeros vazios.
        if ok and name in EFEITO_CUSTA_CAIXA:
            # Poll: a cobranca pode nao estar liquidada no primeiro frame apos a
            # animacao. So declaramos "sem efeito" depois de insistir.
            # A afirmacao e "custou dinheiro", entao o teste e caixa MENOR — nao
            # "caixa diferente". Receita e custo trimestral tambem mexem no caixa,
            # e a janela de poll aumenta a chance de capturar uma mudanca alheia:
            # com "!=" uma acao que falhou passaria no gate por carona.
            cash_depois = cash_antes
            for _ in range(4):
                self.b.advance(60)
                cash_depois = read_cash_k(self.b)
                if cash_depois < cash_antes:
                    break
            if cash_depois >= cash_antes:
                ok = False
                detail = f"{detail} | SEM EFEITO: caixa nao caiu ({cash_antes}K -> {cash_depois}K)"
            else:
                detail = f"{detail} | caixa {cash_antes}K -> {cash_depois}K ({cash_depois - cash_antes:+d}K)"
        if not self._ensure_menu():
            # _restore_guard reverte o savestate E a escrituracao — sem isso um
            # hub/rota anotado pela macro sobreviveria ao rollback do jogo.
            self._restore_guard()
            return False, f"{detail} | nao voltou ao menu, savestate restaurado"
        # INVARIANTE DE ESTADO: toda acao devolve o mapa a regiao da BASE.
        # Sem isto, uma negociacao na Europa deixava o menu exibindo a Europa e a
        # acao SEGUINTE partia de uma regiao inesperada — a 1a acao do turno
        # funcionava e as demais falhavam em sequencia (medido em 3 runs).
        try:
            self.map_region, _ = switch_to_region(self.b, 0, self.map_region)
        except Exception:  # noqa: BLE001 — normalizacao best-effort
            self.map_region = None
        # CURSOR TRAVADO: acontece quando a acao ANTERIOR deixou o jogo numa tela
        # intermediaria. Medido ao vivo: a 1a negociacao do turno funcionava e as
        # seguintes falhavam em sequencia. Voltar ao menu, esquecer a regiao
        # (para relê-la da tela) e tentar UMA vez recupera sem custo de run.
        if not ok and _retry and "cursor do mapa nao respondeu" in str(detail):
            # Contabilizado para que um aceite "4/4" nao possa ser creditado ao
            # retry: se ele disparou, a correcao de causa raiz NAO resolveu.
            self.retries_fired += 1
            self._ensure_menu()
            self.map_region = None
            ok2, det2 = self.run(action, _retry=False)
            return ok2, f"{det2} | (RETRY de cursor disparou: {detail})"
        return ok, detail

    # --- macros de acao ---
    def _step(self, tries=3):
        """Aperta A e so retorna quando a PERGUNTA mudou.

        Contar A's fixos nao funciona: o jogo ignora input enquanto o texto
        datilografa, entao um A vira zero passos — e um A a mais vira dois.
        Medindo o fluxo passo a passo (probe_cursor.py flow) foram precisos 7 A's
        para 5 transicoes: dois foram engolidos.

        A comparacao usa o recorte da CAIXA DE TEXTO (world.TEXTBOX). Hash da
        tela inteira NAO serve: as setinhas dos sliders piscam, entao dois frames
        da MESMA tela sempre diferem e "mudou = avancou" da falso positivo — foi
        o que fez a macro percorrer o fluxo reportando sucesso e parar em
        "How many flights per week?". Medido: as 7 telas do fluxo tem hashes
        distintos neste recorte.
        """
        before = wait_text(self.b)
        for _ in range(tries):
            self.b.press("A", hold=5, wait=25)
            if wait_text(self.b) != before:
                return True
        return False

    def _select_city(self, cid):
        """Seleciona QUALQUER cidade do catalogo global, trocando de regiao.

        Aceita id de qualquer uma das 7 regioes: `point_cursor_at_world` aperta
        R ate o mapa estar no continente certo (conferindo por pixels de terra,
        nao por contagem cega) e so entao escreve a posicao do cursor na RAM.
        A regiao em que o mapa FICOU e guardada em self.map_region — a acao
        seguinte comeca de la, porque o jogo nao volta para a base sozinho.
        """
        if cid not in WORLD_CITIES:
            raise ValueError(f"id de cidade inexistente: {cid}")
        from world import on_map_screen

        reg, pos, verificado = point_cursor_at_world(self.b, cid, self.map_region)
        self.map_region = reg
        # A ate SAIR do mapa: os A's sao engolidos durante a datilografia (medido:
        # 3 A's para uma selecao). Se depois de `tries` ainda estamos no mapa, o
        # jogo RECUSOU a cidade (ou nao ha nada sob o cursor) — quem chama trata.
        for _ in range(4):
            wait_text(self.b)
            self.b.press("A", hold=5, wait=25)
            self.b.advance(TYPE_SETTLE)
            if not on_map_screen(Image.open(self.b.screenshot()).convert("RGB")):
                return pos, reg, verificado
        return pos, reg, verificado


    def _goto_region(self, alvo, tries=3):
        """Poe o mapa do MENU PRINCIPAL na regiao `alvo` e CONFIRMA por leitura.

        Por que confirmar de novo se switch_to_region ja le a tela: ela devolve
        `verificado=False` quando ALGUMA leitura saiu ambigua e cai no palpite —
        e foi o que aconteceu na medicao do hub (probe_hub3.py: `verif=False`
        com a regiao certa no fim). Para uma acao cujo gate de efeito e "o caixa
        caiu e um funcionario saiu", a regiao errada passaria no gate: abrir hub
        na Africa custa os mesmos $28.800K e o mesmo funcionario que na America
        do Sul. Aqui a regiao e lida de novo, sozinha, e tem de bater.

        Devolve (ok, detalhe). MEDIDO 17/08 que detect_region funciona no mapa
        do menu principal (probe_hub1/2: land 1019 -> regiao 1, 2262 -> 0), e
        nao so no mapa da tela de rota onde REGION_LAND foi calibrada.
        """
        from world import REGION_NAMES, detect_region

        self.map_region, _ = switch_to_region(self.b, alvo, self.map_region)
        for _ in range(tries):
            lido = detect_region(Image.open(self.b.screenshot()).convert("RGB"))
            if lido == alvo:
                self.map_region = alvo
                return True, f"mapa confirmado na regiao {alvo} ({REGION_NAMES[alvo]})"
            self.b.advance(60)
        self.map_region = lido
        return False, (f"mapa NAO esta na regiao {alvo} ({REGION_NAMES[alvo]}): "
                       f"leitura devolveu {lido}")

    # --- regra de rota (validada ANTES de tocar no emulador) -----------------
    def free_slots(self, cid):
        """Slots livres que o HARNESS acredita ter em `cid`.

        CALIBRADO 12/08: cada voo/semana consome 1 slot EM CADA PONTA da rota
        (1 voo -> SLOTS 1/34 e 1/12; 5 voos -> 5/34 e 5/12). Comparar o pedido
        com os slots POSSUIDOS, sem descontar o que as rotas ja consomem, daria
        o motivo errado de recusa exatamente no caso que interessa: Havana tem
        1 slot e a rota Washington->Havana ja o consome, entao uma rota PARTINDO
        de Havana e recusada na ORIGEM, nao no destino.
        """
        usados = sum(r.get("flights", 1) for r in self.routes
                     if r.get("from") == cid or r.get("to") == cid)
        return self.owned_slots.get(cid, 0) - usados

    def check_route(self, origem, dest, flights=1):
        """Motivo pelo qual a rota NAO pode abrir, ou None se pode.

        REGRA DO JOGO (confirmada pelo usuario e medida em 15-17/08):
          (a) toda rota parte de um HUB NOSSO — nao existe rota entre duas
              cidades comuns, nem dentro do mesmo continente;
          (b) e preciso slot livre nas DUAS pontas;
          (c) a aeronave precisa de alcance >= distancia.
        A regiao EXIBIDA no mapa quando r0c0 e invocado escolhe o hub de origem;
        com a regiao errada o jogo responde "We don't have a regional hub here."
        e TRAVA a tela. Recusar aqui devolve ao modelo o motivo certo em vez de
        uma mensagem generica tres telas adiante.
        """
        from world import (FLEET_START, HOME, MEASURED_DIST_FROM_HOME, REGION_NAMES,
                           WORLD_CITIES, city_region)

        for rot, cid in (("origem", origem), ("destino", dest)):
            if cid not in WORLD_CITIES:
                return f"{rot} '{cid}' nao existe no catalogo de cidades"
        if origem == dest:
            return f"origem e destino sao a mesma cidade ({origem})"
        if any(r.get("from") == origem and r.get("to") == dest for r in self.routes):
            return f"ja existe rota {origem}->{dest} (o harness acredita)"
        # (a) hub
        if origem not in self.hubs:
            reg = city_region(origem)
            extra = ""
            if self.hubs_pending.get(reg) == origem:
                extra = (f" — a negociacao do hub em {origem} esta EM ANDAMENTO; "
                         "espere ela concluir (passe turnos)")
            elif dest in self.hubs:
                extra = (f" — {dest} E hub nosso: inverta a rota "
                         f"(from={dest}, to={origem})")
            return (f"rota {origem}->{dest} recusada: toda rota parte de um HUB nosso e "
                    f"{origem} nao e hub (hubs: {sorted(self.hubs)}; "
                    f"regiao {reg} {REGION_NAMES[reg]}){extra}. "
                    "Para criar um hub numa regiao: negocie slots numa cidade dela, "
                    "abra rota de um hub existente ate la e so entao use open_hub")
        # (b) slots nas duas pontas.
        # SEM CRENCA NENHUMA (owned_slots vazio) a checagem e PULADA: dicionario
        # vazio significa "ninguem declarou os slots deste savestate", nao "nao
        # temos slot nenhum". Tratar as duas coisas como iguais recusaria toda
        # rota nos probes antigos, que nunca declaram slots — e uma recusa
        # inventada e pior que nenhuma. Com crenca declarada, cidade AUSENTE si
        # conta como 0 (e o que EVAL_SLOTS_2000 significa).
        for rot, cid in (("origem", origem), ("destino", dest)) if self.owned_slots else ():
            livres = self.free_slots(cid)
            if livres < flights:
                return (f"rota {origem}->{dest} recusada na {rot} {cid}: o harness "
                        f"acredita em {self.owned_slots.get(cid, 0)} slot(s) possuido(s) "
                        f"menos {self.owned_slots.get(cid, 0) - livres} ja consumido(s) "
                        f"por rotas = {livres} livre(s), e a rota pede {flights}. "
                        f"Negocie slots em {cid} (negotiate_slots) antes")
        # (c) alcance — so da para afirmar quando a distancia foi LIDA do jogo.
        # MEDIDO_DIST so tem distancias a partir da BASE; entre outros pares o
        # jogo nunca mostrou numero, entao aqui nao se inventa: deixa o jogo
        # recusar e a recusa e traduzida por on_plane_screen().
        if origem == HOME and dest in MEASURED_DIST_FROM_HOME:
            alcance = max([a["range_mi"] for a in FLEET_START] + [0])
            for c in getattr(self, "comprados", []):
                alcance = max(alcance, c.get("range_mi", 0))
            if MEASURED_DIST_FROM_HOME[dest] > alcance:
                return (f"rota {origem}->{dest} recusada: distancia LIDA do jogo "
                        f"{MEASURED_DIST_FROM_HOME[dest]} mi > alcance da frota "
                        f"inicial {alcance} mi")
        return None

    def _do_open_route(self, p):
        from world import HOME, FLEET_START, city_region, on_map_screen, on_plane_screen

        dest = p.get("to")
        if not dest:
            return False, "open_route sem destino"
        # ORIGEM = o HUB de onde a rota parte. Voltou ao schema em 17/08, quando
        # open_hub passou a existir: sem ela o modelo nao consegue expressar
        # "rota partindo do hub novo" e o harness mandaria tudo de Washington.
        origem = p.get("from") or HOME
        flights = int(p.get("flights_week", 1))
        # VALIDACAO ANTES DO EMULADOR: hub na origem, slots livres nas duas
        # pontas, alcance. O modelo recebe o motivo CERTO em vez da recusa
        # generica que o jogo mostra tres telas depois.
        erro = self.check_route(origem, dest, flights)
        if erro:
            return False, erro
        self._ensure_menu()
        # CAUSA RAIZ do "menu inacessivel" / "cursor nao respondeu" (medido 15/08):
        # a REGIAO EXIBIDA no mapa define de qual hub a rota parte. Se o comando
        # abre com o mapa numa regiao sem hub nosso, o jogo responde
        # "We don't have a regional hub here." e fica nessa tela — o cursor esta
        # morto porque e uma mensagem, nao uma selecao. Capturas: Africa e Oriente
        # Medio em logs/run_f0/rota_travada_*.png.
        origem_reg = city_region(origem)
        ok_reg, det_reg = self._goto_region(origem_reg)
        if not ok_reg:
            self._restore_guard()
            return False, (f"rota {origem}->{dest}: {det_reg} — sem a regiao da origem "
                           "certa a rota partiria do hub errado; estado restaurado")
        self.g.open_cmd("new_route")
        # DE QUAL HUB O JOGO VAI PARTIR — lido da caixa de rodape, nao deduzido.
        # A regiao escolhe o hub, entao errar a regiao abriria uma rota a partir
        # de outro hub sem erro nenhum: o caixa cairia igual e o gate passaria.
        from world import ROUTE_ORIGIN_MD5, route_screen_kind
        wait_text(self.b)
        self.b.advance(60)
        kind, val = route_screen_kind(Image.open(self.b.screenshot()).convert("RGB"))
        if kind == "sem_hub":
            shot = self.g.shot(f"rota_sem_hub_{origem}_{dest}")
            self._restore_guard()
            return False, (f"rota {origem}->{dest} recusada: o jogo diz \"We don't have a "
                           f"regional hub here.\" na regiao {origem_reg} — o harness acreditava "
                           f"que {origem} era hub nosso (hubs={sorted(self.hubs)}). Se o hub foi "
                           "aberto ha pouco, a negociacao ainda pode estar em andamento; "
                           f"tela={shot}; estado restaurado")
        if kind == "origem" and val != origem:
            shot = self.g.shot(f"rota_origem_errada_{origem}_{dest}")
            self._restore_guard()
            return False, (f"rota {origem}->{dest} abortada: o jogo abriu o fluxo partindo de "
                           f"{val}, nao de {origem}; tela={shot}; estado restaurado")
        banner_desconhecido = (kind == "desconhecido")
        try:
            pos, reg, verif = self._select_city(dest)
        except RuntimeError as e:
            # MEDIDO 13/08: se o cursor foi deixado sobre uma cidade SEM slots, o
            # jogo ja abre o comando com "We don't have any slots in X" e trava a
            # tela — nenhum toque de d-pad passa. Nao ha o que recuperar por
            # teclas: recarregar o savestate de guarda e a saida determinista.
            shot = self.g.shot(f"rota_travada_{dest}")
            self._restore_guard()
            return False, f"rota {dest}: mapa travado ({e}); tela={shot}; estado restaurado"

        # O jogo RECUSA a rota se nao temos slots no destino ("We don't have any
        # slots in X") e permanece no mapa. Sem esta checagem a macro seguia
        # apertando A no mapa e reportava sucesso — era assim que 11 "rotas
        # abertas" conviviam com caixa intacto (CALIBRATION 4b).
        img = Image.open(self.b.screenshot()).convert("RGB")
        if on_map_screen(img):
            # Sair da tela de recusa por teclas e traicoeiro: B sozinho nao sai
            # (o jogo espera um A para dispensar a mensagem) e o A pode reentrar
            # no fluxo. Medido ao vivo: a acao SEGUINTE falhava depois dessa
            # recuperacao. Como uma rota recusada nao mudou nada, recarregar o
            # savestate de guarda e a volta ao menu mais barata e determinista.
            shot = self.g.shot(f"rota_recusada_{dest}")
            self._restore_guard()
            return False, (f"{dest} recusado (tela={shot}): nao temos slots no destino "
                           f"(regiao {REGION_NAMES[reg]}, cursor={pos}); estado restaurado")

        # RECUSA POR ALCANCE. MEDIDO 15/08 (rota NA13->EU11, Bruxelas, com 1 slot
        # ja negociado no destino): o jogo aceita a cidade, sai do mapa e mostra
        # "We don't have any aircraft capable of flying such a great distance."
        # numa tela AZUL sem o painel do aviao. Como on_map_screen() e False ali,
        # a macro seguia apertando A e so quebrava tres telas adiante, reportando
        # "fluxo travou na tela de voos/semana" — sintoma longe da causa.
        img = Image.open(self.b.screenshot()).convert("RGB")
        if not on_plane_screen(img):
            shot = self.g.shot(f"rota_sem_alcance_{dest}")
            self._restore_guard()
            frota = ", ".join("%s %dmi" % (a["model"], a["range_mi"]) for a in FLEET_START)
            # FLEET_START e a frota INICIAL do savestate — nao a frota atual (o
            # harness ainda nao le Info->fleet). Dizer "frota: MD100 4680mi"
            # depois de comprar um A340 e mentira; a mensagem agora diz o que a
            # constante e. MEDIDO 15/08: EU11 continua recusado mesmo com um
            # A340 de 8870 mi entregue e livre, logo a recusa NAO se resolve
            # comprando o aviao de maior alcance do catalogo.
            return False, (f"{dest} recusado antes da escolha do aviao — o jogo diz nao ter "
                           f"aeronave com alcance suficiente (frota INICIAL do savestate: "
                           f"{frota}; a atual pode ter mudado por buy_aircraft); "
                           f"tela={shot}; estado restaurado")

        idx = int(p.get("aircraft_index", 0))
        planes = int(p.get("planes", 1))
        flights = int(p.get("flights_week", 1))
        fare = FARE_STEPS.get(p.get("fare_level", "mid"), 0)

        # Sequencia de telas REMEDIDA em 12/08, tarefa 1.4, uma screenshot por
        # tela (probe_flow14.py walk NA06 -> logs/flow14/, hash do TEXTBOX entre
        # parenteses; as 5 sao distintas):
        #   1 "What type of plane will you use on the route?"  (cf168dc0)
        #       cabecalho: "Washington <| 1500MI |> Denver" — a DISTANCIA da rota
        #       mora aqui e so aqui; <| |> ciclam o modelo (NAO CALIBRADO)
        #   2 "How many planes will be used on this route?"    (91636979)
        #   3 "How many flights per week?"                     (8f754e59)
        #   4 "How much is the fare?"  (padrao: average fare, $490)  (b6fba1fe)
        #   5 "Shall we go ahead and open this route?" + (YES NO)    (41bc671f)
        #       -> A responde YES: cobra o caixa e roda a animacao de decolagem
        # NAO existe tela de distancia/custo: o custo NUNCA aparece na tela, so
        # como delta do caixa. Ver INVENTARIO_TELAS.md §9.
        # evidencia + calibracao de aircraft_index: a tela do aviao mostra modelo,
        # alcance e a DISTANCIA da rota no cabecalho
        self.g.shot(f"rota_aviao_{dest}_idx{idx}")

        # ETAPA 3a (19/08): `aircraft_index` e `planes` deixaram de ser toques as
        # cegas. As duas telas sao LIDAS DE VOLTA a cada toque — pelo mesmo
        # motivo que fare/flights sao confiaveis e estas duas nao eram.
        ok_av, det_av, modelo = self._pick_aircraft(idx, dest)
        if not ok_av:
            self._restore_guard()
            return False, det_av
        if not self._step():
            shot = self.g.shot(f"rota_travou_{dest}_aviao")
            return False, f"rota {dest}: fluxo travou na tela de aviao (tela={shot})"

        ok_qt, det_qt, planes_reais = self._pick_planes(planes, dest)
        if not ok_qt:
            self._restore_guard()
            return False, det_qt

        # O `A` que SAI da tela de quantidade. Sem ele o fluxo inteiro anda uma
        # tela atrasado: o bump de voos cairia na tela de quantidade, o de tarifa
        # na de voos, e o ultimo `_step` pararia na pergunta "Shall we go ahead?"
        # sem responder — a rota nunca abriria e a macro ficaria pendurada.
        if not self._step():
            shot = self.g.shot(f"rota_travou_{dest}_quantidade")
            return False, f"rota {dest}: fluxo travou saindo da tela de quantidade (tela={shot})"

        etapas = [
            ("voos/semana", self._bump("Right", flights - 1)),
            ("tarifa", self._bump("Right" if fare > 0 else "Left", abs(fare))),
            ("confirmacao", []),
        ]
        for nome, seq in etapas:
            if seq:
                self.b.batch(seq, extra_frames=len(seq) * 25 + 60)
            if not self._step():
                # nome pode ter '/' ("voos/semana") — vira subdiretorio no caminho
                shot = self.g.shot(f"rota_travou_{dest}_{nome.split()[0].replace('/', '_')}")
                return False, f"rota {dest}: fluxo travou na tela de {nome} (tela={shot})"
        self._wait_route_opened()
        # ESCRITURACAO: so aqui, depois do fluxo inteiro. O gate de caixa em
        # run() ainda pode reprovar a acao — e nesse caminho _restore_guard()
        # devolve a lista de rotas ao que era.
        self.routes.append({"from": origem, "to": dest, "flights": flights,
                            # ATENCAO (§31.8): `flights` aqui e o valor PEDIDO, NAO lido —
                            # e o unico campo do dicionario que ainda e crenca. check_route
                            # faz a conta de slots por ele, entao um toque de voo perdido
                            # desalinha a crenca em silencio.
                            "fare_level": p.get("fare_level", "mid"),
                            # LIDOS da tela, nao o que o modelo pediu (R4)
                            "planes": planes_reais, "aircraft": modelo})
        # Banner ainda nao catalogado: registrar o hash para que a proxima rota
        # partindo deste hub possa ser CONFERIDA em vez de suposta.
        nota = ""
        if banner_desconhecido:
            nota = (f" | banner de origem NAO catalogado (md5 {val}) — se esta rota realmente "
                    f"partiu de {origem}, acrescente ROUTE_ORIGIN_MD5['{val}'] = '{origem}'")
        return True, (
            f"rota {origem}->{dest}: aviao {idx} ({modelo or 'modelo nao identificado'}), "
            f"{planes_reais} aeronave(s) LIDAS na tela, {flights} voos/sem, "
            f"tarifa {p.get('fare_level','mid')}{nota}"
        )

    # --- ETAPA 3a: as duas alavancas que o modelo "controlava" sem ler a tela ---
    # MEDIDO 19/08 (logs/etapa3a/): o toque em lote deste executor PERDIA toques.
    # Com `_bump` + `b.batch` (settle de 25 frames por toque) k toques na tela de
    # quantidade davam 1+ceil(k/2) avioes: k=0..5 -> 1,2,2,3,3,4. Toque a toque,
    # esperando o frame ESTABILIZAR, os mesmos toques dao 1,2,3,4,5,6. O
    # parametro nunca esteve errado no jogo — estava errado no harness, e como
    # ninguem lia a tela de volta, ele reportava sucesso com o valor errado.
    def _frame_estavel(self, tag=None, tries=8, chunk=30):
        """Screenshot so depois de dois frames identicos (a caixinha anima)."""
        import hashlib

        prev = None
        caminho = None
        for _ in range(tries):
            self.b.advance(chunk)
            caminho = self.b.screenshot() if tag is None else self.g.shot(tag)
            atual = hashlib.md5(open(caminho, "rb").read()).hexdigest()
            if atual == prev:
                break
            prev = atual
        return Image.open(caminho).convert("RGB")

    def _pick_aircraft(self, idx, dest):
        """Anda ate `idx` na tela de aviao LENDO o modelo a cada toque.

        Devolve (ok, detalhe, modelo). MEDIDO: 1 toque Right = proximo modelo, e
        a lista tem exatamente os modelos que POSSUIMOS, na ordem de Info->fleet
        (MD100, A340 em _buy_entregue), com volta ao inicio no fim. Num savestate
        de um modelo so, TODOS os toques sao no-op — foi o caso em que o executor
        antigo "escolhia" 8 avioes diferentes sem nunca mudar de aviao.

        Pedir um indice >= ao numero de modelos NAO e traduzido para o resto da
        divisao em silencio: a acao e recusada dizendo quantos modelos existem.
        """
        from world import identify_route_plane, read_route_plane

        # O QUE E O GATE, E O QUE NAO E (corrigido antes de entrar em producao):
        # para andar no seletor basta DISTINGUIR uma tela da outra, e para isso
        # bastam alcance e assentos — digitos do atlas ja provado. Casar o aviao
        # com AIRCRAFT_CATALOG e outra coisa: o catalogo tem 8 modelos de
        # 1988-1998, e uma partida de 1970 voa DC-8/707. Exigir o catalogo aqui
        # recusaria TODA rota nesses cenarios, inclusive com o default idx=0,
        # que antes abria rota sem tocar em nada — o erro de "guard que recusa
        # demais" do §28. O catalogo fica so para NOMEAR o modelo no relato.
        def chave(img):
            _, alcance, assentos = read_route_plane(img)
            return None if (alcance is None or assentos is None) else (alcance, assentos)

        img = self._frame_estavel(f"rota_aviao_{dest}_0")
        k = chave(img)
        if k is None:
            return False, (f"rota {dest}: nao consegui LER alcance/assentos do aviao na tela "
                           f"(bruto={read_route_plane(img)}); recuso em vez de "
                           "escolher no escuro"), None
        vistos, nomes = [k], [identify_route_plane(img) or read_route_plane(img)[0]]
        for i in range(1, idx + 1):
            self.b.press("Right", hold=3, wait=14)
            img = self._frame_estavel(f"rota_aviao_{dest}_{i}")
            k = chave(img)
            if k is None:
                return False, (f"rota {dest}: tela de aviao ilegivel no toque {i} "
                               f"(bruto={read_route_plane(img)})"), None
            if k in vistos:
                return False, (f"rota {dest}: aircraft_index={idx} nao existe — o seletor "
                               f"cicla por {len(vistos)} modelo(s) que POSSUIMOS "
                               f"({nomes}) e no toque {i} ele voltou para "
                               f"{identify_route_plane(img) or k}. "
                               "Indices validos: 0.." + str(len(vistos) - 1) +
                               ". Compre outro modelo (buy_aircraft) para ter mais"), None
            vistos.append(k)
            nomes.append(identify_route_plane(img) or read_route_plane(img)[0])
        return True, "", nomes[-1]

    def _pick_planes(self, alvo, dest, max_toques=12):
        """Ajusta a QUANTIDADE de avioes lendo "x N" da tela a cada toque.

        Devolve (ok, detalhe, valor_lido). Base medida = 1; 1 toque = +1. O TETO
        e o numero de unidades DISPONIVEIS do modelo (6 no savestate do eval): no
        teto o toque nao faz nada e nao da a volta. Se o alvo nao for alcancavel,
        a acao e RECUSADA com o teto medido em vez de abrir a rota com outro
        numero — que era o que acontecia antes, sem ninguem perceber.
        """
        from world import on_route_qty_screen, read_route_planes, read_route_planes_pool

        img = self._frame_estavel(f"rota_qtd_{dest}_0")
        if not on_route_qty_screen(img):
            return False, (f"rota {dest}: esperava a tela de quantidade de avioes e "
                           "ela nao esta na tela; recuso"), None
        atual = read_route_planes(img)
        if atual is None:
            return False, f"rota {dest}: nao consegui LER quantos avioes a tela mostra", None
        for i in range(max_toques):
            if atual == alvo:
                pool = read_route_planes_pool(img)
                return True, f"quantidade {atual} (piscina restante {pool})", atual
            if atual > alvo:
                return False, (f"rota {dest}: a tela ja mostra {atual} avioes e o pedido e "
                               f"{alvo}; este seletor so sobe (nao foi medido como descer)"), atual
            self.b.press("Right", hold=3, wait=14)
            img = self._frame_estavel(f"rota_qtd_{dest}_{i+1}")
            novo = read_route_planes(img)
            if novo is None:
                return False, f"rota {dest}: tela de quantidade ilegivel no toque {i+1}", atual
            if novo == atual:
                return False, (f"rota {dest}: planes={alvo} recusado — a tela travou em "
                               f"{atual} aviao(oes). O teto MEDIDO desta tela e o numero de "
                               f"unidades DISPONIVEIS do modelo escolhido "
                               f"(piscina restante={read_route_planes_pool(img)}); "
                               "compre mais unidades ou peca menos"), atual
            atual = novo
        return False, (f"rota {dest}: nao cheguei a planes={alvo} em {max_toques} toques "
                       f"(parei em {atual})"), atual

    def _wait_route_opened(self, budget=OPEN_ANIM_FRAMES, chunk=60, polls=8):
        """Espera a animacao de abertura terminar — o jogo volta ao menu SOZINHO.

        MEDIDO (probe_flow14.py tail NA06): do A de confirmacao ate o menu
        principal passam-se **420 frames sem apertar tecla nenhuma**. O valor
        antigo aqui era um `advance(240)` cego, que devolvia o controle no meio
        da animacao e deixava o `_ensure_menu` apertando B em cima dela — o
        mesmo padrao de "tecla emitida na tela errada" que ja tinha quebrado a
        acao SEGUINTE duas vezes (§12.8c).

        Espera-se o grosso de uma vez (sem screenshot, que custa ~0.4s) e so
        entao confirma por imagem, para nao amarrar a macro a um numero fixo:
        uma animacao mais longa em outra rota continua coberta pelo poll.
        """
        from world import at_main_menu_img

        self.b.advance(budget)
        for _ in range(polls):
            if at_main_menu_img(Image.open(self.b.screenshot()).convert("RGB")):
                return True
            self.b.advance(chunk)
        return False

    # --- edicao de rota existente (comando r0c1) --------------------------
    def _route_tab_index(self, img=None):
        """Le qual aba da barra de r0c1 esta destacada (indice em ROUTE_TAB_NAMES).

        CALIBRADO 17/08 (revisao 2 — ver aviso em ROUTE_TAB_BOUNDS): amostra
        UMA linha (ROUTE_TAB_ROW_Y, acima do texto) e usa so o canal G, que
        separa destacado (~103-107) de nao-destacado (~41-52) com folga
        grande — inclusive para SET, cujas letras brancas inflavam a soma
        R+G+B da 1a versao mesmo sem destaque. Validado 7/7 contra as 7
        celulas com destaque conhecido, incluindo Susp e Close.
        """
        if img is None:
            img = Image.open(self.b.screenshot()).convert("RGB")
        px = img.load()
        means = []
        for i in range(7):
            x0, x1 = ROUTE_TAB_BOUNDS[i], ROUTE_TAB_BOUNDS[i + 1]
            total, n = 0, 0
            for x in range(x0, x1):
                _, g, _ = px[x, ROUTE_TAB_ROW_Y]
                total += g
                n += 1
            means.append(total / n)
        return means.index(max(means))

    def _route_tab_to(self, target_name, tries=8):
        """Move o destaque da barra de abas ate `target_name`, UM toque por vez,
        conferindo a celula destacada a cada toque — malha fechada, no molde de
        `switch_to_region` (um R engolido bastou para pedir a regiao errada)."""
        idx_alvo = ROUTE_TAB_NAMES.index(target_name)
        for _ in range(tries):
            atual = self._route_tab_index()
            if atual == idx_alvo:
                return True
            direcao = "Right" if idx_alvo > atual else "Left"
            self.b.press(direcao, hold=3, wait=14)
            self.b.advance(50)
        return self._route_tab_index() == idx_alvo

    def _crop_hash(self, box):
        import hashlib

        img = Image.open(self.b.screenshot()).convert("RGB")
        return hashlib.md5(img.crop(box).tobytes()).hexdigest()[:8]

    def _bump_field_capped(self, box, direction, times, stall_limit=2):
        """Right/Left dentro do editor de campo (Flts/Fare), parando cedo se o
        recorte do VALOR nao mudar por `stall_limit` toques seguidos.

        MEDIDO 17/08: Flts tem um TETO POR ROTA que a criacao de rota nao tem
        (Havana trava em 1 voo mesmo com 3 avioes; Washington-San Fran trava em
        2) — sem essa deteccao a macro reportaria "+2" tendo movido so 1 e
        mentiria sobre o estado do jogo (Regra 2). Devolve quantos toques
        REALMENTE mudaram o valor exibido.
        """
        moved = 0
        stall = 0
        for _ in range(times):
            before = self._crop_hash(box)
            self.b.press(direction, hold=5, wait=30)
            self.b.advance(80)
            after = self._crop_hash(box)
            if after == before:
                stall += 1
                if stall >= stall_limit:
                    break
            else:
                moved += 1
                stall = 0
        return moved

    def _do_adjust_route(self, p):
        """AJUSTA Flts (voos/semana) e/ou Fare (tarifa) de uma rota JA ABERTA.

        E a alavanca de reacao ao feedback que faltava: ate 17/08 o modelo
        abria uma rota e nunca podia corrigi-la.

        CALIBRADO 17/08 (probe_hub_open_sa.state, Washington-Havana, e
        _edit_2rotas.state, Washington-San Fran; evidencia em logs/edit_commit
        e logs/edit_sa): a alavanca e A MESMA da criacao — 1 toque = +1
        voo/semana (FLIGHTS_PER_STEP), 1 toque = +5% de tarifa
        (FARE_PCT_PER_STEP; confirmado $720->$792 com 2 toques = exatamente
        "10% above avg.") — mas com um TETO POR ROTA que a criacao nao expõe:
        o campo Flts para de responder ao Right sem aviso nenhum. Medido: a
        rota de Havana trava em 1 voo mesmo depois de subir Planes de 1 para 3
        (o teto NAO escala com Planes); a rota de San Fran trava em 2. O teto
        segue NAO CARACTERIZADO (suspeita: slots livres no destino, nao
        confirmado) — o harness detecta por hash do valor exibido em vez de
        inventar um numero.

        Fluxo medido (screenshots em logs/edit_commit/a_..l_*.png):
          route_edit -> resumo da rota (A) -> barra de abas (A, comeca em
          Model) -> Right/Left ate a aba alvo -> A ativa o campo -> Right/Left
          ajusta -> A confirma o campo (volta a barra, AINDA SEM COMMITAR) ->
          Right ate SET -> A -> "Is it OK to change this flight as shown?"
          (YES/NO, cursor comeca em YES) -> A commita e VOLTA AO RESUMO.
          PERSISTENCIA CONFIRMADA: saida completa ate o MENU PRINCIPAL (6x B)
          e reabertura de route_edit mostraram Fare $792/10% e Flts 2 intactos
          — nao e um buffer de tela (logs/edit_commit/n_reopen_summary.png).

        LIMITACAO DELIBERADA: so opera sobre a rota que o jogo mostra por
        padrao ao abrir route_edit. A navegacao entre rotas ("SEL" no
        ACTION_SPACE.md antigo) NAO foi encontrada — a celula extra medida e
        'SET' (commit), nao uma lista. Com mais de uma rota aberta a acao
        RECUSA, porque escolher a errada seria silencioso.
        """
        from world import city_region

        dest = p.get("route") or p.get("to")
        if not dest:
            return False, "adjust_route sem 'route' (destino da rota a editar)"
        alvo = next((r for r in self.routes if r.get("to") == dest), None)
        if alvo is None:
            return False, f"adjust_route: nenhuma rota aberta para {dest} (rotas: {self.routes})"
        if len(self.routes) > 1:
            return False, (
                f"adjust_route({dest}) recusado: ha {len(self.routes)} rotas abertas e o "
                "harness ainda nao sabe navegar a lista para escolher uma especifica (so a "
                "rota default-mostrada foi calibrada) — risco de editar a rota ERRADA em "
                "silencio"
            )

        flights_target = p.get("flights_week")
        fare_target = p.get("fare_level")
        if flights_target is None and fare_target is None:
            return False, "adjust_route sem 'flights_week' nem 'fare_level' — nada a fazer"
        if fare_target is not None and fare_target not in FARE_STEPS:
            return False, f"adjust_route: fare_level invalido {fare_target!r} (use low/mid/high)"

        self._ensure_menu()
        origem = alvo.get("from")
        if origem:
            ok_reg, det_reg = self._goto_region(city_region(origem))
            if not ok_reg:
                self._restore_guard()
                return False, f"adjust_route({dest}): {det_reg} — estado restaurado"

        self.g.open_cmd("route_edit")
        wait_text(self.b)
        self.b.advance(60)
        # ETAPA 2-OraculosFracos: LEITURA DE ENTRADA do resumo. O que a
        # escrituracao (`alvo`) diz que a rota tem e CRENCA do harness; o que
        # vale e a tela. Sem isto o "pedido 1->3" era comparado contra um numero
        # que ninguem nunca leu.
        antes_tela = world.read_route_summary(
            Image.open(self.g.shot(f"adjust_resumo_antes_{dest}")).convert("RGB"))
        self.b.press("A", hold=5, wait=25)   # resumo -> barra de abas
        self.b.advance(80)
        if self._route_tab_index() != ROUTE_TAB_NAMES.index("model"):
            shot = self.g.shot(f"adjust_travou_abrir_{dest}")
            self._restore_guard()
            return False, (f"adjust_route({dest}): a barra de abas nao abriu no estado "
                           f"esperado (tela={shot}); estado restaurado — SUSPEITA: mais de "
                           "uma rota e o jogo mostrou outra por padrao")

        notas = []
        # Preferir o NUMERO LIDO da tela ao numero da escrituracao (R4).
        flights_before = alvo.get("flights", FLIGHTS_BASE)
        if antes_tela["flights"] is not None:
            if antes_tela["flights"] != flights_before:
                notas.append(f"Flts na TELA era {antes_tela['flights']}, escrituracao dizia "
                             f"{flights_before} — vale a tela")
            flights_before = antes_tela["flights"]
        fare_before = alvo.get("fare_level", "mid")
        # `bateu_teto`: o executor DECLARA teto so quando `_bump_field_capped`
        # parou cedo. O oraculo do teste exige essa declaracao para aceitar um
        # valor lido menor que o pedido.
        flts_bateu_teto = False
        fare_bateu_teto = False

        if flights_target is not None:
            delta = int(flights_target) - int(flights_before)
            if delta == 0:
                notas.append(f"Flts: ja em {flights_before}, nada a fazer")
            else:
                if not self._route_tab_to("flts"):
                    shot = self.g.shot(f"adjust_semflts_{dest}")
                    self._restore_guard()
                    return False, f"adjust_route({dest}): nao cheguei na aba Flts (tela={shot})"
                self.b.press("A", hold=5, wait=25)
                self.b.advance(80)
                direcao = "Right" if delta > 0 else "Left"
                moved = self._bump_field_capped(FLTS_VALUE_BOX, direcao, abs(delta))
                self.b.press("A", hold=5, wait=25)   # confirma o campo (ainda nao commita)
                self.b.advance(80)
                achieved = flights_before + (moved if delta > 0 else -moved)
                alvo["flights"] = achieved
                if moved < abs(delta):
                    flts_bateu_teto = True
                    notas.append(
                        f"Flts: pedido {flights_before}->{flights_target}, TETO em {achieved} "
                        f"({moved}/{abs(delta)} toques efetivos — a rota nao aceita mais "
                        "voos/semana, teto nao caracterizado)"
                    )
                else:
                    notas.append(f"Flts: {flights_before} -> {achieved} ({moved} toque(s))")

        if fare_target is not None:
            delta = FARE_STEPS[fare_target] - FARE_STEPS.get(fare_before, 0)
            if delta == 0:
                notas.append(f"Fare: ja em {fare_before}, nada a fazer")
            else:
                if not self._route_tab_to("fare"):
                    shot = self.g.shot(f"adjust_semfare_{dest}")
                    self._restore_guard()
                    return False, f"adjust_route({dest}): nao cheguei na aba Fare (tela={shot})"
                self.b.press("A", hold=5, wait=25)
                self.b.advance(80)
                direcao = "Right" if delta > 0 else "Left"
                moved = self._bump_field_capped(FARE_VALUE_BOX, direcao, abs(delta))
                self.b.press("A", hold=5, wait=25)
                self.b.advance(80)
                if moved == abs(delta):
                    alvo["fare_level"] = fare_target
                    notas.append(f"Fare: {fare_before} -> {fare_target} ({moved} toque(s))")
                else:
                    fare_bateu_teto = True
                    notas.append(
                        f"Fare: pedido {fare_before}->{fare_target}, TETO em "
                        f"{moved}/{abs(delta)} toques efetivos"
                    )

        if not self._route_tab_to("set"):
            shot = self.g.shot(f"adjust_semset_{dest}")
            self._restore_guard()
            return False, f"adjust_route({dest}): nao cheguei em SET (tela={shot})"
        self.b.press("A", hold=5, wait=25)
        self.b.advance(150)
        wait_text(self.b)
        self.b.press("A", hold=5, wait=25)   # YES em "change this flight as shown?"
        self.b.advance(200)
        wait_text(self.b)

        # ETAPA 2-OraculosFracos: LEITURA DE VOLTA. O commit devolve ao RESUMO
        # (calibrado 17/08), entao os dois campos que a acao mexe estao na tela
        # agora. Ate aqui o harness devolvia ok=True com base nas suas proprias
        # contagens de toque — o "Flts 1->3" do §17 nunca foi lido de ninguem.
        depois_tela = world.read_route_summary(
            Image.open(self.g.shot(f"adjust_resumo_depois_{dest}")).convert("RGB"))

        if not self._ensure_menu():
            self._restore_guard()
            return False, f"adjust_route({dest}): nao voltou ao menu apos SET; estado restaurado"

        # --- oraculo: o VALOR LIDO tem que bater com o pedido, OU com o teto
        #     que o executor DECLAROU ter batido. Tela ilegivel = NAO MEDI (R1),
        #     e nao-medido nao vira ok=True (R5).
        if not depois_tela["on_summary"]:
            self._restore_guard()
            return False, (f"adjust_route({dest}): NAO MEDIDO — a tela apos o commit nao e "
                           "o resumo da rota; efeito nao verificado, estado restaurado")

        falhas = []
        if flights_target is not None:
            lido = depois_tela["flights"]
            if lido is None:
                falhas.append("Flts NAO MEDIDO (digito ilegivel no resumo)")
            elif lido == int(flights_target):
                notas.append(f"Flts LIDO DE VOLTA = {lido} (== pedido)")
            elif flts_bateu_teto and lido == alvo.get("flights"):
                notas.append(f"Flts LIDO DE VOLTA = {lido} (TETO da rota, pedido era "
                             f"{flights_target}) — teto medido na tela, nao inferido")
            else:
                falhas.append(f"Flts lido {lido}, pedido {flights_target}, executor "
                              f"achava {alvo.get('flights')} (teto declarado="
                              f"{flts_bateu_teto})")
            alvo["flights"] = lido if lido is not None else alvo.get("flights")

        if fare_target is not None:
            pct_lido = depois_tela["fare_pct"]
            pct_alvo = FARE_STEPS[fare_target] * world.FARE_PCT_PER_SEG
            if pct_lido is None:
                falhas.append("Fare NAO MEDIDO (barra ilegivel)")
            elif pct_lido == pct_alvo:
                notas.append(f"Fare LIDO DE VOLTA = {pct_lido:+d}% "
                             f"({depois_tela['fare_segs']} segmentos, == pedido {fare_target})")
            elif fare_bateu_teto:
                notas.append(f"Fare LIDO DE VOLTA = {pct_lido:+d}% (TETO; pedido "
                             f"{fare_target} = {pct_alvo:+d}%)")
            else:
                falhas.append(f"Fare lido {pct_lido:+d}%, pedido {fare_target} "
                              f"({pct_alvo:+d}%), antes {antes_tela['fare_pct']}%")

        if falhas:
            return False, (f"adjust_route({dest}) EXECUTOU MAS NAO CONFERE: "
                           + "; ".join(falhas) + " | " + "; ".join(notas))

        return True, f"adjust_route({dest}): " + "; ".join(notas)

    def _bump(self, direction, times):
        """Move um seletor/slider N vezes (0 = mantem o padrao do jogo).

        NAO CALIBRADO: nao foi medido quantos toques valem uma unidade em cada
        slider. Com os padroes (idx=0, planes=1, flights=1, fare=mid) nenhum
        toque e emitido, que e o caso provado.
        """
        seq = []
        for _ in range(max(0, times)):
            seq += self.b.seq_press(direction, hold=3, wait=14) + self.b.seq_advance(20)
        return seq

    def _staff_px(self, tag, tries=3):
        """Pixels de texto no painel do funcionario (0 = ocioso). Ver world.

        NAO E MAIS O GATE de `negotiate_slots` (16/08): o painel Area/Type/Wait
        descreve APENAS o funcionario destacado, que e sempre o 0. A partir da
        2a negociacao do turno quem sai e outro, o painel nao muda e a acao
        seria reprovada tendo funcionado. O gate passou a ser
        `_menu_free_staff()`. Fica aqui porque continua sendo a unica leitura
        que diz PARA ONDE e POR QUANTO TEMPO o funcionario 0 foi.

        Devolve (px, caminho) ou (None, caminho) se a tela lida NAO for a de
        staff — depois do fim de turno o jogo intercala mensagens do assessor e
        a navegacao cai noutra tela. Ler 0px dali fez o harness declarar uma
        negociacao "concluida" que seguia em andamento.
        """
        from world import on_staff_screen, staff_panel_px

        shot = None
        for _ in range(tries):
            self._ensure_menu()
            shot = self.g.info_screen("staff", tag)
            img = Image.open(shot).convert("RGB")
            if on_staff_screen(img):
                self._ensure_menu()
                return staff_panel_px(img), shot
        self._ensure_menu()
        return None, shot

    def _menu_free_staff(self, tries=3):
        """Funcionarios livres lidos do MENU PRINCIPAL (bonecos da barra).

        MEDIDO 16/08: 23 px por boneco, 4 livres = 92 px, 3 livres = 69 px
        (logs/staffpick/c_menu_zero_neg.png x c_menu_uma_neg.png). E o sinal de
        efeito correto para a negociacao: cumulativo (cai 1 por despacho) e de
        graca — o menu principal ja precisa ser fotografado por _ensure_menu.
        Substitui a leitura do painel Info->staff, que descreve APENAS o
        funcionario destacado (sempre o 0) e por isso nao muda quando quem sai
        e o 2o ou o 3o — falso negativo garantido a partir da 2a negociacao.
        """
        from world import at_main_menu_img, free_staff_menu

        for _ in range(tries):
            self._ensure_menu()
            img = Image.open(self.b.screenshot()).convert("RGB")
            if at_main_menu_img(img):
                return free_staff_menu(img)
            self.b.advance(60)
        return None

    def _pick_free_staff(self, tries=4):
        """Poe o destaque da tela de negociacao sobre um funcionario NA BASE.

        CAUSA RAIZ da falha "a 2a negociacao do turno nao acontece" (medida ao
        vivo em 16/08, logs/neg2/): a macro apertava A as cegas com o destaque
        parado no funcionario 0. Depois da 1a negociacao ele esta em missao e o
        jogo responde "Sorry, I'm busy making a bid for some airport slots" sem
        sair da tela; os A's seguintes se perdiam ali e a acao so quebrava tres
        passos depois, em `activate_cursor`, como "cursor do mapa nao respondeu".

        Devolve (ok, celula, detalhe).
        """
        from world import staff_action_is_bid, staff_free_cells, staff_sel_cell

        img = Image.open(self.b.screenshot()).convert("RGB")
        livres = staff_free_cells(img)
        if not livres:
            return False, None, "todos os funcionarios estao em missao"
        alvo = livres[0]
        for _ in range(tries):
            sel = staff_sel_cell(img)
            if sel is None:
                # o destaque so e desenhado quando a tela assenta; medido:
                # ausente na 1a foto apos open_cmd, presente logo depois.
                self.b.advance(30)
                img = Image.open(self.b.screenshot()).convert("RGB")
                continue
            if sel == alvo:
                break
            dr, dc = alvo[0] - sel[0], alvo[1] - sel[1]
            seq = []
            if dr:
                seq += self.b.seq_press("Down" if dr > 0 else "Up", hold=3, wait=14, times=abs(dr))
            if dc:
                seq += self.b.seq_press(
                    "Right" if dc > 0 else "Left", hold=3, wait=14, times=abs(dc)
                )
            self.b.batch(seq + self.b.seq_advance(30), extra_frames=200)
            img = Image.open(self.b.screenshot()).convert("RGB")
        sel = staff_sel_cell(img)
        if sel != alvo:
            return False, None, f"destaque nao chegou em {alvo} (ficou em {sel}); livres={livres}"
        # TRAVA DE SEGURANCA: a celula (1,2) NAO e funcionario — pousar nela
        # troca a acao para **Return** e o A abre "Return which city's slots?".
        # Uma negociacao que virasse devolucao de slots destruiria a partida em
        # silencio. Medido em logs/staffpick/c_celula5*.png.
        bid = staff_action_is_bid(img)
        if bid is not True:
            return False, None, (
                f"acao selecionada nao e Bid (bid={bid}, celula={sel}) — abortado "
                "para nao devolver slots"
            )
        return True, alvo, f"funcionario {alvo}, livres={livres}"

    def _pick_free_staff_single(self, tries=4):
        """Como `_pick_free_staff`, mas SEM a trava Bid/Return.

        MEDIDO 18/08 (ETAPA 10-Marketing): a tela de despacho de `ad_campaign`
        ("Who will you send to conduct an ad campaign?") tem a MESMA grade
        4x2 de funcionarios, mas NAO tem o par de acoes Bid/Return na esquerda
        (label "Area/Type/Wait" no lugar) — `staff_action_is_bid` le 0px em
        BID_BOX e 0px em RETURN_BOX nessa tela (ambigua, `None`), entao a
        trava de `_pick_free_staff` aborta sempre, mesmo com a selecao certa
        (`logs/run_f0/adcamp_semstaff.png`). Como esta tela so tem UMA acao
        possivel (nao ha equivalente destrutivo de "Return" aqui), a trava
        nao se aplica — usar esta variante para qualquer comando cuja tela de
        despacho nao seja negociar (r0c2) ou hub regional (r1c0).
        """
        from world import staff_free_cells, staff_sel_cell

        img = Image.open(self.b.screenshot()).convert("RGB")
        livres = staff_free_cells(img)
        if not livres:
            # MEDIDO 18/08: nem sempre e "funcionarios ocupados". Numa regiao
            # sem NENHUMA rota nossa, `ad_campaign` recusa ANTES do seletor de
            # funcionario, com uma tela totalmente diferente ("We can't run an
            # ad campaign in North America. We don't have any routes there.",
            # `logs/run_f0/adcamp_semstaff.png` — cash intocado, so texto) —
            # essa tela tambem nao tem cracha nenhum, entao cai aqui do mesmo
            # jeito. Nao afirmar qual das duas causas foi sem inspecionar a
            # tela; quem chama deve tratar como recusa generica.
            return False, None, ("nenhum funcionario livre detectado (funcionarios "
                                  "ocupados OU recusa antes do seletor, ex.: sem "
                                  "rotas na regiao)")
        alvo = livres[0]
        for _ in range(tries):
            sel = staff_sel_cell(img)
            if sel is None:
                self.b.advance(30)
                img = Image.open(self.b.screenshot()).convert("RGB")
                continue
            if sel == alvo:
                break
            dr, dc = alvo[0] - sel[0], alvo[1] - sel[1]
            seq = []
            if dr:
                seq += self.b.seq_press("Down" if dr > 0 else "Up", hold=3, wait=14, times=abs(dr))
            if dc:
                seq += self.b.seq_press(
                    "Right" if dc > 0 else "Left", hold=3, wait=14, times=abs(dc)
                )
            self.b.batch(seq + self.b.seq_advance(30), extra_frames=200)
            img = Image.open(self.b.screenshot()).convert("RGB")
        sel = staff_sel_cell(img)
        if sel != alvo:
            return False, None, f"destaque nao chegou em {alvo} (ficou em {sel}); livres={livres}"
        return True, alvo, f"funcionario {alvo}, livres={livres}"

    def _read_gauge_stable(self, tentativas=10, quiesce=240):
        """(escolhidos, teto) do medidor de slots, exigindo leitura QUIESCENTE.

        MEDIDO (logs/run_f0/neg_EU11.png, dump ASCII 23/08): o medidor e
        desenhado de cima para baixo e um frame pego no meio mostra o primeiro
        boneco cortado na linha 182 e NENHUMA outra posicao. Nesse frame o
        gabarito recusa (None) — mas um frame ADIANTE, com o primeiro boneco ja
        inteiro e os demais ainda por desenhar, casa perfeitamente como
        (1 escolhido, teto 1): ordem valida, tall>=1, e ate a soma de pixels
        confere (43+88=131 e de fato o que esta na tela naquele instante).
        Ou seja: uma leitura bem-formada NAO prova que o desenho acabou.

        Por isso "duas leituras iguais separadas por advance(60)" NAO basta:
        se houver qualquer pausa entre figuras maior que 60 frames, o par igual
        e um par de SUB-LEITURAS, o teto sai 1, e a acao recusa um pedido legal
        com uma mensagem indistinguivel de "esta cidade so tem 1 posicao" — e a
        causa de N nao foi medida, entao ninguem consegue desmentir. Depois do
        primeiro par igual esperamos `quiesce` frames (4x o passo) e exigimos a
        MESMA leitura: so ai "igual" vira "parado".
        Devolve None se nunca estabilizou (recusa visivel, R5).
        """
        anterior = None
        for _ in range(tentativas):
            atual = world.read_slots_gauge(
                Image.open(self.b.screenshot()).convert("RGB"))
            if atual is not None and atual == anterior:
                self.b.advance(quiesce)
                confirma = world.read_slots_gauge(
                    Image.open(self.b.screenshot()).convert("RGB"))
                if confirma == atual:
                    return atual
                # ainda estava desenhando: recomeca a partir do que se viu agora
                anterior = confirma
                continue
            anterior = atual
            self.b.advance(60)
        return None

    def _do_negotiate_slots(self, p):
        from world import on_map_screen

        cid = p.get("city")
        if not cid:
            return False, "negotiate_slots sem cidade"
        # ETAPA 3b-a (19/08, CALIBRATION §32): a QUANTIDADE de slots e uma
        # alavanca real (medidor de 5 bonequinhos, 1 Right = +1, teto 5 sem
        # wrap). Ate aqui a macro aceitava o padrao sem nunca ter olhado a tela.
        slots = p.get("slots", world.SLOTS_MIN)
        if (not isinstance(slots, int) or isinstance(slots, bool)
                or not (world.SLOTS_MIN <= slots <= world.SLOTS_MAX)):
            return False, (f"negotiate_slots: slots={slots!r} fora do alcance "
                           f"{world.SLOTS_MIN}..{world.SLOTS_MAX} (MEDIDO: o "
                           "medidor satura em 5 e nao da a volta)")
        livres_antes = self._menu_free_staff()
        if livres_antes is None:
            return False, f"negociacao em {cid}: nao consegui ler a barra de funcionarios do menu"
        if livres_antes == 0:
            return False, (
                f"negociacao em {cid} impossivel: nenhum funcionario livre "
                "(os 4 estao em missao). Passe o turno para eles voltarem."
            )
        self.g.open_cmd("negotiate")
        wait_text(self.b)
        ok_sel, celula, det_sel = self._pick_free_staff()
        if not ok_sel:
            shot = self.g.shot(f"neg_semstaff_{cid}")
            return False, f"negociacao em {cid}: {det_sel} (tela={shot})"
        # A ate CHEGAR AO MAPA. Contagem fixa de A's nao serve: o jogo engole os
        # que caem durante a datilografia. Para assim que o mapa aparece, senao
        # o proximo A selecionaria uma cidade ao acaso.
        for _ in range(5):
            wait_text(self.b)
            self.b.press("A", hold=5, wait=25)
            self.b.advance(STEP_SETTLE)
            if on_map_screen(Image.open(self.b.screenshot()).convert("RGB")):
                break
        else:
            shot = self.g.shot(f"neg_semmapa_{cid}")
            return False, f"negociacao em {cid}: nao chegou ao mapa apos {det_sel} (tela={shot})"
        # POSICIONA o cursor e aperta A **uma vez**, com leitura de volta.
        # NAO usar _select_city aqui (ETAPA 3b, medido em logs/etapa3b/s00_*):
        # ele martela A "ate sair do mapa", e `on_map_screen` devolve True TAMBEM
        # na tela "How many slots?" e na de confirmacao — ou seja, ele atravessava
        # as duas e a negociacao ja saia fechada de dentro dele, no padrao. Os dois
        # _step() seguintes caiam no seletor de funcionario ("Sorry, I'm busy...").
        reg, pos, verif = point_cursor_at_world(self.b, cid, self.map_region)
        self.map_region = reg
        # UM unico A, e depois SO LEITURA. Medido 19/08 (ETAPA 3b, primeira
        # tentativa ao vivo): com "aperta A ate reconhecer", o A da tela de
        # quantidade caiu enquanto o texto ainda datilografava, o medidor leu
        # None, e os dois A's seguintes ATRAVESSARAM a quantidade e o YES/NO —
        # a negociacao fechou no padrao e a macro reportou "medidor ilegivel"
        # (logs/run_f0/neg_semqtd_NA14.png). Insistir com A numa tela que talvez
        # ja seja outra e exatamente o padrao que R2 proibe. Agora a insistencia
        # e so no OLHO: se o medidor nao aparecer, a acao falha e o savestate
        # volta — falha visivel e barata em vez de negociacao errada silenciosa.
        wait_text(self.b)
        self.b.press("A", hold=5, wait=25)
        self.b.advance(STEP_SETTLE)
        wait_text(self.b)
        gauge = self._read_gauge_stable()
        lido, teto = (None, None) if gauge is None else gauge
        if lido is None:
            shot = self.g.shot(f"neg_semqtd_{cid}")
            # DIAGNOSTICO: _select_city (que esta rotina substituiu) sabia
            # distinguir "o jogo RECUSOU a cidade" (continuamos no mapa) de
            # qualquer outra falha. Sem esta bifurcacao toda recusa apareceria
            # como "medidor ilegivel" — sintoma tres telas depois da causa, o
            # padrao que este arquivo inteiro existe para evitar.
            ainda_no_mapa = on_map_screen(Image.open(self.b.screenshot()).convert("RGB"))
            self._restore_guard()
            if ainda_no_mapa:
                return False, (f"negociacao em {cid}: o jogo nao saiu do mapa apos o A "
                               f"— cidade recusada ou nada sob o cursor (cursor={pos}, "
                               f"regiao_verificada={verif}) — savestate restaurado "
                               f"(tela={shot})")
            return False, (f"negociacao em {cid}: saiu do mapa mas nao reconheci a tela "
                           f"'How many slots?' (medidor ilegivel) — savestate "
                           f"restaurado (tela={shot})")
        # EVIDENCIA: esta tela traz o NOME e o pais da cidade no cabecalho. E a
        # unica prova disponivel de que a negociacao pegou a cidade certa — o
        # lance por slots nao debita o caixa na hora (so no fechamento do
        # trimestre), entao o gate de caixa nao serve aqui.
        shot = self.g.shot(f"neg_{cid}")
        # TETO POR CIDADE (ETAPA 1-RegressaoSlots, 23/08): o medidor tem N
        # posicoes e N MUDA POR CIDADE (Denver ja foi visto com 2 e com 3;
        # Phoenix/Philadelphia com 5). Pedir mais que N nao e negociavel: o
        # loop de Right abaixo bateria no teto e a acao fecharia com menos slots
        # que o modelo pediu — mentir para o modelo e pior que recusar (R5).
        # A mensagem descreve o que foi LIDO; o que fixa N nao foi medido e por
        # isso nao e afirmado (nao e "slots livres": Denver 24/94 deu N=2 e
        # Phoenix 5/53 deu N=5).
        if slots > teto:
            shot_teto = self.g.shot(f"neg_teto_{cid}")
            self._restore_guard()
            return False, (f"negociacao em {cid} RECUSADA: o medidor desta tela tem "
                           f"{teto} posicao(oes) (teto LIDO DA TELA), e o pedido foi "
                           f"{slots} slot(s). Peca no maximo {teto} nesta cidade — "
                           f"savestate restaurado (tela={shot_teto})")
        # AJUSTE: 1 Right = +1 slot, LIDO DE VOLTA a cada toque (R4). Toque que
        # nao mexe no medidor e falha, nao "tentar de novo as cegas".
        for _ in range(slots - lido):
            antes_q = lido
            self.b.press("Right", hold=3, wait=20)
            # LEITURA DE VOLTA ESTAVEL, nao um unico frame (ETAPA 1-RegressaoSlots,
            # 23/08): a leitura inicial ja ganhava 10 tentativas por causa do
            # desenho progressivo, mas esta aqui era single-shot depois de um
            # advance(60) — o mesmo frame no meio do desenho que motivou
            # `_read_gauge_stable` derrubaria a negociacao com "o medidor parou",
            # sintoma que aponta para o jogo quando a causa e o obturador. O teto
            # tambem e reconferido: o Right nao pode mexer no numero de posicoes.
            g2 = self._read_gauge_stable()
            lido = None if g2 is None else g2[0]
            if lido is None or lido <= antes_q or g2[1] != teto:
                shot_q = self.g.shot(f"neg_qtd_travou_{cid}")
                self._restore_guard()
                if g2 is not None and g2[1] != teto:
                    return False, (f"negociacao em {cid}: o teto do medidor mudou de "
                                   f"{teto} para {g2[1]} durante o ajuste — leitura "
                                   f"instavel, nada foi negociado, savestate "
                                   f"restaurado (tela={shot_q})")
                return False, (f"negociacao em {cid}: o medidor parou em {antes_q} "
                               f"e nao foi para {antes_q + 1} (alvo {slots}) — "
                               f"savestate restaurado (tela={shot_q})")
        if lido != slots:
            shot_q = self.g.shot(f"neg_qtd_errada_{cid}")
            self._restore_guard()
            return False, (f"negociacao em {cid}: medidor em {lido}, pedido {slots} "
                           f"— savestate restaurado (tela={shot_q})")
        shot_qtd = self.g.shot(f"neg_qtd_{cid}_{slots}")
        # A -> "Negotiations should take N months. Shall we negotiate?" (YES/NO)
        # A -> "I will begin negotiations."
        # MEDIDO 13/08: um BATCH de A's aqui NAO conclui — os A's caem durante a
        # datilografia e sao engolidos. _step() aperta ate a PERGUNTA mudar.
        for etapa in ("confirmacao de meses", "YES/NO"):
            if not self._step():
                shot = self.g.shot(f"neg_travou_{cid}_{etapa.split()[0]}")
                # ETAPA 1-RegressaoSlots: este ramo saia SEM restaurar — deixava
                # a partida parada numa tela de dialogo a meio caminho.
                self._restore_guard()
                return False, (f"negociacao em {cid}: fluxo travou na tela de {etapa} "
                               f"— savestate restaurado (tela={shot})")
        # VERIFICACAO DE EFEITO: um funcionario a MENOS na base.
        # A leitura insiste antes de declarar fracasso — logo apos o "I will
        # begin negotiations." o jogo ainda esta voltando do mapa e a barra pode
        # ser fotografada antes de atualizar. Falso NEGATIVO e tao corrosivo
        # quanto falso positivo: descartaria uma negociacao paga (MEDIDO 15/08
        # com o antigo gate de painel, CALIBRATION §15c).
        livres_depois = None
        for _ in range(3):
            self.b.advance(180)
            livres_depois = self._menu_free_staff()
            if livres_depois is not None and livres_depois < livres_antes:
                break
        menu_shot = self.g.shot(f"staff_bar_{cid}")
        detalhe = (f"{cid} (regiao {REGION_NAMES[reg]}, cursor={pos}, "
                   f"regiao_verificada={verif}, {det_sel}, slots pedidos={slots} "
                   f"LIDOS DE VOLTA={lido} de teto={teto} (tela={shot_qtd}), tela={shot}, "
                   f"barra={menu_shot}, funcionarios livres {livres_antes} -> {livres_depois})")
        if livres_depois is None or livres_depois >= livres_antes:
            return False, f"negociacao SEM EFEITO em {detalhe}"
        return True, f"negociacao iniciada em {detalhe}"

    def _do_return_slots(self, p):
        """Devolve slots negociados em uma cidade (r0c2, aba Return, ETAPA 6-Reversos).

        CALIBRADO 17/08 (CALIBRATION §17.1): a tela de negociacao (staff picker,
        grade 2x2) tem 4 funcionarios + Return em (1,2). Navegacao: sem wrap.

        A celula (1,2) = Return. `A` nela abre "Return which city's slots?"
        Depois: mapa com cidade alvo, confirmacao YES/NO, volta ao menu.

        Params:
          city (str): qual cidade devolve slots

        ORACULO CORRIGIDO 24/08 (ETAPA 2-OraculosFracos). O oraculo antigo era
        "funcionarios livres +1" e estava ERRADO POR CONSTRUCAO: quem despacha
        funcionario e `negotiate_slots` (§17.2, o cracha sai da celula e pousa
        no mapa); devolver slot e transacao imediata e nunca recrutou ninguem.
        Por isso o §17.1 registrava 3 -> 3 (+0) em 2 corridas: o oraculo estava
        morto, nao a acao.

        E, revendo as capturas dessas MESMAS duas corridas
        (logs/return_slots_aceite/ e logs/return_slots_debug/,
        return_slots_SA01_confirmado.png), o jogo tinha RECUSADO na cara:
          "All of your slots in this city are currently being used.
           It's impossible to return them at this time."
        O harness respondia ok=True em cima da recusa. Agora:
          1. `world.return_slots_refusal()` le a recusa (hash da TEXTBOX) e a
             acao devolve ok=False com a frase do jogo;
          2. o oraculo de efeito passa a ser `our_slots` do PAINEL DA CIDADE
             (world.read_city_panel, coluna carmim = nossa, §33.8), lido antes
             e depois via `city_probe.inspect` — o mesmo leitor que ja serve o
             modelo, nao um leitor novo.
        Slot ocupado por rota NAO PODE ser devolvido: feche/suspenda a rota
        antes (e essas duas acoes estao FORA do action space, §19).
        """
        from world import WORLD_CITIES

        cid = p.get("city")
        if not cid or cid not in WORLD_CITIES:
            return False, f"return_slots: cidade invalida ou ausente: {cid}"

        slots_antes = self._city_our_slots(cid)
        if slots_antes is None:
            return False, (f"return_slots em {cid}: NAO MEDIDO — nao consegui ler nossos "
                           "slots no painel da cidade; sem leitura de entrada nao ha como "
                           "provar efeito, entao nao toco no jogo (R1)")
        if slots_antes == 0:
            return False, (f"return_slots em {cid}: recusado — o painel diz que temos 0 "
                           "slots nessa cidade; nao ha o que devolver")
        livres_antes = self._menu_free_staff()

        self.g.open_cmd("negotiate")
        wait_text(self.b)

        # Navegar para a celula (1,2) = Return
        # Grade: (0,0), (0,1), (1,0), (1,1) = 4 funcionarios
        # (1,2) = celula extra com Return (nao funcionario)
        # De (0,0) para (1,2): Down 1x + Right 2x
        self.b.press("Down", hold=3, wait=14)
        self.b.advance(40)
        self.b.press("Right", hold=3, wait=14)
        self.b.advance(40)
        self.b.press("Right", hold=3, wait=14)
        self.b.advance(60)

        # Verificar que Return esta realmente destacado, nao Bid
        # MEDIDO: Bid = 359px laranja (198,97,66), Return = 297px na sua caixa
        img = Image.open(self.b.screenshot()).convert("RGB")
        if staff_action_is_bid(img):
            self._restore_guard()
            return False, (
                f"return_slots em {cid}: acao destacada nao e Return (bid_pixels "
                "ainda > threshold) — abortado para nao comear negociacao por engano"
            )

        # Confirmar Return (abre "Return which city's slots?")
        self.b.press("A", hold=5, wait=25)
        self.b.advance(150)
        wait_text(self.b)

        # Tela de mapa: "Which city's slots will you return?"
        # Usar point_cursor_at_world + 1 A (padding=open_venture pattern)
        try:
            reg, pos, verificado = point_cursor_at_world(self.b, cid, self.map_region)
            self.map_region = reg
        except Exception as e:
            self._restore_guard()
            return False, f"return_slots em {cid}: erro ao navegar: {e}"

        shot_antes = self.g.shot(f"return_slots_{cid}_mapa")

        # 1 A para selecionar a cidade (nao martela ate sair como _select_city)
        wait_text(self.b)
        self.b.press("A", hold=5, wait=25)
        self.b.advance(150)
        wait_text(self.b)

        # CADEIA DE CONFIRMACAO (corrigido 24/08, ETAPA 2-OraculosFracos).
        # MEDIDO: com apenas 1 `A` aqui, a tela FICAVA em "Will you give back 1
        # slot to <cidade>" e nada era commitado — por isso o oraculo novo lia
        # 12 -> 12 em NA06 (logs/suite/return_slots/return_slots_NA06_confirmado.png,
        # onde o painel mostra Slot 12|12 E a pergunta ainda aberta). Nao era o
        # oraculo errado nem o jogo recusando: era o executor parando um passo
        # antes do fim. Mesma familia do bug de `close_hub` (a cadeia real tem
        # mais de uma confirmacao) e mesma solucao: cadeia de ate 6 `_step()`
        # com parada antecipada no menu. `_step()` para sozinho se a pergunta
        # nao muda, entao o excedente e inofensivo.
        # A RECUSA e lida DEPOIS da cadeia terminar: a caixa de recusa pode
        # aparecer na SEGUNDA confirmacao, e le-la antes a perderia.
        chegou_menu = False
        travou = None
        for i in range(1, 7):
            if world.at_main_menu_img(
                    Image.open(self.b.screenshot()).convert("RGB")):
                chegou_menu = True
                break
            if not self._step():
                travou = i
                break
            self.b.advance(STEP_SETTLE)

        shot_depois = self.g.shot(f"return_slots_{cid}_confirmado")

        # RECUSA DO JOGO — lida da tela, nao inferida. Era exatamente aqui que
        # o harness devolvia ok=True por cima de "It's impossible to return".
        recusa = world.return_slots_refusal(
            Image.open(shot_depois).convert("RGB"))
        if recusa:
            self._ensure_menu()
            self._restore_guard()
            return False, (f"return_slots em {cid}: O JOGO RECUSOU — \"{recusa}\" "
                           f"(tela={shot_depois}); estado restaurado")

        if travou is not None and not chegou_menu:
            self._ensure_menu()
            self._restore_guard()
            return False, (f"return_slots em {cid}: fluxo travou no passo A{travou} "
                           f"(tela={shot_depois}); estado restaurado")

        # Volta ao menu principal
        if not chegou_menu:
            self._ensure_menu()

        if not world.at_main_menu_img(Image.open(self.b.screenshot()).convert("RGB")):
            self._restore_guard()
            return False, f"return_slots em {cid}: nao voltou ao menu; estado restaurado"

        # ORACULO DE EFEITO: nossos slots na cidade, do painel. Sem queda medida
        # a acao NAO passa — nem que a sequencia inteira tenha rodado sem erro.
        slots_depois = self._city_our_slots(cid)
        livres_depois = self._menu_free_staff()
        if slots_depois is None:
            self._restore_guard()
            return False, (f"return_slots em {cid}: NAO MEDIDO — painel da cidade ilegivel "
                           f"depois da acao (nossos slots antes {slots_antes}); "
                           "estado restaurado")
        if slots_depois >= slots_antes:
            self._restore_guard()
            return False, (f"return_slots em {cid}: SEM EFEITO — nossos slots {slots_antes} "
                           f"-> {slots_depois} no painel da cidade; estado restaurado "
                           f"(telas={shot_antes}, {shot_depois})")

        return True, (f"slots devolvidos de {cid}: NOSSOS SLOTS {slots_antes} -> "
                      f"{slots_depois} (lido do painel da cidade); funcionarios livres "
                      f"{livres_antes} -> {livres_depois} (NAO e oraculo: devolver slot "
                      f"nao despacha funcionario); telas={shot_antes}, {shot_depois}")

    def _city_our_slots(self, cid):
        """Nossos slots (coluna carmim) na cidade, LIDOS do painel. None = nao medi.

        Reusa `city_probe.inspect`, o mesmo leitor que serve o modelo — nao um
        segundo leitor que poderia divergir. `inspect` ja tem a guarda de caixa
        da R2 e volta ao menu sozinho.
        """
        try:
            import city_probe
            dados, avisos = city_probe.inspect(self.b, self, [cid])
        except Exception as e:  # noqa: BLE001
            self._ensure_menu()
            print(f"[return_slots] painel de {cid} falhou: {e}", flush=True)
            return None
        self._ensure_menu()
        p = dados.get(cid)
        if not p or not p.get("on_panel"):
            print(f"[return_slots] painel de {cid} nao lido: {avisos}", flush=True)
            return None
        return p.get("our_slots")

    # --- compra de aeronave (comando r0c3) -------------------------------
    def _step_buy(self, tries=4):
        """Como _step(), mas no recorte de texto do FLUXO DE COMPRA.

        A TEXTBOX do fluxo de rota (rodape) fica CONSTANTE aqui — medido: o mesmo
        hash `1cf2b866` em 8 telas seguidas da compra, porque cai sobre a linha
        "Price $...". Com ela o _step() devolveria False sempre. O dialogo da
        compra mora no TOPO (world.BUY_TEXT).
        """
        from world import wait_buy_text

        before = wait_buy_text(self.b)
        for _ in range(tries):
            self.b.press("A", hold=5, wait=25)
            if wait_buy_text(self.b) != before:
                return True
        return False

    def _exit_buy_screens(self, tries=14):
        """Sai do showroom ate o menu principal — SO com B, de proposito.

        MEDIDO 15/08 (savestate `_buy_pos_compra.state`, logo apos a compra):
        depois de "Thank you very much. Please wait about 3 months for delivery"
        o jogo VOLTA para a tela de modelo do mesmo fabricante. Apertar A ali
        NAO sai: reabre a descricao do aviao e chega de novo no (YES NO) de
        compra — ou seja, a saida "alterna A e B" que eu tinha escrito podia
        COMPRAR OUTRO AVIAO. Medido com a sequencia AAABAB: passo 3 = "The first
        Airbus 4-engine...", passo 6 = a mesma pergunta com (YES NO) armado.
        So com B: 6 toques levam ao mapa dos fabricantes e o 7o ao menu
        principal (logs/buy/ex_00..06.png). O numero varia com a datilografia,
        por isso o laco confere por imagem em vez de contar toques.
        """
        from world import at_main_menu_img

        for _ in range(tries):
            if at_main_menu_img(Image.open(self.b.screenshot()).convert("RGB")):
                return True
            self.b.press("B", hold=5, wait=25)
            self.b.advance(120)
        return at_main_menu_img(Image.open(self.b.screenshot()).convert("RGB"))

    def _do_buy_aircraft(self, p):
        """Compra N aeronaves de um modelo do catalogo (world.AIRCRAFT_CATALOG).

        Fluxo MEDIDO (probe_buy.py walk/cont, logs/buy/):
          r0c3 -> "Which manufacturer would you like to visit?"  (mapa dos makers,
                  seletor `◁ Maker MDC ▷`; Right = proximo, ciclo de 6)
           A -> "Nice to meet you. Which model are you interested in?"
                  (painel com alcance/assentos/preco; DOWN = proximo modelo)
           A -> descricao do modelo + (YES NO)
           A -> "You can order a maximum of 10 planes. How many do you want?"
                  (Right = +1, base 1)
           A -> "N plane(s) will cost $X. Is this OK?" + (YES NO)
           A -> "Thank you very much. Please wait about 3 months for delivery."
                  <- O CAIXA E DEBITADO AQUI
          e o jogo VOLTA sozinho para a tela de modelo; sai-se com B (despedida),
          A (volta ao mapa dos makers) e B (menu principal).
        """
        from world import (AIRCRAFT_CATALOG, BUY_QTY_MAX, MAKERS, buy_panel_hash,
                           read_cash_k, read_maker_idx, wait_buy_text)

        model = str(p.get("model", "")).upper().strip()
        if model not in AIRCRAFT_CATALOG:
            return False, (f"modelo desconhecido: {p.get('model')!r}; "
                           f"disponiveis: {', '.join(sorted(AIRCRAFT_CATALOG))}")
        spec = AIRCRAFT_CATALOG[model]
        qty = int(p.get("qty", 1))
        if not 1 <= qty <= BUY_QTY_MAX:
            return False, f"qty fora de 1..{BUY_QTY_MAX}: {qty}"
        custo = spec["price_k"] * qty
        caixa = read_cash_k(self.b)
        # Barrar aqui e melhor que descobrir na tela: a recusa do jogo por caixa
        # insuficiente e uma tela que nao mapeei, e entrar nela deixaria o fluxo
        # num estado desconhecido para a acao seguinte.
        if caixa < custo:
            return False, (f"caixa insuficiente para {qty}x {model}: "
                           f"precisa {custo}K, tem {caixa}K")

        self._ensure_menu()
        self.g.open_cmd("buy_aircraft")
        wait_buy_text(self.b)  # sem isto o 1o toque no seletor e engolido

        # 1) fabricante — LENDO onde o seletor esta, nunca assumindo MDC.
        # O seletor e pegajoso (world.MAKER_LABEL_MD5 documenta o custo do erro:
        # 5 A340 comprados por engano por $550.000K).
        atual = None
        for _ in range(5):  # o rotulo pode ainda estar desenhando
            atual = read_maker_idx(Image.open(self.b.screenshot()).convert("RGB"))
            if atual is not None:
                break
            self.b.advance(90)
        if atual is None:
            shot = self.g.shot(f"buy_maker_ilegivel_{model}")
            self._restore_guard()
            return False, (f"compra {model}: nao consegui LER o fabricante na tela "
                           f"(tela={shot}); nao vou andar as cegas com o seletor "
                           f"pegajoso; estado restaurado")
        passos = (spec["maker_idx"] - atual) % len(MAKERS)
        seq = self._bump("Right", passos)
        if seq:
            self.b.batch(seq, extra_frames=len(seq) * 25 + 60)
        if not self._step_buy():
            shot = self.g.shot(f"buy_travou_maker_{model}")
            self._restore_guard()
            return False, (f"compra {model}: nao saiu da tela de fabricante "
                           f"(estava em {MAKERS[atual]}, {passos} passos ate "
                           f"{MAKERS[spec['maker_idx']]}; tela={shot})")

        # 2) modelo: DOWN ate o painel na tela ser o do modelo pedido.
        # O seletor de modelo tambem pode vir pegajoso, entao andar um numero
        # fixo de vezes nao basta — a malha e fechada pelo proprio painel.
        # MDC tem 3 modelos, Boeing 2, os demais 1 (medido), logo <=4 tentativas
        # cobrem qualquer volta completa.
        def _painel():
            # wait_buy_text ANTES de olhar/andar: sem isso o toque cai durante a
            # datilografia e e engolido (o laco rodava 4 vezes com o painel
            # parado no B747-400 quando o pedido era B777), e a captura pega um
            # frame intermediario cujo hash nao esta na tabela.
            wait_buy_text(self.b)
            self.b.advance(60)
            shot = self.g.shot(f"buy_{model}_x{qty}")
            return shot, buy_panel_hash(Image.open(shot).convert("RGB"))

        shot_modelo, painel = _painel()
        # 8 tentativas, nao 3 (o maior fabricante tem 3 modelos): sobra margem
        # para um toque engolido sem transformar isso em falha da acao.
        for _ in range(8):
            if painel == spec["panel"]:
                break
            self.b.batch(self._bump("Down", 1), extra_frames=120)
            shot_modelo, painel = _painel()
        if painel != spec["panel"]:
            # "o modelo pediu X" tem de virar "o jogo esta com X". Sem esta
            # checagem uma troca de catalogo do jogo (ou um toque engolido)
            # compraria outro aviao em silencio — e o caixa cairia do mesmo
            # jeito, entao o gate de caixa NAO pegaria o erro.
            self._restore_guard()
            return False, (f"compra {model} abortada: painel na tela e {painel}, "
                           f"esperado {spec['panel']} ({MAKERS[spec['maker_idx']]}, "
                           f"modelo {spec['model_idx']}); tela={shot_modelo}; "
                           f"estado restaurado")

        # 3) descricao + YES  -> 4) quantidade
        for etapa in ("descricao/confirmacao do modelo", "pergunta de quantidade"):
            if not self._step_buy():
                shot = self.g.shot(f"buy_travou_{model}_{etapa.split('/')[0]}")
                self._restore_guard()
                return False, f"compra {model}: fluxo travou em {etapa} (tela={shot})"

        seq = self._bump("Right", qty - 1)
        if seq:
            self.b.batch(seq, extra_frames=len(seq) * 25 + 60)
        self.b.advance(60)
        shot_qtd = self.g.shot(f"buy_{model}_x{qty}_qtd")

        # 5) "N plane(s) will cost $X. Is this OK?"  6) YES -> cobra o caixa
        for etapa in ("resumo do pedido", "confirmacao final"):
            if not self._step_buy():
                shot = self.g.shot(f"buy_travou_{model}_{etapa.split()[0]}")
                self._restore_guard()
                return False, f"compra {model}: fluxo travou no {etapa} (tela={shot})"

        self._exit_buy_screens()
        return True, (f"comprado {qty}x {model} ({spec['maker']}, {spec['range_mi']}mi, "
                      f"{spec['seats']} assentos) por ~{custo}K; "
                      f"entrega em ~3 meses; tela={shot_qtd}")

    def _do_sell_aircraft(self, p):
        """Vende N aeronaves pelo fabricante World Lease (r0c3, indice 2, ETAPA 6-Reversos).

        MEDIDO 15/08 (CALIBRATION §12.1): o indice 2 (World Lease) nao e um
        fabricante de compra — abre uma tela de VENDA. O catalogo mostra a NOSSA
        frota com opcoes de revenda. Preco por unidade variou de $20.880K para
        $20.520K em poucos trimestres (cenario de 20 anos, precos mudam ao longo
        do tempo). O seletor de quantidade tem um **limite de 3 por visita**, nao
        investigado alem disso.

        Params:
          model (str): chave de mundo.AIRCRAFT_CATALOG (ex.: "MD100")
          qty (int): 1..3 (limite de 3 por visita, §12.1)

        Oracles de efeito (ETAPA 6):
          1. Caixa sobe (delta = preco de revenda x qty)
          2. Info→fleet: Avail N → N-1 (confirmado, equipamento removido)

        Armadilha: o seletor de fabricante e pegajoso (CALIBRATION §15b); reusa
        world.read_maker_idx e malha fechada como em _do_buy_aircraft.
        """
        from world import (AIRCRAFT_CATALOG, read_cash_k, read_maker_idx,
                           wait_buy_text)

        model = str(p.get("model", "")).upper().strip()
        if model not in AIRCRAFT_CATALOG:
            return False, (f"modelo desconhecido: {p.get('model')!r}; "
                           f"disponiveis: {', '.join(sorted(AIRCRAFT_CATALOG))}")
        spec = AIRCRAFT_CATALOG[model]
        qty = int(p.get("qty", 1))
        # Venda: limite de 3 por visita (§12.1), nao investigado alem
        SELL_QTY_MAX = 3
        if not 1 <= qty <= SELL_QTY_MAX:
            return False, f"qty fora de 1..{SELL_QTY_MAX}: {qty}"

        caixa_antes = read_cash_k(self.b)
        self._ensure_menu()
        self.g.open_cmd("buy_aircraft")
        wait_buy_text(self.b)

        # Navegar para o fabricante 2 (World Lease) — MALHA FECHADA, nao assume MDC
        atual = None
        for _ in range(5):
            atual = read_maker_idx(Image.open(self.b.screenshot()).convert("RGB"))
            if atual is not None:
                break
            self.b.advance(90)
        if atual is None:
            self._restore_guard()
            return False, "sell_aircraft: nao consegui ler indice do fabricante inicial"

        # Pedir Right (alvo=2, World Lease)
        passos = (2 - atual) % 6
        for _ in range(passos):
            self.b.press("Right", hold=3, wait=14)
            self.b.advance(40)

        self.b.advance(60)
        shot_maker = self.g.shot(f"sell_{model}_world_lease")

        # Confirmar fabricante (sai do mapa de makers, entra no showroom de VENDA)
        if not self._step_buy():
            shot = self.g.shot(f"sell_travou_maker_{model}")
            self._restore_guard()
            return False, f"sell_aircraft: fluxo travou ao confirmar World Lease (tela={shot})"

        # Nesta tela, o painel mostra o modelo NOSSO disponivel para venda.
        # CALIBRADO anteriormente: MD100 tem "panel" especifico. Validar que
        # estamos vendendo o modelo certo (cash cai tanto para MD100 quanto
        # para qualquer outro, por isso o gate de caixa nao pega modelo errado).
        def _painel():
            return AIRCRAFT_CATALOG[model]["panel"], buy_panel_hash(
                Image.open(self.b.screenshot()).convert("RGB")
            )

        painel_esperado, painel = _painel()
        if painel != painel_esperado:
            shot = self.g.shot(f"sell_modelo_errado_{model}")
            self._restore_guard()
            return False, (f"sell_aircraft: painel na tela e {painel}, "
                           f"esperado {painel_esperado} (modelo {model}); "
                           f"tela={shot}; estado restaurado")

        # Quantidade: Right = +1, base 1 (mesmo mecanismo que buy_aircraft)
        seq = self._bump("Right", qty - 1)
        if seq:
            self.b.batch(seq, extra_frames=len(seq) * 25 + 60)
        self.b.advance(60)
        shot_qty = self.g.shot(f"sell_{model}_x{qty}")

        # Confirmacao final: "N plane(s) will be sold for $X. Is this OK?" + YES
        for etapa in ("resumo", "confirmacao final"):
            if not self._step_buy():
                shot = self.g.shot(f"sell_travou_{model}_{etapa.split()[0]}")
                self._restore_guard()
                return False, f"sell_aircraft: fluxo travou no {etapa} (tela={shot})"

        # Sair das telas de venda
        self._exit_buy_screens()

        # Verificar que voltamos ao menu
        if not world.at_main_menu_img(Image.open(self.b.screenshot()).convert("RGB")):
            self._restore_guard()
            return False, f"sell_aircraft: nao voltou ao menu apos venda; estado restaurado"

        # Ler caixa depois (verifica efeito)
        caixa_depois = read_cash_k(self.b)
        delta = caixa_depois - caixa_antes

        if delta <= 0:
            return False, (f"sell_aircraft: efeito nao verificado — caixa "
                           f"{caixa_antes}K -> {caixa_depois}K ({delta:+d}K, "
                           f"esperado >0K)")

        preco_unitario = delta // qty if qty > 0 else 0
        return True, (f"vendido {qty}x {model} via World Lease: caixa "
                      f"{caixa_antes}K -> {caixa_depois}K (+{delta}K, "
                      f"~{preco_unitario}K/unid); telas={shot_maker}, {shot_qty}")

    # --- hub regional (comando r1c0) -------------------------------------
    def _do_open_hub(self, p):
        """Abre a negociacao de um HUB REGIONAL na regiao pedida.

        O hub e a espinha do jogo: a vitoria exige um em TODA regiao e, mais que
        isso, ele E o mecanismo de alcance — toda rota parte de um hub nosso.
        Cadeia (medida): negociar slots numa cidade da regiao X -> abrir rota de
        um hub existente ate ela -> `open_hub(X)` -> esperar -> rotas partem de X.

        Fluxo MEDIDO 17/08 (probe_hub3.py, `prova_ic_rota_sa.state` -> regiao 1):
          r1c0 com o mapa na regiao X -> tela de funcionario (abas **Open**/Close,
              mesma geometria da negociacao de slots)
           A -> "Hub Set-up | Maintenance Expense $1760K | Construction Costs
                 $28800K" + lista das cidades candidatas (as que ja recebem rota
                 nossa; so havia "Havana")
           A -> detalhe da cidade + "Shall we open [a hub here]?"
           A -> "I'll get right on it"   <- O CAIXA E DEBITADO AQUI (-$28.800K)
           A -> menu principal
        Efeito verificado por DOIS sinais independentes: caixa 1.166.820K ->
        1.138.020K e funcionarios livres 4 -> 3. Cada um sozinho seria fraco —
        o caixa nao distingue hub de qualquer outra despesa.

        O hub NAO fica pronto na hora: MEDIDO (probe_hub1.py) que com a
        negociacao em andamento o jogo ainda responde "We don't have a regional
        hub here." a uma rota partindo de la. Por isso a regiao entra em
        `hubs_pending`, nao em `hubs`.
        """
        from world import (HOME_REGION, HUB_CONSTRUCTION_K, REGION_NAMES, WORLD_CITIES,
                           city_region, on_staff_screen, read_cash_k)

        reg = p.get("region")
        if reg is None and p.get("city"):
            if p["city"] not in WORLD_CITIES:
                return False, f"open_hub: cidade '{p['city']}' nao existe no catalogo"
            reg = city_region(p["city"])
        if isinstance(reg, str):
            achado = [k for k, v in REGION_NAMES.items() if v.lower() == reg.strip().lower()]
            if not achado:
                return False, (f"open_hub: regiao '{p.get('region')}' desconhecida; "
                               f"use 0..6 ou um de {sorted(REGION_NAMES.values())}")
            reg = achado[0]
        if reg not in REGION_NAMES:
            return False, f"open_hub: regiao invalida {p.get('region')!r} (use 0..6)"

        # --- recusas que o JOGO daria, antecipadas com a mensagem dele ---
        if reg == HOME_REGION:
            return False, (f"open_hub({reg} {REGION_NAMES[reg]}) recusado: e a regiao da BASE "
                           "— o jogo responde \"Our home base is here in North America. "
                           "We don't need a regional hub.\"")
        if reg in self.hub_regions:
            ja = [c for c in self.hubs if city_region(c) == reg]
            return False, f"open_hub({reg} {REGION_NAMES[reg]}) recusado: ja temos hub la ({ja})"
        if reg in self.hubs_pending:
            return False, (f"open_hub({reg} {REGION_NAMES[reg]}) recusado: negociacao de hub em "
                           f"{self.hubs_pending[reg]} JA EM ANDAMENTO — o jogo responde "
                           "\"preparations for a regional hub are already underway\". "
                           "Passe turnos ate concluir")
        if self.routes and not any(city_region(r["to"]) == reg or city_region(r["from"]) == reg
                                   for r in self.routes):
            return False, (f"open_hub({reg} {REGION_NAMES[reg]}) recusado: nenhuma rota nossa "
                           f"chega la — o jogo responde \"We can't open a regional hub in "
                           f"{REGION_NAMES[reg]}. We don't have any flights going there.\" "
                           "Abra antes uma rota de um hub existente ate uma cidade da regiao "
                           "(o que exige negociar slots la primeiro)")
        livres_antes = self._menu_free_staff()
        if livres_antes is None:
            return False, f"open_hub({reg}): nao consegui ler a barra de funcionarios do menu"
        if livres_antes == 0:
            return False, (f"open_hub({reg} {REGION_NAMES[reg]}) impossivel: nenhum funcionario "
                           "livre (os 4 estao em missao). Passe o turno para eles voltarem")
        caixa = read_cash_k(self.b)
        if caixa < HUB_CONSTRUCTION_K:
            return False, (f"open_hub({reg}): caixa {caixa}K < custo de construcao "
                           f"{HUB_CONSTRUCTION_K}K (valor LIDO da tela Hub Set-up)")

        # --- regiao: dois sinais, porque o gate de efeito nao distingue ---
        self._ensure_menu()
        ok_reg, det_reg = self._goto_region(reg)
        if not ok_reg:
            self._restore_guard()
            return False, (f"open_hub({reg} {REGION_NAMES[reg]}): {det_reg} — abrir hub na "
                           "regiao errada custa o MESMO caixa e o MESMO funcionario, entao o "
                           "gate de efeito nao pegaria o erro; estado restaurado")

        self.g.open_cmd("home_info")
        wait_text(self.b)
        self.b.advance(120)
        img = Image.open(self.b.screenshot()).convert("RGB")
        if not on_staff_screen(img):
            # As tres recusas medidas sao telas de MENSAGEM: o cursor esta morto
            # e sair por tecla e traicoeiro (foi assim que a acao SEGUINTE
            # quebrava). Recarregar o guard e a saida determinista.
            shot = self.g.shot(f"hub_recusado_r{reg}")
            self._restore_guard()
            return False, (f"open_hub({reg} {REGION_NAMES[reg]}) recusado pelo jogo antes da "
                           f"escolha de funcionario (mensagem na tela={shot}); estado restaurado")

        ok_sel, celula, det_sel = self._pick_free_staff()
        if not ok_sel:
            shot = self.g.shot(f"hub_semstaff_r{reg}")
            self._restore_guard()
            return False, f"open_hub({reg}): {det_sel} (tela={shot}); estado restaurado"

        # A1 lista as cidades candidatas ("Hub Set-up"); A2 e o detalhe da cidade
        # com "Shall we open?"; A3 confirma e COBRA. _step() em vez de contar A's:
        # os que caem durante a datilografia sao engolidos (armadilha medida).
        evid = {}
        for i, etapa in enumerate(("lista de cidades (Hub Set-up)",
                                   "detalhe da cidade / Shall we open",
                                   "confirmacao"), start=1):
            evid[etapa] = self.g.shot(f"hub_r{reg}_A{i}")
            if not self._step():
                shot = self.g.shot(f"hub_travou_r{reg}_{i}")
                self._restore_guard()
                return False, (f"open_hub({reg}): fluxo travou na {etapa} (tela={shot}); "
                               "estado restaurado")
        self.b.advance(STEP_SETTLE)
        self._ensure_menu()

        # --- gate de efeito: caixa CAIU **e** um funcionario SAIU ---
        # Os dois, independentes. So o caixa nao distingue hub de outra despesa;
        # so o funcionario nao distingue hub de negociacao de slots.
        caixa_depois = read_cash_k(self.b)
        livres_depois = None
        for _ in range(3):
            livres_depois = self._menu_free_staff()
            if livres_depois is not None and livres_depois < livres_antes:
                break
            self.b.advance(120)
        menu_shot = self.g.shot(f"hub_barra_r{reg}")
        detalhe = (f"regiao {reg} {REGION_NAMES[reg]}, {det_sel}, caixa {caixa}K -> "
                   f"{caixa_depois}K ({caixa_depois - caixa:+d}K), funcionarios livres "
                   f"{livres_antes} -> {livres_depois}, telas={list(evid.values())}, "
                   f"barra={menu_shot}")
        if caixa_depois >= caixa:
            self._restore_guard()
            return False, f"open_hub SEM EFEITO (caixa nao caiu) em {detalhe}; estado restaurado"
        if livres_depois is None or livres_depois >= livres_antes:
            self._restore_guard()
            return False, (f"open_hub SEM EFEITO (nenhum funcionario saiu — o caixa caiu por "
                           f"outro motivo?) em {detalhe}; estado restaurado")
        # Cidade: com UMA candidata na lista o jogo ja vem com ela selecionada.
        # Com varias, a navegacao da lista NAO esta calibrada — por isso a
        # cidade anotada e "a que o jogo escolheu", e a evidencia e a captura do
        # detalhe (que mostra bandeira e nome).
        cands = [r["to"] for r in self.routes if city_region(r["to"]) == reg]
        cidade = cands[0] if len(cands) == 1 else None
        self.hubs_pending[reg] = cidade or f"?regiao{reg}"
        return True, (f"hub regional iniciado ({detalhe}); cidade="
                      f"{cidade or 'nao determinada pelo harness (mais de uma candidata)'}; "
                      "NAO esta pronto: o hub so vira origem valida quando a negociacao "
                      "concluir (passe turnos e confirme com hub_ready)")

    def _do_close_hub(self, p):
        """Fecha um hub regional (r1c0, aba Close). CALIBRADO AO VIVO 18/08
        (ETAPA 12-HubsCompleto, `_probe_close_full.py`/`_probe_close_and_reopen.py`,
        savestate `_hub_rota_do_hub.state`: hub em Havana/SA01 + rota que PARTE
        do hub ate SA03/Kingston).

        Fluxo MEDIDO (r1c0 -> tela de funcionario -> Down 1x + Right 2x ate a
        celula extra (1,2)=Close, mesma geometria de Return em r0c2), COM 1
        SO HUB NA REGIAO (lista de hubs multiplos nao calibrada):
          A -> "Are you sure you want to close the regional hub in Havana?" (YES/NO)
          A -> "1 regional hub and 1 route will be closed." (aviso, so info)
          A -> detalhe por rota afetada ("All flights listed above will be
               closed.") — MEDIDO com 1 rota; lista de VARIAS rotas nao testada
          A -> "Are you sure you want to close?" (2a pergunta YES/NO, agora
               sobre a ROTA) — FACIL DE PERDER: parar cedo demais aqui e
               responder com B equivale a NO e cancela o close inteiro
          A -> menu principal, caixa CREDITADA aqui

        MEDIDO (nao suposto), `_probe_close_extra_a.py`, Havana/SA01 com 1
        hub + 1 rota (Havana->Kingston) partindo dele:
          - Caixa: CREDITO de +32.300K no fechamento completo (nao e delta 0
            nem e a Construction Cost de abertura, 28.800K, refletida ao
            contrario — o numero exato pode variar com o que estava associado
            aa rota fechada; NAO assumir 32.300K fixo sem recalibrar).
          - Funcionarios livres: inalterados (4->4) em TODA a cadeia. Fechar
            hub (e a rota em cascata) NAO consome negociador — a celula Close
            nao e um funcionario.
          - Cascata: toda rota que PARTE do hub fechado e fechada junto pelo
            jogo (confirmado por texto na tela, 2 telas distintas). Rota que
            so CHEGA no hub (ex.: base->hub) sobrevive intacta.
          - Reabertura: com o close REALMENTE commitado (caixa creditada),
            `open_hub` na MESMA regiao/cidade volta a funcionar normalmente
            e custa a Construction Cost normal de novo (-28.800K) — MEDIDO
            round-trip completo em `_probe_close_extra_a.py`. ARMADILHA
            MEDIDA: um close que PARA na 2a pergunta YES/NO e sai por B
            (in)voluntariamente NAO commita nada (caixa 0K) mas a UI parece
            ter voltado ao normal — o unico jeito de saber que ficou preso
            "no limbo" e o open_hub seguinte recusar com "You already have a
            regional hub", mesmo o harness achando que ja fechou.

        Params:
          region (int|str): regiao do hub a fechar
          city (str): opcional, nome da cidade do hub (para verificacao)
        """
        from world import (HOME_REGION, REGION_NAMES, WORLD_CITIES,
                           city_region, on_staff_screen, read_cash_k)

        reg = p.get("region")
        if reg is None and p.get("city"):
            if p["city"] not in WORLD_CITIES:
                return False, f"close_hub: cidade '{p['city']}' nao existe no catalogo"
            reg = city_region(p["city"])
        if isinstance(reg, str):
            achado = [k for k, v in REGION_NAMES.items() if v.lower() == reg.strip().lower()]
            if not achado:
                return False, (f"close_hub: regiao '{p.get('region')}' desconhecida; "
                               f"use 0..6 ou um de {sorted(REGION_NAMES.values())}")
            reg = achado[0]
        if reg not in REGION_NAMES:
            return False, f"close_hub: regiao invalida {p.get('region')!r} (use 0..6)"

        # --- recusas que o JOGO daria, antecipadas com a mensagem dele ---
        if reg == HOME_REGION:
            return False, (f"close_hub({reg} {REGION_NAMES[reg]}) recusado: e a regiao da BASE "
                           "— nao tem hub regional para fechar")
        if reg not in self.hubs:
            hubs_esta_regiao = [c for c in self.hubs if city_region(c) == reg]
            if not hubs_esta_regiao:
                return False, (f"close_hub({reg} {REGION_NAMES[reg]}) recusado: "
                               f"nenhum hub confirmado nesta regiao (o harness acredita)")
        # MEDIDO 18/08: close_hub NAO consome negociador (a celula Close nao
        # e um funcionario) — ao contrario de open_hub, nao ha precondicao de
        # funcionario livre. `livres_antes` so serve de referencia no log.
        livres_antes = self._menu_free_staff()
        if livres_antes is None:
            return False, f"close_hub({reg}): nao consegui ler a barra de funcionarios do menu"
        caixa = read_cash_k(self.b)

        # --- regiao
        self._ensure_menu()
        ok_reg, det_reg = self._goto_region(reg)
        if not ok_reg:
            self._restore_guard()
            return False, (f"close_hub({reg} {REGION_NAMES[reg]}): {det_reg} — "
                           "estado restaurado")

        self.g.open_cmd("home_info")
        wait_text(self.b)
        self.b.advance(120)
        img = Image.open(self.b.screenshot()).convert("RGB")
        if not on_staff_screen(img):
            shot = self.g.shot(f"close_hub_nao_staff_r{reg}")
            self._restore_guard()
            return False, (f"close_hub({reg} {REGION_NAMES[reg]}): nao abriu tela de staff "
                           f"(tela={shot}); estado restaurado")

        # NAO chamar _pick_free_staff() aqui: MEDIDO 18/08 que a celula
        # Open/Close(1,2) NAO e um funcionario, e mover ate ela E RELATIVO
        # a posicao ATUAL do cursor. _pick_free_staff() pousa no primeiro
        # funcionario LIVRE (que pode nao ser (0,0)), e um Down+Right+Right
        # DALI acertaria a celula errada sempre que o funcionario livre nao
        # for o (0,0). return_slots (r0c2) tem o mesmo padrao: navega direto
        # da posicao NEUTRA (cursor sempre em (0,0) logo apos open_cmd,
        # confirmado em _probe_close_visual*.py) sem escolher funcionario.
        det_sel = "sem selecao de funcionario (celula Close nao e staff)"

        # Navegar para Close: MEDIDO 18/08 (ETAPA 12-HubsCompleto,
        # _probe_close_visual6.py) que a geometria e IDENTICA a return_slots
        # (r0c2): grade de staff 2 colunas e uma coluna EXTRA (col=2) com
        # Open na linha 0 e Close na linha 1. De (0,0), Down 1x + Right 2x
        # chega em (1,2)=Close (confirmado por staff_action_is_bid()==False
        # E captura de tela com "Close" destacado em laranja). A hipotese
        # antiga (Left) estava ERRADA: Left/Right/Up dentro da grade de fotos
        # NUNCA tocam Open/Close, so a celula extra faz isso.
        self.b.press("Down", hold=3, wait=14)
        self.b.advance(40)
        self.b.press("Right", hold=3, wait=14)
        self.b.advance(40)
        self.b.press("Right", hold=3, wait=14)
        self.b.advance(60)

        # Verificar que Close esta destacado, nao Open
        img = Image.open(self.b.screenshot()).convert("RGB")
        if staff_action_is_bid(img):
            self._restore_guard()
            return False, (
                f"close_hub em {reg}: acao destacada nao e Close (open_pixels "
                "ainda > threshold) — abortado para nao abrir hub por engano"
            )

        shot_close_tab = self.g.shot(f"close_hub_aba_r{reg}")

        # Confirmar Close (abre a 1a pergunta "Are you sure you want to
        # close the regional hub in X?")
        self.b.press("A", hold=5, wait=25)
        self.b.advance(150)
        wait_text(self.b)

        # MEDIDO 18/08 (`_probe_close_extra_a.py`, ao vivo): a cadeia real tem
        # DUAS perguntas YES/NO distintas, nao uma so:
        #   A -> "Are you sure you want to close the regional hub in X?" (YES/NO)
        #   A -> "N regional hub(s) and N route(s) will be closed." (aviso)
        #   A -> detalhe por rota afetada ("All flights listed above will be
        #        closed.") — com 1 SO ROTA testado; lista de VARIAS rotas nao
        #        calibrada
        #   A -> "Are you sure you want to close?" (2a pergunta, YES/NO,
        #        confirma a ROTA especificamente)
        #   A -> menu principal, caixa CREDITADA aqui
        # A 1a tentativa desta calibracao usou so 3 `_step()` e ficou PRESA
        # antes da 2a pergunta; `_ensure_menu()` (que so aperta B) nesse ponto
        # equivale a responder NO e CANCELA o close inteiro em silencio —
        # caixa 0K, hub continua do jogo (medido: open_hub subsequente
        # recusou com "You already have a regional hub"). Por isso: ate 6
        # `_step()` (excedente e inofensivo, _step() para sozinho se a
        # textbox nao mudar) com parada antecipada assim que a tela virar
        # menu principal — nunca sair por B enquanto uma pergunta YES/NO
        # puder estar pendente.
        from world import at_main_menu_img

        evid = {}
        chegou_menu = False
        for i in range(1, 7):
            evid[f"A{i}"] = self.g.shot(f"close_hub_r{reg}_A{i}")
            if at_main_menu_img(Image.open(self.b.screenshot()).convert("RGB")):
                chegou_menu = True
                break
            if not self._step():
                shot = self.g.shot(f"close_hub_travou_r{reg}_{i}")
                self._restore_guard()
                return False, (f"close_hub({reg}): fluxo travou no passo A{i} (tela={shot}); "
                               "estado restaurado")
            self.b.advance(STEP_SETTLE)
        if not chegou_menu:
            chegou_menu = self._ensure_menu()

        # --- gate de efeito: MEDIDO 18/08 que fechar hub CREDITA caixa
        # (`_probe_close_extra_a.py`: +32.300K num round-trip Havana, hub +
        # 1 rota) e NAO consome negociador (livres antes==depois sempre — a
        # celula Close nao e um funcionario). O oracle antigo baseado em
        # "funcionario saiu" e SEMPRE falso para close_hub (bug ativo, nao so
        # gate fraco); o de "reabrir r1c0 mostra Open" tambem e INUTIL: a
        # tela de funcionario aparece IGUAL exista ou nao hub — a recusa "You
        # already have..." so vem DEPOIS de escolher funcionario e apertar A
        # no fluxo de Open, entao nao dava pra usar como sinal leve. Oracle
        # correto: caixa SOBE (credito). Se nao subiu, o close nao commitou
        # (mais provavel: uma das perguntas YES/NO foi respondida NO por
        # engano/B).
        caixa_depois = read_cash_k(self.b)
        livres_depois = self._menu_free_staff()
        menu_shot = self.g.shot(f"close_hub_barra_r{reg}")

        detalhe = (f"regiao {reg} {REGION_NAMES[reg]}, {det_sel}, caixa {caixa}K -> "
                   f"{caixa_depois}K ({caixa_depois - caixa:+d}K), funcionarios livres "
                   f"{livres_antes} -> {livres_depois}, chegou_menu={chegou_menu}, "
                   f"telas={list(evid.values())}, aba={shot_close_tab}, barra={menu_shot}")

        if not chegou_menu or caixa_depois <= caixa:
            self._restore_guard()
            return False, (f"close_hub SEM EFEITO (caixa nao subiu — a transacao "
                           f"provavelmente nao commitou) em {detalhe}; estado restaurado")

        # Remover o hub da lista do harness
        hubs_removidos = [c for c in self.hubs if city_region(c) == reg]
        for h in hubs_removidos:
            self.hubs.discard(h)
        # MEDIDO 18/08: o jogo fecha em CASCATA toda rota que PARTIA do hub
        # fechado (tela intermediaria confirmou "1 regional hub and 1 route
        # will be closed"). Rotas que so CHEGAM la (ex.: base->hub) sobrevivem.
        rotas_fechadas = [r for r in self.routes if r["from"] in hubs_removidos]
        self.routes = [r for r in self.routes if r["from"] not in hubs_removidos]

        return True, (f"hub regional fechado ({detalhe}); hubs removidos: {hubs_removidos}; "
                      f"rotas fechadas em cascata pelo jogo (partiam do hub): {rotas_fechadas}; "
                      "MEDIDO 18/08: caixa CREDITADA no fechamento (valor exato varia "
                      "com a rota fechada, NAO reusar 32.300K como constante) e SEM "
                      "consumo de negociador (livres antes==depois)")

    # --- business venture (comando r0c5) ----------------------------------
    def _do_open_venture(self, p):
        """Compra um empreendimento comercial (business venture) numa cidade.

        ETAPA 5-Venture, CALIBRADO 17/08 AO VIVO (probe_venture2..10.py,
        logs/run_f0/v2_*..v10_*.png). Fluxo medido:

          buy_sell -> funcionario livre (Buy/Sell, mesma geometria de r0c2/
          r1c0) -> A ate sair do mapa -> 1 A SOBRE A CIDADE abre DIRETO a tela
          de tipo, ja no tipo 0 (o "primeiro" oferecido POR ESSA CIDADE), com
          a pergunta "Which business venture will you purchase?" armada.

        ARMADILHA MEDIDA (custou $144.000K de verdade, probe_venture.py 1a
        versao): o helper generico `_select_city` marteca A ate sair da tela
        do mapa — nesta tela especifica isso ULTRAPASSA a selecao de tipo e
        cai direto no YES/NO ja respondido (a resposta default e YES), porque
        o "sair do mapa" so acontece DEPOIS da tela de tipo, nao antes dela.
        Por isso esta acao NAO usa `_select_city`: navega o mapa (mesma
        `point_cursor_at_world`) e da exatamente UM A para abrir a tela de
        tipo, sem tocar A de novo ate escolher o tipo certo.

        Right cicla os tipos DESSA cidade (preco/nome mudam) SEM WRAP; Left/
        Up/Down NAO tem efeito (medido, probe_venture10.py). O catalogo NAO E
        FIXO/universal: Washington ofereceu 3 tipos (Concert Hall $144.000K,
        Grand Hotel $288.000K, Commuter Airline $576.000K — SEM City Hotel),
        e Denver ja abriu no tipo 0 com um nome nunca antes visto ("Arts
        Pavilion", $27.000K) — ou seja, disponibilidade E preco variam por
        cidade. `type_index` (default 0) escolhe a posicao no catalogo DESSA
        cidade; o executor NUNCA martela Right as cegas alem do que a tela
        realmente mudou (gate por hash de tela, `world.venture_type_hash`).

        Confirmar (2x A, padrao `_step`) DEBITA O CAIXA NA HORA (medido:
        -144.000K em Washington/tipo0, 1.184.900K -> 1.040.900K) e consome 1
        funcionario — MESMO PADRAO do hub (r1c0), apesar do texto dizer "It
        will take N months": o pagamento e imediato, o efeito NAO.
        Confirmado (`Info->facilities` e a recusa de r1c1 "no businesses in
        our ... network") que a compra RECEM-FEITA ainda NAO conta como
        venture pronto — os 3 icones de facilities continuam em `x0` e r1c1
        continua recusando logo depois da compra, exatamente como o hub fica
        em `hubs_pending` ate a negociacao concluir. Este executor NAO tem
        ainda um `ventures_pending`/`ventures` (equivalente ao hub) — fica
        para quando alguem precisar consultar prontidao, o mesmo gap que
        `hub_ready` resolveu para hub.
        """
        from world import (WORLD_CITIES, on_map_screen, point_cursor_at_world,
                           read_cash_k, venture_type_hash)

        cid = p.get("city")
        if not cid or cid not in WORLD_CITIES:
            return False, f"open_venture: cidade invalida ou ausente: {p.get('city')!r}"
        try:
            tipo = int(p.get("type_index", 0))
        except (TypeError, ValueError):
            return False, f"open_venture: type_index invalido: {p.get('type_index')!r}"
        if tipo < 0:
            return False, f"open_venture: type_index negativo: {tipo}"

        livres_antes = self._menu_free_staff()
        if livres_antes is None:
            return False, "open_venture: nao consegui ler a barra de funcionarios do menu"
        if livres_antes == 0:
            return False, ("open_venture impossivel: nenhum funcionario livre "
                           "(os 4 estao em missao). Passe o turno para eles voltarem")
        caixa_antes = read_cash_k(self.b)

        self._ensure_menu()
        self.g.open_cmd("buy_sell")
        wait_text(self.b)
        ok_sel, celula, det_sel = self._pick_free_staff()
        if not ok_sel:
            shot = self.g.shot(f"venture_semstaff_{cid}")
            self._restore_guard()
            return False, f"open_venture({cid}): {det_sel} (tela={shot}); estado restaurado"

        for _ in range(5):
            wait_text(self.b)
            self.b.press("A", hold=5, wait=25)
            self.b.advance(90)
            if on_map_screen(Image.open(self.b.screenshot()).convert("RGB")):
                break
        else:
            shot = self.g.shot(f"venture_semmapa_{cid}")
            self._restore_guard()
            return False, f"open_venture({cid}): nao chegou ao mapa (tela={shot}); estado restaurado"

        reg, pos, verif = point_cursor_at_world(self.b, cid, self.map_region)
        self.map_region = reg

        # UM A abre direto a tela de tipo (tipo 0) — NAO usar _select_city
        # (ver docstring: martelaria A alem da selecao de tipo).
        wait_text(self.b)
        self.b.press("A", hold=5, wait=25)
        wait_text(self.b)
        self.b.advance(60)
        hash_atual = venture_type_hash(Image.open(self.b.screenshot()).convert("RGB"))

        alcancado = 0
        for _ in range(tipo):
            mudou = False
            for _tentativa in range(3):
                self.b.press("Right", hold=4, wait=18)
                self.b.advance(60)
                novo = venture_type_hash(Image.open(self.b.screenshot()).convert("RGB"))
                if novo != hash_atual:
                    hash_atual = novo
                    alcancado += 1
                    mudou = True
                    break
            if not mudou:
                # Right parou de mudar a tela: OU e o ultimo tipo desta cidade
                # (sem wrap, MEDIDO) OU o toque nao pegou. Ou jeito, nao se
                # segue as cegas — reporta o indice REAL alcancado.
                break

        if alcancado < tipo:
            shot = self.g.shot(f"venture_tipo_limite_{cid}")
            self._restore_guard()
            return False, (f"open_venture({cid}): pedido type_index={tipo}, mas so "
                           f"{alcancado} passo(s) alem do tipo 0 mudaram a tela nesta "
                           f"cidade (catalogo por cidade, sem wrap — MEDIDO variar; "
                           f"Washington tem 3 tipos, ex.: 0=Concert Hall); tela={shot}; "
                           "estado restaurado")

        shot_tipo = self.g.shot(f"venture_tipo{tipo}_{cid}")

        # A confirma o tipo -> "You must negotiate...Is this OK?" -> A confirma
        # de novo -> caixa debitada. _step() em vez de contar A's (o jogo
        # engole toque durante a datilografia).
        for etapa in ("negociacao/pergunta", "confirmacao"):
            if not self._step():
                shot = self.g.shot(f"venture_travou_{cid}")
                self._restore_guard()
                return False, (f"open_venture({cid}, tipo={tipo}): fluxo travou em "
                               f"{etapa} (tela={shot}); estado restaurado")
        self.b.advance(90)

        # --- gate de efeito: caixa CAIU **e** um funcionario SAIU (mesmo
        # padrao duplo do hub — sozinho, nenhum dos dois sinais distingue
        # venture de qualquer outra despesa/negociacao) ---
        caixa_depois = caixa_antes
        for _ in range(4):
            self.b.advance(60)
            caixa_depois = read_cash_k(self.b)
            if caixa_depois < caixa_antes:
                break
        livres_depois = None
        for _ in range(3):
            livres_depois = self._menu_free_staff()
            if livres_depois is not None and livres_depois < livres_antes:
                break
            self.b.advance(120)
        detalhe = (f"{cid} tipo={tipo}, caixa {caixa_antes}K -> {caixa_depois}K "
                   f"({caixa_depois - caixa_antes:+d}K), funcionarios livres "
                   f"{livres_antes} -> {livres_depois}, tela={shot_tipo}")
        if caixa_depois >= caixa_antes:
            self._restore_guard()
            return False, f"open_venture SEM EFEITO (caixa nao caiu) em {detalhe}; estado restaurado"
        if livres_depois is None or livres_depois >= livres_antes:
            self._restore_guard()
            return False, (f"open_venture SEM EFEITO (nenhum funcionario saiu) em "
                           f"{detalhe}; estado restaurado")
        return True, (f"venture iniciado ({detalhe}); NEGOCIACAO EM ANDAMENTO — "
                      "medido que Info->facilities e a campanha de anuncio (r1c1) "
                      "continuam sem contar este venture ate a negociacao concluir "
                      "(meses; sem contador ventures_pending implementado ainda)")

    def _do_ad_campaign(self, p):
        """Executa uma campanha de publicidade cultural (r1c1) para promover
        um business venture PRONTO (1 `end_turn` apos a compra — ver
        `_do_open_venture`) na regiao ativa do mapa.

        ETAPA 10-Marketing, CALIBRADO 18/08. Fluxo medido AO VIVO em
        `_probe_ad2.py`/`_probe_ad3.py` a partir de `states/_venture_pronto.state`
        (Concert Hall pronto em Washington/America do Norte) e documentado em
        CALIBRATION.md ("RESOLVIDO 18/08 — contador de facilities sobe em 1
        end_turn, e r1c1 tem fluxo de sucesso"):

          r1c1 -> seletor de funcionario (mesma barra Buy/Sell/hub/venture) ->
          "We will sponsor cultural events at our facilities." -> tela
          "Culture and Arts" (Standard Expense $1.800K = Promotion Expense
          $1.800K, "Chance for Success average" — fixos no fluxo medido, a
          macro nao alterna a escolha) -> "Are you sure you want to run this
          Culture and Arts campaign?" YES/NO (default YES) -> A confirma ->
          "I'll get right on it." Caixa medida: $1.040.220K -> $1.038.420K,
          -1.800K EXATOS (bate com "Standard Expense" mostrado na tela).

        SEM PARAMETROS: nao ha escolha de regiao/venture/expense medida alem
        do default — a campanha promove TODOS os facilities prontos da regiao
        ATIVA do mapa (a mesma que `open_hub`/`open_venture` usam), sempre com
        a opcao Standard Expense. Nao testado com 2+ facilities prontos na
        mesma regiao nem com regiao != America do Norte.

        RECUSAS MEDIDAS (sem custo — cash intocado em ambas, sem consumir
        funcionario): DUAS telas diferentes, dependendo do motivo:
          - Sem venture PRONTO na regiao (venture ausente OU ainda "em
            negociacao"): "There are no businesses in our [regiao] network to
            promote." (CALIBRATION.md §21, `venture_ad_before.png`/
            `venture_ad_after_imediato.png`) — esta recusa aparece DEPOIS do
            seletor de funcionario.
          - Sem NENHUMA rota nossa na regiao (regiao nunca explorada): "We
            can't run an ad campaign in [regiao]. We don't have any routes
            there." (MEDIDO 18/08 ao vivo em `eval_single_2000_lv5.state`,
            `logs/run_f0/adcamp_semstaff.png`, cash $1.220.000K intocado) —
            esta recusa aparece ANTES do seletor de funcionario (nenhuma
            grade de funcionarios chega a aparecer).
        O executor nao distingue as duas causas (`_pick_free_staff_single`
        retorna vazio nos dois casos, ja que nenhuma tem cracha de
        funcionario detectavel) — reporta so que a caixa nao caiu.

        RELACAO COM O ORCAMENTO DE Ad (r0c4/`set_budget(category="ad")`):
        duas alavancas de demanda DIFERENTES, nao substitutas. `set_budget`
        ajusta um GASTO RECORRENTE por turno (5 niveis MAXIMUM..STOP) que
        entra no P&L todo trimestre automaticamente, sem selecionar
        funcionario nem cidade — e generico, aplica-se a companhia inteira.
        `ad_campaign` e um GASTO PONTUAL (-1.800K medido, 1x por execucao)
        que EXIGE um business venture pronto (Concert Hall/Arts Pavilion/etc,
        comprado via `open_venture`) e consome 1 funcionario livre — sem
        venture nenhum pronto na rede, a acao recusa e nao debita nada,
        MESMO com o orcamento de Ad no maximo. Ou seja `open_venture` e
        pre-requisito de `ad_campaign`, mas nao de `set_budget(ad=...)`.
        """
        from world import at_main_menu_img, read_cash_k

        livres_antes = self._menu_free_staff()
        if livres_antes is None:
            return False, "ad_campaign: nao consegui ler a barra de funcionarios do menu"
        caixa_antes = read_cash_k(self.b)

        self._ensure_menu()
        self.g.open_cmd("ad_campaign")
        wait_text(self.b)
        # `_pick_free_staff_single`, NAO `_pick_free_staff`: a tela de despacho
        # de ad_campaign nao tem o par Bid/Return, entao a trava do generico
        # aborta sempre nesta tela (MEDIDO — ver docstring do helper).
        ok_sel, celula, det_sel = self._pick_free_staff_single()
        if not ok_sel:
            shot = self.g.shot("adcamp_semstaff")
            self._restore_guard()
            return False, f"ad_campaign: {det_sel} (tela={shot}); estado restaurado"

        # Fluxo de SUCESSO medido = exatamente 5 _step() apos selecionar o
        # funcionario (ad3_step3..7.png); folga ate 7 para cobrir a recusa
        # (menos telas) e eventuais variacoes sem martelar as cegas alem do
        # necessario (_step para sozinho quando o texto para de mudar).
        for _ in range(7):
            if not self._step():
                break
            self.b.advance(60)
            if at_main_menu_img(Image.open(self.b.screenshot()).convert("RGB")):
                break

        shot = self.g.shot("adcamp_fim")
        self.dismiss_to_menu()
        self._ensure_menu()
        if not at_main_menu_img(Image.open(self.b.screenshot()).convert("RGB")):
            self._restore_guard()
            return False, f"ad_campaign: nao voltamos ao menu principal (tela={shot}); estado restaurado"

        caixa_depois = read_cash_k(self.b)
        livres_depois = self._menu_free_staff()

        if caixa_depois >= caixa_antes:
            return False, (f"ad_campaign SEM EFEITO (caixa nao caiu: {caixa_antes}K -> "
                           f"{caixa_depois}K) — provavel recusa 'no businesses ... to "
                           f"promote' (nenhum business venture PRONTO na regiao ativa "
                           f"do mapa; compre com open_venture e passe 1 end_turn antes "
                           f"de tentar de novo); tela={shot}")

        detalhe = (f"caixa {caixa_antes}K -> {caixa_depois}K "
                   f"({caixa_depois - caixa_antes:+d}K), funcionarios livres "
                   f"{livres_antes} -> {livres_depois}, tela={shot}")
        return True, f"ad_campaign executada ({detalhe})"

    def dismiss_to_menu(self, max_presses=96, cash_sentinela=20000):
        """Volta ao MENU PRINCIPAL depois do fim de turno. B primeiro; A so em ultimo caso.

        Depois de `end_turn` o jogo pode parar em DUAS familias de tela, e cada
        uma sai por um botao diferente (MEDIDO 17/08, prova_hub.py fase b):
          - NOTICIA/evento ("Switzerland has joined the European Community(EC)")
            -> B nao faz nada; so A dispensa;
          - RELATORIO ANUAL "Regional Rankings 2001" (aparece na virada de ano)
            -> e uma tela NAVEGAVEL: A entra nas caixas de regiao e nao sai; B sai.

        A primeira versao apertava A ate 40 vezes as cegas. Na virada de ano ela
        caiu no relatorio anual, gastou os toques ali, atravessou para o menu e
        **confirmou alguma compra**: a mesma sequencia de 8 turnos terminou com
        860.220K contra 1.132.590K da run de controle — **$276.000K a menos**,
        um quarto do caixa da companhia, gasto por um helper de navegacao.

        Regra nova: B e o botao padrao (cancela, nunca confirma). So quando um B
        NAO muda pixel nenhum — assinatura de tela de mensagem — cabe UM A, e
        volta-se ao B. A tela e conferida ANTES de qualquer toque, entao nunca
        se aperta nada estando no menu.

        MEDIDO 17/08 (probe_hub4/probe_hub5, savestate `_hub_chain.state`):

        - a narracao **nao anda sozinha**: 8.000 frames sem tecla nenhuma e a
          tela para de vez no "Quarterly Report Jul2001" (hash f4a1dc30 repetido
          em 18 blocos seguidos). Esperar nao e alternativa a apertar;
        - o caminho inteiro do fim de turno ate o menu custa **28 toques de B**,
          e **so de B**: relatorio trimestral -> Passenger Totals por regiao ->
          relatorios das 4 companhias -> jogadas dos rivais ("AirRoma entered
          into negotiations with Mexico City") -> menu. Nenhum A foi necessario
          e o caixa terminou em 1.136.200K contra 1.138.020K do inicio (so o
          custo trimestral de $1.820K).

        Por isso o teto subiu de 16 (que ABORTAVA a fase b no turno 1, preso na
        caixa de Regional Rankings) para 48. E por isso existe a **sentinela de
        caixa**: se durante a navegacao o caixa cair mais que `cash_sentinela`,
        alguma tecla confirmou algo e a funcao devolve False em vez de entregar
        um menu contaminado — o unico modo de falha aqui ja MEDIDO custou
        $276.000K.

        MEDIDO 17/08 (ETAPA 1, `probe_demand.py`, savestate `_demand_guard`) —
        DUAS correcoes, as duas com numero:

        1. **48 nao bastava.** Cadeias medidas com B a partir de
           `probe_hub_open_sa`: 35, 38 e uma em que a caixa de pedido ainda
           aparecia no toque **51**. O aceite do end_turn falhou exatamente por
           esgotar o teto — o trimestre TINHA virado. Teto novo: 96.

        2. **A caixa de decisao (YES NO) e uma mina.** A cadeia pode parar em
           "Rep. of EC ... $372000K is requested. Will you back this Project?"
           com o cursor em **YES**. Medido a partir do savestate de guarda:
             - `A` (o fallback desta funcao):  1.133.070K -> **761.070K**  (-372.000K)
             - `Right` + `A` (recusar):        1.133.070K -> 1.133.070K
             - `B` (3 toques ate o menu):      1.133.070K -> 1.133.070K
           Ou seja, **B dispensa o pedido de graca** e o A cobra um terco do
           caixa. Nao foi so sorte esta funcao nao ter pago: o cursor da caixa
           PISCA, entao o teste "dois frames iguais" que autoriza o A nunca
           fechava ali. Agora o A e proibido explicitamente enquanto
           `world.yesno_prompt` enxergar a caixa — a politica do harness e
           **recusar** patrocinio; aceitar e decisao de modelo, e vira acao
           propria quando for calibrada.
        """
        from world import at_main_menu_img, read_cash_k, yesno_prompt

        def _tela():
            p = self.b.screenshot()
            return Image.open(p).convert("RGB"), pathlib.Path(p).read_bytes()

        caixa_inicial = read_cash_k(self.b)
        parado = 0
        for _ in range(max_presses):
            img, antes = _tela()
            if at_main_menu_img(img):
                return True
            self.b.batch(self.b.seq_press("B", hold=5, wait=25) + self.b.seq_advance(90),
                         extra_frames=200)
            if caixa_inicial - read_cash_k(self.b) > cash_sentinela:
                self.g.shot("dismiss_queda_de_caixa")
                return False
            img, depois = _tela()
            if at_main_menu_img(img):
                return True
            if depois != antes:
                parado = 0
                continue  # o B esta funcionando nesta tela; nao arrisque um A
            # B nao mexeu nada. Uma unica leitura igual pode ser so a captura
            # cedo demais, entao exige-se DUAS seguidas antes de arriscar um A
            # (o A e a tecla que confirma — foi ela que queimou o caixa).
            parado += 1
            if parado < 2:
                continue
            if yesno_prompt(img) is not None:
                # Caixa de decisao na tela: o A vale -$372.000K (medido). Aqui
                # so B, e ele resolve — insiste-se com B em vez de arriscar.
                self.g.shot("dismiss_caixa_yesno")
                parado = 0
                continue
            parado = 0
            self.b.batch(self.b.seq_press("A", hold=5, wait=25) + self.b.seq_advance(90),
                         extra_frames=200)
            if caixa_inicial - read_cash_k(self.b) > cash_sentinela:
                self.g.shot("dismiss_queda_de_caixa")
                return False
        return at_main_menu_img(Image.open(self.b.screenshot()).convert("RGB"))

    def hub_ready(self, reg, cidade=None):
        """O hub da regiao `reg` ja abre rota? Pergunta AO JOGO, nao a um contador.

        Sinal: invocar r0c0 com o mapa na regiao e LER a caixa de rodape.
        "We don't have a regional hub here." (md5 11d9dcad, medido em 4
        capturas) = ainda nao. Qualquer banner de origem = sim, e o banner
        ainda diz DE QUAL cidade a rota partiria.

        A versao anterior deste metodo usava so `activate_cursor` (cursor vivo =
        pronto) e deu TRES falsos positivos seguidos numa tela de noticia, onde
        nem mapa havia — por isso agora exige o menu principal antes de comecar
        e le a caixa em vez de sondar o cursor. A tela e sempre desfeita por
        savestate, nunca por tecla.
        """
        from world import REGION_NAMES, route_screen_kind

        if not self.dismiss_to_menu():
            return False, f"hub_ready({reg}): nao consegui chegar ao menu principal"
        self.b.save(GUARD)
        self._snap = self._snapshot()
        pronto, det = False, ""
        try:
            ok_reg, det_reg = self._goto_region(reg)
            if not ok_reg:
                return False, f"hub_ready({reg}): {det_reg}"
            self.g.open_cmd("new_route")
            wait_text(self.b)
            self.b.advance(120)
            shot = self.g.shot(f"hub_ready_r{reg}")
            kind, val = route_screen_kind(Image.open(shot).convert("RGB"))
            pronto = kind != "sem_hub"
            det = (f"regiao {reg} {REGION_NAMES[reg]}: caixa da tela de rota = "
                   f"{kind}:{val} (tela={shot})")
        finally:
            self._restore_guard()
        if pronto and cidade:
            self.hubs.add(cidade)
            self.hubs_pending.pop(reg, None)
        return pronto, det

    def _do_suspend_route(self, p):
        """SUSPENDE uma rota aberta (pausa reversivel, nao fecha).

        ETAPA 3-RotaFechar, CORRIGIDO 18/08: acao executada direto na barra de abas.

        Fluxo simples: route_edit -> resumo (A) -> barra de abas (A) ->
        Left ate Susp -> A ativa -> ACAO EXECUTADA (rota suspendida) -> barra muda
        para "Resume" em vez de "Susp" -> volta ao menu principal via B repetidos.

        Sinal de efeito IMEDIATO:
        - A barra de abas muda: "Susp" vira "Resume" na primeira celula
        - A rota continua listada (count = 1)
        - Flts pode virar 0 quando suspendida?

        ARMOR DELIBERADO: ate medir o efeito completo, recusa se ha mais de uma rota
        aberta (igual adjust_route).
        """
        from world import city_region

        dest = p.get("route") or p.get("to")
        if not dest:
            return False, "suspend_route sem 'route' (destino da rota a suspender)"
        alvo = next((r for r in self.routes if r.get("to") == dest), None)
        if alvo is None:
            return False, f"suspend_route: nenhuma rota aberta para {dest} (rotas: {self.routes})"
        if len(self.routes) > 1:
            return False, (
                f"suspend_route({dest}) recusado: ha {len(self.routes)} rotas abertas e o "
                "harness ainda nao sabe navegar a lista para escolher uma especifica"
            )

        self._ensure_menu()
        origem = alvo.get("from")
        if origem:
            ok_reg, det_reg = self._goto_region(city_region(origem))
            if not ok_reg:
                self._restore_guard()
                return False, f"suspend_route({dest}): {det_reg} — estado restaurado"

        self.g.open_cmd("route_edit")
        wait_text(self.b)
        self.b.advance(60)
        self.b.press("A", hold=5, wait=25)   # resumo -> barra de abas
        self.b.advance(80)

        if not self._route_tab_to("susp"):
            shot = self.g.shot(f"suspend_travou_{dest}")
            self._restore_guard()
            return False, f"suspend_route({dest}): nao cheguei na aba Susp (tela={shot})"

        # Ativar Susp -> EXECUTA A ACAO IMEDIATAMENTE (rota é suspendida)
        # A barra de abas mudará: "Susp" vira "Resume"
        self.b.press("A", hold=5, wait=25)
        self.b.advance(150)
        wait_text(self.b)

        # Verificar se a acao foi executada: a primeira aba agora deve ser "resume" (indice 0)
        tab_atual = self._route_tab_index()
        # Indice 0 deveria ser "susp", mas agora pode ser "resume" (resultado de suspender)
        # Por enquanto, sair da barra de abas (voltar ao menu principal)
        self.b.press("B", hold=3, wait=14)
        self.b.advance(100)

        if not self._ensure_menu():
            self._restore_guard()
            return False, f"suspend_route({dest}): nao voltou ao menu apos Susp; estado restaurado"

        return True, f"suspend_route({dest}): rota suspendida"

    def _do_close_route(self, p):
        """FECHA uma rota aberta PERMANENTEMENTE (destrutivo, nao reversivel).

        ETAPA 3-RotaFechar, CORRIGIDO 18/08: acao executada direto na barra de abas.

        Fluxo simples: route_edit -> resumo (A) -> barra de abas (A) ->
        Right ate Close -> A ativa -> ACAO EXECUTADA (rota fechada) -> sai da
        barra de abas (rota foi deletada) -> volta ao menu principal.

        Sinal de efeito CLARO:
        - A rota some da lista de rotas (count: 1 -> 0)
        - Fecha automaticamente a barra de abas quando nao ha mais rotas

        ARMOR DELIBERADO: ate medir o efeito completo, recusa se ha mais de uma rota
        aberta (igual adjust_route).
        """
        from world import city_region

        dest = p.get("route") or p.get("to")
        if not dest:
            return False, "close_route sem 'route' (destino da rota a fechar)"
        alvo = next((r for r in self.routes if r.get("to") == dest), None)
        if alvo is None:
            return False, f"close_route: nenhuma rota aberta para {dest} (rotas: {self.routes})"
        if len(self.routes) > 1:
            return False, (
                f"close_route({dest}) recusado: ha {len(self.routes)} rotas abertas e o "
                "harness ainda nao sabe navegar a lista para escolher uma especifica"
            )

        self._ensure_menu()
        origem = alvo.get("from")
        if origem:
            ok_reg, det_reg = self._goto_region(city_region(origem))
            if not ok_reg:
                self._restore_guard()
                return False, f"close_route({dest}): {det_reg} — estado restaurado"

        self.g.open_cmd("route_edit")
        wait_text(self.b)
        self.b.advance(60)
        self.b.press("A", hold=5, wait=25)   # resumo -> barra de abas
        self.b.advance(80)

        if not self._route_tab_to("close"):
            shot = self.g.shot(f"close_travou_{dest}")
            self._restore_guard()
            return False, f"close_route({dest}): nao cheguei na aba Close (tela={shot})"

        # Ativar Close -> EXECUTA A ACAO IMEDIATAMENTE (rota é deletada)
        self.b.press("A", hold=5, wait=25)
        self.b.advance(150)
        wait_text(self.b)

        # A rota foi deletada, entao a barra de abas pode ter saido automaticamente
        # (ou a lista de rotas fica vazia). Sair via B para voltar ao menu principal.
        self.b.press("B", hold=3, wait=14)
        self.b.advance(100)

        if not self._ensure_menu():
            self._restore_guard()
            return False, f"close_route({dest}): nao voltou ao menu apos Close; estado restaurado"

        # Remover a rota da escrituracao do harness (ela foi deletada no jogo).
        self.routes = [r for r in self.routes if r.get("to") != dest]

        return True, f"close_route({dest}): rota fechada e removida da lista"

    def _do_wait(self, p):
        return True, "sem acao neste trimestre"

    def _do_set_budget(self, p):
        """Define o nivel de orcamento de uma categoria (Repair/Ad/Service).

        Params:
          category (str): "repair" | "ad" | "service"
          level (int): 0-4 (MAXIMUM=0, RAISE=1, MAINTAIN=2, REDUCE=3, STOP=4)

        Retorna: (success, msg) onde success=True se aplicado, False + erro se nao.

        CORREÇÕES (18/08):
        - Navegar ordem com malha fechada: ler rótulo após cada Down
        - Confirmar com guard on_budget_screen() entre os _step chamados
        - Retornar False se label não bater no alvo (não warn-and-continue)
        """
        category = p.get("category", "").lower()
        level = p.get("level")

        cat_map = {"repair": 0, "ad": 1, "service": 2}
        if category not in cat_map:
            return False, f"categoria desconhecida: {category} (use repair/ad/service)"
        if not isinstance(level, int) or level < 0 or level > 4:
            return False, f"level {level} invalido (use 0-4: MAXIMUM/RAISE/MAINTAIN/REDUCE/STOP)"

        col = cat_map[category]
        from world import read_budget_money, read_budget_col, read_budget_orders, BUDGET_ORDERS

        # Ler estado antes
        self._ensure_menu()
        self.g.open_cmd("budgets")
        self.b.advance(200)

        # Verificar que estamos na tela de orçamentos
        img = Image.open(self.b.screenshot()).convert("RGB")
        if not world.on_budget_screen(img):
            self._restore_guard()
            return False, "nao consegui abrir a tela de orcamentos"

        # Ler valores antes
        money_before = read_budget_money(img)
        if money_before is None or not isinstance(money_before, list) or len(money_before) < 3:
            self._restore_guard()
            return False, f"nao consegui ler orcamentos antes (money={money_before})"
        money_before = money_before[col]   # pode ser None por glifo desconhecido

        # STEP 1: navegar para a coluna selecionada
        col_atual = world.wait_budget_col(self.b, tries=4)
        if col_atual is None:
            self._restore_guard()
            return False, "nao consegui ler coluna selecionada"

        steps_needed = (col - col_atual) % 3
        for step in range(steps_needed):
            self.b.press("Right", hold=3, wait=14)
            self.b.advance(40)
            img = Image.open(self.b.screenshot()).convert("RGB")
            col_novo = world.read_budget_col(img)
            if col_novo != col and step == steps_needed - 1:
                self._restore_guard()
                return False, f"navegacao de coluna falhou (esperava {col}, li {col_novo})"

        # STEP 2: abrir a popup de ordem
        self.b.press("A", hold=5, wait=25)
        self.b.advance(200)

        # STEP 3: navegar para a ordem desejada (malha fechada com leitura de rótulo)
        img = Image.open(self.b.screenshot()).convert("RGB")
        orders_lidas = read_budget_orders(img)
        order_atual_str = orders_lidas[col] if orders_lidas and orders_lidas[col] else None
        if order_atual_str is None:
            self._restore_guard()
            return False, f"nao consegui ler ordem inicial na coluna {col}"

        # BUG RAIZ CORRIGIDO 19/08: `BUDGET_ORDERS` guarda os rotulos em
        # MINUSCULO ("maximum", "raise", ...) e todo este bloco comparava em
        # MAIUSCULO. Nenhuma busca casava: o `in` dava False sempre e o codigo
        # caia no indice assumido (0 = maximum), enquanto a confirmacao final
        # recusava texto IDENTICO ("li 'maximum', esperava 'maximum'").
        # Era esta a falha real do set_budget — o "Down-only" apontado pela
        # auditoria era sintoma dela, nao a causa.
        _norm = order_atual_str.strip().lower()
        if _norm not in BUDGET_ORDERS:
            self._restore_guard()
            return False, f"ordem inicial ilegivel na coluna {col}: {order_atual_str!r}"
        order_idx_atual = BUDGET_ORDERS.index(_norm)

        # Navegar ate a ordem desejada, EM QUALQUER SENTIDO (malha fechada).
        #
        # BUG CORRIGIDO 19/08: o laco era `while order_idx_atual < level` com
        # Down fixo, ou seja, so sabia DESCER na lista. Pedir uma ordem ACIMA da
        # atual (ex.: de `reduce` para `maximum`) nao apertava nada e caia no
        # "navegacao de ordem falhou". Foi por isso que a auditoria classificou a
        # calibracao como falso-positivo: os testes tinham escolhido, por acaso,
        # so alvos abaixo do valor corrente.
        max_tries = 2 * 5 + 4  # proteção contra loop infinito
        tries = 0
        while order_idx_atual != level and tries < max_tries:
            botao = "Down" if order_idx_atual < level else "Up"
            self.b.press(botao, hold=3, wait=14)
            self.b.advance(40)
            img = Image.open(self.b.screenshot()).convert("RGB")
            orders_lidas = read_budget_orders(img)
            order_nova_str = orders_lidas[col] if orders_lidas and orders_lidas[col] else None
            if order_nova_str is None:
                self._restore_guard()
                return False, f"nao consegui ler ordem nova na coluna {col}, try {tries + 1}"
            _n = order_nova_str.strip().lower()
            order_idx_novo = BUDGET_ORDERS.index(_n) if _n in BUDGET_ORDERS else order_idx_atual
            if order_idx_novo == order_idx_atual:
                # O rotulo nao mudou apos o toque: ou batemos na ponta da lista,
                # ou o input foi engolido pela animacao. Insistir as cegas aqui e
                # o padrao que ja passou do alvo em outras telas; melhor falhar.
                self._restore_guard()
                return False, (f"ordem travada em '{order_nova_str}' (idx {order_idx_atual}) "
                               f"apos {botao}; alvo era idx {level}")
            order_idx_atual = order_idx_novo
            tries += 1

        if order_idx_atual != level:
            self._restore_guard()
            return False, f"navegacao de ordem falhou (esperava idx {level}, li {order_idx_atual})"

        # Capturar antes de confirmar
        img_pre = Image.open(self.b.screenshot()).convert("RGB")
        orders_pre = read_budget_orders(img_pre)
        order_pre = orders_pre[col] if orders_pre and orders_pre[col] else None
        if order_pre and order_pre.strip().lower() != BUDGET_ORDERS[level]:
            self._restore_guard()
            return False, f"ordem selecionada nao bate: li '{order_pre}', esperava '{BUDGET_ORDERS[level]}'"

        # STEP 4: confirmar a ordem (apertar A com guard on_budget_screen)
        for i in range(2):
            img_check = Image.open(self.b.screenshot()).convert("RGB")
            # `on_budget_family` e nao `on_budget_screen`: com a caixa
            # "What are your orders?" aberta o realce do cabecalho some e o
            # detector estrito da False com a tela certa na frente (medido em
            # CALIBRATION §28). O guard continua existindo — so parou de recusar
            # o A que ele deveria proteger.
            if not world.on_budget_family(img_check):
                self._restore_guard()
                return False, f"deixei a tela de orcamento no confirm A#{i+1}"
            self._step(tries=4)
        self.b.advance(120)

        # Ler estado depois
        img_pos = Image.open(self.b.screenshot()).convert("RGB")
        if not world.on_budget_family(img_pos):
            self._restore_guard()
            return False, "nao retornei a tela de orcamentos apos confirmar"

        money_after = read_budget_money(img_pos)
        if money_after is None or not isinstance(money_after, list) or len(money_after) < 3:
            self._restore_guard()
            return False, f"nao consegui ler orcamentos depois (money={money_after})"
        money_after = money_after[col]
        # O CUSTO e informacao acessoria; a ORDEM e o efeito. Um digito fora do
        # catalogo da linha de dinheiro (falta "3" e "8") deixava `money_*` em
        # None e a subtracao la embaixo derrubava a acao inteira com TypeError —
        # transformando em falha um set_budget que ja tinha aplicado a ordem
        # certa, com as colunas vizinhas intactas e o caixa parado. Agora o custo
        # ilegivel vira texto, nao excecao.

        # Verificar novamente que a ordem foi aplicada (leitura de rótulo pós-confirmação)
        orders_pos = read_budget_orders(img_pos)
        order_pos = orders_pos[col] if orders_pos and orders_pos[col] else None
        if order_pos and order_pos.strip().lower() != BUDGET_ORDERS[level]:
            self._restore_guard()
            return False, f"ordem nao foi aplicada: pos-confirm li '{order_pos}', esperava '{BUDGET_ORDERS[level]}'"

        # Voltar ao menu principal
        self.dismiss_to_menu()
        self._ensure_menu()

        # Verificar se voltamos ao menu
        # `b.screenshot()` devolve o CAMINHO do PNG, nao a imagem — passar o
        # caminho direto levantava "'str' object has no attribute 'load'" e
        # transformava um set_budget que JA tinha funcionado (ordem aplicada,
        # vizinhas intactas, caixa parada) em ok=False.
        if not world.at_main_menu_img(Image.open(self.b.screenshot()).convert("RGB")):
            self._restore_guard()
            return False, "nao voltamos ao menu principal apos set_budget"

        # Resumo de efeito
        order_name = BUDGET_ORDERS[level]
        if money_before is None or money_after is None:
            delta_str = (f"custo nao lido (antes={money_before}, depois={money_after}) "
                         f"— digito fora do catalogo da linha de dinheiro")
        else:
            delta = money_after - money_before
            delta_str = f"{money_before}K -> {money_after}K ({delta:+d}K)"

        return True, f"set_budget({category}={order_name}): {delta_str}"
