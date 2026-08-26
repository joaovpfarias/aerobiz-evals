# ETAPA 5c - Instruções de Execução Finais

## Status Atual

**Piloto em progresso:** `etapa5c_pilot.py` (Região AF, 7 cidades)

- Teste: Valida que o harness consegue ler 7 cidades completas sem erros
- Critério de sucesso: cash estável + name_hashes distintos + zero falhas
- ETA: 7 minutos

## Se o Piloto PASSAR ✓

Executar a varredura completa em background (NÃO interromper):

```bash
cd harness
python etapa5c_varredura.py > ../logs/etapa5c/varredura.log 2>&1 &
```

Monitorar progresso (em outra janela):

```bash
tail -f ../logs/etapa5c/varredura.log | grep "^\[" | head -20
```

Ou apenas a cada 10 cidades:

```bash
tail -f ../logs/etapa5c/varredura.log | grep "^\[.*0\]" 
```

## Se o Piloto FALHAR ✗

Causas possíveis e como investigar:

### Erro: `UnicodeEncodeError` ou caracteres garbled
**Solução:** Já foi corrigido. Se reaparecer, rodar com `PYTHONIOENCODING=utf-8`:
```bash
PYTHONIOENCODING=utf-8 python etapa5c_pilot.py
```

### Erro: `BridgeError: timeout...`
**Causa:** Emulador não responde ou não está rodando com bridge.lua  
**Solução:**
```
1. Verificar se BizHawk está aberto
2. Verificar se o script está usando bridge.lua (--lua=bridge.lua)
3. Se necessário, reiniciar BizHawk e recarregar o savestate
```

### Erro: `ABORTO: caixa caiu`
**Causa:** Uma das As de navegação consumiu cash  
**Solução:** Investigar qual A causou. Se for consistente, pode ser problema do savestate.

### Erro: `Guard on_city_panel recusou`
**Causa:** OCR do painel falhou (digito novo ou fora do atlas)  
**Solução:**
```bash
# Verificar o PNG capturado em logs/etapa5c/AF0X_panel.png
# Se houver caractere fora do atlas, rodar harvest_glyphs.py
python harvest_glyphs.py AF01  # exemplo
# Adicionar glifo novo ao glyphs.json
# Re-executar piloto
```

### Erro: `B não devolveu ao mapa`
**Causa:** Painel não fechou corretamente após B  
**Solução:** Pode ser variação aleatória do jogo. Re-executar piloto.

## Após Sucesso do Piloto

### Passo 1: Iniciar Varredura
```bash
cd harness
python etapa5c_varredura.py > ../logs/etapa5c/varredura.log 2>&1 &
```

### Passo 2: Acompanhar (paralelo)
```bash
# Terminal 2
watch -n 5 "tail -5 ../logs/etapa5c/varredura.log"
```

### Passo 3: Aguardar (90 minutos)
A varredura salva `city_intel.json` incrementalmente a cada cidade, então é seguro interromper e retomar se necessário.

### Passo 4: Verificar Resultado
```bash
# Contar cidades processadas
jq 'length' harness/city_intel.json

# Ver metadados
cat ../logs/etapa5c/varredura_metadata.json | jq '.scanned, .total, .missing | length'
```

### Passo 5: Gerar Sumário
```bash
python harness/etapa5c_summarize.py
cat ../logs/etapa5c/SUMARIO.md
```

## Arquivo de Saída

### `harness/city_intel.json`
```json
{
  "NA01": {
    "pos": [256, 24],
    "region": 0,
    "cursor_verificado": true,
    "cash_before": 1220000,
    "cash_after": 1220000,
    "cash_delta": 0,
    "name_ocr": "Washington D.C.",
    "name_hash": "d8c92e23",
    "pop_m": 0.6,
    "econ": 42,
    "trsm": 45,
    "slots_used": 3,
    "slots_cap": 34,
    ...
  },
  ...96 cidades total
}
```

### `logs/etapa5c/varredura_metadata.json`
```json
{
  "timestamp": "2026-08-24 10:08:00",
  "scanned": 96,
  "total": 96,
  "missing": [],
  "failed_reads": [],
  "cash_init": 1220000,
  "cash_final": 1219000,
  "cash_delta": -1000,
  "duplicates_name_hash": [],
  "none_counts": {
    "digito_8": 5
  }
}
```

## Checklist de Validação Pós-Varredura

- [ ] `scanned == 96` (cobertura 100%)
- [ ] `missing == []` (nenhuma cidade deixada de fora)
- [ ] `failed_reads == []` (sem falhas de leitura)
- [ ] `duplicates_name_hash == []` (navegação correta)
- [ ] `abs(cash_delta) < 50000` (cash estável)
- [ ] Todos os screenshots salvos: `ls logs/etapa5c/*_panel.png | wc -l` = 96
- [ ] Nenhum campo crítico com None > 10% (se houver, rodar harvest_glyphs.py)

## Referências

- **CALIBRATION.md §34:** Documentação do `read_city_panel`
- **prova_city_panel_vivo.py:** Padrão de navegação (3/3 com cash estável)
- **ETAPA5c_README.md:** Guia técnico completo da etapa
- **ETAPA5c_STATUS.md:** Timeline e status de conclusão

## Próximas Etapas

Após conclusão da varredura:

1. **ETAPA 6a:** Análise de Hub (quais cidades têm subs/hubs)
2. **ETAPA 6b:** Mapeamento de Slots (rotas e capacidade)
3. **ETAPA 7:** Integração no estado do modelo (pilot.py)
