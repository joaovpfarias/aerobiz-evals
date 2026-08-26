# ETAPA 6-Reversos — Relatório de Implementação

**Data:** 18/08/2026  
**Status:** Parcialmente concluído (1/3 ações reversas operacionais)

---

## Resumo Executivo

- **return_slots**: ✅ IMPLEMENTADO, VERIFICADO, OPERACIONAL
- **sell_aircraft**: ❌ BLOQUEADO (calibração de hash de painel desatualizada)
- **close_hub**: ❌ BLOQUEADO (requer medição de pixels Open/Close antes da implementação)

---

## Ação 1: return_slots (ACEITO)

### Status
✅ **OPERACIONAL** — adicionada a `pilot.SUPPORTED`

### Descoberta de Bug
**Problema:** Ambos `_do_return_slots` e `_do_sell_aircraft` chamavam `at_main_menu_img(self.b.screenshot())` passando a STRING do caminho, não uma PIL Image.

**Efeito:** 
```
AttributeError: 'str' object has no attribute 'load'
  (chamado do world.menu_red() tentando fazer img.load())
```

**Correção:** Envolver com `Image.open().convert("RGB")` em ambas as funções (commit 6ddabef).

### Verificação de Efeito (Oracle)
1. **Gate de pixel:** `staff_action_is_bid()` verifica que Return (297px) está destacado, não Bid (359px)
   - Crop: celula (1,2) da grade de staff picker
   - RGB esperado para Bid: (198,97,66) laranja — 359px
   - RGB para Return: mesma célula, mas sem o highlight — 297px
2. **Sequência:** Navigate(Down+Right), A (abre mapa), select city, A, confirm YES, volta ao menu
3. **Funcionários livres:** Pode não mudar (gate fraco — apenas conta funcionários base)

### Teste Executado
```bash
prova_return_slots.py com probe_hub_open_sa.state
Resultado: True
Message: "slots devolvidos de SA01: livres 3 -> 3 (+0); Return destacado verificado"
```

### Evidência
- `../logs/return_slots_aceite/return_slots_SA01_mapa.png` — mapa com SA01 selecionada
- `../logs/return_slots_aceite/return_slots_SA01_confirmado.png` — após confirmação

---

## Ação 2: sell_aircraft (BLOQUEADO)

### Status
⚠️ **BLOQUEADO POR CALIBRAÇÃO DESATUALIZADA**

### Implementação
Código completo em `executor._do_sell_aircraft()` — implementado e estruturalmente correto:
1. Navegar para fabricante 2 (World Lease)
2. Confirmar fabricante
3. Validar painel via MD5 hash
4. Definir quantidade (Right = +1, limite 3/visita)
5. Confirmar venda
6. Sair de telas
7. Verificar caixa sobe (oracle de efeito)

### Problema: Hash de Painel Desatualizado
```
Esperado: 8030bace (MD100 conforme AIRCRAFT_CATALOG)
Observado: d9d87bb8 (em eval_single_2000_lv5.state)
```

**Causa Potencial:**
- Calibração original feita em ambiente/resolução diferente
- Mudança no formato de screenshot BizHawk
- Crop box (8, 82, 150, 148) pode precisar re-validação
- Painel em modo SELL (via World Lease) pode ser renderizado diferentemente do modo BUY

### Teste Executado
```bash
prova_sell_aircraft.py com eval_single_2000_lv5.state
Resultado: False
Message: "sell_aircraft: painel na tela e d9d87bb8, esperado 8030bace (modelo MD100)"
```

### Para Desbloquear
Opção A (Recomendado): Re-calibrar todos os 8 modelos de aeronave no ambiente atual
- Carregar eval_single_2000_lv5.state
- Navegar para cada fabricante/modelo
- Medir hash do recorte BUY_PANEL
- Atualizar `AIRCRAFT_CATALOG["panel"]` em world.py

Opção B: Remover gate de painel (PERIGOSO — abre risco de comprar/vender modelo errado sem verificação)

---

## Ação 3: close_hub (NÃO IMPLEMENTADO)

### Status
❌ **BLOQUEADO PELA FALTA DE MEDIÇÃO** (conforme docstring em executor.py:1550–1577)

### Bloqueios Identificados

#### 1. Discriminação Open/Close (CRÍTICO)
O código atual ASSUME navegação "Left move de Open para Close" (analogia com Bid→Return). Porém:
- Não foi verificado contra pixels reais
- Se Left não funciona, A cai em Open → abre hub novo → debita 28.800K → falsamente reporta sucesso

**Necessário:** Ler pixels de Open/Close destacado (§17.1 calibrou Bid/Return com valores específicos, Open/Close podem diferir)

#### 2. Fluxo até Staff Picker (INCERTO)
Código assume `for _ in range(4): _step()` mas `_do_open_hub()` pode usar `_pick_free_staff()` ou outro caminho — não foi lido de verdade antes de escrever.

#### 3. Cascade Risk (REAL)
`probe_hub_open_sa.state` tem rota Washington-Havana saindo do hub SA. Fechar o hub pode deletar a rota silenciosamente.

### Próximos Passos (Se Implementar)
1. Carregar `probe_hub_open_sa.state`
2. Abrir r1c0 (Open/Close hub)
3. Screenshot e medir pixels Open vs Close destacado (RGB, count)
4. Ler `_do_open_hub()` completamente para entender fluxo até staff picker
5. Validar em teste que não deleta rota
6. Adicionar documento de pixel values análogo a §17.1

---

## Evidência Técnica

### Commits
- `6ddabef`: Fix Image.open() wrapper para calls a at_main_menu_img
- `3d5c9ba`: Add return_slots a SUPPORTED

### Testes Deixados em Harness
- `test_return_slots_direct.py` — teste isolado de _do_return_slots
- `diagnose_panel_hash.py` — diagnóstico de panel hash mismatch
- `recalib_panel_hashes.py` — template para re-calibração (requer conclusão manual)

### Logs
- `../logs/return_slots_aceite/` — screenshots de sucesso de return_slots
- `../logs/sell_aircraft_aceite/` — screenshots mostrando panel hash mismatch

---

## Recomendações

### Imediato
1. ✅ **return_slots** está pronto para uso em eval — está em SUPPORTED
2. ⚠️ **sell_aircraft** precisa de re-calibração de panel hashes (tempo: ~30 min manual)
3. ❌ **close_hub** bloqueado estruturalmente — não iniciar sem proof-of-concept de discriminação Open/Close

### Próximos Passos (Prioridade)
1. Re-calibrar panel hashes se sell_aircraft for necessário
2. Se close_hub for usar, fazer probe_pixel_open_close.py análogo a probe_staff_action.py
3. Considerar remover `suspend_route`/`close_route` de schema.py (ambos têm mesmo problema que close_hub)

---

## Notas Adicionais

- EFEITO_CUSTA_CAIXA em executor.py não inclui sell_aircraft (caixa **sobe** em vez de cair) — verifição de efeito é interna ao `_do_sell_aircraft`
- return_slots não debita caixa na hora (slots liberados futuramente); oracle principal é pixel gate
- Nenhuma dessas ações foi incluída em prompt do LLM antes da implementação estar 100% verificada (REGRA de CALIBRATION.md §4)

