# ============================================================
# diagnostico_fluxo_v2.py - Valida queries v2 vs relatório
# Execute: python diagnostico_fluxo_v2.py
#          python diagnostico_fluxo_v2.py 2026-07-18
# ============================================================

import sys
from datetime import date, datetime, timedelta
from fluxo_v2 import get_fluxo_dia

if len(sys.argv) >= 2:
    ref = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
else:
    ref = date.today()

ontem = ref - timedelta(days=1)

print(f"\n{'='*75}")
print(f"  BID de {ontem.strftime('%d/%m/%Y')} — gerado em {ref.strftime('%d/%m/%Y')}")
print(f"{'='*75}\n")

dados = get_fluxo_dia(ref)

colunas = [
    ("ocupacao_inicial",     "Ocup.Ini"),
    ("admissao",             "Admis."),
    ("transferencia_entrada","Tr.Ent."),
    ("transferencia_saida",  "Tr.Saí."),
    ("alta_medica",          "Altas"),
    ("transferencia_externa","Tr.Ext."),
    ("evasao",               "Evas."),
    ("obito",                "Óbito"),
    ("ocupacao_final",       "Ocup.Fin"),
]

# Cabeçalho
print(f"  {'SETOR':<42}", end="")
for _, label in colunas:
    print(f" {label:>8}", end="")
print()
print(f"  {'-'*42}", end="")
for _ in colunas:
    print(f" {'--------':>8}", end="")
print()

# Totais
totais = {k: 0 for k, _ in colunas}

for cod, d in sorted(dados.items(), key=lambda x: x[1]["setor"]):
    print(f"  {d['setor'][:42]:<42}", end="")
    for chave, _ in colunas:
        val = d.get(chave, 0)
        totais[chave] += val
        print(f" {val:>8}", end="")
    print()

# Linha de totais
print(f"\n  {'TOTAL':<42}", end="")
for chave, _ in colunas:
    print(f" {totais[chave]:>8}", end="")
print()

print(f"\n{'='*75}")
print(f"  {len(dados)} setores encontrados")
print(f"{'='*75}\n")
