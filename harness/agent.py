"""Loop de turno do agente-jogador (F0 semi-manual / F1 automatico).

Modo F0 (executor manual): o estado chega como JSON (extraido por vision fora
daqui), o modelo decide, as acoes sao impressas para execucao via cli.py.

  python agent.py turn --state state.json --run logs/run_f0

O diario e mantido pelo proprio modelo (campo diary_update) — gestao de memoria
e capacidade avaliada, nao infra. Tudo vai para <run>/turns.jsonl.
"""

import argparse
import json
import pathlib
import time

from opencode_client import DEFAULT_MODEL, chat, extract_json
import city_probe
import obs
from schema import ACTIONS, MAX_ACTIONS_PER_TURN, validate_turn

SYSTEM_RULES = """You are the CEO of a startup airline in the strategy game Aerobiz Supersonic (turn-based; 1 turn = 1 quarter; the match lasts at most 20 years = 80 turns).

VICTORY (within 20 years): (1) establish a regional hub in every world region, (2) hold the #1 passenger count in enough regions (4-7, per difficulty), and (3) show annual profit. Bankruptcy = defeat.

WORLD RULES:
- Slots: you can only fly to cities where you own airport slots. Getting new slots requires sending staff to negotiate; negotiations take 1-4 quarters depending on city relations; at most 4 negotiations may run at once; slots cost money.
- Routes: opening a route requires slots at both endpoints and an idle aircraft with enough range. Route profit depends on traffic demand, fare level, flights/week, service quality, ads, and competition on the route.
- Aircraft: bought outright (there is no lease option) or sold; the price is charged immediately and delivery takes one quarter; each model has range, capacity, and running costs.
- Budgets: advertising (per region) and service/maintenance affect demand, safety and reputation.
- Events: wars close regions, oil crises raise fuel costs, Olympics boost a host city's traffic. Quarterly reports show your P&L; annual reports show rankings.
- Rival airlines (3) expand simultaneously and compete for slots and passengers.

AVAILABLE ACTIONS (execute in order, max {max_actions} per turn):
{actions_list}

RESPONSE FORMAT — reply ONLY with valid JSON, no markdown fences:
{{"diary_update": "<=120 words: what happened, what you decided, plan for next quarters",
  "actions": [{{"action": "...", "params": {{...}}}}, ...]}}

SCOUTING CITIES (optional, once per turn, costs no money):
The state does not list city demand. Before committing to a destination you may
look up the real stats of up to {max_inspect} cities by replying with ONLY:

{{"inspect": ["NA06", "SA01"]}}

You then receive, for each city: population, economy, tourism, and slots
used/capacity (including how many are yours), read live from the game screen.
Immediately after that you must reply with your actions for this same quarter.

Use it when the choice actually depends on the numbers - comparing two candidate
destinations, or checking whether a city still has free slots. Opening a route
into a city you never looked at is a guess.

Numbers you are not shown are unknown — never invent prices or demand; prefer actions that reveal information (reports, small tests) when uncertain."""


def build_system(allowed=None):
    """allowed: subconjunto de acoes que o harness sabe executar nesta run.

    Anunciar acoes sem macro implementada e a receita para desperdicar turnos —
    o modelo escolhe o que lhe foi oferecido.
    """
    lines = []
    for name, spec in ACTIONS.items():
        if allowed is not None and name not in allowed:
            continue
        ps = ", ".join(
            f"{p}: {('|'.join(r) if isinstance(r, tuple) else r.__name__)}" for p, r in spec.items()
        )
        lines.append(f"- {name}({ps})")
    return SYSTEM_RULES.format(max_actions=MAX_ACTIONS_PER_TURN,
                               max_inspect=city_probe.MAX_POR_TURNO,
 actions_list="\n".join(lines))


DIARY_KEEP = 12  # ultimas entradas enviadas ao modelo
MAX_TOKENS = 8000  # reasoning models (deepseek) gastam muito antes do JSON final


