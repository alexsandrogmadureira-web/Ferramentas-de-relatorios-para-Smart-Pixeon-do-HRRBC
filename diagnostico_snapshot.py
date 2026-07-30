# ============================================================
# diagnostico_snapshot.py
# Compara o snapshot do nosso programa com o relatório do sistema
# Execute: python diagnostico_snapshot.py 2026-07-16 23:59:59
# ============================================================

import sys
from database import executar

if len(sys.argv) >= 2:
    data_hora = " ".join(sys.argv[1:])
else:
    data_hora = "2026-07-16 23:59:59"

print(f"\n{'='*65}")
print(f"  Snapshot: {data_hora}")
print(f"{'='*65}\n")

# Query exata do relatório interno do sistema
sql_sistema = f"""
SELECT
    str.str_nome                    AS unidade,
    COUNT(DISTINCT lto.lto_loc_cod) AS ocupados
FROM hsp, cfg, loc, str, cle, lto
WHERE hsp.hsp_pac    = lto.lto_pac_reg
  AND hsp.hsp_num    = lto.lto_hsp_num
  AND lto.lto_loc_cod = loc.loc_cod
  AND loc.loc_str    = str.str_cod
  AND cle.cle_cod    = loc.loc_cle_cod
  AND cle.cle_tipo   = 'L'
  AND hsp.hsp_stat   = 'A'
  AND lto.lto_dthr_ini = lto.lto_dthr_fim
  AND lto.lto_dthr_ini <= '{data_hora}'
GROUP BY str.str_nome

UNION

SELECT
    str.str_nome                    AS unidade,
    COUNT(DISTINCT lto.lto_loc_cod) AS ocupados
FROM hsp, cfg, loc, str, cle, lto
WHERE hsp.hsp_pac    = lto.lto_pac_reg
  AND hsp.hsp_num    = lto.lto_hsp_num
  AND lto.lto_loc_cod = loc.loc_cod
  AND loc.loc_str    = str.str_cod
  AND cle.cle_cod    = loc.loc_cle_cod
  AND cle.cle_tipo   = 'L'
  AND lto.lto_dthr_ini <= '{data_hora}'
  AND lto.lto_dthr_fim >= '{data_hora}'
  AND lto.lto_dthr_ini <> lto.lto_dthr_fim
GROUP BY str.str_nome
"""

# Nossa query atual
sql_nosso = f"""
SELECT
    str.str_cod                         AS str_cod,
    str.str_nome                        AS unidade,
    COUNT(DISTINCT lto.lto_loc_cod)     AS ocupados
FROM hsp
JOIN lto ON hsp.hsp_pac = lto.lto_pac_reg
        AND hsp.hsp_num = lto.lto_hsp_num
JOIN loc ON lto.lto_loc_cod = loc.loc_cod
JOIN str ON loc.loc_str     = str.str_cod
JOIN cle ON cle.cle_cod     = loc.loc_cle_cod
WHERE cle.cle_tipo      = 'L'
  AND hsp.hsp_stat      = 'A'
  AND lto.lto_dthr_ini  = lto.lto_dthr_fim
  AND lto.lto_dthr_ini <= '{data_hora}'
GROUP BY str.str_cod, str.str_nome

UNION

SELECT
    str.str_cod                         AS str_cod,
    str.str_nome                        AS unidade,
    COUNT(DISTINCT lto.lto_loc_cod)     AS ocupados
FROM hsp
JOIN lto ON hsp.hsp_pac = lto.lto_pac_reg
        AND hsp.hsp_num = lto.lto_hsp_num
JOIN loc ON lto.lto_loc_cod = loc.loc_cod
JOIN str ON loc.loc_str     = str.str_cod
JOIN cle ON cle.cle_cod     = loc.loc_cle_cod
WHERE cle.cle_tipo      = 'L'
  AND lto.lto_dthr_ini <= '{data_hora}'
  AND lto.lto_dthr_fim >= '{data_hora}'
  AND lto.lto_dthr_ini <> lto.lto_dthr_fim
GROUP BY str.str_cod, str.str_nome
"""

df_sis  = executar(sql_sistema)
df_nos  = executar(sql_nosso)

# Monta mapas
sis = {}
if not df_sis.empty:
    for _, r in df_sis.iterrows():
        nome = str(r["unidade"]).strip().upper()
        sis[nome] = sis.get(nome, 0) + int(r["ocupados"])

nos = {}
if not df_nos.empty:
    for _, r in df_nos.iterrows():
        nome = str(r["unidade"]).strip().upper()
        nos[nome] = nos.get(nome, 0) + int(r["ocupados"])

todas = sorted(set(list(sis.keys()) + list(nos.keys())))

print(f"  {'UNIDADE':<42} {'SISTEMA':>8} {'NOSSO':>8} {'DIFF':>6}")
print(f"  {'-'*42} {'-'*8} {'-'*8} {'-'*6}")
diffs = 0
for nome in todas:
    v_sis = sis.get(nome, 0)
    v_nos = nos.get(nome, 0)
    diff  = v_nos - v_sis
    flag  = " ⚠" if diff != 0 else ""
    if diff != 0: diffs += 1
    print(f"  {nome:<42} {v_sis:>8} {v_nos:>8} {diff:>+6}{flag}")

print(f"\n  {diffs} diferença(s) encontrada(s)")
print(f"{'='*65}\n")
