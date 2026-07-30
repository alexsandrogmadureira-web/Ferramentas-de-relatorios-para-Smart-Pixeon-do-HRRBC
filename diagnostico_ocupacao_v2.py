# ============================================================
# diagnostico_ocupacao_v2.py - Valida queries de ocupação v2
# Execute: python diagnostico_ocupacao_v2.py
#          python diagnostico_ocupacao_v2.py 2026-07-24 23:59:59
# ============================================================

import sys
from datetime import date, datetime
from ocupacao_v2 import get_leitos_ativos, get_ocupados_instante, get_ocupacao_dia

if len(sys.argv) >= 2:
    data_hora = " ".join(sys.argv[1:])
    dia = datetime.strptime(data_hora[:10], "%Y-%m-%d").date()
else:
    dia = date.today()
    data_hora = dia.strftime("%Y-%m-%d 23:59:59")

print(f"\n{'='*65}")
print(f"  Diagnóstico Ocupação v2 — {data_hora}")
print(f"{'='*65}\n")

# Capacidade
print(">>> Query 1 — Leitos Ativos (capacidade instalada)\n")
leitos = get_leitos_ativos()
total_cap = sum(d["capacidade"] for d in leitos.values())
print(f"  {'SETOR':<42} {'CAP':>5}")
print(f"  {'-'*42} {'-----':>5}")
for cod, d in sorted(leitos.items(), key=lambda x: x[1]["setor"]):
    print(f"  {d['setor']:<42} {d['capacidade']:>5}")
print(f"  {'TOTAL':<42} {total_cap:>5}")

# Ocupados
print(f"\n>>> Query 3 — Ocupados em {data_hora}\n")
ocupados = get_ocupados_instante(data_hora)
total_ocup = sum(len(v) for v in ocupados.values())

# Cruzamento
print(f"  {'SETOR':<42} {'CAP':>5} {'OCUP':>5} {'LIVRE':>6} {'TAXA':>7}")
print(f"  {'-'*42} {'-----':>5} {'-----':>5} {'------':>6} {'-------':>7}")

resultado = get_ocupacao_dia(dia)
for cod, d in sorted(resultado.items(), key=lambda x: x[1]["setor"]):
    taxa_str = f"{d['taxa']}%"
    print(f"  {d['setor']:<42} {d['capacidade']:>5} {d['ocupados']:>5} {d['livres']:>6} {taxa_str:>7}")

total_ocup2 = sum(d["ocupados"] for d in resultado.values())
taxa_geral  = round(total_ocup2 / total_cap * 100, 1) if total_cap else 0
print(f"\n  {'TOTAL GERAL':<42} {total_cap:>5} {total_ocup2:>5} {total_cap-total_ocup2:>6} {taxa_geral:>6}%")
print(f"\n{'='*65}\n")
