# Aerobiz Evals — Plano de Execução Operacional

**Data:** 2026-08-10 | **Complementa:** [VIABILIDADE.md](VIABILIDADE.md) (análise estratégica) | **Status:** em execução

> **Status de execução (noite de 10/08/2026):**
> ✅ BizHawk 2.11.1 instalado (`~/tools`) e validado com homebrew (screenshot lido por visão)
> ✅ Ponte file-IPC Lua↔Python completa (`harness/`): ping/shot/press/save/load/ram/speed
> ✅ API OpenCode Go conectada; bake-off dos 8 modelos free (`logs/probe_report.json`): 7 ok
> ✅ Jogador titular: **`ling-3.0-flash-free`** (3-4s, JSON direto); deepseek-free descartado (reasoning estoura 8k tokens sem emitir JSON); north-mini-code-free = 401
> ✅ Agent loop + schema + baselines smoke-testados (custo até aqui: **$0** — modelos free)
> ✅ **ROM recebida (11/08) e F0 iniciado** — jogo roda pela ponte; setup completo (Federal/Washington vs 3 CPUs, cenário 1970-90, Lv 3, $1.02B, meta #1 em 6 regiões)
> ✅ **Pergunta central do F0 respondida: as telas são 100% legíveis** por visão com upscale 3x (`zoom.py`). Li cenários, cash, metas, slots por cidade, mensagens
> ✅ Ferramentas de navegação: `locate.py` (cidades por cor + cursor por frame-diff + goto em malha fechada), `find_hotspot.py`, `sweep.py`, `hunt.py`
> ✅ Savestate `states/f0_ingame.state` = turno 1 dentro do jogo (pula todo o setup)
> 📋 **Armadilhas de controle documentadas** em `logs/run_f0/INVENTARIO_TELAS.md` — texto com auto-limpeza, cursor livre 2px/toque com aceleração, hotspot deslocado (+4,+4)
> 🔜 Próximo: mapear os 12 ícones de comando + telas de relatório trimestral → `macros.py` → loop `agent.py` rodando turnos

---

## Visão Geral das Fases

```
F0 Piloto Wizard-of-Oz ──gate──▶ F1 Harness semiauto ──gate──▶ F2 Eval real ──gate──▶ F3 Extensões
   1-2 noites, ~$5              1-2 fins de semana           2-4 fins de semana      opcional
   "o jogo presta?"             "dá pra automatizar?"        "discrimina modelos?"   arena/publicação
```

Cada gate tem kill-criteria explícito. Nenhuma fase começa sem a anterior passar no gate.

---

## F0 — Piloto Wizard-of-Oz (1-2 noites, ~US$5)

**Pergunta que responde:** o jogo é legível, jogável com coerência e tem tensão suficiente para discriminar? (Único risco killer não-mitigável por engenharia — por isso vem primeiro.)

### Setup (checklist)

- [ ] Baixar BizHawk 2.x mais recente (TASEmulators no GitHub) + rodar `prereqs installer`
- [ ] ROM Aerobiz Supersonic (USA) SNES — dump próprio (nunca commitar no repo; adicionar `*.smc`/`*.sfc` ao .gitignore)
- [ ] Testar jogo manualmente 15 min (confirmar telas, menu, save)
- [ ] **Rota A (mão):** você opera, cola screenshots no Claude Code
- [ ] **Rota B (semiauto, preferida):** `npm install -g mcp-bizhawk` → `EmuHawk.exe --socket_ip=127.0.0.1 --socket_port=8766 <rom>` → carregar `lua/bridge.lua` no Lua Console → registrar MCP no Claude Code (`claude mcp add`, stdio) → Claude tira os próprios screenshots e aperta botões
- [ ] Criar `logs/f0/` com: `diario.md` (mantido pelo Claude), `screenshots/`, `protocolo_f0.md`

### Protocolo do piloto

| Parâmetro | Valor |
|---|---|
| Cenário | 1970-1990 (choque do petróleo ≈ ano 4-9 = teste de adaptação embutido) |
| Dificuldade | padrão |
| Companhia/base | fixar 1 (sugestão: base em região com concorrência forte) |
| Duração | 5-10 anos in-game (20-40 turnos) |
| Loop por turno | screenshot(s) → Claude atualiza diário + decide ações do trimestre → execução → end turn |

### Template do diário (mantido pelo modelo, 1 entrada/turno)

```markdown
## T{n} — {trimestre/ano}
Estado: caixa ${x}M | rotas {n} | aviões {n} | rank {1-4}
Eventos: {...}
Decisões: {lista com 1 linha de racional cada}
Plano 4 turnos: {...}
Aprendizado: {o que o resultado do turno anterior ensinou}
```

### Subprodutos do F0 (insumos do F1)

1. **Inventário de telas** — lista de cada tela do jogo + dados que ela exibe + sequência de botões para alcançá-la (base das macros)
2. **Formato do state-summary** — qual JSON de estado o agente realmente precisa por turno
3. **Calibração de legibilidade** — quais telas o vision lê com confiança, quais precisam de RAM/zoom

### Gate F0 → F1 (kill-criteria)

- ❌ KILL se: Claude vence trivialmente no padrão E também no difícil (sem tensão)
- ❌ KILL se: telas ilegíveis mesmo com prompt de extração dedicado
- ❌ KILL se: incoerência estrutural antes do turno 20 mesmo com diário (esquece frota, contradiz plano sem motivo)
- ✅ GO se: decisões coerentes + diário sustenta + resultado incerto vs sua partida casual

---

## F1 — Harness Semiautomático (1-2 fins de semana)

**Pergunta que responde:** dá para rodar partidas inteiras sem humano no loop, com ≥90% de execução correta de ações?

### Arquitetura

```
experiments/aerobiz_evals/
├── harness/
│   ├── bridge.py        # wrapper do mcp-bizhawk/socket Lua: screenshot, press, savestate, loadstate, read_ram
│   ├── macros.py        # ações semânticas → sequências de botões (máquina de estados por tela)
│   ├── state.py         # navegação p/ telas de relatório + vision→JSON + cross-check RAM
│   ├── agent.py         # loop: prompt → ação JSON → validação → execução → log
│   ├── baselines.py     # random-legal + greedy
│   └── schema.py        # action space + state schema (pydantic)
├── logs/                # JSONL por turno + screenshots por run
└── analysis/            # notebooks F2
```

### Componentes e padrões

1. **`bridge.py`** — funções: `screenshot() → PNG`, `press(seq)`, `save(slot)`, `load(slot)`, `read_ram(addr, n)`. Latência ~1 frame/call (irrelevante, jogo de turno).

2. **`macros.py`** — o grosso do trabalho. Padrão anti-fragilidade por ação:
   ```
   savestate → executar sequência → verificar tela-alvo (pixel/checksum/OCR do título)
   → mismatch? loadstate + retry (máx 3) → falhou? marcar ação como failed no log e seguir
   ```
   ~10 ações do action space (VIABILIDADE §12). Começar pelas 6 essenciais: `negotiate_slots`, `open_route`, `adjust_route`, `buy_aircraft`, `set_budget`, `end_turn`.

3. **`state.py`** — por turno: navegar às telas de relatório (inventário do F0), screenshot de cada, UMA call de vision → JSON estruturado. **Cross-check:** caixa/data lidos por RAM validam a extração vision (mede acurácia de percepção como métrica separada — padrão lmgame-bench de módulos isoláveis).

4. **`agent.py`** — pseudocódigo do loop:
   ```python
   state = extract_state()                      # vision + ram
   diario = update_diary(model, diario, state)  # rolling, cap ~2k tokens, resumo anual
   actions = model(SYSTEM_RULES + diario + state)  # JSON batch do trimestre
   validate(actions, schema)                    # ação ilegal → contabiliza + pede correção 1x
   for a in actions: macros.execute(a)
   macros.end_turn(); savestate(turn_n)
   log_jsonl(turn_n, state, actions, results, custo_tokens)
   ```

5. **Prompt — decisão registrada:** system prompt contém **regras do jogo, não estratégia** (mede descoberta de estratégia, não execução de meta decorada; contaminação por FAQs antigos existe e fica documentada como limitação). Output forçado em JSON via schema.

6. **Sessão RAM Search** (~1-2h, encaixa aqui): endereços de caixa, data, passageiros via RAM Search do BizHawk (buscar valor exato mostrado na tela → gastar → re-buscar). Dica: jogos Koei às vezes guardam dinheiro em BCD ou ×100 — se busca exata falhar, usar modo "changed by". Atalho: conferir gamehacking.org/game/42160 no browser antes (códigos PAR embutem endereços).

### Milestone F1

3 runs completas Sonnet + 3 runs random-legal, zero intervenção humana após o start.

### Gate F1 → F2 (kill-criteria)

- ❌ KILL se: taxa de execução de macros <90% após 2 fins de semana
- ❌ KILL se: extração vision <95% de acurácia vs RAM nos campos core
- ✅ GO se: 6 runs completas + logs íntegros + custo/run dentro de 2× da estimativa

---

## F2 — Eval Real (2-4 fins de semana acumulados)

**Pergunta que responde:** o campo discrimina modelos acima do ruído?

### Passos

1. **Congelar protocolo v1.0** (`PROTOCOLO.md`, estilo pré-registro, ANTES de rodar): cenário, base, dificuldade, prompt exato, schema, procedimento de seeds, métricas e testes. Nada muda depois — mudanças = v1.1 com changelog.
2. **Seeds:** savestate no turno 1 → jitter (N frames aleatórios + input inócuo) → verificar divergência real (ex.: resultado da 1ª negociação difere entre seeds).
3. **Matriz de runs:** 3-4 modelos (Haiku, Sonnet, Opus/Fable + 1 não-Anthropic via OpenRouter) × 5 seeds; baselines × 10 seeds (baratas). Rodar em background, ~1 run/noite se necessário.
4. **Análise** (`analysis/f2.ipynb`): métricas primárias/secundárias (VIABILIDADE §6), bootstrap 10k (padrão astrology-betting), decomposição de variância within vs between, curvas de patrimônio por trimestre, case studies de resposta a eventos (o modelo reprecificou/realocou em ≤2 turnos após o choque do petróleo?).
5. **Relatório** (`RELATORIO.md`) no formato Strategy Lab: § numerados, tabela-mestra, negativos reportados sem maquiagem.

### Gate F2 → F3

- ❌ KILL (= resultado negativo publicável no Strategy Lab): variância within-model ≥ diferença between-model após 1 ajuste de dificuldade/cenário
- ✅ GO se: ordenação de modelos estável entre seeds com IC separado em ≥1 métrica primária

---

## F3 — Extensões (opcional, só se F2 discriminar)

| Extensão | Esforço | Nota |
|---|---|---|
| **Arena multi-LLM** (4 modelos, mesma partida) | +1 fim de semana | Jogo suporta 4 companhias humanas nativamente; harness detecta "fase de qual jogador" e troca o modelo ativo. Estatisticamente mais fraco (interferência), forte como conteúdo |
| **Hard mode raw** (pixels+controller) | +1-2 fins de semana | Segunda trilha; mede computer-use |
| **Publicação** | variável | Blogpost + repo do harness (bring-your-own-ROM, precedente VideoGameBench; zero assets da Koei no repo) |
| **Wiki** | 30 min | Criar entity `aerobiz-evals`, linkar [[ai-evals]] e [[strategy-lab]], registrar como estudo §N |

---

## Custos e Cronograma

| Fase | Calendário (ritmo fim de semana) | API |
|---|---|---|
| F0 | esta semana (2 noites) | ~US$5 |
| F1 | +2 fins de semana | ~US$20-50 (runs de teste) |
| F2 | +2-3 fins de semana | ~US$200-800 (4 modelos × 5 seeds) |
| **Total até F2** | **~6 semanas corridas** | **~US$250-850** |

## Riscos Operacionais (condensado — análise completa em VIABILIDADE §9)

| Risco | Resposta operacional |
|---|---|
| Macro quebra em tela inesperada (evento popup) | Detector de tela desconhecida → screenshot → vision classifica → handler genérico "apertar A p/ dispensar" + log |
| RNG não dessincroniza com jitter | Alternativa: seeds = pontos de início diferentes (savestates após 1º turno jogado de formas distintas) |
| Contexto estoura em 80 turnos | Diário com cap + resumo anual obrigatório; se ainda estourar, vira achado (limite de coerência do modelo) |
| Custo de vision explode | Reduzir a 1 screenshot composto/turno; RAM cobre os escalares |
