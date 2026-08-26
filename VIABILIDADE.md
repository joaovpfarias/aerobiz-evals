# Aerobiz Supersonic como Campo de Evals de LLMs — Análise de Viabilidade

**Data:** 2026-08-10 | **Status:** análise pré-projeto (nenhum código escrito) | **Pesquisa:** web em 10/08/2026

---

## TL;DR — Veredito

**Viável, e o nicho está vazio.** Nenhum trabalho público usa Aerobiz (ou qualquer management sim comercial) como eval de LLM. O benchmark mais próximo — Vending-Bench, da Andon Labs — mede coerência de longo horizonte em um negócio *solo*, sem concorrência, sem geografia, sem choques macro. Aerobiz Supersonic adiciona exatamente essas três dimensões, em formato turn-based trimestral que custa ~2 ordens de magnitude menos tokens por rollout.

Condições para dar certo:
1. **Interface semântica** (ações de negócio, não pixels+controller) — senão vira eval de navegação de menu.
2. **Stack BizHawk + mcp-bizhawk** (já existe, Windows-nativo) — o esqueleto do harness está pronto.
3. **Vision-first, RAM só para métricas-núcleo** — evita o maior custo de engenharia (mapa de RAM completo).
4. **Piloto Wizard-of-Oz (F0) antes de qualquer código** — testa em 1-2 noites o único risco não-mitigável de antemão: o jogo discriminar modelos ou não.

---

## §1 A Tese

Usar um business sim competitivo de 1994 (Koei), turn-based e menu-driven, como ambiente de avaliação de **raciocínio estratégico-econômico de longo horizonte**. O que o torna candidato raro:

- **Turno = 1 trimestre, partida = 20 anos = 80 turnos.** Zero exigência de reflexo/latência (o problema que domina VideoGameBench). Todo o desafio é decisório.
- **Economia competitiva real:** 4 companhias aéreas na mesma partida disputando slots, rotas e passageiros — não um mundo passivo.
- **Choques exógenos históricos:** guerras, crise do petróleo, Olimpíadas — testa replanejamento, não só execução de plano.
- **Payoffs atrasados e estocásticos:** negociação de slots leva 1-4 trimestres conforme relações com a cidade; aviões comprados hoje pagam em anos.
- **Menu-driven:** espaço de ações discreto e enumerável — tratável para scripting, sem física nem timing.

## §2 O Que o Jogo Mede — Mapa Mecânica → Capacidade

| Mecânica do jogo | Capacidade avaliada |
|---|---|
| Compra/leasing de frota (707, DC-8, Concorde, 747…) | Alocação de capital, planejamento de fluxo de caixa, payoff atrasado |
| Abertura de rotas entre slots | Economia de redes, expansão espacial, custo de oportunidade |
| Negociação de slots (1-4 trimestres, máx. 4 simultâneas) | Planejamento sob resultado estocástico, gestão de pipeline |
| Preço, nº de voos/semana, qualidade de serviço | Microeconomia, elasticidade, resposta à concorrência |
| Eventos (guerra, choque do petróleo, Olimpíadas, erupções) | Adaptação a shocks, replanejamento sob nova informação |
| 3 rivais ativos | Estratégia competitiva, leitura de adversário, corrida por posição |
| Relatórios trimestrais (P&L, balanço, share) | Leitura de feedback ruidoso, atribuição causal |
| 80 turnos até o fim | **Coerência de longo horizonte** (o que Vending-Bench mede — aqui com concorrência) |
| Condição de vitória composta (hubs em toda região + nº1 em passageiros em 4-7 regiões + lucro anual) | Otimização multi-objetivo, sequenciamento de sub-metas |

## §3 Prior Art — Onde Isso Se Encaixa (pesquisa 10/08/2026)

**Aerobiz + LLM: nada encontrado.** Busca direta não retorna nenhum agente, benchmark ou experimento. Whitespace confirmado.

