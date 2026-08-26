"""Baselines NAO-LLM: aleatoria-legal (piso) e gulosa (heuristica honesta).

Sem baseline o placar do eval nao significa nada: nao da para separar "o modelo
jogou bem" de "o jogo e facil". As duas entram pelo MESMO caminho do agente LLM
— mesmo savestate, mesmo `pilot.py`, mesmo `Executor`, mesmo `turns.jsonl`,
mesma telemetria, mesmo `resumo.json`.

REESCRITA EM 24/08 (ETAPA 4-Baselines). A versao anterior tinha sido escrita
contra o `schema.STATE_EXAMPLE` (v0) e NAO casava mais com nada do que o pilot
manda hoje. Todo item abaixo foi conferido no `pilot.estado_para_prompt` e no
`schema.py` atuais — baseline que emite parametro invalido nao e baseline, e
ruido, e ruido correlacionado (erra sempre igual) e pior que ruido aleatorio:

  * `company.planes[].idle`  -> `company.fleet[].avail` (lido de Info->fleet;
    pode vir a string "nao lido neste turno", e ai a frota e DESCONHECIDA, nao
    zero);
  * `company.slots`          -> NAO EXISTE. Quantos slots temos por cidade so
    aparece dentro das linhas de texto de `cities_by_region`
    (`ledger=N` e `(nossosN)`); ver `_linhas_de_cidade`;
  * `company.routes`         -> `company.routes_open` (e as linhas sao
    {origin,dest,load_pct} quando lidas do jogo, {from,to,flights} quando vem
    do ledger do harness — NAO ha `fare_level` nem `flights_week` em nenhuma
    das duas);
  * `company.negotiations`   -> `company.negotiations_pending` +
    `negociadores_livres` (o teto REAL sao os 4 negociadores, e quantos estao
    na base e leitura da barra do menu);
  * nomes de cidade ("New York", "London") -> IDs do jogo ("NA13"). O pool
    antigo era 100% invalido: `agent.Run._check_cities` recusaria TODAS as
    acoes das duas baselines, que marcariam 0 acoes por turno para sempre;
  * `open_route.aircraft`    -> nao existe mais (param desconhecido = acao
    recusada). Os opcionais medidos sao `aircraft_index` (default 0) e
    `planes` (default 1); `from` tem de ser hub CONFIRMADO — hub em negociacao
    e recusado como origem (executor.py:391);
  * `negotiate_slots.slots`  -> opcional, alcance MEDIDO 1..5 (schema.PARAM_RANGES);
  * `employee`               -> removido do action space; nao emitir.

ACHADOS que ficam registrados aqui porque foram medidos ao escrever isto (R5):

 A) `schema.validate_action` limita negociacoes simultaneas lendo
    `state["company"]["negotiations"]` — chave que o estado REAL nunca teve
    (o pilot escreve `negotiations_pending`). Essa guarda e LETRA MORTA em run
    ao vivo. As baselines se auto-limitam por `negociadores_livres`, que e
    leitura do jogo.
 B) `ad_campaign` esta em `pilot.SUPPORTED` (portanto e oferecida ao LLM no
    prompt) mas NAO esta em `schema.ACTIONS`: toda emissao volta como "acao
    desconhecida" na validacao, antes de chegar ao executor — que a implementa.
    Sao 10 acoes anunciadas e 9 emitiveis. Nenhuma baseline a emite.
"""

import random
import re
import time

from agent import Run
from schema import PARAM_RANGES, validate_turn  # noqa: F401  (validate_turn via Run._registrar)

KINDS = ("random", "greedy")

# Politica: quantos slots pedir. 1 e o unico valor que a macro sempre fez e o
# unico com efeito medido; o teto 1..5 vem de schema.PARAM_RANGES.
SLOTS_PEDIDOS = 1
_SLOTS_MIN, _SLOTS_MAX = PARAM_RANGES[("negotiate_slots", "slots")]

