# ============================================================
# database.py - Conexão com SAP MaxDB (JDBC via jaydebeapi)
# ============================================================

import os
import pandas as pd
import jaydebeapi
from config import DB_CONFIG

JAR_PATH   = os.path.join(os.path.dirname(__file__), "sapdbc.jar")
JDBC_CLASS = "com.sap.dbtech.jdbc.DriverSapDB"
JDBC_URL   = (
    f"jdbc:sapdb://{DB_CONFIG['host']}:"
    f"{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)


def get_connection():
    return jaydebeapi.connect(
        JDBC_CLASS,
        JDBC_URL,
        [DB_CONFIG["user"], DB_CONFIG["password"]],
        JAR_PATH,
    )


def executar(sql: str) -> pd.DataFrame:
    """Executa um SQL e retorna um DataFrame. Retorna vazio em caso de erro."""
    try:
        conn = get_connection()
        df = pd.read_sql(sql, conn)
        df.columns = df.columns.str.lower()
        conn.close()
        return df
    except Exception as e:
        print(f"[DB ERRO] {e}")
        return pd.DataFrame()
