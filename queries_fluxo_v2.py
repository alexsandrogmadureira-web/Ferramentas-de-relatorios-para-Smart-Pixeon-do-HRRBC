# ============================================================
# queries_fluxo_v2.py - Queries otimizadas de Fluxo de Leitos
# Baseadas no dicionário de dados do sistema Pixeon SMART
# ============================================================
#
# Tabelas utilizadas (conforme dicionário):
#   LTO  - Reserva/movimentação de leito
#          lto_tipo: A=Admissão, T=Transferência, L=Transf.mesmo setor
#          lto_dthr_ini / lto_dthr_fim: período de ocupação
#   HSP  - Internamento hospitalar
#          hsp_stat: A=Aberto, E=Encerrado
#          hsp_tpa: M=Alta Médica, P=A Pedido, A=Adm, E=Evasão, O=Óbito, T=Transferência
#          hsp_trat_int: I=Internação, T=Tratamento Ambulatorial
#          hsp_dthra: data/hora da alta
#   STR  - Setor
#   LOC  - Local/Leito (loc_str = setor, loc_cle_cod = categoria)
#   CLE  - Categoria do leito (cle_tipo: L=Leito, A=Ambulatório, C=Cirurgia)
#   PAC  - Paciente
# ============================================================


def SQL_SNAPSHOT_OCUPACAO(data_hora: str) -> str:
    """
    Snapshot de leitos ocupados por setor em um instante.
    
    Lógica (conforme dicionário):
      - lto_dthr_ini = lto_dthr_fim → internação de 1 dia (mesma data)
      - lto_dthr_ini <> lto_dthr_fim → internação em curso (intervalo)
      - cle_tipo = 'L' → apenas leitos (não ambulatório/cirurgia)
      - hsp_stat = 'A' → apenas internamentos abertos
    
    Args:
        data_hora: 'AAAA-MM-DD HH:MM:SS'
    """
    return f"""
SELECT
    str.str_cod                         AS str_cod,
    str.str_nome                        AS setor,
    COUNT(DISTINCT lto.lto_loc_cod)     AS ocupados
FROM hsp
JOIN lto ON hsp.hsp_pac = lto.lto_pac_reg
        AND hsp.hsp_num = lto.lto_hsp_num
JOIN loc ON lto.lto_loc_cod  = loc.loc_cod
JOIN str ON loc.loc_str      = str.str_cod
JOIN cle ON cle.cle_cod      = loc.loc_cle_cod
WHERE cle.cle_tipo      = 'L'
  AND hsp.hsp_stat      = 'A'
  AND lto.lto_dthr_ini  = lto.lto_dthr_fim
  AND lto.lto_dthr_ini <= '{data_hora}'
GROUP BY str.str_cod, str.str_nome

UNION

SELECT
    str.str_cod                         AS str_cod,
    str.str_nome                        AS setor,
    COUNT(DISTINCT lto.lto_loc_cod)     AS ocupados
FROM hsp
JOIN lto ON hsp.hsp_pac = lto.lto_pac_reg
        AND hsp.hsp_num = lto.lto_hsp_num
JOIN loc ON lto.lto_loc_cod  = loc.loc_cod
JOIN str ON loc.loc_str      = str.str_cod
JOIN cle ON cle.cle_cod      = loc.loc_cle_cod
WHERE cle.cle_tipo      = 'L'
  AND lto.lto_dthr_ini <= '{data_hora}'
  AND lto.lto_dthr_fim >= '{data_hora}'
  AND lto.lto_dthr_ini <> lto.lto_dthr_fim
GROUP BY str.str_cod, str.str_nome
"""


def SQL_ADMISSOES(data_ini: str, data_fim: str) -> str:
    """
    Admissões diretas no período.
    lto_tipo = 'A' → admissão direta (conforme dicionário)
    """
    return f"""
SELECT
    str.str_cod     AS str_cod,
    str.str_nome    AS setor,
    COUNT(*)        AS quantidade
FROM lto
JOIN loc ON loc.loc_cod  = lto.lto_loc_cod
JOIN str ON str.str_cod  = loc.loc_str
JOIN cle ON cle.cle_cod  = loc.loc_cle_cod
WHERE lto.lto_tipo      = 'A'
  AND cle.cle_tipo      = 'L'
  AND lto.lto_dthr_ini >= '{data_ini}'
  AND lto.lto_dthr_ini <  '{data_fim}'
GROUP BY str.str_cod, str.str_nome
"""


