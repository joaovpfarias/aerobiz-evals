"""UM COMANDO roda a partida inteira, sem Claude Code no meio.

    python run_eval.py --model laguna-s-2.1-free --city NA13 --turns 20

O que este script faz e SO orquestracao (o loop de turno continua sendo
`pilot.py`, o executor continua sendo `executor.py`):

  1. ponte viva? senao lanca o EmuHawk (launch.ps1) e ESPERA o ping — nunca
     `sleep` fixo, porque o 1o boot varia (~40s) e um sleep curto derruba a run
     inteira antes de comecar;
  2. savestate da cidade pedida (`../states/eval_<CITY>_<ANO>_lv<N>.state`);
     se faltar, chama `setup_game.py` — com `--boot` SO quando fomos nos que
     acabamos de lancar o emulador (fora disso a tela e desconhecida e `--boot`
     tecla as cegas, o que ja custou caixa: R2);
  3. roda `pilot.py` com o modelo pedido, `--no-fallback` POR PADRAO (com
     fallback outro modelo pode responder um turno e a comparacao vira ficcao)
     e Logfire ligado por padrao (obs.py);
  4. escreve `resumo.json` + resumo em texto: turnos, acoes por tipo com
     efeito, taxa de efeito verificado, caixa final, placar, cidades
     consultadas;
  5. exit code util e watchdog de inatividade — se o emulador morrer no meio,
     cada chamada da ponte bloqueia 30s e a run moeria por horas.

EXIT CODES
  0  rodou os --turns pedidos
  2  argumento/estado invalido (dir de run ocupado, savestate ausente e setup recusado)
  3  a ponte nunca respondeu ao ping
  4  pilot.py saiu com erro
  5  watchdog: nenhuma linha do pilot por --timeout-min minutos (processo morto)
  6  terminou com MENOS turnos que os pedidos
  7  o modelo que respondeu nao foi o pedido (fallback trocou; eval invalido)
  8  ZERO turnos: o agente nunca produziu turno valido (modelo fora do ar, etc.)

O QUE ESTE RESUMO NAO MEDE (R5): `ok` de uma acao e o veredito do ORACULO DO
EXECUTOR (caixa/tela lidas por `executor.run`), nao uma medicao feita aqui.
Este script apenas conta o que o pilot ja mediu e diz de onde tirou cada numero.
"""

import argparse
import collections
import json
import pathlib
import queue
import re
import subprocess
import sys
import threading
import time

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent
STATES = RAIZ / "states"
LOGS = RAIZ / "logs"
ROM = RAIZ / "roms" / "Aerobiz Supersonic (USA).sfc"
PY = sys.executable


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- ponte

def ping(timeout=6.0):
    from bridge import BizHawkBridge
    try:
        return BizHawkBridge(timeout=timeout).ping()
    except Exception:  # noqa: BLE001
        return None


_PS = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"]


def emuhawk_pids():
    """PIDs dos EmuHawk que carregaram A NOSSA bridge.lua (filtra por CommandLine
    para nao matar um EmuHawk que o usuario abriu para outra coisa).
    Devolve None quando a consulta falha — 'nao sei' != 'nao ha'."""
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='EmuHawk.exe'\" | "
          "Where-Object { $_.CommandLine -like '*bridge.lua*' } | "
          "ForEach-Object { $_.ProcessId }")
    try:
        r = subprocess.run(_PS + [ps], capture_output=True, text=True, timeout=40)
    except Exception:  # noqa: BLE001
        return None
    if r.returncode != 0:
        return None
    return [int(x) for x in (r.stdout or "").split() if x.strip().isdigit()]


def mata_emuhawks(pids):
    if not pids:
        return
    lista = ",".join(str(p) for p in pids)
    try:
        subprocess.run(_PS + [f"Stop-Process -Id {lista} -Force -ErrorAction SilentlyContinue"],
                       capture_output=True, text=True, timeout=40)
    except Exception as e:  # noqa: BLE001
        log(f"[ponte] aviso: falha ao matar {lista}: {e}")
    time.sleep(3)


def emuhawk_vivo():
    """O emulador esta na lista de processos? (nao toca na ponte — ver watchdog)"""
    pids = emuhawk_pids()
    if pids is None:
        return True  # falha da consulta nao e prova de morte: nao mata a run
    return bool(pids)


