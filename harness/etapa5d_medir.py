"""ETAPA 5d — o CUSTO da inteligencia de cidade no prompt, em numeros.

Tres estados sobre o MESMO turno, para que o ganho de compactacao nao esconda
o custo da intel (que e o que a etapa pediu para nao esconder):

  A ANTES      — `catalog_for_prompt_world`, como o piloto mandava ate agora.
                 E RECONSTRUCAO, nao o arquivo historico: monta o estado novo e
                 devolve `cities_by_region` ao formato antigo, tirando os dois
                 campos que a 5d criou. E fiel porque o diff da 5d em
                 `build_state` removeu EXATAMENTE 3 linhas (assinatura,
                 `cities_by_region` e a chamada) — nenhum outro campo mudou.
  B ANTES+INTEL— o mesmo formato verboso com os 5 campos de painel colados em
                 TODAS as 95 cidades. E uma SIMULACAO DE TAMANHO: os valores
                 sao os de uma cidade real repetidos so para medir a largura da
                 linha. Nada daqui vai para `city_intel.json` nem para o jogo.
  C DEPOIS     — o que o piloto manda agora: linhas compactas + intel so das
                 cidades medidas neste savestate + a declaracao do recorte.

Uso: python etapa5d_medir.py [--tokens]   (--tokens faz 1 chamada por estado
     ao modelo so para LER `prompt_tokens` do usage; sem isso, so chars)
"""

import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import city_intel  # noqa: E402
import pilot  # noqa: E402
import world  # noqa: E402

# Turno de referencia (numeros do savestate do piloto, lidos em 5d).
CTX = dict(turn=1, cash_k=1014360, owned=dict(world.EVAL_SLOTS_2000), routes=[],
           negotiating=[], last_results={"note": "medicao de tamanho"},
           hubs={"NA13"}, savestate=city_intel.SAVESTATE_MEDIDO_EM_5D)


def estado_antes():
    st = pilot.build_state(**CTX)
    st["cities_by_region"] = world.catalog_for_prompt_world(CTX["owned"], CTX["routes"])
    st.pop("cities_legend", None)
    st.pop("cities_intel_declaracao", None)
    return st


def estado_antes_com_intel_completa():
    """SIMULACAO DE TAMANHO: 95 cidades x 5 campos no formato verboso."""
    st = estado_antes()
    molde = {"pop_m": 14.8, "econ": 43, "trsm": 38, "slots_used": 27, "slots_cap": 130}
    for linhas in st["cities_by_region"].values():
        for e in linhas:
            e.update(molde)  # valores FICTICIOS, so para medir largura de linha
    return st


def estado_depois():
    return pilot.build_state(**CTX)


def chars(st):
    return len(json.dumps(st, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", action="store_true")
    ap.add_argument("--dump", default="../logs/etapa5d")
    a = ap.parse_args()

    a_st, b_st, c_st = estado_antes(), estado_antes_com_intel_completa(), estado_depois()
    linhas = [("A antes (catalogo verboso, sem intel)", a_st),
              ("B antes + intel em TODAS as 95 (simulacao)", b_st),
              ("C depois (compacto + intel medida + declaracao)", c_st)]
    base = chars(a_st)
    print("%-48s %9s %9s" % ("estado", "chars", "vs A"))
    for nome, st in linhas:
        n = chars(st)
        print("%-48s %9d %+8.0f%%" % (nome, n, (n - base) / base * 100))
    print("\ncampo a campo (chars de JSON):")
    print("%-32s %9s %9s %9s" % ("campo", "A", "B", "C"))
    for k in sorted(set(a_st) | set(c_st)):
        f = lambda st: (len(json.dumps(st[k], ensure_ascii=False)) if k in st else 0)  # noqa: E731
        print("%-32s %9d %9d %9d" % (k, f(a_st), f(b_st), f(c_st)))

    out = pathlib.Path(a.dump)
    out.mkdir(parents=True, exist_ok=True)
    (out / "estado_A_antes.json").write_text(
        json.dumps(a_st, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "estado_C_depois.json").write_text(
        json.dumps(c_st, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nJSONs em %s" % out)

    if a.tokens:
        from agent import MAX_TOKENS, build_system  # noqa: PLC0415
        from opencode_client import chat  # noqa: PLC0415
        sistema = build_system(pilot.SUPPORTED)
        print("\nprompt_tokens MEDIDO (1 chamada por estado, resposta descartada):")
        for nome, st in linhas:
            msgs = [{"role": "system", "content": sistema},
                    {"role": "user", "content":
                     "CURRENT STATE:\n" + json.dumps(st, ensure_ascii=False)
                     + "\n\nReply with the single word OK."}]
            try:
                r = chat(msgs, max_tokens=32, fallbacks=True)
                print("  %-48s %s" % (nome, r.get("usage", {})))
            except Exception as e:  # noqa: BLE001
                print("  %-48s ERRO %r" % (nome, e))


if __name__ == "__main__":
    main()
