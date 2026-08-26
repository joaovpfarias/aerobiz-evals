"""Cliente minimo OpenAI-compativel para a API do OpenCode (assinatura Go).

Le a chave de ~/.local/share/opencode/auth.json (provider "opencode-go").
Modelos free da assinatura (custo zero) — ver probe_models.py para o bake-off.
"""

import json
import pathlib
import time

import requests

AUTH_PATH = pathlib.Path.home() / ".local" / "share" / "opencode" / "auth.json"
BASE = "https://opencode.ai/zen/v1"

# Ordem = ordem de fallback. Health check em 11/08/2026: os dois `ling` estavam
# 503 e `north-mini-code-free` da 401 (fora do plano Go), entao ficam por ultimo
# — cada modelo morto na frente da fila custa segundos em TODA chamada.
FREE_MODELS = [
    "laguna-s-2.1-free",
    "longcat-2.0-free",
    "mimo-v2.5-free",
    "deepseek-v4-flash-free",
    "nemotron-3-ultra-free",
    "ling-3.0-flash-free",
    "ling-3.0-tiny-free",
]

# Titular: passou 2/2 no bake-off e responde em ~13s emitindo JSON direto.
# (deepseek e reasoning-heavy e as vezes gasta todo o budget sem emitir JSON.)
DEFAULT_MODEL = "laguna-s-2.1-free"


def _key():
    return json.loads(AUTH_PATH.read_text(encoding="utf-8"))["opencode-go"]["key"]


def chat(messages, model=DEFAULT_MODEL, max_tokens=2000, temperature=None, retries=4, timeout=240,
         fallbacks=True):
    """Retorna dict: content, reasoning, usage, latency_s, model.

    Modelos free saem do ar (503) sem aviso; com fallbacks=True a chamada
    percorre os demais free antes de desistir — necessario para runs longas.
    """
    chain = [model]
    if fallbacks:
        chain += [m for m in FREE_MODELS if m != model]
    last = None
    for i, candidate in enumerate(chain):
        try:
            # so o titular merece re-tentativas; um fallback que falha uma vez
            # provavelmente esta fora do ar e insistir custa segundos por turno
            return _chat_one(messages, candidate, max_tokens, temperature, retries if i == 0 else 1, timeout)
        except Exception as e:  # noqa: BLE001
            last = e
            if candidate != chain[-1]:
                print(f"  [opencode] {candidate} indisponivel ({str(e)[:60]}); tentando proximo", flush=True)
    raise RuntimeError(f"OpenCode chat falhou em todos os modelos: {last}")


def _chat_one(messages, model, max_tokens, temperature, retries, timeout):
    body = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if temperature is not None:
        body["temperature"] = temperature
    last = None
    for i in range(retries):
        try:
            t0 = time.time()
            r = requests.post(
                f"{BASE}/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {_key()}"},
                timeout=timeout,
            )
            r.raise_for_status()
            d = r.json()
            choice = d["choices"][0]
            msg = choice["message"]
            return {
                "content": msg.get("content") or "",
                "reasoning": msg.get("reasoning_content") or "",
                "finish_reason": choice.get("finish_reason"),
                "usage": d.get("usage", {}),
                "latency_s": round(time.time() - t0, 2),
                "model": model,
            }
        except Exception as e:  # noqa: BLE001 — retry generico com backoff
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"{model}: falhou apos {retries} tentativas: {last}")


def _balanced_objects(s):
    """Gera cada objeto JSON top-level balanceado encontrado na string."""
    i = 0
    while True:
        start = s.find("{", i)
        if start < 0:
            return
        depth = 0
        end = None
        for j in range(start, len(s)):
            if s[j] == "{":
                depth += 1
            elif s[j] == "}":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end is None:
            return  # truncado
        yield s[start : end + 1]
        i = end + 1


def extract_json(text, required_key=None):
    """Extrai um objeto JSON da resposta (tolera cercas de markdown e lixo em volta).

    Com required_key, retorna o primeiro objeto que contenha essa chave —
    protege contra pescar fragmentos ecoados (ex.: o proprio state) no reasoning.
    """
    s = text.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1]
        s = s.split("\n", 1)[1] if "\n" in s else s
    fallback_err = None
    for cand in _balanced_objects(s):
        try:
            obj = json.loads(cand)
        except json.JSONDecodeError as e:
            fallback_err = e
            continue
        if required_key is None or (isinstance(obj, dict) and required_key in obj):
            return obj
    raise ValueError(
        f"sem JSON{f' com chave {required_key!r}' if required_key else ''} na resposta "
        f"({fallback_err or 'nenhum objeto'}): {text[:200]!r}"
    )