def _confere_dono(timeout=6.0):
    """Le o token do dono DE VOLTA da instancia que respondeu (R4) e compara com
    ipc/owner.txt. Devolve (token_da_instancia, token_do_arquivo) ou (None, ...)."""
    try:
        from bridge import BizHawkBridge
        info = BizHawkBridge(timeout=timeout)._call("INFO")
    except Exception:  # noqa: BLE001
        return None, None
    tok_inst = info[3] if len(info) > 3 else ""
    try:
        tok_arq = (AQUI / "ipc" / "owner.txt").read_text(encoding="ascii").strip()
    except OSError:
        tok_arq = ""
    return tok_inst, tok_arq


def garante_ponte(espera_s):
    """Devolve (ok, lancado_por_nos). Sem sleep fixo: poll do ping ate o prazo.

    INSTANCIA UNICA (bug medido 24/08, ETAPA 1-PonteLonga): a versao anterior
    decidia so pelo ping — 'ping falhou' era tratado como 'nao existe emulador'.
    Um EmuHawk esquecido, vivo mas disputando o IPC, falha o ping de 3s -> o
    run_eval lancava OUTRO -> mais disputa -> mais falha de ping -> mais
    lancamentos. Foi assim que 3 instancias sobreviveram e mataram as 4 runs de
    12 turnos no client.screenshot. Agora a decisao e pela TABELA DE PROCESSOS.
    """
    pids = emuhawk_pids()
    if pids is None:
        # "Nao sei quantos ha" NAO pode virar "nao ha" — foi exatamente esse
        # atalho (ping falho = sem emulador) que multiplicou as instancias.
        log("[ponte] ABORT: nao consegui listar os processos EmuHawk. Sem essa "
            "contagem nao da para garantir instancia unica; rode de novo ou "
            "feche os EmuHawk na mao antes.")
        return False, False
    if len(pids) > 1:
        log(f"[ponte] {len(pids)} EmuHawk com bridge.lua ({pids}) — TODOS disputam o "
            "mesmo IPC. Matando e relancando exatamente um.")
        mata_emuhawks(pids)
        pids = []
    if len(pids) == 1:
        f = ping()
        if f is not None:
            tok_inst, tok_arq = _confere_dono()
            if tok_inst and tok_inst == tok_arq:
                log(f"[ponte] viva (frame {f}, dono {tok_inst}) — nao vou relancar")
                return True, False
            log(f"[ponte] instancia unica mas token divergente (respondeu={tok_inst!r} "
                f"owner.txt={tok_arq!r}) — relancando")
        else:
            log("[ponte] 1 EmuHawk vivo mas sem ping — matando antes de relancar")
        mata_emuhawks(pids)
    if not ROM.exists():
        log(f"[ponte] ROM ausente: {ROM}")
        return False, False
    log("[ponte] morta — lancando EmuHawk via launch.ps1")
    subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", str(AQUI / "launch.ps1"), "-Rom", str(ROM)],
        cwd=str(AQUI), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while time.time() - t0 < espera_s:
        f = ping(timeout=3.0)
        if f is not None:
            # PING NAO PROVA QUE A ROM CARREGOU. O proprio launch.ps1 documenta
            # o caso medido em 18/08: com caminho de ROM que nao resolve, o
            # EmuHawk abre VAZIO — e o Lua da ponte responde igual. Sem esta
            # conferencia a run so quebraria la na frente, num b.load confuso.
            try:
                from bridge import BizHawkBridge
                info = BizHawkBridge(timeout=6).info()
            except Exception as e:  # noqa: BLE001
                log(f"[ponte] INFO falhou apos o ping: {e}")
                return False, True
            log(f"[ponte] respondeu em {time.time() - t0:.0f}s | info={info}")
            # PROVA de instancia unica lida DE VOLTA (R4): contagem de processos
            # + token da instancia que de fato respondeu == owner.txt.
            vivos = emuhawk_pids()
            try:
                tok_arq = (AQUI / "ipc" / "owner.txt").read_text(encoding="ascii").strip()
            except OSError:
                tok_arq = ""
            log(f"[ponte] instancias com bridge.lua: "
                f"{len(vivos) if vivos is not None else '?'} | "
                f"token respondido={info.get('token')!r} owner.txt={tok_arq!r}")
            if vivos is not None and len(vivos) != 1:
                log(f"[ponte] ABORT: esperava 1 EmuHawk, achei {len(vivos)} ({vivos})")
                return False, True
            if not info.get("token") or info.get("token") != tok_arq:
                log("[ponte] ABORT: quem respondeu nao e o dono do IPC "
                    "(bridge.lua desatualizada ou instancia estranha)")
                return False, True
            if not (info.get("rom") or "").strip() or info.get("rom") == "NULL":
                log("[ponte] ABORT: EmuHawk subiu SEM ROM (info.rom vazio) — "
                    f"confira o caminho {ROM}")
                return False, True
            return True, True
        time.sleep(2)
    log(f"[ponte] sem ping em {espera_s}s")
    return False, True