_RE_LINHA = re.compile(
    r"^(?P<cid>[A-Z]{2}\d{2})\s+(?P<nome>.*?)\s*\|\s*ledger=(?P<ledger>-?\d+)\s*\|"
    r"\s*rota=(?P<rota>\w+)\s*\|\s*dist=(?P<dist>\S+)\s*\|\s*(?P<intel>.*)$")
_RE_NOSSOS = re.compile(r"\(nossos(\d+)\)")


# ------------------------------------------------------------------ leitura


def _linhas_de_cidade(state):
    """Le `cities_by_region` (linhas de TEXTO) -> lista de dicts.

    Acoplamento explicito ao formato de `city_intel.compact_rows`. Se o formato
    mudar isto devolve lista VAZIA e as baselines dizem "0 linhas de cidade
    parseadas" no diario — em vez de simplesmente nao achar destino e parecer
    que nao havia o que fazer (R4: falha silenciosa mente na direcao do sucesso).
    """
    out = []
    regs = state.get("cities_by_region") or {}
    if not isinstance(regs, dict):
        return out
    for chave, linhas in regs.items():
        try:
            reg = int(str(chave).split()[0])
        except (ValueError, IndexError):
            reg = None
        for l in linhas or []:
            # Estados GRAVADOS ANTES da ETAPA 5d trazem dict por cidade, nao a
            # linha compacta. Sao ilegiveis para esta baseline; ignorar em
            # silencio seria dizer "nao ha cidade", entao quem chama ve lista
            # vazia e o diario acusa "0 linhas parseadas".
            if not isinstance(l, str):
                continue
            m = _RE_LINHA.match(l)
            if not m:
                continue
            nossos = _RE_NOSSOS.search(m.group("intel"))
            d = m.group("dist")
            try:
                dist = int(d.lstrip("~").split("(")[0])
            except ValueError:
                dist = None
            out.append({
                "cid": m.group("cid"),
                "regiao": reg,
                "ledger": int(m.group("ledger")),
                "tem_rota": m.group("rota") == "sim",
                "dist": dist,
                # `our_slots` do painel, quando lido. None = nunca medido: NAO
                # e zero (R1).
                "nossos": int(nossos.group(1)) if nossos else None,
            })
    return out


def _slots_de(c):
    """Quantos slots temos ali. O painel (`nossos`) ganha do ledger quando existe
    — medido divergindo (Washington 34 x 27, Denver 12 x 11)."""
    return c["nossos"] if c["nossos"] is not None else c["ledger"]


def _hubs(state):
    h = state.get("company", {}).get("hubs_confirmados")
    return list(h) if isinstance(h, list) else []


def _frota(state):
    """(avail_total, frota_lida?). `fleet` vem string quando a leitura falhou."""
    f = state.get("company", {}).get("fleet")
    if not isinstance(f, list):
        return None, False
    tot = 0
    for p in f:
        v = p.get("avail")
        if isinstance(v, int):
            tot += v
    return tot, True


_RE_ROTA_TXT = re.compile(r"^([A-Z]{2}\d{2})-([A-Z]{2}\d{2})\s*\((\d+)\s*voos/sem\)")


def _rotas(state):
    """Normaliza as TRES formas que `routes_open` assume — sim, tres.

    1. dicts {origin,dest,load_pct}  — leitura de Info->map (pilot.py:588);
    2. dicts {from,to,flights}       — ledger do Executor;
    3. STRINGS "NA13-NA14 (1 voos/sem)" — o que o pilot manda quando a tabela
       do jogo nao foi lida (pilot.py:564). MEDIDO na run
       logs/eval_greedy_NA13_20260824-154412: era a forma de TODOS os turnos, e
       a primeira versao desta funcao ignorava strings — a gulosa ficava cega
       para a propria rota e repetia `open_route NA13->NA14` nos turnos 2 e 3,
       levando "ja existe rota (o harness acredita)" as duas vezes. Um `if not
       isinstance(r, dict): continue` que so parecia defensivo custou 2 das 6
       acoes da run.
    """
    rs = state.get("company", {}).get("routes_open")
    if not isinstance(rs, list):
        return []
    out = []
    for r in rs:
        if isinstance(r, dict):
            out.append({"origin": r.get("origin") or r.get("from"),
                        "dest": r.get("dest") or r.get("to"),
                        "flights": r.get("flights"),
                        "load_pct": r.get("load_pct")})
        elif isinstance(r, str):
            m = _RE_ROTA_TXT.match(r.strip())
            if m:
                out.append({"origin": m.group(1), "dest": m.group(2),
                            "flights": int(m.group(3)), "load_pct": None})
    return [r for r in out if r["dest"]]


