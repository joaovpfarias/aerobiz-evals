"""Consulta AO VIVO dos stats de uma cidade — para o modelo comparar antes de decidir.

Por que consulta e nao cache: os numeros do painel MUDAM com a epoca do cenario
e envelhecem dentro da propria partida (MEDIDO, CALIBRATION §35.1: Washington
1.2M/90/48 num savestate e 0.6M/60/42 noutro). Um cache generico seria veneno
silencioso — nao da erro e contamina toda decisao. Lendo na hora, o dado e
sempre o do estado atual.

E ha um ganho de EVAL, nao so de correcao: pesquisar antes de agir vira
comportamento MEDIVEL. Um modelo fraco abre rota no escuro; um forte compara
duas ou tres cidades primeiro. Essa diferenca aparece no log.

Custo: ~1 min por cidade (12 toques ate o mapa + ~9 por cidade). Por isso ha
teto por turno — pesquisa e barata em dinheiro (o painel NAO cobra: caixa
medida antes e depois), mas cara em tempo de parede.
"""

import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import world  # noqa: E402

MAX_POR_TURNO = 5   # teto de cidades por rodada de pesquisa
STEP_SETTLE = 40


def _entrar_no_mapa(b, ex):
    """Abre o fluxo r0c2 e para no mapa (a unica tela que expoe o painel)."""
    ex.g.open_cmd("negotiate")
    world.wait_text(b)
    for _ in range(5):
        world.wait_text(b)
        b.press("A", hold=5, wait=25)
        b.advance(STEP_SETTLE)
        if world.on_map_screen(Image.open(b.screenshot()).convert("RGB")):
            return True
    return False


def inspect(b, ex, cids, shot_dir=None, max_cidades=MAX_POR_TURNO):
    """Le o painel de cada cidade pedida. Devolve (dados, avisos).

    NUNCA levanta por cidade ruim: cidade que falhar entra em `avisos` e as
    outras seguem. Abortar no meio deixaria o jogo numa tela intermediaria, que
    e pior que um dado faltando.

    GUARDA DE CAIXA (R2): consultar e leitura, tem que custar zero. Se o caixa
    cair, a funcao PARA — significa que um `A` vazou para uma tela de
    confirmacao, e foi assim que ja se queimou $276.000K.
    """
    dados, avisos = {}, []
    pedidas = [c for c in dict.fromkeys(cids or []) if c in world.WORLD_CITIES]
    desconhecidas = [c for c in (cids or []) if c not in world.WORLD_CITIES]
    if desconhecidas:
        avisos.append("ids fora do catalogo, ignorados: %s" % desconhecidas)
    if len(pedidas) > max_cidades:
        avisos.append("pedidas %d cidades, teto e %d — consultei as %d primeiras"
                      % (len(pedidas), max_cidades, max_cidades))
        pedidas = pedidas[:max_cidades]
    if not pedidas:
        return dados, avisos

    caixa0 = world.read_cash_k(b)
    if not _entrar_no_mapa(b, ex):
        ex.dismiss_to_menu()
        return dados, avisos + ["nao cheguei ao mapa; nenhuma cidade consultada"]

    regiao = None
    for cid in pedidas:
        try:
            regiao, _pos, verif = world.point_cursor_at_world(b, cid, regiao)
            world.wait_text(b)
            b.press("A", hold=5, wait=25)
            b.advance(STEP_SETTLE)
            world.wait_text(b)
            caminho = (pathlib.Path(shot_dir) / ("painel_%s.png" % cid)) if shot_dir else None
            img = Image.open(b.screenshot(str(caminho) if caminho else None)).convert("RGB")
            if not world.on_city_panel(img):
                avisos.append("%s: a tela aberta nao e o painel de cidade" % cid)
            else:
                p = world.read_city_panel(img)
                p["cursor_verificado"] = verif
                dados[cid] = p
            b.press("B", hold=5, wait=25)   # B devolve o mapa (medido 5/5)
            b.advance(STEP_SETTLE)
            caixa = world.read_cash_k(b)
            if caixa is not None and caixa0 is not None and caixa < caixa0:
                avisos.append("PAREI em %s: o caixa CAIU %sK -> %sK durante a consulta"
                              % (cid, caixa0, caixa))
                break
        except Exception as e:  # noqa: BLE001
            avisos.append("%s: %s" % (cid, e))
    ex.dismiss_to_menu()
    return dados, avisos


def formatar(dados, avisos):
    """Texto curto para devolver ao modelo. `?` = campo nao decodificado (R1)."""
    if not dados and not avisos:
        return "nenhuma cidade consultada"
    linhas = []
    for cid, p in dados.items():
        nome = world.WORLD_CITIES.get(cid, ("", "", "", cid))[3]
        def n(v):
            return "?" if v is None else v
        linhas.append(
            "%s (%s): pop %sM | econ %s | turismo %s | slots %s/%s (nossos %s)"
            % (cid, nome, n(p.get("pop_m")), n(p.get("econ")), n(p.get("trsm")),
               n(p.get("slots_used")), n(p.get("slots_cap")), n(p.get("our_slots")))
        )
    for a in avisos:
        linhas.append("AVISO: %s" % a)
    return "\n".join(linhas)