# ---------------------------------------------------------------- savestate

def garante_savestate(city, ano, dificuldade, state_arg, podemos_bootar):
    if state_arg:
        p = pathlib.Path(state_arg)
        if not p.is_absolute():
            p = (AQUI / state_arg).resolve()
        if not p.exists():
            log(f"ABORT: --state {p} nao existe")
            return None
        return p
    p = STATES / f"eval_{city}_{ano}_lv{dificuldade}.state"
    if p.exists():
        log(f"[state] {p.name} ja existe — reuso")
        return p
    cmd = [PY, str(AQUI / "setup_game.py"), "--city", city,
           "--ano", str(ano), "--dificuldade", str(dificuldade)]
    if podemos_bootar:
        cmd.append("--boot")
        log(f"[state] {p.name} ausente — gerando com --boot (emulador recem-lancado, tela de titulo)")
    elif (ano, dificuldade) != (2000, 5):
        log(f"ABORT: {p.name} ausente e a ponte ja estava viva (tela desconhecida): "
            f"sem --boot o setup so sabe fazer 2000/lv5/1 jogador. "
            f"Rode setup_game.py --boot a mao ou peca --ano 2000 --dificuldade 5.")
        return None
    else:
        log(f"[state] {p.name} ausente — gerando a partir de eval_players_screen.state")
    r = subprocess.run(cmd, cwd=str(AQUI))
    if r.returncode != 0 or not p.exists():
        log(f"ABORT: setup_game.py saiu {r.returncode} e {p.name} nao apareceu")
        return None
    return p


# ---------------------------------------------------------------- pilot

LINHA_CAIXA = re.compile(r"^\[t\d+\] caixa (-?\d+)K -> (-?\d+)K")
LINHA_ERRO = re.compile(r"^\[t\d+\] (agente falhou|menu inacessivel)")
# Quantas vezes o watchdog aceita "silencio com a ponte viva" antes de desistir.
MAX_INDULTOS = 6


def roda_pilot(cmd, run_dir, timeout_s):
    """Roda o pilot em subprocesso, ecoando stdout e vigiando inatividade."""
    logf = (run_dir / "pilot.log").open("w", encoding="utf-8")
    p = subprocess.Popen(cmd, cwd=str(AQUI), stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                         errors="replace", bufsize=1)
    q = queue.Queue()

    def _ler():
        for linha in p.stdout:
            q.put(linha)
        q.put(None)

    threading.Thread(target=_ler, daemon=True).start()
    ultima_caixa = None
    matou = False
    indultos = 0
    fatais = []
    while True:
        try:
            linha = q.get(timeout=timeout_s)
            indultos = 0
        except queue.Empty:
            # SILENCIO NAO E MORTE. O pilot nao imprime nada durante `run.turn`,
            # e `opencode_client.chat` tem retries=4 x timeout=240s: um unico
            # turno pode ficar >30 min mudo com o emulador perfeitamente vivo.
            # Matar por tempo diria "o emulador morreu" onde o modelo so estava
            # lento. Quem decide e a PONTE, nao o relogio.
            # E o PROCESSO que se pergunta, nao a ponte: `bridge._call` e um
            # par de arquivos (ipc/cmd.txt, ipc/resp.txt) com UM dono. Um ping
            # do run_eval enquanto o pilot espera resposta pode consumir a
            # resposta do pilot — o vigia corromperia a run que vigia.
            if emuhawk_vivo() and indultos < MAX_INDULTOS:
                indultos += 1
                log(f"[watchdog] {timeout_s/60:.0f} min sem linha, mas a ponte responde "
                    f"— indulto {indultos}/{MAX_INDULTOS} (modelo lento, nao emulador morto)")
                continue
            log(f"[watchdog] {timeout_s/60:.0f} min sem linha e EmuHawk "
                f"{'ausente da lista de processos' if indultos < MAX_INDULTOS else 'vivo mas indultos esgotados'} "
                f"— matando o pilot")
            p.kill()
            matou = True
            break
        if linha is None:
            break
        sys.stdout.write(linha)
        sys.stdout.flush()
        logf.write(linha)
        m = LINHA_CAIXA.match(linha)
        if m:
            ultima_caixa = int(m.group(2))
        if LINHA_ERRO.match(linha):
            fatais.append(linha.strip())
    logf.close()
    p.wait()
    return p.returncode, ultima_caixa, matou, fatais