| Benchmark | O que cobre | O que falta (que Aerobiz tem) |
|---|---|---|
| **Vending-Bench 1/2** (Andon Labs) | Negócio de longo horizonte, coerência ao longo de 1 ano simulado; 3.000-6.000 tool calls e 60-100M tokens por rollout | Concorrência, geografia/rede, choques macro; custo por rollout enorme |
| **RetailBench** | Decisão de longo prazo em varejo realista | Idem — ambiente solo |
| **lmgame-bench** (ICLR 2026) | 6 jogos plataforma/puzzle/narrativa; harness modular percepção/memória/raciocínio | Nenhum sim de gestão; referência de *arquitetura* para o nosso harness |
| **VideoGameBench** | Vision+controller raw em jogos GB/DOS; mostrou que latência de inferência domina o fracasso em tempo real | Argumento empírico PRÓ interface semântica e jogo turn-based |
| **Balrog** (NetHack etc.) | Roguelikes, exploração | Economia |
| **Factorio Learning Environment** | Produção/logística com scaling exponencial | Concorrência direta; economia de mercado |
| **CivRealm** | 4X estratégia | Foco RL, complexidade enorme, não é gestão empresarial |
| **Kaggle Game Arena** | Head-to-head zero-sum (xadrez etc.) | Informação parcial, economia |

**Posicionamento em uma frase:** *"Vending-Bench com concorrência, geografia e macro — por 1% do custo de tokens"* ou *"o primeiro eval de estratégia empresarial competitiva em um jogo comercial"*.

Bônus de narrativa: o modo arena (§5-D3) permite **Claude vs GPT vs Gemini vs Grok na mesma partida**, cada um dirigindo uma companhia aérea — formato de conteúdo forte (precedente: Kaggle Game Arena, Claude Plays Pokémon).

## §4 Fatos do Jogo Que Importam Para o Design (verificados)

- **Cenários:** 4 — 1955-75 (era do jato), 1970-90 (crise do petróleo/Guerra Fria), 1985-2005 (prosperidade), 2000-20 (supersônicos + eventos climáticos). Cada um: limite de 20 anos.
- **Vitória:** hub regional em toda região + maior nº de passageiros em 4-7 regiões (conforme dificuldade) + lucro anual.
- **4 companhias** simultâneas, cada uma AI ou humana → arena multi-LLM na mesma partida é suportada nativamente.
- **Slots:** negociação via envio de staff; duração 1-4 trimestres conforme relações; máx. 4 negociações simultâneas; slots custam dinheiro e podem ser devolvidos.
- **Plataformas:** SNES (EUA ago/1994) e Genesis (EUA jan/1995) — ambas emuláveis no BizHawk. Existem versões PC-98/DOS/Windows (provavelmente só Japão, como "Air Management II" — confirmar antes de considerar rota DOSBox).
- **Recomendação:** SNES USA (mais documentação; TCRF tem página do jogo — curiosidade: sobras de código C no ROM).

## §5 As 3 Decisões de Design

### D1 — Nível da interface (a decisão que define o que se mede)

| Opção | Mede | Contras |
|---|---|---|
| (a) Raw: screenshot + botões do controle | "Computer use" + estratégia, entangled | Caro (~×5 calls), frágil, confundido — Pokémon mostrou que vira eval de navegação |
| **(b) Semântica: ações tipo `open_route(NYC-LON, 747, 14/sem, fare=alto)` executadas por macros Lua** | **Estratégia pura, comparável entre modelos** | Exige escrever as macros (o grosso do F1) |
| (c) Duas trilhas: (b) como benchmark principal, (a) como "hard mode" | Ambos | Só faz sentido depois que (b) existir |

**Recomendação: (b).** O insight do lmgame-bench (módulos de percepção/memória toggleáveis para isolar capacidades) e do VideoGameBench (latência/percepção dominam e mascaram o raciocínio) apontam na mesma direção.

### D2 — Stack técnico

- **Emulador:** BizHawk (Windows-first — seu ambiente) rodando SNES ou Genesis.
- **Ponte:** **mcp-bizhawk** (npm, achado da pesquisa): expõe via MCP leitura/escrita de memória 8/16/32-bit, batch até 4KB, botões, frame advance, pause, savestates em disco, reset, screenshot PNG, metadados do ROM. Setup: BizHawk 2.6.2+, Node 22+, `EmuHawk.exe --socket_ip=127.0.0.1 --socket_port=8766`, carregar `lua/bridge.lua`. Latência ~1 frame por call — irrelevante para jogo de turno. Alternativas: BrainHawk (bridge Python), tpp-BizHawk2 (HTTP), stable-retro (descartado: linux-first, integração custom pesada).
- **Extração de estado — híbrida:**
  - **Vision:** screenshot das telas de relatório trimestral; Claude lê tabelas de SNES bem. MVP pode ser 100% vision.
  - **RAM (só métricas-núcleo):** caixa, data, passageiros — endereços não documentados publicamente (Data Crystal não tem o jogo), mas acháveis via RAM Search do próprio BizHawk em ~30-60 min por variável (buscar valor conhecido → gastar → refinar). Atalho provável: gamehacking.org/game/42160 tem códigos para o jogo (página bloqueia bots — abrir manualmente no browser); códigos PAR embutem o endereço de dinheiro.
