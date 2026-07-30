# ============================================================
# queries_ocupacao.py - SQL de ocupação de leitos por clínica
# ============================================================
# Adaptado do relatório interno do sistema (parâmetros
# :a_dthr e :a_sStrCod substituídos por f-string).
#
# O UNION cobre dois cenários:
#   Parte 1 — internações de 1 dia (lto_dthr_ini = lto_dthr_fim)
#   Parte 2 — internações em curso  (ini <= snapshot <= fim)
# ============================================================


def SQL_OCUPACAO_LEITOS(data_hora: str, str_cod: str = "%") -> str:
    """
    Retorna leitos ocupados por clínica no snapshot informado.

    Args:
        data_hora : 'AAAA-MM-DD HH:MM:SS'  ex: '2026-05-26 23:59:59'
        str_cod   : filtro de setor — '%' para todos (padrão)
    """
    return f"""
SELECT
    loc.loc_str                     AS str_cod,
    str.str_nome                    AS clinica,
    COUNT(DISTINCT lto.lto_loc_cod) AS leitos_ocupados
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
  AND loc.loc_str        LIKE '{str_cod}'
GROUP BY loc.loc_str, str.str_nome

UNION

SELECT
    loc.loc_str                     AS str_cod,
    str.str_nome                    AS clinica,
    COUNT(DISTINCT lto.lto_loc_cod) AS leitos_ocupados
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
  AND loc.loc_str        LIKE '{str_cod}'
GROUP BY loc.loc_str, str.str_nome
"""