# ---------------------------------------------------------------- resumo

def _publica_no_logfire(resumo, run_dir):
    """Emite a PARTIDA INTEIRA como um evento, alem dos spans de turno e acao.

    Sem isto o Logfire so tem o detalhe (um span por turno, um por acao) e nao
    tem a linha que representa a corrida — que e justamente a unidade de
    comparacao do eval: um modelo, uma sede, N turnos, uma taxa.

    A taxa que vai como metrica principal e `taxa_efeito_substantivas_pct`, que
    EXCLUI `wait`. A taxa antiga vai junto, mas com o nome dizendo o que ela e:
    medido que, contando `wait` como efeito, a baseline aleatoria marcava 100%
    contra 66% da gulosa — o jogador mais passivo ganhava o placar.

    Nunca levanta: telemetria quebrada nao pode derrubar o fim de uma partida
    que levou horas e cujo resumo.json JA foi escrito em disco.
    """
    try:
        import obs

        if not obs.configurar(service_name="aerobiz-eval"):
            return
        obs.info(
            "partida concluida",
            tipo_de_jogador=resumo.get("tipo_de_jogador"),
            model_solicitado=resumo.get("model_solicitado"),
            model_respondeu=resumo.get("model_respondeu"),
            sede=resumo.get("cidade"),
            baseline_seed=resumo.get("baseline_seed"),
            turnos_rodados=resumo.get("turnos_rodados"),
            acoes_pedidas=resumo.get("acoes_pedidas_pelo_modelo"),
            acoes_substantivas_executadas=resumo.get("acoes_substantivas_executadas"),
            acoes_substantivas_com_efeito=resumo.get("acoes_substantivas_com_efeito"),
            taxa_efeito_substantivas_pct=resumo.get("taxa_efeito_substantivas_pct"),
            taxa_com_wait_pct=resumo.get("taxa_efeito_verificado_pct"),
            acoes_wait=resumo.get("acoes_wait"),
            turnos_sem_acao_substantiva=resumo.get("turnos_sem_acao_substantiva"),
            cidades_consultadas=resumo.get("cidades_consultadas"),
            caixa_final_k=resumo.get("caixa_final_k"),
            erros_de_validacao=resumo.get("erros_de_validacao"),
            # OBJETIVO, nao so harness (25/08). Sem estes campos o evento de
            # partida so dizia se o executor funcionou; agora diz ate onde o
            # jogador chegou. Vale a ressalva de pilot.py: `placar` e presenca
            # por regiao, nao magnitude — n1 em passageiros e lucro anual, as
            # outras duas parcelas da vitoria, exigiriam Info->finance por turno.
            placar=resumo.get("placar"),
            n_regioes_com_valor=resumo.get("n_regioes_com_valor"),
            regioes_com_valor=resumo.get("regioes_com_valor"),
            turno_do_primeiro_hub=resumo.get("turno_do_primeiro_hub"),
            turnos_com_end_turn_falho=resumo.get("turnos_com_end_turn_falho"),
            turnos_com_parse_error=resumo.get("turnos_com_parse_error"),
            taxa_sobre_pedidas_pct=resumo.get("taxa_sobre_pedidas_pct"),
            # Serializado: e um dict de dicts e viraria um atributo aninhado.
            acoes_por_tipo=json.dumps(resumo.get("acoes_por_tipo") or {}, ensure_ascii=False),
            savestate=resumo.get("savestate"),
            teve_linha_fatal=bool(resumo.get("linhas_fatais_do_pilot")),
            run_dir=str(run_dir),
        )
        import logfire

        logfire.force_flush(timeout_millis=15000)
    except Exception as e:  # noqa: BLE001
        print(f"[obs] nao consegui publicar o resumo no Logfire: {e}", flush=True)


