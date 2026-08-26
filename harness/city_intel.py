"""ETAPA 5d — inteligencia de cidade no prompt, sem afogar o modelo.

O leitor (`world.read_city_panel`, §34) entrega Pop/Econ/Trsm/slots por cidade,
mas custa ~1 min de navegacao POR CIDADE (§34.7.6) e a varredura de 5c NUNCA
terminou: `city_intel.json` nao existia. Logo, o gargalo de cobertura NAO e o
contexto do modelo — e o custo de medicao.

Este modulo faz tres coisas e nenhuma delas inventa numero:

1. `seed_from_shots()` — recolhe o cache RODANDO o leitor sobre os PNGs de
   painel ja gravados (offline, zero toques, reproduzivel). Nada de transcrever
   tabela de markdown: o valor vem do mesmo codigo que rodaria ao vivo.
2. `slice_for_prompt()` — decide QUE cidades levam intel ao prompt e devolve a
   DECLARACAO do recorte junto. Recorte silencioso e pior que recorte nenhum:
   o modelo decidiria achando que viu o mundo inteiro.
3. `compact_rows()` — codificacao terca do catalogo de cidades. Mesma
   informacao MEDIDA que o dicionario verboso de `catalog_for_prompt_world`,
   em ~1/3 dos caracteres, o que paga o espaco da intel com folga.

RESULTADO NEGATIVO QUE MANDA NESTE MODULO (ETAPA 5d, §35.1, MEDIDO):
o cache **nao transfere entre savestates** — nem a parte que se supunha
"propriedade da cidade". `probe_intel_transfer.py` releu 3 paineis do cache no
savestate do piloto (`f0_t02_route.state`) e os 3 divergiram em TODOS os campos:

  Washington NA13: 1.2M/90/48/116 (cache)  ->  0.6M/60/42/68 (piloto)
  Denver     NA06: 0.6M/64/40/94  (cache)  ->  0.4M/40/32/47 (piloto)
  Moscow     EU06: 9.6M/56/38/105 (cache)  ->  6.5M/37/20/71 (piloto)

E a MESMA cidade nos dois lados (o hash do recorte SO do nome, y<20, bate:
Washington `4376d3ff`, Denver `0df29b94`) — o que muda e o valor, por epoca do
cenario. Portanto: **so entra no prompt registro medido no savestate da propria
run**, e `usavel()` FALHA FECHADA quando quem chama nao declara qual e. O resto
fica no arquivo como historico auditavel, com `usar_no_prompt: false`.

Dois tipos de campo, com fragilidades diferentes:
  PROPRIEDADE  pop_m, econ, trsm, slots_cap — mudam por CENARIO (medido acima) e
      por DECADA dentro da propria partida; por isso `medido_no_trimestre`.
  OCUPACAO     slots_used, our_slots — as 3 rivais negociam slots todo
      trimestre, entao envelhecem dentro da run. O prompt avisa; ninguem re-le.

FORA do estado, por medicao e nao por esquecimento (§34.4):
  `rltns_icon` — hash sem ORDEM medida; virar "bom/ruim" seria palpite.
  `Fl`         — zero nos 12 paineis, sem significado medido.
  `name`       — sempre None; `name_ocr` e diagnostico, nao conteudo.
"""

import json
import pathlib
import sys

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
RAIZ = HERE.parent
CACHE_PATH = HERE / "city_intel.json"

PROPRIEDADE = ("pop_m", "econ", "trsm", "slots_cap")
OCUPACAO = ("slots_used", "our_slots")

