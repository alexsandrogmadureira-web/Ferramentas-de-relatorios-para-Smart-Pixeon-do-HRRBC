# ============================================================
# fluxo_v2.py - Coleta otimizada de fluxo de leitos
# Usa queries isoladas para melhor performance e manutenção
# ============================================================

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from database import executar
from queries_fluxo_v2 import (
    SQL_SNAPSHOT_OCUPACAO,
    SQL_ADMISSOES,
    SQL_TRANSFERENCIAS_INTERNAS,
    SQL_SAIDAS,
    SQL_DETALHAMENTO_SETOR,
)

DATA_DIR = Path(__file__).parent / "dados_fluxo"
DATA_DIR.mkdir(exist_ok=True)


def _snapshot(data_hora: str) -> dict:
    """Retorna {str_cod: {setor, ocupados}} somando duplicatas do UNION."""
    df = executar(SQL_SNAPSHOT_OCUPACAO(data_hora))
    resultado = {}
    if df.empty:
        return resultado
    for _, row in df.iterrows():
        cod  = str(row["str_cod"]).strip()
        nome = str(row["setor"]).strip().upper()
        qtd  = int(row["ocupados"])
        if cod in resultado:
            resultado[cod]["ocupados"] += qtd
        else:
            resultado[cod] = {"setor": nome, "ocupados": qtd}
    return resultado


def _movimentos(sql: str, tipo: str = None) -> dict:
    """
    Executa uma query de movimentos e retorna 
    {str_cod: {setor, tipo: quantidade}}.
    """
    df = executar(sql)
    resultado = {}
    if df.empty:
        return resultado
    for _, row in df.iterrows():
        cod  = str(row["str_cod"]).strip()
        nome = str(row["setor"]).strip().upper()
        tp   = tipo or str(row.get("tipo", "")).strip().lower()
        qtd  = int(row["quantidade"])
        resultado.setdefault(cod, {"setor": nome})
        resultado[cod][tp] = resultado[cod].get(tp, 0) + qtd
    return resultado


def get_fluxo_dia(dia_referencia: date) -> dict:
    """
    Coleta fluxo do dia anterior ao dia_referencia.
    
    BID de hoje (19/07) → dados de ontem (18/07):
      snap_ini = 17/07 23:59:59  (ocupação inicial)
      snap_fim = 18/07 23:59:59  (ocupação final)
      mov_ini  = 18/07 00:00:00
      mov_fim  = 19/07 00:00:00  (exclusive)
    
    Retorna dict por str_cod:
    {
      "setor": "CLINICA MEDICA",
      "ocupacao_inicial": 30,
      "admissao": 0,
      "transferencia_entrada": 3,
      "transferencia_saida": 1,
      "alta_medica": 2,
      "transferencia_externa": 0,
      "evasao": 0,
      "obito": 0,
      "ocupacao_final": 29,
    }
    """
    ontem     = dia_referencia - timedelta(days=1)
    anteontem = dia_referencia - timedelta(days=2)

    snap_ini_dt = anteontem.strftime("%Y-%m-%d 23:59:59")
    snap_fim_dt = ontem.strftime("%Y-%m-%d 23:59:59")
    mov_ini_dt  = ontem.strftime("%Y-%m-%d 00:00:00")
    mov_fim_dt  = dia_referencia.strftime("%Y-%m-%d 00:00:00")

    print(f"[fluxo_v2] BID de {ontem.strftime('%d/%m/%Y')}")
    print(f"[fluxo_v2] mov: {mov_ini_dt} → {mov_fim_dt}")

    # Executa todas as queries
    snap_ini = _snapshot(snap_ini_dt)
    snap_fim = _snapshot(snap_fim_dt)

    admissoes = _movimentos(
        SQL_ADMISSOES(mov_ini_dt, mov_fim_dt), "admissao"
    )
    transferencias = _movimentos(
        SQL_TRANSFERENCIAS_INTERNAS(mov_ini_dt, mov_fim_dt)
    )
    saidas = _movimentos(
        SQL_SAIDAS(mov_ini_dt, mov_fim_dt)
    )

    # Consolida todos os setores encontrados
    todos_cods = (
        set(snap_ini) | set(snap_fim) |
        set(admissoes) | set(transferencias) | set(saidas)
    )

    resultado = {}
    for cod in todos_cods:
        # Nome do setor (pega de qualquer fonte disponível)
        nome = (
            snap_ini.get(cod, {}).get("setor") or
            snap_fim.get(cod, {}).get("setor") or
            admissoes.get(cod, {}).get("setor") or
            transferencias.get(cod, {}).get("setor") or
            saidas.get(cod, {}).get("setor") or
            cod
        )
        resultado[cod] = {
            "setor":                  nome,
            "ocupacao_inicial":       snap_ini.get(cod, {}).get("ocupados", 0),
            "admissao":               admissoes.get(cod, {}).get("admissao", 0),
            "transferencia_entrada":  transferencias.get(cod, {}).get("transferencia_entrada", 0),
            "transferencia_saida":    transferencias.get(cod, {}).get("transferencia_saida", 0),
            "alta_medica":            saidas.get(cod, {}).get("alta_medica", 0),
            "transferencia_externa":  saidas.get(cod, {}).get("transferencia_externa", 0),
            "evasao":                 saidas.get(cod, {}).get("evasao", 0),
            "obito":                  saidas.get(cod, {}).get("obito", 0),
            "ocupacao_final":         snap_fim.get(cod, {}).get("ocupados", 0),
        }

    return resultado