def calcular_metricas_acoes(run_dir):
    """Calcula metricas de acoes (substantivas e totais) sem tocar na ponte.

    Retorna dict com:
      acoes_executadas, acoes_com_efeito_verificado, taxa_efeito_verificado_pct,
      acoes_substantivas_executadas, acoes_substantivas_com_efeito,
      taxa_efeito_substantivas_pct, acoes_wait, turnos_sem_acao_substantiva,
      por_tipo
    """
    from pilot import SUPPORTED
    SUBSTANTIVAS = frozenset(SUPPORTED) - {"wait"}

    por_tipo = collections.defaultdict(lambda: {"pedidas": 0, "efeito": 0, "delta_caixa_k": 0})
    acoes_exec = acoes_efeito = 0
    subst_exec = subst_efeito = 0
    acoes_wait = 0

    ap = run_dir / "acoes.jsonl"
    if ap.exists():
        for linha in ap.read_text(encoding="utf-8").splitlines():
            a = json.loads(linha)
            d = por_tipo[a["action"]]
            d["pedidas"] += 1
            tem_efeito = a.get("ok_oraculo_executor", False)
            d["efeito"] += 1 if tem_efeito else 0
            if a.get("caixa_delta_k") is not None:
                d["delta_caixa_k"] += a["caixa_delta_k"]

            acoes_exec += 1
            if tem_efeito:
                acoes_efeito += 1

            if a["action"] == "wait":
                acoes_wait += 1
            elif a["action"] in SUBSTANTIVAS:
                subst_exec += 1
                if tem_efeito:
                    subst_efeito += 1

    # Turnos sem acao substantiva (pedida): turnos onde o modelo nao pediu nenhuma
    # acao que nao seja wait.
    turnos_sem_subst = 0
    tp = run_dir / "turns.jsonl"
    if tp.exists():
        for linha in tp.read_text(encoding="utf-8").splitlines():
            rec = json.loads(linha)
            actions_raw = rec.get("actions_raw") or []
            tem_subst = any(a.get("action") in SUBSTANTIVAS for a in actions_raw)
            if not tem_subst:
                turnos_sem_subst += 1

    taxa_efeito = round(acoes_efeito / acoes_exec * 100, 1) if acoes_exec else None
    taxa_subst = round(subst_efeito / subst_exec * 100, 1) if subst_exec else None

    return {
        "acoes_executadas": acoes_exec,
        "acoes_com_efeito_verificado": acoes_efeito,
        "taxa_efeito_verificado_pct": taxa_efeito,
        "acoes_substantivas_executadas": subst_exec,
        "acoes_substantivas_com_efeito": subst_efeito,
        "taxa_efeito_substantivas_pct": taxa_subst,
        "acoes_wait": acoes_wait,
        "turnos_sem_acao_substantiva": turnos_sem_subst,
        "por_tipo": dict(por_tipo),
    }


