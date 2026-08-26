"""Macros de menu do Aerobiz Supersonic (USA/SNES).

Mapa dos 12 comandos levantado no F0 (11/08/2026) — ver logs/run_f0/INVENTARIO_TELAS.md.
Toda macro parte do MENU PRINCIPAL e volta para ele (padrao: navega, age, recua).
"""

import hashlib
import pathlib

from bridge import BizHawkBridge

# (linha, coluna) na grade 6x2 de icones
CMD = {
    "new_route": (0, 0),
    "route_edit": (0, 1),      # exige rotas existentes
    "negotiate": (0, 2),       # enviar funcionario: Bid / Return
    "buy_aircraft": (0, 3),    # escolher fabricante
    "budgets": (0, 4),         # Repair / Ad / Service
    "buy_sell": (0, 5),        # Buy / Sell via funcionario
    "home_info": (1, 0),
    "ad_campaign": (1, 1),     # exige rotas
    "meeting": (1, 2),
    "info": (1, 3),            # submenu de relatorios
    "system": (1, 4),          # Save / Animation / Sound / Message / End Game
    "end_turn": (1, 5),
}

# Itens do submenu Info (ordem da esquerda para a direita)
INFO = {
    "map": 0,
    "staff": 1,
    "fleet": 2,        # Plane | In Use | Avail | Order
    "finance": 3,      # P&L completo do periodo
    "facilities": 4,   # Cultural Facilities por regiao
    "victory": 5,      # CONDICOES DE VITORIA + status por regiao  <- placar do eval
}

# Apertar A pula a animacao de texto, entao acoes nao precisam espera-la; so as
# capturas que vamos LER precisam. O core SNES roda a ~32fps aqui, entao cada
# frame economizado conta.
TEXT_SETTLE = 70    # entre passos de menu
READ_SETTLE = 200   # antes de capturar uma tela para leitura

# Assinatura do menu principal: o mini-mapa do rodape (regiao atual em vermelho).
# NAO usar a grade de icones — o cursor fica sobre um icone diferente a cada vez
# e a diferenca dispara falso negativo.
GRID_REF = pathlib.Path(__file__).parent.parent / "logs" / "run_f0" / "menu_top.png"
GRID_BOX = (4, 183, 70, 199)