def _livres(state):
    v = state.get("company", {}).get("negociadores_livres")
    return v if isinstance(v, int) else 0


def _em_negociacao(state):
    n = state.get("company", {}).get("negotiations_pending")
    return [x for x in (n or []) if isinstance(x, str)]


def _slots_livres(state, cid):
    """Slots que temos em `cid` MENOS os que as rotas ja consomem.

    MEDIDO (executor.py:355, calibracao 12/08): cada voo/semana come 1 slot em
    CADA PONTA. `flights_week=7` num destino onde temos 1 slot e recusa certa —
    foi o que aconteceu nos 3 turnos da run
    logs/eval_greedy_NA13_20260824-151915 ("a rota pede 7", 0/3 com efeito).
    Pedir o que nao cabe nao e "ser guloso", e emitir ruido correlacionado.
    """
    linha = next((c for c in _linhas_de_cidade(state) if c["cid"] == cid), None)
    if linha is None:
        return 0
    usados = sum((r.get("flights") or 1) for r in _rotas(state)
                 if cid in (r.get("origin"), r.get("dest")))
    return max(0, _slots_de(linha) - usados)


def _voos_possiveis(state, origem, dest, teto=7):
    """Quantos voos/semana cabem nas DUAS pontas. 0 = a rota nao abre."""
    return max(0, min(_slots_livres(state, origem), _slots_livres(state, dest), teto))


def _destinos_com_slot(state, hubs):
    """Cidades onde JA temos slot, nao sao hub e nao tem rota nossa."""
    rotas = {r["dest"] for r in _rotas(state)} | {r["origin"] for r in _rotas(state)}
    cs = [c for c in _linhas_de_cidade(state)
          if _slots_de(c) > 0 and c["cid"] not in hubs and c["cid"] not in rotas]
    # perto primeiro: distancia desconhecida vai para o fim (nao inventa numero)
    cs.sort(key=lambda c: (c["dist"] is None, c["dist"] or 0))
    return cs


# ------------------------------------------------------------------ politicas


def random_legal(state, rng=None):
    """Piso: sorteia 1..3 acoes ESTRUTURALMENTE validas. Zero inteligencia.

    O `wait` entra como UM candidato entre outros, nunca como tapa-buraco de
    "nao achei nada" — se a lista de candidatos vier so com `wait`, o diario diz
    que foi por falta de alternativa legal.
    """
    rng = rng or random.Random()
    hubs = _hubs(state)
    avail, lida = _frota(state)
    rotas = _rotas(state)
    cands = []

    livres = _livres(state)
    linhas = _linhas_de_cidade(state)
    sem_slot = [c for c in linhas if _slots_de(c) <= 0
                and c["cid"] not in _em_negociacao(state)]
    if livres > 0 and sem_slot:
        cands.append({"action": "negotiate_slots",
                      "params": {"city": rng.choice(sem_slot)["cid"],
                                 "slots": rng.randint(_SLOTS_MIN, min(2, _SLOTS_MAX))}})
    alvos = _destinos_com_slot(state, hubs)
    if hubs and lida and avail and alvos:
        _org = rng.choice(hubs)
        _dst = rng.choice(alvos[:8])["cid"]
        _max = _voos_possiveis(state, _org, _dst)
        if _max:
            cands.append({"action": "open_route",
                          "params": {"from": _org, "to": _dst,
                                     "flights_week": rng.randint(1, _max),
                                     "fare_level": rng.choice(["low", "mid", "high"]),
                                     "aircraft_index": 0, "planes": 1}})
    # adjust_route SO com exatamente 1 rota aberta: com 2+ o executor recusa
    # (nao sabe navegar a lista) e a acao viraria falha garantida — ruido.
    if len(rotas) == 1:
        cands.append({"action": "adjust_route",
                      "params": {"route": rotas[0]["dest"],
                                 # `flights_week` vai JUNTO porque schema.ACTIONS
                                 # exige os DOIS params (ver nota em greedy()).
                                 "flights_week": rotas[0].get("flights") or 1,
                                 "fare_level": rng.choice(["low", "mid", "high"])}})
    cands.append({"action": "wait", "params": {}})
    k = min(len(cands), rng.randint(1, 3))
    acoes = rng.sample(cands, k)
    motivo = ("so 'wait' era legal (hubs=%d frota_lida=%s avail=%s alvos=%d livres=%d)"
              % (len(hubs), lida, avail, len(alvos), livres)) if len(cands) == 1 else ""
    diario = ("baseline aleatoria: %d de %d candidatos legais%s"
              % (k, len(cands), (" — " + motivo) if motivo else ""))
    return acoes, diario


