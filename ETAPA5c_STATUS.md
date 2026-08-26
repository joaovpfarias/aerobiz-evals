# ETAPA 5c - STATUS

**Data inicio:** 23/08/2026 ~23:59  
**Status:** 🟡 EM EXECUÇÃO (piloto em progresso)

## O que foi feito

1. **Leitura de CALIBRATION.md §34**: `read_city_panel` validado offline (9/9) e ao vivo (3/3)
2. **Análise de prova_city_panel_vivo.py**: Padrão de navegação aprovado (cash estável)
3. **Consulta ao advisor**: Bloqueios identificados e soluções aplicadas
   - ✓ Reusou loop de prova_city_panel_vivo (não _select_city)
   - ✓ Medição de cash antes/depois de CADA A (não apenas fim)
   - ✓ Volta ao mapa com B (economiza toques)
   - ✓ Armazenamento de cursor_verificado (prova de acerto)
   - ✓ Verificação de distinctness de name_hash (detecta navegação errada)

4. **Scripts criados:**
   - `etapa5c_pilot.py`: Valida com 7 cidades da Região AF
   - `etapa5c_varredura.py`: Varredura de 96 cidades (pronta para background)
   - `etapa5c_summarize.py`: Gera relatório após conclusão
   - `ETAPA5c_README.md`: Documentação completa da etapa

## Execução

### Fase 1: Piloto (AGORA)
- Status: 🟡 EM PROGRESSO
- Comando: `python etapa5c_pilot.py`
- Critério: 7/7 cidades, cash estável, name_hashes distintos
- ETA: 7 minutos
- Saída: `logs/etapa5c/pilot.log`

### Fase 2: Varredura Completa (SE PILOTO PASSAR)
- Status: ⏳ ENFILEIRADA
- Comando: `python etapa5c_varredura.py`
- Cidades: 96 total (todo o mapa)
- ETA: 90 minutos (~1 min/city)
- Saída:
  - `city_intel.json` - dados brutos de cada cidade
  - `logs/etapa5c/varredura_metadata.json` - estatísticas e cobertura
  - `logs/etapa5c/{cid}_panel.png` - screenshots para auditoria

### Fase 3: Sumário (APÓS CONCLUSÃO)
- Comando: `python etapa5c_summarize.py`
- Saída: `logs/etapa5c/SUMARIO.md`

## Riscos Mitigados

| Risco | Mitigation | Status |
|-------|-----------|--------|
| Caixa cair silenciosamente (§28) | Mede antes/depois cada A, ABORTA se cair (R2) | ✓ |
| Cursor errado (navegação) | Armazena cursor_verificado + valida name_hash (R4) | ✓ |
| Duplicatas de hash | Verifica distinctness ao final | ✓ |
| Digito 8 faltando (R1) | Reporta None-per-campo em metadados | ✓ |
| Timeout longo | Pilot primeiro (7 min), depois varredura em background | ✓ |
| Cobertura incompleta | Explicitamente lista missing + failed_reads | ✓ |

## Entrega

Após varredura completa:

**Arquivo principal:** `harness/city_intel.json`
```json
{
  "NA01": {
    "pos": [256, 24],
    "region": 0,
    "cursor_verificado": true,
    "name_ocr": "Washington D.C.",
    "name_hash": "d8c92e23",
    "pop_m": 0.6,
    "econ": 42,
    "trsm": 45,
    "slots_used": 3,
    "slots_cap": 34,
    ...
  },
  ...
}
```

**Metadados:** `logs/etapa5c/varredura_metadata.json`
- coverage: 96/96 (100%)
- missing: []
- failed_reads: []
- duplicates_name_hash: [] (deve estar vazio)
- none_counts: {digito_8_falta?}
- cash_delta: ±5000K (estável)

**Screenshots:** `logs/etapa5c/*_panel.png` (para auditoria)

## Cronograma

- 📍 **23/08 23:59:** Scripts prontos
- 📍 **24/08 ~10:00:** Piloto iniciado
- 🔲 **24/08 ~10:07:** Piloto conclui
- 🔲 **24/08 ~10:08:** Varredura completa inicia (background)
- 🔲 **24/08 ~11:38:** Varredura completa conclui
- 🔲 **24/08 ~11:39:** Sumário gerado

## Checklist de Aceite

- [ ] Piloto: 7/7 cidades, cash estável
- [ ] Piloto: name_hashes distintivos (7 únicos)
- [ ] Piloto: zero falhas de leitura
- [ ] Varredura: 96/96 cidades, 100% coverage
- [ ] Varredura: cash delta < 50000K
- [ ] Varredura: zero duplicatas de name_hash
- [ ] Varredura: cursor_verificado = true para todas
- [ ] city_intel.json: todos os campos preenchidos (exceto None legítimos)
- [ ] Metadados: missing=[], failed_reads=[]
- [ ] Screenshots: 96 arquivos, um por cidade

---

**Próximas etapas:** Análise de relacionamentos, identificação de hubs, mapa de slots por região.
