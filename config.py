# ============================================================
# config.py - Configurações do BID Hospital
# ============================================================

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "port":     int(os.getenv("DB_PORT", 7210)),
    "database": os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}

NOME_HOSPITAL = "Hospital Regional Ruy de Barros Correia"
NOME_CIDADE   = "Arcoverde — PE"
SECRET_KEY    = os.getenv("SECRET_KEY", "bid-hrrbc-2026")
PORTA         = int(os.getenv("PORTA", 8051))

# Nomes exatos conforme retornam no banco (str.str_nome em maiúsculas)
# Capacidade = número de leitos físicos instalados
LEITOS_CAPACIDADE: dict[str, int] = {
    "UTI I GERAL":                           10,
    "UTI II GERAL":                          10,
    "CLINICA MEDICA":                        30,
    "CLINICA MEDICA EXTRA":                  12,
    "CLINICA OBSTETRICA":                    22,
    "CLINICA ORTOPEDICA":                    23,
    "CLINICA ORTOPEDICA EXTRA":              13,
    "CLINICA ORTOPEDICA PEDIATRICA":          4,
    "CLINICA PEDIATRICA":                    12,
    "CLINICA PEDIATRICA ANEXO":              10,
    "CLINICA CIRURGICA GERAL":               13,
    "CLINICA CIRURGICA GERAL EXTRA":          9,
    "MATERNIDADE BERCARIO":                   4,
    "MATERNIDADE PRE-PARTO EXTRA":            3,
    "CLINICA LEITOS INTEGRAIS":               6,
    "CLINICA LEITOS INTEGRAIS EXTRA":         6,
    "EME GERAL - SALA AMARELA":               5,
    "EME GERAL - SALA VERMELHA":              3,
    "EMERGENCIA PEDIATRICA - SALA AMARELA":   3,
    "EMERGENCIA PEDIATRICA - SALA VERMELHA":  4,
    "RPA BLOCO CIRURGICO EXTRA":              6,
}

CLINICAS_EXCLUIR: list[str] = []
