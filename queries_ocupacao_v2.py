# ============================================================
# queries_ocupacao_v2.py - Queries de Ocupação de Leitos
# Desenvolvidas e validadas contra o relatório nativo do
# sistema Pixeon SMART (comparação feita em 24/07/2026).
# ============================================================
#
# REGRAS IMPORTANTES (documentadas no arquivo taxa_ocupacao_leitos.sql):
#
#   - Leito real: cle_tipo = 'L'  (exclui salas, consultórios, etc.)
#   - Leito ativo: loc_del_logica <> 'S' E loc_status <> 'I'
#   - Setor ativo: str_status = 'A' E str_tipo_atende IN ('I','H','R')
#   - Ocupação em curso: lto_dthr_ini = lto_dthr_fim AND hsp_stat = 'A'
#   - Ocupação histórica: lto_dthr_ini <> lto_dthr_fim AND
#                         lto_dthr_ini <= instante AND
#                         lto_dthr_fim >= instante
#
# O Python faz a agregação (COUNT, percentual) — as queries
# retornam dados brutos (uma linha por leito).
# ============================================================


def SQL_LEITOS_ATIVOS() -> str:
    """
    Query 1 — Lista mestre de leitos ativos por setor.
    Substitui o LEITOS_CAPACIDADE estático do config.py.
    Retorna uma linha por leito (loc_cod).
    Python agrega: COUNT(loc_cod) por str_cod = capacidade instalada.
    """
    return """
SELECT
    s.str_cod,
    s.str_nome,
    l.loc_cod,
    l.loc_status
FROM str s
INNER JOIN loc l
        ON l.loc_str = s.str_cod
INNER JOIN cle c
        ON c.cle_cod = l.loc_cle_cod
WHERE s.str_status       = 'A'
  AND s.str_tipo_atende  IN ('I', 'H', 'R')
  AND c.cle_tipo         = 'L'
  AND (l.loc_del_logica IS NULL OR l.loc_del_logica <> 'S')
  AND l.loc_status       <> 'I'
ORDER BY s.str_nome, l.loc_cod
"""


def SQL_OCUPACAO_INSTANTE(data_hora: str) -> str:
    """
    Query 3 — Leitos ocupados em um instante específico.
    Retorna uma linha por leito ocupado (str_cod + loc_cod).
    Python agrega: COUNT(loc_cod) por str_cod = ocupados no instante.

    Cobre dois cenários (lógica do relatório nativo Pixeon SMART):
      Bloco 1: ocupação em curso
               lto_dthr_ini = lto_dthr_fim AND hsp_stat = 'A'
               AND lto_dthr_ini <= instante
      Bloco 2: ocupação já encerrada mas ativa no instante consultado
               lto_dthr_ini <> lto_dthr_fim
               AND lto_dthr_ini <= instante
               AND lto_dthr_fim >= instante

    Args:
        data_hora: 'AAAA-MM-DD HH:MM:SS'
                   Ex: '2026-07-23 23:59:59' para censo do dia 23/07
    """
    return f"""
SELECT DISTINCT
    l.loc_str       AS str_cod,
    lt.lto_loc_cod  AS loc_cod
FROM lto lt
INNER JOIN loc l
        ON l.loc_cod = lt.lto_loc_cod
INNER JOIN cle c
        ON c.cle_cod = l.loc_cle_cod
INNER JOIN hsp h
        ON h.hsp_pac = lt.lto_pac_reg
       AND h.hsp_num = lt.lto_hsp_num
WHERE c.cle_tipo       = 'L'
  AND h.hsp_trat_int   = 'I'
  AND (l.loc_del_logica IS NULL OR l.loc_del_logica <> 'S')
  AND (
        ( lt.lto_dthr_ini  = lt.lto_dthr_fim
          AND h.hsp_stat   = 'A'
          AND lt.lto_dthr_ini <= '{data_hora}' )
        OR
        ( lt.lto_dthr_ini <> lt.lto_dthr_fim
          AND lt.lto_dthr_ini <= '{data_hora}'
          AND lt.lto_dthr_fim >= '{data_hora}' )
      )
"""