# PNGs de painel ja gravados, com a PROCEDENCIA de cada um. O cid vem do script
# que gravou o PNG (prova_city_panel.py / prova_city_panel_vivo.py); os NUMEROS
# vem do leitor, aqui, agora.
SHOTS = [
    # (cid, caminho relativo a RAIZ, savestate/origem)
    ("NA13", "logs/etapa5a/r4_panel_NA13.png", "sessao 5a (§33) — savestate nao registrado"),
    ("NA02", "logs/etapa5a/panel_NA02.png", "sessao 5a (§33) — savestate nao registrado"),
    ("NA06", "logs/etapa5a/panel_NA06.png", "sessao 5a (§33) — savestate nao registrado"),
    ("NA14", "logs/etapa5a/panel_NA14.png", "sessao 5a (§33) — savestate nao registrado"),
    ("NA11", "logs/etapa5a/r4_panel_NA11.png", "sessao 5a (§33) — savestate nao registrado"),
    ("NA16", "logs/etapa5a/r4_panel_NA16.png", "sessao 5a (§33) — savestate nao registrado"),
    ("NA01", "logs/etapa5a/r4_panel_NA01.png", "sessao 5a (§33) — savestate nao registrado"),
    ("EU06", "logs/etapa5a/r4_panel_EU06.png", "sessao 5a (§33) — savestate nao registrado"),
    ("EU02", "logs/etapa5a/r4_panel_EU02.png", "sessao 5a (§33) — savestate nao registrado"),
    ("SA02", "logs/etapa5b/panel_SA02.png", "_e3b_base.state"),
    ("ME02", "logs/etapa5b/panel_ME02.png", "_e3b_base.state"),
    ("AS03", "logs/etapa5b/panel_AS03.png", "_e3b_base.state"),
    # ETAPA 5d, medidos NO SAVESTATE DO PILOTO (probe_intel_transfer.py):
    ("NA13", "logs/etapa5d/panel_NA13.png", "f0_t02_route.state"),
    ("NA06", "logs/etapa5d/panel_NA06.png", "f0_t02_route.state"),
    ("EU06", "logs/etapa5d/panel_EU06.png", "f0_t02_route.state"),
]

# Savestate em que a ETAPA 5d mediu ao vivo. NAO e um default de publicacao: o
# `savestate` de quem chama e OBRIGATORIO e vem do `--state` do piloto. Um
# default aqui publicaria a Washington de 1970 numa run de 2000 como se fosse
# atual — o §35.1 com cara amigavel.
SAVESTATE_MEDIDO_EM_5D = "f0_t02_route.state"

# Trimestre absoluto (RAM, `world.read_quarter_index`) em que cada PNG foi
# tirado. `None` = a sessao nao registrou. Serve para o prompt dizer a IDADE da
# medida: Washington tem 0.6M em 1970 e 1.2M em 2000, entao a propriedade
# envelhece DENTRO da partida tambem, nao so entre savestates (§35.1).
TRIMESTRE = {"logs/etapa5d/panel_NA13.png": 62,
             "logs/etapa5d/panel_NA06.png": 62,
             "logs/etapa5d/panel_EU06.png": 62}


def seed_from_shots(shots=None, path=CACHE_PATH):
    """Roda `world.read_city_panel` sobre os PNGs e escreve o cache.

    Offline: nao abre emulador, nao aperta nada. Quando o mesmo cid aparece em
    mais de um PNG, o ULTIMO vence (a lista poe o savestate do piloto por
    ultimo de proposito) e os anteriores ficam em `historico` — sem apagar
    medida, para que a divergencia entre savestates continue auditavel.
    """
    import world  # noqa: PLC0415  (import tardio: world.py e caro)

    out = {}
    faltando = []
    for cid, rel, origem in (shots or SHOTS):
        p = RAIZ / rel
        if not p.exists():
            faltando.append(rel)
            continue
        r = world.read_city_panel(Image.open(p).convert("RGB"))
        if not r["on_panel"]:
            faltando.append(rel + " (guard on_city_panel recusou)")
            continue
        rec = {k: r[k] for k in PROPRIEDADE + OCUPACAO}
        # `world.read_city_panel().name_hash` usa CITY_NAME_BOX=(0,0,200,32), que
        # ENGLOBA a linha y=24 (Pop/Econ/Trsm). Ou seja: ele muda quando os
        # NUMEROS mudam, mesmo sendo a mesma cidade — nao serve de identidade
        # entre savestates (MEDIDO, §35.2). O hash de identidade e o do recorte
        # so do nome/pais/bandeira, y<20.
        import hashlib  # noqa: PLC0415
        nome20 = hashlib.md5(
            Image.open(p).convert("RGB").crop((0, 0, 200, 20)).tobytes()).hexdigest()[:8]
        rec.update({"medido_em": origem, "fonte_png": rel,
                    "name_hash_do_leitor": r["name_hash"],
                    "name_only_hash": nome20,
                    "usar_no_prompt": (origem == SAVESTATE_MEDIDO_EM_5D),
                    "medido_no_trimestre": TRIMESTRE.get(rel),
                    "soma_confere": r["soma_confere"]})
        if cid in out:
            rec["historico"] = out[cid].get("historico", []) + [
                {k: out[cid][k] for k in PROPRIEDADE + OCUPACAO + ("medido_em",)}]
            rec["mesma_cidade_que_o_historico"] = (
                nome20 == out[cid].get("name_only_hash"))
        out[cid] = rec
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    return out, faltando


