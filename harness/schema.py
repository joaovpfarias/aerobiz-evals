"""Action space semantico do Aerobiz Evals + validacao leve (sem dependencias).

O estado observado por turno segue STATE_EXAMPLE (v0 — sera calibrado no F0
contra as telas reais do jogo).
"""

FARE_LEVELS = ("low", "mid", "high")

# acao -> {param: validador}
ACTIONS = {
    "negotiate_slots": {"city": str},
    # FORA DE pilot.SUPPORTED desde 24/08 (ETAPA 2-OraculosFracos, sem efeito
    # medido — ver pilot.py e CALIBRATION §17.3-bis). Fica aqui so como
    # validacao de parametro para quem for calibrar; o prompt do piloto lista
    # `allowed_actions=pilot.SUPPORTED`, entao o modelo nao a recebe.
    "return_slots": {"city": str},
    # ALINHADO AO EXECUTOR 15/08. O schema pedia 'from' e 'aircraft' (str) que a
    # macro IGNORA, e o prompt do piloto mandava usar 'aircraft_index' — que a
    # validacao rejeitava como param desconhecido. Ou seja: a unica combinacao
    # que passava era a que nao escolhia aviao nenhum, e o modelo nao tinha como
    # saber disso.
    #  - 'from' sai: toda rota parte da base (Washington); a macro nao seleciona
    #    origem.
    #  - 'aircraft' sai: MEDIDO 15/08 (logs/prova_ic/fleet_NA06_00..04.png) que
    #    o seletor <| |> cicla apenas os modelos QUE A COMPANHIA POSSUI; com um
    #    unico modelo (MD100 x6 no savestate do eval) os 4 toques nao mudam nada
    #    — hashes das 5 capturas identicos. Enquanto nao houver compra de aviao,
    #    escolher aeronave e uma alavanca inexistente.
    # 'from' VOLTOU em 17/08, quando open_hub passou a existir: a origem de uma
    # rota e um HUB NOSSO e agora ha mais de um hub possivel. Continua OPCIONAL
    # (default = a base) para nao invalidar as acoes ja emitidas — ver
    # OPTIONAL_PARAMS abaixo.
    "open_route": {
        "to": str,
        "flights_week": int,
        "fare_level": FARE_LEVELS,
    },
    # r1c0 — abre a negociacao de um hub regional. 'region' e 0..6; 'city' e
    # opcional e serve so para derivar a regiao. CALIBRADO 17/08: custa
    # $28.800K na hora + 1 negociador, e o hub NAO fica pronto no mesmo turno.
    "open_hub": {"region": int},
    # r1c0 — fecha um hub regional (acao destrutiva, ETAPA 6-Reversos). Pode custar
    # funcionario ou nao (TBD). Oracle: staff panel; cascade: rotas partindo desse
    # hub podem ser deletadas.
    "close_hub": {"region": int},
    "suspend_route": {"route": str},
    "close_route": {"route": str},
    "adjust_route": {"route": str, "flights_week": int, "fare_level": FARE_LEVELS},
    # CALIBRADO 15/08 (CALIBRATION §12): `model` e uma das 8 chaves de
    # world.AIRCRAFT_CATALOG e `qty` vai de 1 a 10 ("You can order a maximum
    # of 10 planes"). NAO existe escolha de financiamento no jogo — o param
    # `financing` era invencao minha e a validacao EXIGIA ele, entao a acao
    # era impossivel de emitir corretamente.
    "buy_aircraft": {"model": str, "qty": int},
    "sell_aircraft": {"model": str, "qty": int},
    "set_budget": {"category": str, "level": int},
    "invest": {"city": str, "kind": ("hotel", "tourism")},
    # CALIBRADO 17/08 (CALIBRATION §21): compra business venture (r0c5) numa
    # cidade. 'type_index' e a posicao no catalogo DESSA cidade (0 = primeiro
    # oferecido; catalogo/preco NAO sao fixos, variam por cidade — ver
    # ACTION_SPACE.md r0c5). Debita o caixa NA HORA; fica "em negociacao" por
    # meses antes de contar em Info->facilities/campanha de anuncio.
    "open_venture": {"city": str},
    "wait": {},
}