def greedy(state, rng=None):
    """Heuristica honesta e curta. Ordem = do mais barato/medido ao mais caro:

      1. negociador livre + cidade sem slot  -> negotiate_slots (1 slot)
      2. aviao disponivel + hub + cidade com slot -> open_route (a mais perto)
      3. exatamente 1 rota aberta com ocupacao lida -> adjust_route
         (>85% sobe tarifa, <40% desce)
      4. nada disso -> LISTA VAZIA + diario dizendo QUAL leitura bloqueou.

    O passo 4 e de proposito. A versao antiga fechava com
    `if not actions: actions = [wait]`, o que transforma "a gulosa nao tem o que
    fazer" em "a gulosa jogou" — mascara o achado que a baseline existe para
    revelar.
    """
    acoes, notas = [], []
    hubs = _hubs(state)
    avail, lida = _frota(state)
    rotas = _rotas(state)
    linhas = _linhas_de_cidade(state)
    livres = _livres(state)
    pend = _em_negociacao(state)

    if not linhas:
        return [], ("baseline gulosa BLOQUEADA: 0 linhas de cidade parseadas de "
                    "cities_by_region (formato de city_intel.compact_rows mudou?)")

    sem_slot = [c for c in linhas if _slots_de(c) <= 0 and c["cid"] not in pend]
    sem_slot.sort(key=lambda c: (c["dist"] is None, c["dist"] or 0))
    if livres > 0 and sem_slot:
        acoes.append({"action": "negotiate_slots",
                      "params": {"city": sem_slot[0]["cid"], "slots": SLOTS_PEDIDOS}})
    else:
        notas.append("sem negotiate_slots: negociadores_livres=%d, cidades sem slot=%d"
                     % (livres, len(sem_slot)))

    alvos = _destinos_com_slot(state, hubs)
    # Primeiro alvo (mais perto) em que a rota REALMENTE cabe nos slots das duas
    # pontas. Sem este filtro a gulosa pedia 7 voos/semana onde tinha 1 slot e
    # levava recusa nos 3 turnos (medido; ver `_slots_livres`).
    escolha = None
    for c in alvos:
        if hubs and lida and avail:
            v = _voos_possiveis(state, hubs[0], c["cid"])
            if v:
                escolha = (c["cid"], v)
                break
    if escolha:
        acoes.append({"action": "open_route",
                      "params": {"from": hubs[0], "to": escolha[0],
                                 "flights_week": escolha[1], "fare_level": "mid",
                                 "aircraft_index": 0, "planes": 1}})
    else:
        notas.append("sem open_route: hubs=%d frota_lida=%s avail=%s alvos_com_slot=%d "
                     "(nenhum com slot livre nas duas pontas)"
                     % (len(hubs), lida, avail, len(alvos)))

    # ACHADO (24/08): `schema.ACTIONS['adjust_route']` exige flights_week E
    # fare_level, embora o executor aceite QUALQUER UM DOS DOIS (so recusa
    # quando faltam os dois). Mandar so a tarifa e recusado na validacao, antes
    # do jogo. Por isso os voos/semana ATUAIS vao junto, inalterados.
    if len(rotas) == 1 and isinstance(rotas[0].get("load_pct"), int):
        lp = rotas[0]["load_pct"]
        _fl = rotas[0].get("flights") or 1
        if lp > 85:
            acoes.append({"action": "adjust_route",
                          "params": {"route": rotas[0]["dest"],
                                     "flights_week": _fl, "fare_level": "high"}})
        elif lp < 40:
            acoes.append({"action": "adjust_route",
                          "params": {"route": rotas[0]["dest"],
                                     "flights_week": _fl, "fare_level": "low"}})
        else:
            notas.append("sem adjust_route: ocupacao %d%% esta na faixa 40..85" % lp)
    else:
        notas.append("sem adjust_route: %d rota(s) aberta(s) com ocupacao lida=%s"
                     % (len(rotas), rotas[0].get("load_pct") if len(rotas) == 1 else "n/a"))

    if not acoes:
        return [], "baseline gulosa NADA A FAZER — " + "; ".join(notas)
    return acoes, ("baseline gulosa: %s" % ", ".join(a["action"] for a in acoes)
                   + ((" | " + "; ".join(notas)) if notas else ""))


