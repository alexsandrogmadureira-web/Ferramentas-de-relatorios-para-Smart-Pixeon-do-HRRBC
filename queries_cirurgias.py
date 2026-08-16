# ============================================================
# queries_cirurgias.py - Queries de Produção Cirúrgica
# Base RCI (SAP MaxDB)
# ============================================================


def SQL_PRODUCAO_CIRURGICA(data_ini: str, data_fim: str, cods_sus: list[str] = None) -> str:
    """
    Produção cirúrgica no período, com dados de cirurgia, paciente,
    médicos, convênio, CID e CCIH.

    Args:
        data_ini: 'AAAA-MM-DD HH:MM:SS'
        data_fim: 'AAAA-MM-DD HH:MM:SS'
        cods_sus: lista opcional de códigos SUS para filtrar
                  (ex: ['0408040017', '0408040025']). None = todos.
    """
    filtro_sus = ""
    if cods_sus:
        lista = ",".join(f"'{c}'" for c in cods_sus)
        filtro_sus = f"AND smk.smk_sus_cod_unico IN ({lista})"

    return f"""
SELECT
    rci.rci_serie                       AS cirurgia_serie,
    rci.rci_num                         AS cirurgia_numero,
    rci.rci_dthr_ini                    AS cirurgia_dt_hr_inicio,
    rci.rci_dthr_fim                    AS cirurgia_dt_hr_fim,
    rci.rci_porte                       AS cirurgia_porte,
    rci.rci_ind_urg                     AS cirurgia_urgencia_sn,
    smk.smk_nome                        AS procedimento_nome,
    smk.smk_sus_cod_unico               AS codigo_sus,
    psv_cir.psv_nome                    AS cirurgiao_nome,
    psv_cir.psv_esp_cod                 AS cirurgiao_especialidade_cbo,
    cnv.cnv_nome                        AS convenio_nome,
    pac.pac_nome                        AS paciente_nome
FROM rci
    INNER JOIN pac
        ON pac.pac_reg = rci.rci_pac_reg
    LEFT OUTER JOIN psv psv_cir
        ON psv_cir.psv_cod = rci.rci_psv_cod
    LEFT OUTER JOIN smk
        ON smk.smk_tipo = rci.rci_smk_tipo
       AND smk.smk_cod  = rci.rci_smk_cod
    LEFT OUTER JOIN cnv
        ON cnv.cnv_cod = rci.rci_cnv_cod
WHERE
    rci.rci_dthr_ini >= '{data_ini}'
    AND rci.rci_dthr_ini < '{data_fim}'
    {filtro_sus}
ORDER BY
    rci.rci_dthr_ini DESC
"""


def SQL_EQUIPE_CIRURGICA(data_ini: str, data_fim: str) -> str:
    """
    Equipe cirúrgica completa por cirurgia (1 linha por membro).
    Mesmo período da SQL_PRODUCAO_CIRURGICA, para poder cruzar as duas
    pelo par (cirurgia_serie, cirurgia_numero).

    Códigos de eci_funcao:
      C=Cirurgião  1-4=Auxiliares  A=Anestesista  P=Perfusionista
      E=Enfermeira X=Aux. Enfermagem  I=Instrumentador  U=Circulante
      N,O,T,Q,5,6,7=Neonatologista 1-7
    """
    return f"""
SELECT
    rci.rci_serie                       AS cirurgia_serie,
    rci.rci_num                         AS cirurgia_numero,
    eci.eci_funcao                      AS equipe_funcao_codigo,
    psv_eq.psv_nome                     AS equipe_membro_nome,
    psv_eq.psv_crm                      AS equipe_membro_crm
FROM rci
    INNER JOIN eci
        ON eci.eci_rci_serie = rci.rci_serie
       AND eci.eci_rci_num   = rci.rci_num
    LEFT OUTER JOIN psv psv_eq
        ON psv_eq.psv_cod = eci.eci_psv_cod
WHERE
    rci.rci_dthr_ini >= '{data_ini}'
    AND rci.rci_dthr_ini < '{data_fim}'
ORDER BY
    rci.rci_serie, rci.rci_num, eci.eci_funcao
"""