class Run:
    def __init__(self, run_dir, model=DEFAULT_MODEL, allowed_actions=None, city_ids=None,
                 fallbacks=True):
        self.dir = pathlib.Path(run_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.dir / "turns.jsonl"
        self.model = model
        self.allowed = allowed_actions
        self.city_ids = set(city_ids) if city_ids else None
        # Em run de EVAL isto tem que ser False: com fallback ligado, um turno
        # pode ser respondido por OUTRO modelo e a comparacao vira ficcao.
        self.fallbacks = fallbacks

    def _check_cities(self, actions):
        """IDs de cidade fora do catalogo viram erro de validacao, nunca excecao
        no executor (o modelo ja inventou 'NA17' numa run)."""
        if not self.city_ids:
            return actions, []
        ok, errs = [], []
        for a in actions:
            bad = [
                v
                for k, v in (a.get("params") or {}).items()
                if k in ("city", "to", "from") and isinstance(v, str) and v not in self.city_ids
            ]
            if bad:
                errs.append(f"{a.get('action')}: id de cidade inexistente {bad}")
            else:
                ok.append(a)
        return ok, errs

    def _log(self, rec):
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def _diary(self):
        entries = []
        if self.log_path.exists():
            for line in self.log_path.read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                if rec.get("diary_update"):
                    entries.append(f"T{rec['turn']}: {rec['diary_update']}")
        return entries

    def next_turn_number(self):
        return len(self._diary()) + 1

    @staticmethod
    def _parse(resp):
        """Extrai o JSON de decisao (exige chave 'actions'); fallback: reasoning."""
        for source in (resp["content"], resp.get("reasoning", "")):
            if source:
                try:
                    return extract_json(source, required_key="actions")
                except ValueError:
                    pass
        raise ValueError(
            f"sem JSON com 'actions' (finish_reason={resp.get('finish_reason')}, "
            f"content={len(resp['content'])}ch, reasoning={len(resp.get('reasoning',''))}ch)"
        )

    def turn(self, state, inspector=None):
        """`inspector(cids) -> texto` habilita a RODADA DE PESQUISA.

        O modelo pode responder {"inspect": ["NA06","SA01"]} em vez de agir; o
        harness le os paineis dessas cidades AO VIVO e re-pergunta, no MESMO
        trimestre, agora com os numeros na mao.

        Por que dentro do turno e nao no turno seguinte: pesquisar para decidir
        so faz sentido se a decisao vier junto. Devolver o dado um trimestre
        depois transformaria pesquisa em atraso, e nenhum modelo aprenderia a
        usa-la.

        Uma rodada so. O painel nao cobra caixa (medido), mas custa ~1 min de
        parede por cidade — sem teto, um modelo indeciso consumiria a run
        inteira pesquisando.
        """
        """Roda um turno: estado -> acoes validadas. Loga tudo."""
        turn_n = self.next_turn_number()
        diary = self._diary()[-DIARY_KEEP:]
        user = (
            "DIARY (your own notes from previous turns):\n" + ("\n".join(diary) or "(first turn)")
            + "\n\nCURRENT STATE (from the game screens):\n" + json.dumps(state, ensure_ascii=False)
            + "\n\nDecide this quarter's actions."
        )
        messages = [
            {"role": "system", "content": build_system(self.allowed)},
            {"role": "user", "content": user},
        ]
        t0 = time.time()
        # Um span por turno. `model_respondeu` e separado de `model_solicitado`
        # de proposito: o fallback pode trocar o modelo no meio da run, e sem
        # essa distincao a comparacao fraco x forte fica invalida.
        _span = obs.span("turno", turn=turn_n, model_solicitado=self.model)
        _span.__enter__()
        _erro_span = None
        resp = chat(messages, model=self.model, max_tokens=MAX_TOKENS, fallbacks=self.fallbacks)
        parsed, parse_error = None, None
        try:
            parsed = self._parse(resp)
        except ValueError as e:
            parse_error = str(e)
            # 1 tentativa de reparo (budget dobrado se truncou no reasoning)
            more = MAX_TOKENS * 2 if resp.get("finish_reason") == "length" else MAX_TOKENS
            messages.append({"role": "assistant", "content": resp["content"] or "(empty)"})
            messages.append(
                {"role": "user", "content": f"Invalid/missing JSON ({e}). Reply again with ONLY the JSON object."}
            )
            resp = chat(messages, model=self.model, max_tokens=more, fallbacks=self.fallbacks)
            parsed = self._parse(resp)
        # --- rodada de pesquisa (opcional, uma so) ---
        pesquisa = None
        pedidas = parsed.get("inspect") or []
        if inspector is not None and pedidas:
            pesquisa = {"pedidas": pedidas}
            try:
                texto = inspector(pedidas)
            except Exception as e:  # noqa: BLE001
                texto = "a consulta falhou: %s" % e
            pesquisa["resposta"] = texto
            messages.append({"role": "assistant", "content": resp["content"] or "(empty)"})
            messages.append({"role": "user", "content": (
                "CITY STATS you asked for:" + chr(10) + texto + chr(10) * 2
                + "Now decide this quarter's actions. Do not ask again.")})
            resp = chat(messages, model=self.model, max_tokens=MAX_TOKENS,
                        fallbacks=self.fallbacks)
            try:
                parsed = self._parse(resp)
            except ValueError as e:
                parse_error = (parse_error or "") + " | pos-pesquisa: %s" % e
                parsed = parsed if isinstance(parsed, dict) else {}

        return self._registrar(turn_n, state, parsed, resp, parse_error,
                               pesquisa, t0, _span)

    def _registrar(self, turn_n, state, parsed, resp, parse_error, pesquisa,
                   t0, _span):
        """CAUDA COMUM do turno: validar -> logar -> atributos do span.

        Extraida em 24/08 (ETAPA 4-Baselines) para que `baselines.BaselineRun`
        escreva EXATAMENTE o mesmo `turns.jsonl` que o agente LLM. Sem isto uma
        run de baseline geraria um diario com outras chaves e o `resumir()` do
        run_eval.py reportaria `acoes_pedidas_pelo_modelo: 0` com acoes
        executadas — o mesmo buraco de denominador que ja foi consertado la uma
        vez. A cabeca (chamadas ao `chat`) e o que difere entre jogador LLM e
        baseline; a cauda tem de ser byte-identica ou a comparacao e ficcao.
        O span vem de FORA de proposito: abri-lo aqui mudaria a duracao medida
        do turno do LLM.
        """
        actions = parsed.get("actions", [])
        valid, errors = validate_turn(actions, state)
        valid, city_errs = self._check_cities(valid)
        errors += city_errs
        self._log(
            {
                "turn": turn_n,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "model_solicitado": self.model,
                "model_respondeu": resp.get("model"),  # fallback pode trocar o modelo: sem isso a comparacao e invalida
                "state": state,
                "diary_update": parsed.get("diary_update", ""),
                "actions_raw": actions,
                "actions_valid": valid,
                "validation_errors": errors,
                "parse_error": parse_error,
                # QUANTAS cidades o modelo consultou antes de decidir e, por si
                # so, uma metrica do eval: pesquisar antes de agir separa quem
                # raciocina de quem chuta.
                "pesquisa": pesquisa,
                "usage": resp.get("usage", {}),
                "latency_s": resp.get("latency_s"),
                "wall_s": round(time.time() - t0, 1),
            }
        )
        # Atributos so DEPOIS de tudo apurado: o que interessa no Logfire e o
        # resultado do turno, nao a intencao. `acoes_validas` x `actions_raw`
        # mostra quanto o modelo pediu que o harness recusou — uma das metricas
        # que separam modelo forte de fraco.
        try:
            _span.set_attribute("model_respondeu", resp.get("model"))
            _span.set_attribute("acoes_pedidas", len(actions))
            _span.set_attribute("acoes_validas", len(valid))
            _span.set_attribute("tipos_de_acao", sorted({a.get("action") for a in valid}))
            _span.set_attribute("erros_de_validacao", len(errors))
            _span.set_attribute("parse_error", bool(parse_error))
            _span.set_attribute("cidades_consultadas",
                                len((pesquisa or {}).get("pedidas") or []))
            _span.set_attribute("latency_s", resp.get("latency_s"))
            _span.set_attribute("wall_s", round(time.time() - t0, 1))
            _span.set_attribute("tokens_saida",
                                (resp.get("usage") or {}).get("completion_tokens"))
            _span.set_attribute("cash_k", state.get("cash_k"))
            _span.set_attribute("quarter", (state.get("date") or {}).get("label"))
            if obs.captura_conteudo():
                _span.set_attribute("diary", parsed.get("diary_update", ""))
                _span.set_attribute("resposta", resp.get("content", ""))
        finally:
            _span.__exit__(None, None, None)
        return valid, errors, parsed.get("diary_update", "")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("turn", help="processa 1 turno a partir de um state JSON")
    t.add_argument("--state", required=True, help="arquivo JSON com o estado do turno")
    t.add_argument("--run", required=True, help="diretorio da run (logs)")
    t.add_argument("--model", default=DEFAULT_MODEL)
    s = sub.add_parser("system", help="imprime o system prompt do jogador")
    _ = s
    a = ap.parse_args()
    if a.cmd == "system":
        print(build_system())
        return
    state = json.loads(pathlib.Path(a.state).read_text(encoding="utf-8"))
    run = Run(a.run, model=a.model)
    valid, errors, diary = run.turn(state)
    print("DIARY:", diary)
    print("ACTIONS:")
    for act in valid:
        print("  ", json.dumps(act, ensure_ascii=False))
    if errors:
        print("ERRORS:")
        for e in errors:
            print("  !", e)


if __name__ == "__main__":
    main()
