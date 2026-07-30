# ============================================================
# ocupacao.py - Coleta e persistência da ocupação diária
# ============================================================
# Responsabilidades:
#   - Consultar o banco para uma data específica
#   - Salvar o resultado em JSON  (dados_ocupacao/AAAA-MM-DD.json)
#   - Carregar um dia já salvo
# ============================================================

import json
from datetime import date
from pathlib import Path

import pandas as pd

from config import LEITOS_CAPACIDADE, CLINICAS_EXCLUIR
from database import executar
from queries_ocupacao import SQL_OCUPACAO_LEITOS

DATA_DIR = Path(__file__).parent / "dados_ocupacao"
DATA_DIR.mkdir(exist_ok=True)


def get_ocupacao_dia(data: date) -> dict:
    """
    Consulta o banco e retorna a ocupação da data informada.
    Usa 23:59:59 como snapshot (situação no final do dia).

    Retorna:
        {
          "str_cod": {"clinica": "NOME DA CLINICA", "ocupados": 27},
          ...
        }
    """
    data_hora = data.strftime("%Y-%m-%d 23:59:59")
    df = executar(SQL_OCUPACAO_LEITOS(data_hora))

    if df.empty:
        return {}

    resultado = {}
    for _, row in df.iterrows():
        nome = str(row["clinica"]).strip().upper()
        if nome in CLINICAS_EXCLUIR:
            continue
        resultado[str(row["str_cod"]).strip()] = {
            "clinica":  nome,
            "ocupados": int(row["leitos_ocupados"]),
        }
    return resultado


def salvar_dia(data: date) -> dict:
    """
    Coleta a ocupação e persiste em dados_ocupacao/AAAA-MM-DD.json.
    Retorna o dict salvo (útil para conferência imediata).
    """
    dados = get_ocupacao_dia(data)
    arquivo = DATA_DIR / f"{data.isoformat()}.json"
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print(f"[ocupacao] {data.isoformat()} — {len(dados)} clínicas salvas.")
    return dados


def carregar_dia(data: date) -> dict:
    """
    Lê o JSON do dia salvo anteriormente.
    Retorna {} se o arquivo não existir (dia sem coleta).
    """
    arquivo = DATA_DIR / f"{data.isoformat()}.json"
    if not arquivo.exists():
        return {}
    with open(arquivo, encoding="utf-8") as f:
        return json.load(f)


def mapa_ocupados_dia(dados_dia: dict) -> dict[str, int]:
    """
    Converte o dict salvo em {nome_clinica -> ocupados}.
    Atalho usado pelo gerador de Excel.
    """
    return {v["clinica"]: v["ocupados"] for v in dados_dia.values()}