- **Agente:** loop Python (Claude API / Agent SDK) com scratchpad ("diário de bordo" rolante) — a gestão de memória ao longo de 80 turnos é ela mesma uma capacidade medida (precedente: Claude Plays Pokémon).

### D3 — Protocolo de avaliação

- **Fixos:** cenário **1970-90** (choque do petróleo no meio da partida = teste de adaptação embutido; alternativa clássica: 1955-75), cidade-base fixa, dificuldade dos rivais fixa, 20 anos de limite.
- **Modos:**
  - (i) **Solo vs AIs do jogo** — benchmark padrão, escala barata, k seeds;
  - (ii) **Arena multi-LLM** — até 4 modelos na mesma partida (conteúdo/headline; estatisticamente mais fraco por interferência mútua).
- **Seeds:** savestate no turno 1 + jitter de inputs/frames para dessincronizar o RNG; k≥5 por modelo.

## §6 Métricas

**Primárias:** vitória (bool) | trimestres-até-vitória.
**Secundárias (resultado):** patrimônio líquido final, lucro acumulado, share de passageiros por região, falência (bool), nº de rotas lucrativas.
**Secundárias (trajetória — liga com wiki [[ai-evals]] §3):** sub-goal success rate (hubs conquistados por ano), taxa de ações inválidas/ilegais, self-correction após eventos (mudou rota/preço em ≤2 turnos após choque?), custo em tokens por run.
**Baselines:** agente aleatório-legal | heurística gulosa (sempre abrir a rota de maior tráfego que couber no caixa) | AI nativa do jogo (espelhada) | humano casual (você, 1-2 partidas).

## §7 Estatística e Variância

- Fontes de ruído: eventos aleatórios, duração de negociações, comportamento dos rivais.
- Win-rate exige mais runs que métricas contínuas → usar patrimônio/lucro como métrica de potência e vitória como headline.
- k=5-10 seeds por modelo, IC via bootstrap (mesmo padrão do astrology-betting, 10k resamples).
- **Kill-criterion estatístico (F2):** se a variância entre seeds do mesmo modelo ≥ diferença entre modelos, o campo não discrimina — encerrar ou mudar cenário/dificuldade.

## §8 Custos (ordem de grandeza)

- Interface semântica: ~80-160 calls/run (1-2 por turno, ações do trimestre em batch JSON), ~4-8k tokens não-cacheados/call + diário rolante.
- **Por run completa:** Sonnet ~US$3-8 | tier Opus/Fable ~US$15-40. Vision (1-3 screenshots/turno) multiplica ×2-3.
- **F2 completa** (4 modelos × 5 seeds): ~US$200-800.
- Referência: Vending-Bench queima 60-100M tokens/rollout; Aerobiz semântico fica em ~1-3M — viabiliza rodar em escala pessoal.

## §9 Riscos e Mitigações

| Risco | Prob. | Gravidade | Mitigação |
|---|---|---|---|
| Mapa de RAM além do básico (tabela de rotas, estado dos rivais) | Alta | Média | Não fazer: vision-first; RAM só p/ caixa/data/pax |
| Fragilidade das macros de menu | Alta | Baixa | Savestate a cada turno + retry; máquina de estados por tela; mcp-bizhawk já dá savestate/load |
| RNG/variância engole sinal | Média | **Alta (killer)** | k seeds + IC; kill-criterion do §7; ajustar dificuldade |
| Jogo trivial ou ilegível para o modelo | Média | **Alta (killer)** | **F0 responde em 1-2 noites antes de qualquer harness** |
| ROM/copyright (Koei Tecmo) | — | Média se publicar | Uso pessoal de pesquisa ok; publicação = "bring your own ROM" (precedente VideoGameBench); nunca distribuir ROM/assets |
| Contaminação (FAQs GameFAQs/Neoseeker no treino) | Certa | Baixa | Meta conhecida ≠ execução (como aberturas de xadrez); documentar como limitação |
| Estouro de contexto em 80 turnos | Alta | Média | Diário rolante + resumo por ano; é capacidade medida, não bug |

## §10 Roadmap Faseado (com kill-criteria)

**F0 — Piloto Wizard-of-Oz** (1-2 noites, ~US$5)
BizHawk aberto; mcp-bizhawk plugado no Claude Code (ou você operando na mão). Claude recebe screenshot do trimestre, mantém diário, devolve as ações; você executa. Jogar 5-10 anos in-game.
*Responde:* decisões são coerentes? telas são legíveis? o diário aguenta? o jogo tem tensão (Claude vs sua run casual)?
**Kill se:** trivial, ilegível, ou incoerente por contexto.