def SQL_TRANSFERENCIAS_INTERNAS(data_ini: str, data_fim: str) -> str:
    """
    Transferências internas entre setores DIFERENTES.
    lto_tipo = 'T' → transferência (conforme dicionário)
    
    Retorna:
      - TRANSFERENCIA_ENTRADA: setor destino recebeu paciente
      - TRANSFERENCIA_SAIDA:   setor origem enviou paciente
    
    O JOIN com lto l_ant garante que pegamos apenas transferências
    entre setores diferentes (s_ant.str_cod <> s_dst.str_cod).
    """
    return f"""
SELECT
    str_dst.str_cod     AS str_cod,
    str_dst.str_nome    AS setor,
    'TRANSFERENCIA_ENTRADA' AS tipo,
    COUNT(*)            AS quantidade
FROM lto l_dst
JOIN loc loc_dst ON loc_dst.loc_cod  = l_dst.lto_loc_cod
JOIN str str_dst ON str_dst.str_cod  = loc_dst.loc_str
JOIN lto l_ant   ON l_ant.lto_pac_reg  = l_dst.lto_pac_reg
                AND l_ant.lto_hsp_num  = l_dst.lto_hsp_num
                AND l_ant.lto_dthr_fim = l_dst.lto_dthr_ini
JOIN loc loc_ant ON loc_ant.loc_cod  = l_ant.lto_loc_cod
JOIN str str_ant ON str_ant.str_cod  = loc_ant.loc_str
WHERE l_dst.lto_tipo     = 'T'
  AND str_ant.str_cod   <> str_dst.str_cod
  AND l_dst.lto_dthr_ini >= '{data_ini}'
  AND l_dst.lto_dthr_ini <  '{data_fim}'
GROUP BY str_dst.str_cod, str_dst.str_nome

UNION ALL

SELECT
    str_ant.str_cod     AS str_cod,
    str_ant.str_nome    AS setor,
    'TRANSFERENCIA_SAIDA' AS tipo,
    COUNT(*)            AS quantidade
FROM lto l_dst
JOIN loc loc_dst ON loc_dst.loc_cod  = l_dst.lto_loc_cod
JOIN str str_dst ON str_dst.str_cod  = loc_dst.loc_str
JOIN lto l_ant   ON l_ant.lto_pac_reg  = l_dst.lto_pac_reg
                AND l_ant.lto_hsp_num  = l_dst.lto_hsp_num
                AND l_ant.lto_dthr_fim = l_dst.lto_dthr_ini
JOIN loc loc_ant ON loc_ant.loc_cod  = l_ant.lto_loc_cod
JOIN str str_ant ON str_ant.str_cod  = loc_ant.loc_str
WHERE l_dst.lto_tipo     = 'T'
  AND str_ant.str_cod   <> str_dst.str_cod
  AND l_dst.lto_dthr_ini >= '{data_ini}'
  AND l_dst.lto_dthr_ini <  '{data_fim}'
GROUP BY str_ant.str_cod, str_ant.str_nome
"""