class Game:
    def __init__(self, bridge=None, shot_dir=None):
        self.b = bridge or BizHawkBridge()
        self.shots = pathlib.Path(shot_dir or (pathlib.Path(__file__).parent.parent / "logs" / "run_f0"))
        self.shots.mkdir(parents=True, exist_ok=True)

    # --- navegacao basica (tudo em lote: 1 ida-e-volta por sequencia) ---
    def back_to_menu(self, times=4):
        """B repetido volta ao menu principal de qualquer submenu."""
        self.b.batch(self.b.seq_press("B", hold=5, wait=20, times=times) + self.b.seq_advance(40))

    def open_cmd(self, name):
        """Navega ate um icone e abre.

        O 'homing' (Left x6, Up x2) e obrigatorio: o cursor de icones fica onde
        o comando anterior o deixou, e sem isso abre-se o comando errado.
        """
        row, col = CMD[name]
        seq = (
            self.b.seq_press("Left", hold=3, wait=10, times=6)
            + self.b.seq_press("Up", hold=3, wait=10, times=2)
            + self.b.seq_press("Down", hold=3, wait=10, times=row)
            + self.b.seq_press("Right", hold=3, wait=10, times=col)
            + self.b.seq_press("A", hold=5, wait=40)
            + self.b.seq_advance(TEXT_SETTLE)
        )
        self.b.batch(seq, extra_frames=200)

    def shot(self, name):
        return self.b.screenshot(self.shots / f"{name}.png")

    def _frame(self):
        import pathlib

        # Hash dos bytes do PNG em vez de decodificar com PIL: medido, o decode
        # custava 2.2s por frame contra 0.4s do screenshot — era ~80% do tempo
        # de cada acao. Igualdade exata de bytes basta para "mudou / nao mudou".
        return hashlib.md5(pathlib.Path(self.shot("_f")).read_bytes()).digest()

    def wait_stable(self, max_polls=4, settle=25):
        """Espera a tela parar de mudar (fim da animacao de texto)."""
        prev = self._frame()
        for _ in range(max_polls):
            self.b.advance(settle)
            cur = self._frame()
            if cur == prev:
                return cur
            prev = cur
        return prev

    def press_until_change(self, button="A", max_presses=2, poll=3, settle=30, threshold=120):
        """Aperta e ESPERA a tela mudar antes de cogitar apertar de novo.

        Dois cuidados aprendidos na marra:
        - o jogo ignora input durante a animacao de texto, entao um press cego
          pode ser engolido;
        - mas reapertar cedo demais avanca DOIS passos do fluxo. A mudanca de
          uma selecao e so uma moldura fina (~150px), dai o limiar baixo e o
          poll entre presses em vez de press-press-press.
        """
        before = self.wait_stable()
        for _ in range(max_presses):
            self.b.press(button, hold=5, wait=22)
            for _ in range(poll):
                self.b.advance(settle)
                if self._frame() != before:
                    return True
        return False

    # --- leitura de estado ---
    def info_screen(self, which, name=None):
        """Abre um relatorio do submenu Info e devolve o caminho do screenshot."""
        self.back_to_menu()
        self.open_cmd("info")
        for _ in range(INFO[which]):
            self.b.press("Right", hold=3, wait=10)
        self.b.press("A", hold=5, wait=40)
        self.b.advance(READ_SETTLE)
        p = self.shot(name or f"info_{which}")
        self.back_to_menu()
        return p

    def capture_turn(self, turn):
        """Captura o conjunto de telas que descrevem o turno (fonte do state.json)."""
        self.back_to_menu()
        out = {"main": self.shot(f"t{turn:02d}_main")}
        for which in ("fleet", "finance", "victory"):
            out[which] = self.info_screen(which, f"t{turn:02d}_{which}")
        return out

    # --- acoes ---
    def end_turn(self, dismiss=None, tentativas=3):
        """Passa UM trimestre. Devolve (ok, detalhe).

        O sinal de virada e o CONTADOR DE TRIMESTRES da RAM (world.QUARTER_ADDR,
        16 bits, trimestres desde JAN/1955): a virada e `contador == antes + 1`,
        exato, sem depender de nada mais.

        Duas coisas estavam erradas na versao anterior e as duas causavam o
        sintoma "4 chamadas, 3 turnos":

        1. O DETECTOR era "o caixa mudou". O caixa NAO muda todo trimestre —
           medido: 1218240 -> 1218240 -> 1216420 -> 1216420 em 4 chamadas. Com
           o caixa parado a funcao concluia que o turno nao tinha passado.
        2. O que ela fazia diante disso era pior: reabrir r1c5 (passando um
           SEGUNDO trimestre sem ninguem contar) e martelar ate 160 toques de A
           as cegas. `Executor.dismiss_to_menu` documenta o preco medido desse
           padrao: A na tela de "Regional Rankings" da virada de ano confirmou
           uma compra e queimou $276.000K.

        Agora: o caminho de volta e o `dismiss_to_menu` (B primeiro, A so em
        tela travada, sentinela de caixa), usado DUAS vezes — antes de agir,
        para garantir que o r1c5 e disparado do menu principal, e depois, para
        atravessar a cadeia de relatorios. Entre as duas o contador diz o que
        aconteceu, e so se ele NAO andou o comando e reemitido.

        Um pulo de 2+ trimestres e FALHA, nao sucesso: e o modo de falha que
        ninguem via, e ele desalinha a data do prompt do modelo com a do jogo.
        """
        from world import date_label, read_cash_k, read_quarter_index

        if dismiss is None:
            # Import tardio de proposito: executor importa macros no topo.
            from executor import Executor

            ex = Executor(self.b)
            ex.g = self
            dismiss = ex.dismiss_to_menu

        antes = read_quarter_index(self.b)
        caixa_antes = read_cash_k(self.b)
        estado = {"disparos": 0}

        def veredito(ok_menu):
            """Le o contador e decide. NUNCA dispara r1c5; so classifica.

            A ORDEM importa e foi um bug medido (ETAPA 1, aceite no savestate
            `probe_hub_open_sa`): a versao anterior desistia assim que o
            `dismiss` falhava, ANTES de olhar o contador, e devolveu False numa
            chamada em que o trimestre TINHA virado (186 -> 187). Falso negativo
            aqui e pior que falso positivo: o chamador reexecuta e o jogo pula
            um turno que ninguem contou. Entao: primeiro o contador, e "nao
            voltei ao menu" so decide entre dois jeitos de FALHAR.
            """
            agora = read_quarter_index(self.b)
            disparos = estado["disparos"]
            if agora == antes + 1:
                if ok_menu:
                    return True, (f"{date_label(antes)} -> {date_label(agora)} "
                                  f"(contador {antes} -> {agora}, {disparos} disparo(s), "
                                  f"caixa {caixa_antes}K -> {read_cash_k(self.b)}K)")
                return False, (f"TRIMESTRE VIROU ({date_label(antes)} -> "
                               f"{date_label(agora)}) mas nao voltei ao menu "
                               f"principal — NAO reexecute end_turn, o turno ja "
                               f"passou ({disparos} disparo(s))")
            if agora != antes:
                return False, (f"end_turn PULOU {agora - antes} trimestres: "
                               f"{date_label(antes)} -> {date_label(agora)} "
                               f"(contador {antes} -> {agora}, {disparos} disparo(s))")
            if not ok_menu:
                return False, (f"end_turn: nao cheguei ao menu principal e o "
                               f"trimestre nao virou ({date_label(agora)}, "
                               f"{disparos} disparo(s)) — dismiss_to_menu recusou "
                               f"(tela travada ou sentinela de caixa)")
            return None, ""   # no menu, mesmo trimestre: cabe (re)disparar

        for _ in range(tentativas):
            ok_menu = dismiss()
            if not ok_menu and read_quarter_index(self.b) == antes + 1:
                # Virou, mas a cadeia de relatorios ficou aberta. Insistir no
                # caminho de volta e barato; redisparar o comando custaria um
                # trimestre que ninguem pediu.
                ok_menu = dismiss()
            ok, det = veredito(ok_menu)
            if ok is not None:
                return ok, det
            self.open_cmd("end_turn")
            self.b.advance(120)
            estado["disparos"] += 1
        # BUG CORRIGIDO 17/08 (ETAPA 1): o contador so era conferido no TOPO da
        # iteracao seguinte, entao o efeito do ULTIMO disparo nunca era lido. Se
        # a 3a tentativa funcionasse, a funcao devolvia False com o jogo um
        # trimestre a frente — a mesma dessincronia que esta etapa mata.
        ok, det = veredito(dismiss())
        if ok is not None:
            return ok, det
        agora = read_quarter_index(self.b)
        return False, (f"end_turn nao virou o trimestre em {tentativas} tentativas: "
                       f"contador parado em {agora} ({date_label(agora)}), "
                       f"{estado['disparos']} disparo(s)")

    def at_main_menu(self, img=None):
        """Detector UNICO do menu principal: imagem (vermelho da placa + terra).

        Havia DOIS detectores divergentes: o Executor usava a imagem e este usava
        a RAM 0x0106 == 7 — endereco que ja foi MEDIDO como nao confiavel (variou
        7 -> 14 entre turnos). O diagnostico do bug da 2a negociacao chegou a
        apontar "menu inacessivel" com menu_red=108 e land=2266, ou seja, com a
        tela CERTA na frente: quem mentia era o detector por RAM.
        """
        from PIL import Image

        from world import at_main_menu_img

        img = img or Image.open(self.b.screenshot()).convert("RGB")
        return at_main_menu_img(img)

    def advance_until_my_turn(self, max_rounds=20, per_round=4):
        """Avanca eventos e a narracao dos rivais ate voltarmos ao menu principal.

        Cada rodada dispara `per_round` presses num unico BATCH e so entao le o
        byte de tela na RAM — barato o suficiente para checar com frequencia.
        """
        for i in range(max_rounds):
            if self.at_main_menu():
                return i
            self.b.batch(
                self.b.seq_press("A", hold=4, wait=16, times=per_round) + self.b.seq_advance(30),
                extra_frames=150,
            )
        return -1