**F1 — Harness semiautomático** (1-2 fins de semana)
Macros Lua para ~8 ações-núcleo (§12) + loop Python↔API + extração vision dos relatórios + savestate por turno + log JSONL. 3 runs Sonnet vs baseline aleatória.
**Kill se:** macros exigirem >2 fins de semana ou taxa de execução <90%.

**F2 — Eval de verdade** (2-4 fins de semana acumulados)
RAM para métricas-núcleo, k=5 × 3-4 modelos, relatório com ICs, decidir cenário/dificuldade canônicos.
**Kill se:** variância ≥ diferença entre modelos.

**F3 — Opcional (se F2 discriminar):** arena 4-LLM na mesma partida; blogpost/leaderboard "bring your own ROM"; trilha raw como hard mode.

**Esforço total até F2: ~3-5 fins de semana + US$200-800 de API.** Maior lift de engenharia: macros de menu (F1).

## §11 Alternativas Honestas (e por que não começar por elas)

| Alternativa | Prós | Contras |
|---|---|---|
| **OpenTTD** (open source, API de AI nativa) | Sem ROM, publicável, determinístico | Real-time (pausável), sem cenários históricos, sem o charme; API é Squirrel |
| **Reimplementação "Aerobiz-like"** | Ciência perfeita: determinismo, seeds, sem copyright | Semanas construindo e balanceando um sim; deixa de ser Aerobiz |
| **Sim textual estilo Vending-Bench** | Mais barato ainda | Já existe; perde concorrência/geografia |

Para projeto pessoal com potencial de conteúdo, **Aerobiz real via emulador é o melhor custo/benefício**. Se F2 der certo e quiser publicar benchmark sério, a reimplementação vira o caminho natural (com Aerobiz como "inspiração declarada").

## §12 Draft do Action Space Semântico (~10 ações)

```
negotiate_slots(city)                      # inicia negociação (máx 4 ativas)
return_slots(city, n)
open_route(city_a, city_b, aircraft, flights_week, fare_level)
close_route(route_id)
adjust_route(route_id, flights_week, fare_level)
buy_aircraft(model, qty, cash|lease)
sell_aircraft(model, qty)
set_budget(region, ads, service)           # + manutenção global
invest(city, hotel|tourism)                # opcional no MVP
end_turn()
```
Observação devolvida ao agente por turno: data, caixa, P&L do trimestre, tabela de rotas (ocupação/lucro), status de negociações, eventos anunciados, ranking das 4 companhias.

## Fontes (pesquisa 10/08/2026)

- [Wikipedia — Aerobiz Supersonic](https://en.wikipedia.org/wiki/Aerobiz_Supersonic) — cenários, vitória, 4 companhias
- [Vending-Bench (arXiv 2502.15840)](https://arxiv.org/abs/2502.15840) | [Vending-Bench 2 — Andon Labs](https://andonlabs.com/evals/vending-bench-2)
- [lmgame-Bench (OpenReview)](https://openreview.net/forum?id=qeziG97WUZ) | [GamingAgent repo (ICLR 2026)](https://github.com/lmgame-org/GamingAgent)
- [Factorio Learning Environment (arXiv 2503.09617)](https://arxiv.org/pdf/2503.09617)
- [RetailBench (arXiv 2603.16453)](https://arxiv.org/pdf/2603.16453)
- [mcp-bizhawk — MCP server para BizHawk](https://github.com/dmang-dev/mcp-bizhawk) — memória, inputs, savestates, screenshots
- [BrainHawk — bridge Python p/ BizHawk](https://github.com/TylerLandowski/BrainHawk) | [tpp-BizHawk2 (HTTP API)](https://github.com/TwitchPlaysPokemon/tpp-BizHawk2) | [BizHawk Lua Functions](https://tasvideos.org/Bizhawk/LuaFunctions)
- [GameFAQs — Aerobiz Supersonic Strategy Guide (D_Simpson)](https://gamefaqs.gamespot.com/snes/588190-aerobiz-supersonic/faqs/2757) — mecânica de slots/negociação
- [TCRF — Aerobiz Supersonic (SNES)](https://tcrf.net/Aerobiz_Supersonic_(SNES)) | [GameHacking.org #42160](https://gamehacking.org/game/42160) (abrir no browser; 403 p/ bots)