def load(path=CACHE_PATH):
    if not pathlib.Path(path).exists():
        return {}
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def usavel(rec, savestate):
    """So e usavel no prompt o registro medido NO savestate desta run (§35.1).

    FALHA FECHADA: `savestate` vazio/None nao publica nada. Sem isso, um default
    de modulo faria uma run carregada de OUTRO savestate receber os numeros de
    1970 como se fossem os dela — que e exatamente o erro que §35.1 mediu.
    """
    return bool(savestate) and bool(rec) and rec.get("medido_em") == savestate


def _fmt_intel(rec):
    """Uma cidade em texto curto. `?` = campo que o atlas nao decodificou (R1)."""
    def n(v):
        return "?" if v is None else v
    return "pop%sM econ%s trsm%s slots%s/%s(nossos%s)" % (
        n(rec.get("pop_m")), n(rec.get("econ")), n(rec.get("trsm")),
        n(rec.get("slots_used")), n(rec.get("slots_cap")), n(rec.get("our_slots")))


def _nossas(owned_slots, routes, hubs, world_cities=None):
    pontas = set()
    for r in (routes or []):
        if isinstance(r, dict):
            pontas |= {r.get("from"), r.get("to")}
        elif isinstance(r, str) and world_cities:
            pontas |= {c for c in world_cities if c in r}
    return ({c for c, v in (owned_slots or {}).items() if v}
            | set(hubs or ()) | {p for p in pontas if p})


