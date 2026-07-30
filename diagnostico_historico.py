# Compara JSON salvo vs query v2 para datas específicas
from datetime import date
from ocupacao_v2 import carregar_ocupacao_dia, get_ocupacao_dia

datas = [
    date(2026, 7, 2),
    date(2026, 7, 3),
    date(2026, 7, 4),
]

print(f"\n{'='*65}")
print(f"  Comparação: JSON salvo vs Query v2")
print(f"{'='*65}\n")

for dia in datas:
    json_dados = carregar_ocupacao_dia(dia)
    banco_dados = get_ocupacao_dia(dia)

    # Clínica Médica
    cod_cm = next((c for c, d in json_dados.items() if "CLINICA MEDICA" == d.get("setor","") and "EXTRA" not in d.get("setor","")), None)
    cod_cm_b = next((c for c, d in banco_dados.items() if "CLINICA MEDICA" == d.get("setor","") and "EXTRA" not in d.get("setor","")), None)

    ocup_json  = json_dados.get(cod_cm, {}).get("ocupados", "N/A") if cod_cm else "N/A"
    ocup_banco = banco_dados.get(cod_cm_b, {}).get("ocupados", "N/A") if cod_cm_b else "N/A"

    print(f"  {dia.strftime('%d/%m/%Y')}  JSON={ocup_json}  BANCO={ocup_banco}  {'✓' if ocup_json==ocup_banco else '✗ DIFERENTE'}")

print(f"\n  Conclusão: JSONs antigos precisam ser recriados com query v2")
print(f"{'='*65}\n")
