# Brief de execucao — leitura de regiao + baselines (Aerobiz evals)

Voce vai trabalhar num harness que faz um LLM jogar **Aerobiz Supersonic (SNES)**
dentro do **BizHawk**, para servir de eval comparativo entre modelos. O harness
ja funciona: 10 acoes calibradas, suite de testes verde (32/32), telemetria e um
runner de um comando. Faltam DUAS coisas, descritas abaixo.

---

## 0. Ambiente (Windows)

| Item | Valor |
|---|---|
| Raiz | `<repo>` |
| Python | `<python>` (**sempre caminho absoluto**; `python` puro nao funciona) |
| Codigo | `harness/` |
| Capturas | `logs/` |
| Savestates | `states/` |

Regras de ambiente que ja custaram tempo:

- `PYTHONIOENCODING=utf-8` em tudo. **Sem emoji nem acento em `print`** — o
  console e cp1252 e quebra com `UnicodeEncodeError`.
- Rode script longo em **background** e crie o diretorio de log **antes** do
  redirecionamento (`mkdir -p` primeiro; senao o shell falha).
- Ponte com o emulador: teste `bridge.BizHawkBridge().ping()` **antes** de
  relancar qualquer coisa. Se estiver morta, lance o `launch.ps1` apontando para
  a ROM em `../roms/` (primeiro boot ~40s; espere o `ping`, nao use `sleep` fixo).
- **A trava da ponte e EXCLUSIVA**: dois processos falando com o emulador ao
  mesmo tempo nao funciona. Rode em serie.

---

## 1. As cinco regras do projeto (nao negociaveis)

Cada uma foi comprada com erro real:

**R1 — Nada entra no estado do modelo sem medicao.** Campo assumido e proibido.
Glifo que o atlas nao reconhece vira `?`; numero vira `None`. Nunca palpite.

**R2 — `A` as cegas custa dinheiro.** Um `A` na tela de Regional Rankings
confirmou uma compra e queimou **$276.000K**. Um `A` numa caixa YES/NO de
patrocinio custou **$372.000K**. Volte ao menu por `Executor.dismiss_to_menu`,
meça o caixa antes e depois de qualquer leitura, e **aborte se o caixa caiu**.
Guard que recusa **demais** tambem e bug — ja aconteceu de um detector negar a
tela certa; meça antes de afrouxar.

**R3 — Nada chumbado** de nome, cor ou quantidade de companhia: muda por
cenario, e a companhia do jogador e escolhida na partida.

**R4 — O relato mente nas DUAS direcoes.** Ja houve acao que retornava sucesso
sem efeito nenhum, e acao que retornava falha tendo funcionado. **A prova e ler
o estado de volta da tela**, nunca o valor de retorno da funcao.

**R5 — Negativo documentado vale mais que sucesso alegado.** Se nao mediu, diga
que nao mediu.

---

## TAREFA 1 — O harness fica cego a regiao a partir da 2a rota

### O que esta acontecendo (ja medido, nao precisa remedir)

`world.detect_region` identifica em que regiao o mapa esta **contando pixels de
terra** (`world.land_pixels` comparado com a tabela `world.REGION_LAND`).
Referencias em `harness/world.py` por volta das linhas **317, 635 e 638**.

O problema: **cada rota aberta desenha uma linha por cima do mapa e tapa
verde**. A contagem cai e a assinatura deixa de bater:

| Turno | Rotas no mapa | Pixels de terra | Regiao lida |
|---|---|---|---|
| t1 | 0 | 2265 | 0 (correto) |
| t2 | 1 | 2250 | 0 (correto) |
| t3 | 2 | 2183 | **None** |
| t5 | — | 2166 | **None** |
| t12 | — | 2138 | **None** |

`REGION_LAND[0] = 2262`; o vizinho `REGION_LAND[2] = 2073`. Com a margem atual,
aceitar a regiao 0 exige `land > 2199`.

**Consequencia:** de 2 rotas em diante o harness fica cego **permanentemente**,
loga "regiao do mapa ambigua" em todo turno >= 3 e **recusa toda abertura de
rota** (2 de 7 recusadas numa run de aceite). Ou seja: **quanto mais o modelo
joga, mais cego o harness fica** — o oposto do que um eval precisa.

### PROIBIDO (ja foi medido e da errado)