def resumir(run_dir, turns_pedidos, model, state, caixa_stdout, fatais=(), seed=None):
    stats = {}
    sp = run_dir / "stats.json"
    if sp.exists():
        stats = json.loads(sp.read_text(encoding="utf-8"))

    turnos_rec, cidades, modelos, placar = [], 0, set(), None
    placar_turno = None
    pedidas_raw = erros_val = parse_errs = 0
    tp = run_dir / "turns.jsonl"
    if tp.exists():
        for linha in tp.read_text(encoding="utf-8").splitlines():
            rec = json.loads(linha)
            turnos_rec.append(rec)
            cidades += len(((rec.get("pesquisa") or {}).get("pedidas")) or [])
            modelos.add(rec.get("model_respondeu"))
            # DENOMINADOR HONESTO: `stats["acoes"]` so conta o que passou pela
            # validacao e chegou ao executor. Um modelo que pede 10 acoes malformadas
            # e 1 boa marcaria 100% de efeito. `actions_raw` e `validation_errors`
            # ja estavam no disco e nunca chegavam ao resumo.
            pedidas_raw += len(rec.get("actions_raw") or [])
            erros_val += len(rec.get("validation_errors") or [])
            parse_errs += 1 if rec.get("parse_error") else 0
            # `victory_progress` pode ser a sentinela "nao lido neste turno";
            # guardar a ultima leitura DE VERDADE, com o turno de donde veio.
            vp = (rec.get("state") or {}).get("victory_progress")
            if isinstance(vp, dict):
                placar, placar_turno = vp, rec.get("turn")

    # Calcula metricas de acoes (separa wait de substantivas)
    metricas_acoes = calcular_metricas_acoes(run_dir)
    por_tipo = collections.defaultdict(lambda: {"pedidas": 0, "efeito": 0, "delta_caixa_k": 0})
    turno_do_primeiro_hub = None
    ap = run_dir / "acoes.jsonl"
    if ap.exists():
        for linha in ap.read_text(encoding="utf-8").splitlines():
            a = json.loads(linha)
            d = por_tipo[a["action"]]
            d["pedidas"] += 1
            d["efeito"] += 1 if a["ok_oraculo_executor"] else 0
            if a.get("caixa_delta_k") is not None:
                d["delta_caixa_k"] += a["caixa_delta_k"]
            # QUANDO a expansao aconteceu, nao so SE aconteceu. Abrir hub e o
            # primeiro degrau da condicao de vitoria (hub em toda regiao —
            # VIABILIDADE.md); dois modelos com o mesmo placar final no turno 80
            # nao sao equivalentes se um chegou la no turno 12 e o outro no 60.
            if (a["action"] == "open_hub" and a["ok_oraculo_executor"]
                    and turno_do_primeiro_hub is None):
                turno_do_primeiro_hub = a.get("turn")

    caixa_final, caixa_fonte = None, "nao medido"
    try:
        from bridge import BizHawkBridge
        from world import read_cash_k
        caixa_final = read_cash_k(BizHawkBridge(timeout=8))
        caixa_fonte = "lido da RAM depois da run"
    except Exception as e:  # noqa: BLE001
        if caixa_stdout is not None:
            caixa_final, caixa_fonte = caixa_stdout, "ultima linha de caixa do pilot (RAM falhou: %s)" % e

    acoes = stats.get("acoes", 0)
    # MESMO ROTULO, DOIS SIGNIFICADOS: com zero turnos a caixa "final" lida da
    # RAM e a caixa INICIAL do savestate. Sem esta ressalva o resumo de uma run
    # que nao rodou parece o resumo de uma run que nao gastou nada.
    if not stats.get("turnos", len(turnos_rec)):
        caixa_fonte += " (ZERO turnos: e a caixa INICIAL do savestate, nao um resultado)"
    # ETAPA 4-Baselines: o resumo tem de dizer NA CARA que a run nao e de
    # modelo. Sem isto um resumo.json de baseline e um de LLM sao
    # indistinguiveis a olho — e o arquivo circula solto entre etapas.
    import baselines as _bl
    ehb = _bl.eh_baseline(model)
    resumo = {
        "tipo_de_jogador": ("BASELINE nao-LLM (%s) — nenhuma chamada de modelo; "
                            "serve de PISO de comparacao, nao e resultado de modelo"
                            % _bl.kind_de(model)) if ehb else "modelo LLM",
        "baseline": _bl.kind_de(model) if ehb else None,
        "baseline_seed": seed if ehb else None,
        "model_solicitado": model,
        "model_respondeu": sorted(x for x in modelos if x),
        "savestate": str(state),
        "run_dir": str(run_dir),
        "turnos_pedidos": turns_pedidos,
        "turnos_rodados": stats.get("turnos", len(turnos_rec)),
        "turnos_com_end_turn_falho": stats.get("turnos_falhos", 0),
        "turnos_recuperados_por_savestate": stats.get("turnos_recuperados", 0),
        "acoes_pedidas_pelo_modelo": pedidas_raw,
        "erros_de_validacao": erros_val,
        "turnos_com_parse_error": parse_errs,
        "acoes_executadas": metricas_acoes["acoes_executadas"],
        "acoes_com_efeito_verificado": metricas_acoes["acoes_com_efeito_verificado"],
        "taxa_efeito_verificado_pct": metricas_acoes["taxa_efeito_verificado_pct"],
        "taxa_fonte_inclui_wait": "metricas acima incluem acoes `wait` (nao-substantivas). Ver campos _substantivas_ abaixo.",
        "acoes_substantivas_executadas": metricas_acoes["acoes_substantivas_executadas"],
        "acoes_substantivas_com_efeito": metricas_acoes["acoes_substantivas_com_efeito"],
        "taxa_efeito_substantivas_pct": metricas_acoes["taxa_efeito_substantivas_pct"],
        "taxa_efeito_substantivas_fonte": "veredito do ORACULO DO EXECUTOR (executor.run), nao-substantivas (wait) excluidas",
        "acoes_wait": metricas_acoes["acoes_wait"],
        "turnos_sem_acao_substantiva": metricas_acoes["turnos_sem_acao_substantiva"],
        "taxa_sobre_pedidas_pct": (round(metricas_acoes["acoes_com_efeito_verificado"] / pedidas_raw * 100, 1) if pedidas_raw else None),
        "taxa_fonte": "veredito do ORACULO DO EXECUTOR (executor.run), nao uma medicao do run_eval",
        "acoes_por_tipo": {k: dict(v) for k, v in sorted(por_tipo.items())},
        "cidades_consultadas": cidades,
        "caixa_final_k": caixa_final,
        "caixa_fonte": caixa_fonte,
        "placar": placar,
        # Derivados do placar. None (e nao 0) quando nao houve leitura: zero
        # seria numero inventado. `read_victory` so distingue N/A de com_valor,
        # entao isto e PRESENCA por regiao, nao magnitude.
        "n_regioes_com_valor": (len([r for r, st in placar.items() if st == "com_valor"])
                                if isinstance(placar, dict) else None),
        "regioes_com_valor": (sorted(r for r, st in placar.items() if st == "com_valor")
                              if isinstance(placar, dict) else None),
        "turno_do_primeiro_hub": turno_do_primeiro_hub,
        "placar_fonte": (f"state['victory_progress'] do INICIO do turno {placar_turno} "
                         f"(ultima leitura de Info->victory que deu certo)"
                         if placar else "nenhum turno teve leitura de placar bem-sucedida"),
        "linhas_fatais_do_pilot": list(fatais),
    }
    (run_dir / "resumo.json").write_text(json.dumps(resumo, indent=1, ensure_ascii=False),
                                         encoding="utf-8")
    _publica_no_logfire(resumo, run_dir)
    log("\n===== RESUMO DO EVAL =====")
    for k in ("tipo_de_jogador", "baseline_seed",
              "model_solicitado", "model_respondeu", "turnos_rodados",
              "acoes_pedidas_pelo_modelo", "erros_de_validacao"):
        log(f"  {k}: {resumo[k]}")
    log(f"  acoes_executadas: {resumo['acoes_executadas']} (inclui {resumo['acoes_wait']} wait)")
    log(f"  acoes_com_efeito_verificado: {resumo['acoes_com_efeito_verificado']}")
    log(f"  taxa_efeito_verificado_pct (inclui wait): {resumo['taxa_efeito_verificado_pct']}%")
    log(f"  acoes_substantivas_executadas: {resumo['acoes_substantivas_executadas']}")
    log(f"  acoes_substantivas_com_efeito: {resumo['acoes_substantivas_com_efeito']}")
    log(f"  taxa_efeito_substantivas_pct: {resumo['taxa_efeito_substantivas_pct']}%")
    log(f"  turnos_sem_acao_substantiva: {resumo['turnos_sem_acao_substantiva']}")
    log(f"  taxa_sobre_pedidas_pct: {resumo['taxa_sobre_pedidas_pct']}%")
    for k in ("cidades_consultadas", "caixa_final_k", "caixa_fonte"):
        log(f"  {k}: {resumo[k]}")
    for l in resumo["linhas_fatais_do_pilot"]:
        log(f"  FATAL: {l}")
    for tipo, d in resumo["acoes_por_tipo"].items():
        log(f"  {tipo}: {d['efeito']}/{d['pedidas']} com efeito | caixa {d['delta_caixa_k']:+}K")
    log(f"  placar: {placar}")
    log(f"  resumo.json: {run_dir / 'resumo.json'}")
    return resumo


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True,
                    help="id do modelo OU 'random'/'greedy' (baselines nao-LLM, "
                         "mesmo savestate/executor/resumo — ver baselines.py)")
    ap.add_argument("--seed", type=int, default=0,
                    help="semente da baseline; fica em comando.json e no resumo, "
                         "entao a run e re-executavel identica")
    ap.add_argument("--city", default="NA13")
    ap.add_argument("--turns", type=int, default=20)
    ap.add_argument("--ano", type=int, default=2000)
    ap.add_argument("--dificuldade", type=int, default=5)
    ap.add_argument("--state", help="savestate explicito (default: ../states/eval_<city>_<ano>_lv<N>.state)")
    ap.add_argument("--run", help="pasta da run (default: ../logs/eval_<model>_<city>_<ts>)")
    ap.add_argument("--fallback", action="store_true",
                    help="PERMITE que outro modelo responda se o pedido falhar (invalida a comparacao)")
    ap.add_argument("--com-rota-inicial", action="store_true",
                    help="nao passa --fresh ao pilot (so faz sentido em savestate pos-F0 COM rota aberta)")
    ap.add_argument("--boot-timeout", type=int, default=180, help="segundos de espera pelo ping")
    ap.add_argument("--timeout-min", type=float, default=12.0,
                    help="watchdog: minutos sem nenhuma linha do pilot antes de matar")
    ap.add_argument("--sem-telemetria", action="store_true")
    ap.add_argument("--telemetria-conteudo", action="store_true")
    a = ap.parse_args()

    ok, lancado = garante_ponte(a.boot_timeout)
    if not ok:
        return 3

    state = garante_savestate(a.city, a.ano, a.dificuldade, a.state, lancado)
    if state is None:
        return 2

    # PASTA NOVA POR RUN. `agent.Run.next_turn_number()` conta o turno pelo
    # turns.jsonl que ACHAR na pasta: reaproveitar a pasta faz a run nova
    # herdar o diario da anterior e comecar no turno 21. Contaminacao silenciosa
    # que invalida qualquer comparacao entre modelos.
    slug = re.sub(r"[^A-Za-z0-9._-]", "-", a.model)
    run_dir = pathlib.Path(a.run).resolve() if a.run else (
        LOGS / f"eval_{slug}_{a.city}_{time.strftime('%Y%m%d-%H%M%S')}")
    if run_dir.exists() and any(run_dir.iterdir()):
        log(f"ABORT: {run_dir} ja existe e nao esta vazia (o diario da run antiga "
            f"contaminaria esta). Use --run com outro caminho.")
        return 2
    run_dir.mkdir(parents=True, exist_ok=True)

    cmd = [PY, str(AQUI / "pilot.py"), "--turns", str(a.turns),
           "--state", str(state), "--run", str(run_dir), "--model", a.model]
    import baselines as _bl
    if _bl.eh_baseline(a.model):
        cmd += ["--seed", str(a.seed)]
    if not a.fallback:
        cmd.append("--no-fallback")
    if not a.com_rota_inicial:
        # MEDIDO no eval_NA13_2000_lv5.state: `read_routes` devolve None (o jogo
        # mostra o mapa-mundi, nao a tabela) — o savestate do setup NAO tem rota
        # aberta. Sem --fresh o pilot injeta NA13->NA06 no ledger do executor e
        # o modelo passa a ajustar uma rota que nao existe.
        cmd.append("--fresh")
    if a.sem_telemetria:
        cmd.append("--sem-telemetria")
    if a.telemetria_conteudo:
        cmd.append("--telemetria-conteudo")
    (run_dir / "comando.json").write_text(
        json.dumps({"cmd": cmd, "args": vars(a), "state": str(state),
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}, indent=1, ensure_ascii=False),
        encoding="utf-8")
    log(f"[run] {run_dir}")
    log(f"[cmd] {' '.join(cmd)}")

    # A trava de instancia unica da ponte e POR PROCESSO: o garante_ponte acima
    # abriu um BizHawkBridge aqui e ficou com ela. Sem soltar, o filho pilot.py
    # seria recusado pela nossa propria trava (recusar demais tambem e bug).
    try:
        from bridge import release_bridge_lock
        release_bridge_lock()
    except Exception as e:  # noqa: BLE001
        log(f"[ponte] aviso: nao soltei a trava antes do pilot: {e}")

    rc, caixa_stdout, matou, fatais = roda_pilot(cmd, run_dir, a.timeout_min * 60)
    resumo = resumir(run_dir, a.turns, a.model, state, caixa_stdout, fatais, seed=a.seed)

    if matou:
        return 5
    if rc != 0:
        log(f"[fim] pilot.py saiu {rc}")
        return 4
    # `--model random` e registrado no diario como "baseline:random" (nome
    # honesto, que sobrevive fora do resumo). Sem normalizar, a checagem de
    # fallback leria isso como "outro modelo respondeu" e devolveria 7 em
    # TODA run de baseline.
    esperado = ("baseline:" + _bl.kind_de(a.model)) if _bl.eh_baseline(a.model) else a.model
    outros = [m for m in resumo["model_respondeu"] if m and m != esperado]
    if outros and not a.fallback:
        log(f"[fim] EVAL INVALIDO: --no-fallback pedido mas responderam tambem {outros}")
        return 7
    if resumo["turnos_rodados"] == 0:
        # Codigo proprio: "o modelo nunca respondeu" e um diagnostico diferente de
        # "a partida terminou curta", e com modelo free + --no-fallback e a falha
        # mais provavel de todas.
        log("[fim] ZERO turnos — o agente nao produziu nenhum turno valido")
        return 8
    if resumo["turnos_rodados"] < a.turns:
        log(f"[fim] rodou {resumo['turnos_rodados']} de {a.turns} turnos")
        return 6
    return 0


if __name__ == "__main__":
    sys.exit(main())
