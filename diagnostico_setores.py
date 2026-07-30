# Investiga os setores 1J, 1R, 1S
from database import executar

codigos = ("'1J'", "'1R'", "'1S'")
filtro  = ", ".join(codigos)

sql = f"""
SELECT
    s.str_cod,
    s.str_nome,
    s.str_status,
    s.str_tipo_atende,
    COUNT(l.loc_cod) AS total_leitos
FROM str s
LEFT JOIN loc l ON l.loc_str = s.str_cod
LEFT JOIN cle c ON c.cle_cod = l.loc_cle_cod AND c.cle_tipo = 'L'
WHERE s.str_cod IN ({filtro})
GROUP BY s.str_cod, s.str_nome, s.str_status, s.str_tipo_atende
"""

df = executar(sql)
print(f"\n{'='*70}")
print("  Investigação dos setores 1J, 1R, 1S")
print(f"{'='*70}\n")
if df.empty:
    print("  Nenhum resultado encontrado.")
else:
    for _, r in df.iterrows():
        print(f"  Código:         {r['str_cod']}")
        print(f"  Nome:           {r['str_nome']}")
        print(f"  Status:         {r['str_status']}  (esperado: A)")
        print(f"  Tipo Atende:    {r['str_tipo_atende']}  (esperado: I, H ou R)")
        print(f"  Leitos (cle=L): {r['total_leitos']}")
        print()
print(f"{'='*70}\n")
