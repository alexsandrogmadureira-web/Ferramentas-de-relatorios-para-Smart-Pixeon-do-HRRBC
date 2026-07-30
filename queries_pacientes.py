# ============================================================
# queries_pacientes.py - Queries de Pacientes Internados
# Baseadas nas queries originais do sistema Pixeon SMART
# ============================================================


def SQL_PACIENTES_ATUAL() -> str:
    """
    Pacientes atualmente internados por setor e leito.
    Baseada na query pacientes_internados_historico_atual.SQL
    Retorna todos os setores (sem filtro de str_cod).
    """
    return """
SELECT
    str.str_cod                     AS str_cod,
    str.str_nome                    AS setor,
    loc.loc_nome                    AS leito,
    loc.loc_status                  AS leito_status,
    loc.loc_cod                     AS loc_cod,
    pac.pac_nome                    AS paciente,
    pac.pac_pront                   AS prontuario,
    hsp.hsp_pac                     AS registro,
    hsp.hsp_num                     AS num_internamento,
    hsp.hsp_dthre                   AS admissao,
    hsp.hsp_cnv                     AS convenio,
    hsp.hsp_tipo                    AS tipo_internacao,
    hsp.hsp_mde                     AS medico_cod,
    psv.psv_apel                    AS medico,
    hsp.hsp_clinc_cir               AS clinica_cir,
    hsp.hsp_cle_cod                 AS categoria
FROM hsp
LEFT JOIN psv ON hsp.hsp_mde = psv.psv_cod,
    loc,
    pac,
    str,
    cfg
WHERE loc.loc_cod    = hsp.hsp_loc
  AND pac.pac_reg    = hsp.hsp_pac
  AND str.str_cod    = loc.loc_str
  AND hsp.hsp_stat   = 'A'
  AND hsp.hsp_trat_int = 'I'
ORDER BY str.str_nome, loc.loc_nome
"""


def SQL_PACIENTES_PERIODO(data_ini: str, data_fim: str) -> str:
    """
    Pacientes que passaram por cada setor em um período.
    Baseada na query pacientes_internados_por_periodo.SQL

    Args:
        data_ini: 'AAAA-MM-DD HH:MM:SS'
        data_fim: 'AAAA-MM-DD HH:MM:SS'
    """
    return f"""
SELECT
    str.str_nome                    AS setor,
    str.str_cod                     AS str_cod,
    pac.pac_nome                    AS paciente,
    pac.pac_pront                   AS prontuario,
    hsp.hsp_pac                     AS registro,
    hsp.hsp_num                     AS num_internamento,
    lto.lto_loc_cod                 AS loc_cod,
    lto.lto_dthr_ini                AS admissao,
    lto.lto_dthr_fim                AS alta,
    hsp.hsp_cnv                     AS convenio
FROM hsp, cfg, pac, loc, str, lto
WHERE hsp.hsp_pac    = pac.pac_reg
  AND hsp.hsp_pac    = lto.lto_pac_reg
  AND hsp.hsp_num    = lto.lto_hsp_num
  AND lto.lto_loc_cod = loc.loc_cod
  AND loc.loc_str    = str.str_cod
  AND hsp.hsp_stat   = 'A'
  AND lto.lto_dthr_ini <= '{data_fim}'
  AND lto.lto_dthr_ini  = lto.lto_dthr_fim

UNION

SELECT
    str.str_nome                    AS setor,
    str.str_cod                     AS str_cod,
    pac.pac_nome                    AS paciente,
    pac.pac_pront                   AS prontuario,
    hsp.hsp_pac                     AS registro,
    hsp.hsp_num                     AS num_internamento,
    lto.lto_loc_cod                 AS loc_cod,
    lto.lto_dthr_ini                AS admissao,
    lto.lto_dthr_fim                AS alta,
    hsp.hsp_cnv                     AS convenio
FROM hsp, cfg, pac, loc, str, lto
WHERE loc.loc_cod    = lto.lto_loc_cod
  AND str.str_cod    = loc.loc_str
  AND hsp.hsp_pac    = pac.pac_reg
  AND hsp.hsp_pac    = lto.lto_pac_reg
  AND hsp.hsp_num    = lto.lto_hsp_num
  AND lto.lto_dthr_ini <= '{data_fim}'
  AND lto.lto_dthr_fim >= '{data_ini}'
  AND lto.lto_dthr_ini <> lto.lto_dthr_fim

ORDER BY setor, admissao
"""