def get_fluxo_periodo(horas: int) -> dict:
    """
    Coleta fluxo das últimas `horas` horas, sempre em tempo real.
    Não persiste em disco — usado pelo card Fluxo de Leitos,
    independente do BID (que é sempre o dia anterior).
    Janela: agora - horas  →  agora
    """
    agora  = datetime.now()
    inicio = agora - timedelta(hours=horas)

    snap_ini_dt = inicio.strftime("%Y-%m-%d %H:%M:%S")
    snap_fim_dt = agora.strftime("%Y-%m-%d %H:%M:%S")
    mov_ini_dt  = inicio.strftime("%Y-%m-%d %H:%M:%S")
    mov_fim_dt  = agora.strftime("%Y-%m-%d %H:%M:%S")

    snap_ini = _snapshot(snap_ini_dt)
    snap_fim = _snapshot(snap_fim_dt)

    admissoes = _movimentos(
        SQL_ADMISSOES(mov_ini_dt, mov_fim_dt), "admissao"
    )
    transferencias = _movimentos(
        SQL_TRANSFERENCIAS_INTERNAS(mov_ini_dt, mov_fim_dt)
    )
    saidas = _movimentos(
        SQL_SAIDAS(mov_ini_dt, mov_fim_dt)
    )

    todos_cods = (
        set(snap_ini) | set(snap_fim) |
        set(admissoes) | set(transferencias) | set(saidas)
    )

    resultado = {}
    for cod in todos_cods:
        nome = (
            snap_ini.get(cod, {}).get("setor") or
            snap_fim.get(cod, {}).get("setor") or
            admissoes.get(cod, {}).get("setor") or
            transferencias.get(cod, {}).get("setor") or
            saidas.get(cod, {}).get("setor") or
            cod
        )
        resultado[cod] = {
            "setor":                  nome,
            "ocupacao_inicial":       snap_ini.get(cod, {}).get("ocupados", 0),
            "admissao":               admissoes.get(cod, {}).get("admissao", 0),
            "transferencia_entrada":  transferencias.get(cod, {}).get("transferencia_entrada", 0),
            "transferencia_saida":    transferencias.get(cod, {}).get("transferencia_saida", 0),
            "alta_medica":            saidas.get(cod, {}).get("alta_medica", 0),
            "transferencia_externa":  saidas.get(cod, {}).get("transferencia_externa", 0),
            "evasao":                 saidas.get(cod, {}).get("evasao", 0),
            "obito":                  saidas.get(cod, {}).get("obito", 0),
            "ocupacao_final":         snap_fim.get(cod, {}).get("ocupados", 0),
        }

    return resultado

def get_detalhamento_setor(
    dia_referencia: date, str_cod: str
) -> list[dict]:
    """
    Lista individual de movimentos de um setor para o enfermeiro revisar.
    """
    ontem = dia_referencia - timedelta(days=1)
    mov_ini = ontem.strftime("%Y-%m-%d 00:00:00")
    mov_fim = dia_referencia.strftime("%Y-%m-%d 00:00:00")

    df = executar(SQL_DETALHAMENTO_SETOR(mov_ini, mov_fim, str_cod))
    if df.empty:
        return []
    return df.to_dict("records")


def salvar_fluxo_dia(dia_referencia: date) -> dict:
    dados = get_fluxo_dia(dia_referencia)
    arquivo = DATA_DIR / f"{dia_referencia.isoformat()}.json"
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    ontem = dia_referencia - timedelta(days=1)
    print(f"[fluxo_v2] BID de {ontem.strftime('%d/%m/%Y')} salvo — {len(dados)} setores.")
    return dados


def carregar_fluxo_dia(dia_referencia: date) -> dict:
    arquivo = DATA_DIR / f"{dia_referencia.isoformat()}.json"
    if not arquivo.exists():
        return {}
    with open(arquivo, encoding="utf-8") as f:
        return json.load(f)
