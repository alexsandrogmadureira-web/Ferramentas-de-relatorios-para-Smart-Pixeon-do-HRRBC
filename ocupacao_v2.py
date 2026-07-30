# ============================================================
# ocupacao_v2.py - Ocupação de Leitos (queries v2 do SMART)
# ============================================================

import json
from datetime import date, timedelta
from pathlib import Path

from database import executar
from queries_ocupacao_v2 import SQL_LEITOS_ATIVOS, SQL_OCUPACAO_INSTANTE

DATA_DIR = Path(__file__).parent / "dados_ocupacao"
DATA_DIR.mkdir(exist_ok=True)


def get_leitos_ativos() -> dict:
    """
    Retorna a lista mestre de leitos ativos por setor.
    {str_cod: {"setor": nome, "leitos": [loc_cod, ...], "capacidade": n}}
    """
    df = executar(SQL_LEITOS_ATIVOS())
    if df.empty:
        return {}

    resultado = {}
    for _, row in df.iterrows():
        cod  = str(row["str_cod"]).strip()
        nome = str(row["str_nome"]).strip().upper()
        loc  = str(row["loc_cod"]).strip()
        resultado.setdefault(cod, {"setor": nome, "leitos": [], "capacidade": 0})
        resultado[cod]["leitos"].append(loc)
        resultado[cod]["capacidade"] = len(resultado[cod]["leitos"])

    return resultado


def get_ocupados_instante(data_hora: str) -> dict:
    """
    Retorna leitos ocupados no instante informado.
    {str_cod: set(loc_cod ocupados)}
    """
    df = executar(SQL_OCUPACAO_INSTANTE(data_hora))
    if df.empty:
        return {}

    resultado = {}
    for _, row in df.iterrows():
        cod = str(row["str_cod"]).strip()
        loc = str(row["loc_cod"]).strip()
        resultado.setdefault(cod, set()).add(loc)

    return resultado


def get_ocupacao_dia(dia: date) -> dict:
    """
    Retorna ocupação completa de um dia (snapshot 23:59:59).
    Cruza Query 1 (capacidade) com Query 3 (ocupados).

    Retorna:
    {
      str_cod: {
        "setor":      "CLINICA MEDICA",
        "capacidade": 30,
        "ocupados":   28,
        "taxa":       93.3,
        "livres":     2,
      }
    }
    """
    data_hora = dia.strftime("%Y-%m-%d 23:59:59")

    leitos   = get_leitos_ativos()
    ocupados = get_ocupados_instante(data_hora)

    resultado = {}
    for cod, d in leitos.items():
        ocup = len(ocupados.get(cod, set()))
        cap  = d["capacidade"]
        taxa = round(ocup / cap * 100, 1) if cap else 0
        resultado[cod] = {
            "setor":      d["setor"],
            "capacidade": cap,
            "ocupados":   ocup,
            "taxa":       taxa,
            "livres":     cap - ocup,
        }

    # Inclui setores que aparecem na ocupação mas não na lista mestre
    for cod, locs in ocupados.items():
        if cod not in resultado:
            resultado[cod] = {
                "setor":      cod,
                "capacidade": 0,
                "ocupados":   len(locs),
                "taxa":       0,
                "livres":     0,
            }

    return resultado


def salvar_ocupacao_dia(dia: date) -> dict:
    """Coleta e persiste em dados_ocupacao/AAAA-MM-DD.json."""
    dados = get_ocupacao_dia(dia)
    arquivo = DATA_DIR / f"{dia.isoformat()}.json"

    # Converte para serializável (sem set)
    dados_serial = {cod: d for cod, d in dados.items()}
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados_serial, f, ensure_ascii=False, indent=2)

    total_cap  = sum(d["capacidade"] for d in dados.values())
    total_ocup = sum(d["ocupados"]   for d in dados.values())
    print(f"[ocupacao_v2] {dia} — {len(dados)} setores | {total_ocup}/{total_cap} leitos")
    return dados


def carregar_ocupacao_dia(dia: date) -> dict:
    """Lê o JSON salvo. Retorna {} se não existir."""
    arquivo = DATA_DIR / f"{dia.isoformat()}.json"
    if not arquivo.exists():
        return {}
    with open(arquivo, encoding="utf-8") as f:
        return json.load(f)


def get_capacidade_por_setor() -> dict:
    """
    Retorna {str_cod: {"setor": nome, "capacidade": n}}.
    Usado para substituir LEITOS_CAPACIDADE do config.py.
    """
    leitos = get_leitos_ativos()
    return {
        cod: {"setor": d["setor"], "capacidade": d["capacidade"]}
        for cod, d in leitos.items()
    }