- **Nao** afrouxe a margem.
- **Nao** use "pega a regiao mais parecida". Medido: no t5 o palpite mais
  proximo daria **regiao 2 quando a verdade e 0**. O modelo abriria rota no
  continente errado achando que acertou. **Errado em silencio e pior que
  recusar** — a versao atual pelo menos recusa.

### Caminhos candidatos (escolha por medicao, nao por gosto)

1. **Descontar os pixels das linhas de rota** antes de contar (as linhas tem cor
   propria; identifique-a nas capturas).
2. Assinatura por **forma** ou por janelas de amostragem fixas, em vez de
   contagem global.
3. Ler a regiao de **outro lugar da tela** que nao seja o desenho do mapa.
4. **RAM**, se existir endereco estavel (`bridge.read_ram`).

### Como trabalhar (barato primeiro)

Ha material offline farto: **`logs/run_f0/map_t*.png`** cobre os turnos 1 a 12,
com 0, 1 e 2+ rotas. **Resolva offline** e so va ao emulador para confirmar.

### Criterio de aceite

1. `detect_region` acerta a regiao em **todos** os `map_t*.png`, inclusive os
   com 2+ rotas.
2. Continua devolvendo `None` numa tela que **nao** e mapa — o conserto nao pode
   virar um detector que aceita qualquer coisa (trocaria falso negativo por
   falso positivo).
3. Ao vivo: uma run onde `open_route` seja **aceito em turno >= 3**.

---

## TAREFA 2 — A baseline aleatoria nao e reprodutivel

Mesmo savestate, mesma seed, e a economia **bifurca de forma persistente**
(compare `logs/ponte_longa/aceite12b.log` com `aceite12.log` e `aceite12c.log`).

**Hipotese a testar:** as recusas nao-deterministas de `open_route` (causadas
pela cegueira da Tarefa 1) fazem as partidas divergirem. Pode ser o mesmo bug.

Depois de consertar a Tarefa 1, rode a **mesma seed duas vezes** e compare. Se
ainda bifurcar, **diga** — baseline nao reprodutivel nao serve de piso contra um
modelo, e isso muda o desenho do eval.

---

## TAREFA 3 — Rodar as baselines (so depois das duas acima)

Nesta etapa **nao conserte nada**: consertar durante a medicao contamina o
resultado.

    <python> harness\run_eval.py --model random --city NA13 --turns 12 --seed 0
    <python> harness\run_eval.py --model greedy --city NA13 --turns 12 --seed 0

**Em serie**, nunca em paralelo (trava exclusiva). Uma tentativa anterior
conseguiu so 1 turno em varias horas: se acontecer de novo, **pare, diga em qual
turno travou e o que o log mostra**, em vez de insistir.

### Entrega

`logs/baselines/REFERENCIA.md`, por baseline:

- turnos completados (se nao completou 12, **diga quantos** — nunca apresente
  run curta como completa)
- acoes substantivas por tipo
- `taxa_efeito_substantivas_pct` — o campo **novo**, que **exclui `wait`**
- turnos passivos (sem nenhuma acao substantiva)
- caixa inicial e final, rotas abertas, placar de vitoria

**Nao conclua qual baseline e melhor** — sao 2 corridas, nao uma amostra.

### Por que o campo que exclui `wait` importa

A metrica antiga contava `wait` como "efeito verificado". Resultado: a baseline
**aleatoria** marcava 100% e a **gulosa** 66% — parecia que a aleatoria jogava
melhor. Nao jogava: **metade das jogadas dela era passar a vez**. Com a
correcao, a aleatoria caiu para 58,3% e 75,0% nas runs recalculadas.

Se voce usar a taxa antiga, **o modelo mais passivo ganha o eval**.

---

## Contexto util

- `harness/test_harness.py --offline | --vivo` — suite completa (32/32 verde).
  Rode depois de mexer em qualquer leitor.
- `--only` e **match exato** de nome de teste; nome errado roda menos casos **em
  silencio**.
- Acoes suportadas hoje: 10. `return_slots`, `suspend_route` e `close_route`
  estao **fora** de proposito (a primeira foi medida sem efeito).
- Documentacao: `CALIBRATION.md` (leia **so** a secao citada — sao 30+),
  `ACTION_SPACE.md`, `STATUS.md`.
- **Economia:** use `grep` para achar a funcao e leia o trecho. Nao leia
  `world.py` (1600+ linhas) nem `executor.py` inteiros.