def SQL_SAIDAS(data_ini: str, data_fim: str) -> str:
    """
    Saídas definitivas por tipo no período.
    
    Conforme dicionário hsp_tpa:
      M = Alta Médica
      P = Alta a Pedido       → agrupado em Alta Médica
      A = Alta Administrativa → agrupado em Alta Médica
      E = Evasão
      O = Óbito
      T = Transferência Externa
      R = Reoperação/SUS      → agrupado em Alta Médica
      N = Permanência/SUS     → agrupado em Alta Médica
    
    hsp_trat_int = 'I' → apenas internações (não ambulatorial)
    lto_dthr_fim = hsp_dthra → último leito do paciente
    """
    return f"""
SELECT
    str.str_cod     AS str_cod,
    str.str_nome    AS setor,
    CASE
        WHEN hsp.hsp_tpa = 'O' THEN 'OBITO'
        WHEN hsp.hsp_tpa = 'E' THEN 'EVASAO'
        WHEN hsp.hsp_tpa = 'T' THEN 'TRANSFERENCIA_EXTERNA'
        ELSE 'ALTA_MEDICA'
    END             AS tipo,
    COUNT(*)        AS quantidade
FROM hsp
JOIN lto ON lto.lto_pac_reg  = hsp.hsp_pac
        AND lto.lto_hsp_num  = hsp.hsp_num
        AND lto.lto_dthr_fim = hsp.hsp_dthra
JOIN loc ON loc.loc_cod      = lto.lto_loc_cod
JOIN str ON str.str_cod      = loc.loc_str
WHERE hsp.hsp_trat_int  = 'I'
  AND hsp.hsp_dthra    >= '{data_ini}'
  AND hsp.hsp_dthra    <  '{data_fim}'
GROUP BY str.str_cod, str.str_nome, hsp.hsp_tpa
"""