# Params ACEITOS mas nao exigidos. Sem isto, declarar um param em ACTIONS o
# tornava OBRIGATORIO (validate_action reclama de todo param declarado ausente)
# — adicionar 'from' a open_route invalidaria de uma vez todas as acoes que o
# modelo ja sabe emitir.
OPTIONAL_PARAMS = {
    # ETAPA 3a (19/08, CALIBRATION §31): `aircraft_index` e `planes` VOLTAM ao
    # action space porque agora sao lidos de volta da tela a cada toque. Ficam
    # OPCIONAIS de proposito — os defaults (0 e 1) sao os unicos valores que o
    # jogo garante em qualquer frota, e pedir fora do alcance e RECUSADO com o
    # motivo medido (quantos modelos o seletor cicla / qual o teto de unidades
    # disponiveis), nunca "obedecido" pela metade.
    "open_route": {"from": str, "aircraft_index": int, "planes": int},
    "open_hub": {"city": str},     # alternativa a 'region': deriva a regiao da cidade
    "close_hub": {"city": str},    # alternativa a 'region': deriva a regiao da cidade
    "open_venture": {"type_index": int},  # default 0 = 1o tipo oferecido pela cidade
    # ETAPA 3b-a (19/08, CALIBRATION §32): quantos slots pedir na negociacao.
    # OPCIONAL, default 1 (o que a macro sempre fez sem olhar). Fora de 1..5 a
    # macro RECUSA: o medidor satura em 5 e nao da a volta (medido nos toques
    # 5..8). O param `employee` NAO entra — ver §32, medicao negativa.
    "negotiate_slots": {"slots": int},
}

# Tetos MEDIDOS (nao inventados). Validar aqui devolve o erro ao modelo antes
# de gastar emulador; a macro revalida de qualquer jeito.
PARAM_RANGES = {
    ("negotiate_slots", "slots"): (1, 5),
}

MAX_ACTIONS_PER_TURN = 8
MAX_CONCURRENT_NEGOTIATIONS = 4

STATE_EXAMPLE = {
    "date": {"year": 1970, "quarter": 1},
    "cash_musd": 40,
    "company": {
        "planes": [{"model": "DC-8-61", "count": 2, "idle": 1}],
        "slots": [{"city": "New York", "n": 4}],
        "routes": [
            {
                "route": "New York-London",
                "aircraft": "DC-8-61",
                "flights_week": 7,
                "fare_level": "mid",
                "load_pct": 62,
                "profit_musd": 1.2,
            }
        ],
        "negotiations": [{"city": "Paris", "quarters_left": 2}],
    },
    "rivals": [{"name": "Rival A", "pax_rank": 1}],
    "events": ["Oil crisis: fuel costs +40%"],
    "report": {"revenue_musd": 12.0, "cost_musd": 9.5, "profit_musd": 2.5, "pax_total": 41000},
}


def validate_action(a, state=None):
    """Retorna lista de erros (vazia = valida). Checagens estruturais + as
    semanticas possiveis sem o estado completo do jogo."""
    errors = []
    if not isinstance(a, dict) or "action" not in a:
        return [f"acao sem campo 'action': {a!r}"]
    name = a["action"]
    if name not in ACTIONS:
        return [f"acao desconhecida: {name}"]
    spec = ACTIONS[name]
    opt = OPTIONAL_PARAMS.get(name, {})
    params = a.get("params", {}) or {}
    # `open_hub` e `close_hub` aceitam region OU city; exigir 'region' quando veio 'city'
    # rejeitaria uma acao perfeitamente executavel.
    obrigatorios = dict(spec)
    if name in ("open_hub", "close_hub") and "city" in params and "region" not in params:
        obrigatorios.pop("region", None)
    for p, rule in {**obrigatorios, **opt}.items():
        if p not in params:
            if p in opt:
                continue
            errors.append(f"{name}: falta param '{p}'")
            continue
        v = params[p]
        if isinstance(rule, tuple):
            if v not in rule:
                errors.append(f"{name}.{p}: '{v}' fora de {rule}")
        elif rule is int:
            if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                errors.append(f"{name}.{p}: esperado int >=0, veio {v!r}")
            elif (name, p) in PARAM_RANGES:
                lo, hi = PARAM_RANGES[(name, p)]
                if not (lo <= v <= hi):
                    errors.append(f"{name}.{p}: {v} fora do alcance MEDIDO {lo}..{hi}")
        elif rule is str:
            if not isinstance(v, str) or not v.strip():
                errors.append(f"{name}.{p}: esperado string nao-vazia, veio {v!r}")
    for p in params:
        if p not in spec and p not in opt:
            errors.append(f"{name}: param desconhecido '{p}'")
    if state is not None and name == "negotiate_slots":
        negs = len(state.get("company", {}).get("negotiations", []))
        if negs >= MAX_CONCURRENT_NEGOTIATIONS:
            errors.append(f"negotiate_slots: ja ha {negs} negociacoes (max {MAX_CONCURRENT_NEGOTIATIONS})")
    return errors


def validate_turn(actions, state=None):
    """Valida a lista de acoes de um turno. Retorna (validas, erros)."""
    if not isinstance(actions, list):
        return [], [f"'actions' precisa ser lista, veio {type(actions).__name__}"]
    errors = []
    valid = []
    if len(actions) > MAX_ACTIONS_PER_TURN:
        errors.append(f"{len(actions)} acoes (max {MAX_ACTIONS_PER_TURN}); excedentes ignoradas")
        actions = actions[:MAX_ACTIONS_PER_TURN]
    for a in actions:
        errs = validate_action(a, state)
        if errs:
            errors.extend(errs)
        else:
            valid.append(a)
    return valid, errors