def slice_for_prompt(intel, owned_slots, routes, hubs, region_names, cities_of_region,
                     savestate, world_cities=None):
    """Quais cidades levam intel ao prompt — e a DECLARACAO do recorte.

    Criterio, explicito e verificavel no proprio estado:
      toda cidade cujo painel foi lido NESTE savestate. Mais nada.

    O que ficou de fora e por que:
      - 9 cidades lidas em outra sessao e 3 no `_e3b_base.state`: MEDIDO que os
        numeros nao transferem (§35.1) — publicar seria inventar.
      - as demais: painel nunca aberto. Ler custa ~1 min de navegacao cada.

    NAO e um top-N por econ x pop. Ranquear exigiria ler as cidades nao lidas;
    um ranking sobre o que ja foi lido so reproduz o vies de cobertura.

    Devolve (mapa cid->texto, declaracao).
    """
    total = sum(len(cities_of_region(r)) for r in region_names)
    nossas = _nossas(owned_slots, routes, hubs, world_cities)
    saida = {cid: _fmt_intel(rec) for cid, rec in intel.items()
             if usavel(rec, savestate)}
    sem_intel_mas_nossas = sorted(nossas - set(saida))
    descartados = sorted(c for c, r in intel.items() if not usavel(r, savestate))
    if not savestate:
        return {}, {
            "mostrando": "intel de painel para 0 de %d cidades" % total,
            "por_que": "quem montou o estado nao declarou de que savestate a "
                       "partida saiu. Os numeros do painel mudam de cenario para "
                       "cenario (MEDIDO, §35.1), entao publicar o cache sem saber "
                       "a origem seria inventar. Falha fechada, de proposito.",
        }
    idades = sorted({r.get("medido_no_trimestre") for r in intel.values()
                     if usavel(r, savestate)})
    return saida, {
        "mostrando": "intel de painel para %d de %d cidades" % (len(saida), total),
        "savestate": savestate,
        "medido_no_trimestre": idades,
        "IDADE": "esta intel foi lida UMA vez, nos trimestres acima, e nunca "
                 "reLida. A populacao de uma cidade muda com a decada (MEDIDO: "
                 "Washington 0.6M em 1970 x 1.2M noutro cenario), entao quanto "
                 "mais o jogo avanca, mais velha ela fica.",
        "criterio": "toda cidade cujo painel foi lido AO VIVO neste savestate. "
                    "Sem ranking, sem filtro de qualidade.",
        "AUSENCIA_NAO_E_SINAL": (
            "as outras %d cidades NAO sao piores — apenas nao foram lidas. Ler um "
            "painel custa ~1 minuto de navegacao no emulador e ninguem leu ainda. "
            "Nao trate a falta de intel como sinal negativo ao escolher destino."
            % (total - len(saida))),
        "nossas_cidades_sem_intel": sem_intel_mas_nossas,
        "descartado_por_savestate": {
            "cids": descartados,
            "por_que": "medidos em OUTRO savestate. MEDIDO em 3 cidades que os "
                       "valores mudam de cenario para cenario (Washington 1.2M/90/48 "
                       "-> 0.6M/60/42), entao reaproveitar seria numero inventado.",
        },
        "campos": "pop = populacao em milhoes; econ e trsm sao indices da tela da "
                  "cidade em escala NAO calibrada — servem para COMPARAR cidades "
                  "entre si, nao como valor absoluto; slots usados/capacidade do "
                  "aeroporto e quantos desses slots sao nossos. '?' = o OCR nao "
                  "reconheceu o glifo e o harness se recusa a adivinhar.",
        "envelhecimento": "usados/nossos foram medidos uma vez e as 3 rivais "
                          "negociam slots todo trimestre: trate como foto antiga, "
                          "nao como estado atual.",
        "fora_de_proposito": "Rltns (icone sem ordem medida) e a linha Fl (zerada em "
                             "todos os paineis vistos) NAO entram: seriam palpite.",
    }


def compact_rows(owned_slots, routes, intel, region_names, cities_of_region,
                 world_cities, home, home_region, distance_mi, medidas_dist,
                 savestate):
    """Catalogo de cidades em linhas curtas (mesma informacao medida, 1/3 dos chars).

    Formato:
        "<ID> <nome ou -> | slots=<n> | rota=<sim|nao> | dist=<...> | <intel>"
    `dist` sem marca = LIDA do jogo; `~N(est)` = estimada por pixel dentro da
    regiao da base; `?` = nunca medida. Intel so aparece quando `usavel()`.
    """
    pontas = _nossas({}, routes, (), world_cities)
    out = {}
    for reg, nome in region_names.items():
        linhas = []
        for cid in cities_of_region(reg):
            _, _, _, cname = world_cities[cid]
            real = medidas_dist.get(cid)
            if cid == home:
                dist = "0"
            elif real is not None:
                dist = "%d" % real
            elif reg == home_region:
                # ETAPA 5-CidadeImplementar: com a sede fora da America do Norte
                # `distance_mi` nao tem catalogo de pixels (so NA_CITIES) e
                # levantava KeyError. Distancia ausente vira "?" — numero
                # inventado aqui e pior que numero ausente (R1).
                try:
                    est = distance_mi(home, cid)
                except Exception:  # noqa: BLE001
                    est = None
                dist = "~%d(est)" % est if est is not None else "?"
            else:
                dist = "?"
            rec = intel.get(cid)
            it = _fmt_intel(rec) if usavel(rec, savestate) else "intel:-"
            linhas.append("%s %s | ledger=%d | rota=%s | dist=%s | %s" % (
                cid, cname or "-", (owned_slots or {}).get(cid, 0),
                "sim" if cid in pontas else "nao", dist, it))
        out["%d %s" % (reg, nome)] = linhas
    return out


if __name__ == "__main__":
    dados, faltando = seed_from_shots()
    print(json.dumps({"cidades_no_cache": len(dados),
                      "cids": sorted(dados),
                      "png_faltando": faltando}, indent=2, ensure_ascii=False))
