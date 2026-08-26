"""Observabilidade (Pydantic Logfire) do harness de evals.

Projeto: definido em AEROBIZ_LOGFIRE_PROJETO (https://logfire-us.pydantic.dev)

DUAS ARMADILHAS DESTE REPOSITORIO, tratadas aqui:

1. Este harness nasceu dentro de um monorepo multi-dominio cuja RAIZ ja tinha
   um `.logfire/` apontando para OUTRO projeto. Por isso as credenciais do eval
   vivem no diretorio do proprio experimento e este modulo aponta o SDK para la
   explicitamente — sem depender de qual e o diretorio corrente de quem chama.

2. `LOGFIRE_TOKEN` de ambiente VENCE o arquivo de credenciais no SDK. Num
   monorepo onde algum script exporta essa variavel apontando para outro
   projeto, o eval mandaria seus dados para o lugar errado sem ninguem
   perceber. Aqui o token e lido do arquivo do proprio experimento e passado
   explicitamente; a variavel de ambiente e ignorada de proposito.

POLITICA DE CONTEUDO: por padrao NAO enviamos prompt nem resposta do modelo —
so tempo, modelo, acoes e efeito medido. `capturar_conteudo=True` (ou
AEROBIZ_LOGFIRE_CONTEUDO=1) liga o envio do texto, e existe para quando o dono
do projeto decidir; nao e o default.
"""

import json
import os
import pathlib

CRED = pathlib.Path(__file__).parent.parent / ".logfire" / "logfire_credentials.json"
BASE_URL = "https://logfire-us.pydantic.dev"
# O projeto esperado NAO fica chumbado aqui: este arquivo e publico e o handle
# do Logfire e a conta pessoal de quem roda. Ordem de precedencia:
#   1. AEROBIZ_LOGFIRE_PROJETO (ex: "suaconta/aerobiz") — recomendado;
#   2. o `project_name`/`project_url` do proprio arquivo de credenciais local.
# A guarda das duas armadilhas acima continua valendo: com (1) definido, uma
# credencial de OUTRO projeto e recusada. Sem (1), a guarda cai para "confio no
# arquivo do experimento" — que ainda e melhor que a variavel de ambiente, mas o
# nome do projeto e IMPRESSO no console para nao haver envio silencioso.
PROJETO_ESPERADO = os.environ.get("AEROBIZ_LOGFIRE_PROJETO", "").strip() or None

_ligado = False


def _credenciais():
    """(token, project_url) do experimento. Nao imprime o token."""
    if not CRED.exists():
        return None, None
    d = json.loads(CRED.read_text(encoding="utf-8"))
    return d.get("token"), d.get("project_url")


def disponivel():
    _, url = _credenciais()
    if not url:
        return False
    return PROJETO_ESPERADO in url if PROJETO_ESPERADO else True


def configurar(service_name="aerobiz-eval", capturar_conteudo=None, console=False):
    """Liga o Logfire. Silencioso e inofensivo se nao houver credencial.

    NUNCA levanta: telemetria quebrada nao pode derrubar uma partida de 80
    turnos que leva horas para rodar.
    """
    global _ligado
    if _ligado:
        return True
    try:
        import os

        import logfire

        token, url = _credenciais()
        if not token:
            print("[obs] sem %s — telemetria desligada" % CRED, flush=True)
            return False
        if PROJETO_ESPERADO and PROJETO_ESPERADO not in (url or ""):
            print("[obs] credencial e de %s, mas AEROBIZ_LOGFIRE_PROJETO pede %s "
                  "— telemetria desligada" % (url, PROJETO_ESPERADO), flush=True)
            return False

        if capturar_conteudo is None:
            capturar_conteudo = os.environ.get("AEROBIZ_LOGFIRE_CONTEUDO") == "1"

        logfire.configure(
            service_name=service_name,
            token=token,                      # explicito: ignora LOGFIRE_TOKEN do .env
            console=logfire.ConsoleOptions() if console else False,
            advanced=logfire.AdvancedOptions(base_url=BASE_URL),
        )
        logfire.instrument_system_metrics()
        try:
            logfire.instrument_requests()     # chamadas HTTP ao OpenCode
        except Exception:                     # noqa: BLE001
            pass
        _ligado = True
        print("[obs] Logfire ligado em %s (conteudo=%s)"
              % (url, "SIM" if capturar_conteudo else "nao"), flush=True)
        globals()["_CONTEUDO"] = bool(capturar_conteudo)
        return True
    except Exception as e:  # noqa: BLE001
        print("[obs] Logfire indisponivel (%s) — seguindo sem telemetria" % e, flush=True)
        return False


def captura_conteudo():
    return bool(globals().get("_CONTEUDO"))


class _Nulo:
    """Contexto que nao faz nada — usado quando a telemetria esta desligada."""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def set_attribute(self, *a, **k):
        pass


def span(nome, **attrs):
    if not _ligado:
        return _Nulo()
    import logfire

    return logfire.span(nome, **attrs)


def info(msg, **attrs):
    if not _ligado:
        return
    import logfire

    logfire.info(msg, **attrs)
