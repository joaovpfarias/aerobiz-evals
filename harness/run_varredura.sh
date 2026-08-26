#!/bin/bash
# Script executor para ETAPA 5c - Varredura completa de 96 cidades
# Roda piloto (AF 7 cidades) e, se passar, executa varredura completa

cd "$(dirname "$0")"
PYTHON="python"
LOGDIR="../logs/etapa5c"
mkdir -p "$LOGDIR"

# 1. Executar piloto
echo "=== ETAPA 5c PILOTO - Região AF ==="
echo "Iniciando em $(date)"
$PYTHON etapa5c_pilot.py > "$LOGDIR/pilot.log" 2>&1
PILOT_EXIT=$?

if [ $PILOT_EXIT -ne 0 ]; then
    echo "❌ PILOTO FALHOU (exit $PILOT_EXIT)"
    echo "   Verifique $LOGDIR/pilot.log"
    exit 1
fi

echo "✓ Piloto passou!"
echo ""

# 2. Executar varredura completa
echo "=== ETAPA 5c VARREDURA COMPLETA ==="
echo "Iniciando em $(date)"
echo "ETA: ~90 minutos (96 cidades × ~1 min)"
$PYTHON etapa5c_varredura.py > "$LOGDIR/varredura.log" 2>&1
VARREDURA_EXIT=$?

if [ $VARREDURA_EXIT -ne 0 ]; then
    echo "❌ Varredura terminou com erro (exit $VARREDURA_EXIT)"
    exit 1
fi

echo "✓ Varredura completa!"
echo ""
echo "Resultados em:"
echo "  - city_intel.json"
echo "  - $LOGDIR/varredura_metadata.json"
echo "  - $LOGDIR/*_panel.png"
