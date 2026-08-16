# ============================================================
# cirurgias.py - Produção Cirúrgica (busca + agregação)
# ============================================================

from database import executar
from queries_cirurgias import SQL_PRODUCAO_CIRURGICA, SQL_EQUIPE_CIRURGICA


def get_producao_cirurgica(data_ini: str, data_fim: str, cods_sus: list[str] = None) -> list[dict]:
    """
    Busca a produção cirúrgica do período no MaxDB.
    Retorna uma lista de dicionários, um por cirurgia.
    """
    df = executar(SQL_PRODUCAO_CIRURGICA(data_ini, data_fim, cods_sus))
    if df.empty:
        return []
    return df.to_dict("records")


def get_equipe_cirurgica(data_ini: str, data_fim: str) -> dict:
    """
    Busca a equipe cirúrgica do período e agrupa por cirurgia.
    Retorna: {(serie, numero): [ {funcao, nome, crm}, ... ]}
    """
    df = executar(SQL_EQUIPE_CIRURGICA(data_ini, data_fim))
    if df.empty:
        return {}

    equipe = {}
    for _, linha in df.iterrows():
        chave = (linha["cirurgia_serie"], linha["cirurgia_numero"])
        equipe.setdefault(chave, []).append({
            "funcao": linha["equipe_funcao_codigo"],
            "nome":   linha["equipe_membro_nome"],
            "crm":    linha["equipe_membro_crm"],
        })
    return equipe

def get_producao_completa(data_ini: str, data_fim: str, cods_sus: list[str] = None) -> list[dict]:
    """
    Junta produção cirúrgica + equipe cirúrgica num único resultado.
    Cada cirurgia ganha uma chave "equipe" com a lista de participantes.
    """
    cirurgias = get_producao_cirurgica(data_ini, data_fim, cods_sus)
    equipe_por_cirurgia = get_equipe_cirurgica(data_ini, data_fim)

    for cirurgia in cirurgias:
        chave = (cirurgia["cirurgia_serie"], cirurgia["cirurgia_numero"])
        cirurgia["equipe"] = equipe_por_cirurgia.get(chave, [])

    return cirurgias

def agrupar_por_campo(cirurgias: list[dict], campo: str) -> dict:
    """
    Conta quantas cirurgias existem por valor de um campo
    (ex: "cirurgião_nome", "cirurgia_porte", "cirurgiao_especialidade_cbo").
    Retorna {valor: quantidade}, ordenado do maior para o menor.
    """
    contagem = {}
    for cirurgia in cirurgias:
        valor = cirurgia.get(campo) or "Não informado"
        contagem[valor] = contagem.get(valor, 0) + 1

    return dict(sorted(contagem.items(), key=lambda item: item[1], reverse=True))