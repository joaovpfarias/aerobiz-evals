# ETAPA 5c - Varredura de Cidades

**Status:** EM PROGRESSO (piloto rodando, varredura pronta)

**Objetivo:** Varrer todas as 96 cidades do mapa e cachear os dados do painel de negociação em JSON.

**Padrão:** Reutiliza o loop provado de `prova_city_panel_vivo.py` que passou com 3/3 cidades e cash estável.

## Estrutura

### Scripts

- **`etapa5c_pilot.py`**: Piloto com 7 cidades da Região AF
  - Valida cash estável, name_hash distintos, nenhuma falha
  - Deve passar em ~7 minutos antes de rodar a varredura completa
  - Saída: `logs/etapa5c/pilot.log`

- **`etapa5c_varredura.py`**: Varredura de todas as 96 cidades
  - Reutiliza `point_cursor_at_world` de `world.py` (não `_select_city`)
  - Mede cash **antes e depois de CADA A** (R2)
  - Volta ao mapa com **B**, não ao menu (economiza toques)
  - Armazena `cursor_verificado` de cada city (R4)
  - Verifica distinctness de `name_hash` ao final
  - ETA: ~90 minutos (1 min/city)
  - Saída: `city_intel.json` + `logs/etapa5c/varredura_metadata.json`

- **`run_varredura.sh`**: Executor que roda piloto → varredura

### Dados

**Entrada:**
- Savestate: `states/_e3b_base.state` (padrão, pré-calibrado)
- ROM: `roms/Aerobiz Supersonic (USA).sfc`

**Saída:**
- `city_intel.json`: Dict `{cid: {pos, region, cursor_verificado, cash_before/after, panel_data, ...}}`
- `logs/etapa5c/varredura_metadata.json`: Metadados (coverage, failed_reads, duplicates, none_counts)
- `logs/etapa5c/{cid}_panel.png`: Screenshot do painel de cada cidade (para auditoria)

## Regras de Execução

### R1: Campo Ausente
- Glifo fora do atlas → `None` (não palpite)
- Digito `8` falta do mini-atlas (7px) → qualquer campo com 8 vira `None`
- Reportar `none_counts` por campo no metadados

### R2: Sentinelas de Caixa
- Lê caixa **antes e depois de CADA A** (não apenas início/fim)
- **ABORTA se caixa cair** entre dois As
- Volta ao mapa com B (não dismiss_to_menu) entre cidades
- Cash deve ficar estável ao longo de toda a varredura

### R3: Identidade das Companhias
- Não assume quem somos (companhia do jogador escolhida na partida)
- Lê de volta da tela via `read_our_company()`
- Armazena `ours` (cor: "carmim") do painel de cada cidade

### R4: Prova = Leitura, não Retorno
- Armazena `cursor_verificado` de `point_cursor_at_world` (prova de acerto de navegação)
- Armazena `name_hash` de cada city (permite verificar que painel é da cidade certa)
- Verifica **distinctness**: 96 cidades → 96 name_hashes únicos (duplicatas = erro de navegação)

### R5: Resultado Negativo Documentado
- `failed_reads`: cidades com guard recusado ou exceção
- `missing`: cidades não varridas (timeout ou break por cash)
- Se não couber todas 96 no tempo, **REGISTRE explicitamente quais ficaram de fora**

## Navegação (custos em toques)

Segundo §33.3:

- **Setup por entrada no fluxo:** 12 toques (fixa)
- **Por city:** 9 toques (posiciona cursor, aperta A, volta com B)
- **Ordem alfabética (sorted):** agrupa por região → reduz toques de R (troca de continente)

**Estimativa:**
- 7 cidades (piloto): ~100 toques ≈ 7 minutos
- 96 cidades (varredura): ~900 toques ≈ 90 minutos

## Execução

### Piloto (VALIDAÇÃO)

```bash
cd harness
python etapa5c_pilot.py
```

Saída esperada:
```
✓ Piloto passou - pronto para varredura completa!
```

Critério: 7/7 cidades lidas, cash estável, name_hashes distintos, sem None em campos críticos.

### Varredura Completa (BACKGROUND)

```bash
bash run_varredura.sh
```

Ou direto:

```bash
python etapa5c_varredura.py
```

### Monitorar Progresso

```bash
tail -f logs/etapa5c/varredura.log | grep "^\[" | head -1 && \
  tail -f logs/etapa5c/varredura.log | tail -20
```

## Sinais de Problema

| Sinal | Causa | Ação |
|-------|-------|------|
| `ABORTO: caixa caiu` | Uma cidade deixou o jogo em estado inconsistente | Stop (R2 triggered) |
| `B não devolveu ao mapa` | Script não reconheceu a tela após B | Stop (R4 triggered) |
| `Guard on_city_panel recusou` | OCR do painel falhou ou tela errada | Pula city, continua |
| `Exceção: ...` | Erro ao ler painel ou navegar | Pula city, continua |
| `Duplicatas de name_hash` | Mesma cidade lida 2× ou navegação errou | Parar e revisar |
| `None > 20%` em um campo | Digito falta do atlas | Rodar `harvest_glyphs.py`, adicionar ao atlas |

## Pós-Processamento

Após varredura completa:

1. **Verificar metadados:**
   - Coverage % por região
   - Duplicatas de name_hash (deve ser 0)
   - None counts por campo

2. **Se houve None:**
   - Rodar `harvest_glyphs.py` para glifos novos
   - Adicionar ao `glyphs.json`
   - Re-rodar cidades com None

3. **Gerar análise:**
   - Populações por região
   - Distribuição de slots
   - Relações por país

## Histórico

- **23/08 23:59** - Scripts escritos e validados offline
- **24/08 ~10:00** - Piloto iniciado (AF 7 cidades)
- **24/08 ~11:30** - Varredura completa (96 cidades) se piloto passar

## Referências

- CALIBRATION.md §34 - `read_city_panel` (leitor aprovado)
- prova_city_panel_vivo.py - padrão de navegação (3/3 com cash estável)
- world.py - `point_cursor_at_world`, `read_city_panel`, `on_city_panel`