POLITICAS = {"random": random_legal, "greedy": greedy}


# ------------------------------------------------------------------ runner


class BaselineRun(Run):
    """Jogador nao-LLM com a MESMA interface de `agent.Run`.

    Herda `_check_cities` (o catalogo de IDs vive aqui, nao no schema) e
    `_registrar` (cauda comum: validate_turn -> turns.jsonl -> span), entao o
    diario que o `run_eval.resumir()` le e o mesmo objeto do jogador LLM.
    NENHUMA chamada de rede acontece.
    """

    def __init__(self, run_dir, kind, seed=0, **kw):
        if kind not in POLITICAS:
            raise ValueError("baseline desconhecida: %r (use %s)" % (kind, list(POLITICAS)))
        kw.pop("model", None)
        kw["fallbacks"] = False
        super().__init__(run_dir, model="baseline:" + kind, **kw)
        self.kind = kind
        self.seed = seed
        self.rng = random.Random(seed)

    def turn(self, state, inspector=None):
        """`inspector` e ACEITO e IGNORADO: nenhuma baseline pesquisa cidade.

        Isso e parte do baseline, nao um esquecimento — `cidades_consultadas: 0`
        no resumo e o piso contra o qual "quantas cidades o modelo consultou
        antes de agir" vira metrica.
        """
        import obs

        turn_n = self.next_turn_number()
        t0 = time.time()
        _span = obs.span("turno", turn=turn_n, model_solicitado=self.model)
        _span.__enter__()
        acoes, diario = POLITICAS[self.kind](state, self.rng)
        resp = {
            "model": self.model,          # exit 7 do run_eval compara com o pedido
            "content": "", "reasoning": "",
            "usage": {}, "latency_s": round(time.time() - t0, 3),
            "finish_reason": "baseline",
        }
        # `diary_update` NUNCA vazio: `Run.next_turn_number()` conta as entradas
        # de diario, entao diario vazio congelaria o contador em 1 e o
        # turns.jsonl inteiro sairia com "turn": 1 (com o stats.json contando
        # certo, ou seja, ninguem perceberia olhando so o resumo).
        parsed = {"actions": acoes, "diary_update": diario or ("baseline %s" % self.kind)}
        return self._registrar(turn_n, state, parsed, resp, None, None, t0, _span)


def eh_baseline(model):
    return isinstance(model, str) and (
        model in KINDS or (model.startswith("baseline:") and model.split(":", 1)[1] in KINDS))


def kind_de(model):
    return model.split(":", 1)[1] if model.startswith("baseline:") else model