def SQL_DETALHAMENTO_SETOR(
    data_ini: str, data_fim: str, str_cod: str
) -> str:
    """
    Lista todos os movimentos de um setor (entradas e saídas).
    Baseado na query original do relatório InfoMaker.
    Usa 4 SELECTs com UNION ALL — um por tipo de movimento.
    """
    return f"""
SELECT
    s_dst.str_nome              AS unidade,
    'ADMISSÃO'                  AS movimento,
    1                           AS ordem_mov,
    p.pac_nome                  AS paciente,
    p.pac_nasc                  AS pac_nasc,
    l.lto_pac_reg               AS reg_paciente,
    l.lto_hsp_num               AS num_internamento,
    'Direta'                    AS detalhe_fluxo,
    l.lto_dthr_ini              AS dthr_movimento,
    h.hsp_dthra                 AS dthr_alta
FROM lto l
INNER JOIN pac p      ON p.pac_reg       = l.lto_pac_reg
INNER JOIN hsp h      ON h.hsp_num       = l.lto_hsp_num AND h.hsp_pac = l.lto_pac_reg
INNER JOIN loc lo_dst ON lo_dst.loc_cod  = l.lto_loc_cod
INNER JOIN str s_dst  ON s_dst.str_cod   = lo_dst.loc_str
WHERE l.lto_dthr_ini >= '{data_ini}'
  AND l.lto_dthr_ini <  '{data_fim}'
  AND l.lto_tipo      = 'A'
  AND s_dst.str_cod   = '{str_cod}'

UNION ALL

SELECT
    s_dst.str_nome              AS unidade,
    'TRANSFERÊNCIA (ENTRADA)'   AS movimento,
    2                           AS ordem_mov,
    p.pac_nome                  AS paciente,
    p.pac_nasc                  AS pac_nasc,
    l.lto_pac_reg               AS reg_paciente,
    l.lto_hsp_num               AS num_internamento,
    'Veio de: ' || s_ant.str_nome       AS detalhe_fluxo,
    l.lto_dthr_ini              AS dthr_movimento,
    h.hsp_dthra                 AS dthr_alta
FROM lto l
INNER JOIN pac p       ON p.pac_reg         = l.lto_pac_reg
INNER JOIN hsp h       ON h.hsp_num         = l.lto_hsp_num AND h.hsp_pac = l.lto_pac_reg
INNER JOIN loc lo_dst  ON lo_dst.loc_cod    = l.lto_loc_cod
INNER JOIN str s_dst   ON s_dst.str_cod     = lo_dst.loc_str
INNER JOIN lto l_ant   ON l_ant.lto_pac_reg = l.lto_pac_reg
                      AND l_ant.lto_hsp_num = l.lto_hsp_num
                      AND l_ant.lto_dthr_fim = l.lto_dthr_ini
INNER JOIN loc lo_ant  ON lo_ant.loc_cod    = l_ant.lto_loc_cod
INNER JOIN str s_ant   ON s_ant.str_cod     = lo_ant.loc_str
WHERE l.lto_dthr_ini >= '{data_ini}'
  AND l.lto_dthr_ini <  '{data_fim}'
  AND l.lto_tipo      = 'T'
  AND s_ant.str_cod  <> s_dst.str_cod
  AND s_dst.str_cod   = '{str_cod}'

UNION ALL

SELECT
    s_ant.str_nome              AS unidade,
    'TRANSFERÊNCIA (SAÍDA)'     AS movimento,
    3                           AS ordem_mov,
    p.pac_nome                  AS paciente,
    p.pac_nasc                  AS pac_nasc,
    l.lto_pac_reg               AS reg_paciente,
    l.lto_hsp_num               AS num_internamento,
    'Foi para: ' || s_dst.str_nome       AS detalhe_fluxo,
    l.lto_dthr_ini              AS dthr_movimento,
    h.hsp_dthra                 AS dthr_alta
FROM lto l
INNER JOIN pac p       ON p.pac_reg         = l.lto_pac_reg
INNER JOIN hsp h       ON h.hsp_num         = l.lto_hsp_num AND h.hsp_pac = l.lto_pac_reg
INNER JOIN loc lo_dst  ON lo_dst.loc_cod    = l.lto_loc_cod
INNER JOIN str s_dst   ON s_dst.str_cod     = lo_dst.loc_str
INNER JOIN lto l_ant   ON l_ant.lto_pac_reg = l.lto_pac_reg
                      AND l_ant.lto_hsp_num = l.lto_hsp_num
                      AND l_ant.lto_dthr_fim = l.lto_dthr_ini
INNER JOIN loc lo_ant  ON lo_ant.loc_cod    = l_ant.lto_loc_cod
INNER JOIN str s_ant   ON s_ant.str_cod     = lo_ant.loc_str
WHERE l.lto_dthr_ini >= '{data_ini}'
  AND l.lto_dthr_ini <  '{data_fim}'
  AND l.lto_tipo      = 'T'
  AND s_ant.str_cod  <> s_dst.str_cod
  AND s_ant.str_cod   = '{str_cod}'

UNION ALL

SELECT
    s_ant.str_nome              AS unidade,
    CASE
        WHEN h.hsp_tpa = 'M' THEN 'ALTA MÉDICA'
        WHEN h.hsp_tpa = 'E' THEN 'EVASÃO'
        WHEN h.hsp_tpa = 'T' THEN 'TRANSFERÊNCIA EXTERNA'
        WHEN h.hsp_tpa = 'O' THEN 'ÓBITO'
        ELSE 'ALTA HOSPITALAR'
    END                         AS movimento,
    4                           AS ordem_mov,
    p.pac_nome                  AS paciente,
    p.pac_nasc                  AS pac_nasc,
    l_ant.lto_pac_reg           AS reg_paciente,
    l_ant.lto_hsp_num           AS num_internamento,
    'Saída Definitiva'          AS detalhe_fluxo,
    h.hsp_dthra                 AS dthr_movimento,
    h.hsp_dthra                 AS dthr_alta
FROM lto l_ant
INNER JOIN pac p       ON p.pac_reg         = l_ant.lto_pac_reg
INNER JOIN hsp h       ON h.hsp_num         = l_ant.lto_hsp_num AND h.hsp_pac = l_ant.lto_pac_reg
INNER JOIN loc lo_ant  ON lo_ant.loc_cod    = l_ant.lto_loc_cod
INNER JOIN str s_ant   ON s_ant.str_cod     = lo_ant.loc_str
WHERE h.hsp_dthra      >= '{data_ini}'
  AND h.hsp_dthra      <  '{data_fim}'
  AND h.hsp_trat_int   = 'I'
  AND l_ant.lto_dthr_fim = h.hsp_dthra
  AND s_ant.str_cod    = '{str_cod}'

ORDER BY dthr_movimento
"""

