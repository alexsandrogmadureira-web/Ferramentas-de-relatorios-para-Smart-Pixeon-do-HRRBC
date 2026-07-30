# ============================================================
# db.py - Conexão e operações com PostgreSQL (banco próprio BID)
# Usa psycopg v3 (compatível com Python 3.14)
# ============================================================

import os
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG2_OK = True
except ImportError:
    PSYCOPG2_OK = False
    print("[db] psycopg não instalado. Banco PostgreSQL indisponível.")

PG_CONFIG = {
    "host":     os.getenv("PG_HOST",     "localhost"),
    "port":     int(os.getenv("PG_PORT", 5432)),
    "dbname":   os.getenv("PG_DB",       "bid_hospital"),
    "user":     os.getenv("PG_USER",     "bid_user"),
    "password": os.getenv("PG_PASS",     "bid_pass_2026"),
}


def get_conn():
    if not PSYCOPG2_OK:
        raise RuntimeError("psycopg não instalado.")
    return psycopg.connect(**PG_CONFIG)


def testar_conexao() -> bool:
    try:
        conn = get_conn()
        conn.close()
        return True
    except Exception as e:
        print(f"[db] Erro de conexão: {e}")
        return False


# ── Fluxo ─────────────────────────────────────────────────

def salvar_bid_fluxo(
    data_referencia: date,
    usuario: str,
    setores: dict,
    capacidades: dict,
    observacao: str = "",
) -> int:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bid_registro (modulo_codigo, data_referencia, usuario, observacao)
                VALUES ('fluxo', %s, %s, %s)
                ON CONFLICT (modulo_codigo, data_referencia)
                DO UPDATE SET usuario=EXCLUDED.usuario, observacao=EXCLUDED.observacao,
                              data_geracao=NOW()
                RETURNING id
            """, (data_referencia, usuario, observacao))
            registro_id = cur.fetchone()[0]

            for cod, d in setores.items():
                cap = capacidades.get(d["unidade"], None)
                cur.execute("""
                    INSERT INTO bid_fluxo (
                        bid_registro_id, str_cod, unidade, capacidade,
                        ocupacao_inicial, admissao, transferencia_entrada,
                        transferencia_saida, alta_medica, transferencia_externa,
                        evasao, obito, ocupacao_final
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (bid_registro_id, str_cod)
                    DO UPDATE SET
                        unidade=EXCLUDED.unidade, capacidade=EXCLUDED.capacidade,
                        ocupacao_inicial=EXCLUDED.ocupacao_inicial,
                        admissao=EXCLUDED.admissao,
                        transferencia_entrada=EXCLUDED.transferencia_entrada,
                        transferencia_saida=EXCLUDED.transferencia_saida,
                        alta_medica=EXCLUDED.alta_medica,
                        transferencia_externa=EXCLUDED.transferencia_externa,
                        evasao=EXCLUDED.evasao, obito=EXCLUDED.obito,
                        ocupacao_final=EXCLUDED.ocupacao_final
                """, (
                    registro_id, cod, d["unidade"], cap,
                    d.get("ocupacao_inicial", 0), d.get("admissao", 0),
                    d.get("transferencia_entrada", 0), d.get("transferencia_saida", 0),
                    d.get("alta_medica", 0), d.get("transferencia_externa", 0),
                    d.get("evasao", 0), d.get("obito", 0), d.get("ocupacao_final", 0),
                ))
            conn.commit()
            print(f"[db] BID fluxo {data_referencia} salvo (id={registro_id}).")
            return registro_id
    except Exception as e:
        conn.rollback()
        print(f"[db] Erro ao salvar fluxo: {e}")
        raise
    finally:
        conn.close()


def atualizar_campo_fluxo(
    data_referencia: date,
    str_cod: str,
    campo: str,
    valor: int,
    usuario: str,
):
    campos_validos = {k for k, _ in [
        ("ocupacao_inicial",0),("admissao",0),("transferencia_entrada",0),
        ("transferencia_saida",0),("alta_medica",0),("transferencia_externa",0),
        ("evasao",0),("obito",0),("ocupacao_final",0),
    ]}
    if campo not in campos_validos:
        return
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT f.id, f.{campo}
                FROM bid_fluxo f
                JOIN bid_registro r ON r.id = f.bid_registro_id
                WHERE r.modulo_codigo = 'fluxo'
                  AND r.data_referencia = %s
                  AND f.str_cod = %s
            """, (data_referencia, str_cod))
            row = cur.fetchone()
            if not row:
                return
            fluxo_id, val_orig = row
            cur.execute(f"UPDATE bid_fluxo SET {campo}=%s, editado=TRUE WHERE id=%s", (valor, fluxo_id))
            cur.execute("""
                INSERT INTO bid_edicao (bid_fluxo_id, campo, valor_original, valor_editado, usuario)
                VALUES (%s, %s, %s, %s, %s)
            """, (fluxo_id, campo, val_orig, valor, usuario))
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[db] Erro ao atualizar campo: {e}")
    finally:
        conn.close()


def carregar_bid_fluxo_db(data_referencia: date) -> dict:
    if not PSYCOPG2_OK:
        return {}
    try:
        conn = get_conn()
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT f.*
                FROM bid_fluxo f
                JOIN bid_registro r ON r.id = f.bid_registro_id
                WHERE r.modulo_codigo = 'fluxo'
                  AND r.data_referencia = %s
            """, (data_referencia,))
            rows = cur.fetchall()
        conn.close()
        if not rows:
            return {}
        return {
            row["str_cod"]: {
                "unidade":               row["unidade"],
                "ocupacao_inicial":      row["ocupacao_inicial"],
                "admissao":              row["admissao"],
                "transferencia_entrada": row["transferencia_entrada"],
                "transferencia_saida":   row["transferencia_saida"],
                "alta_medica":           row["alta_medica"],
                "transferencia_externa": row["transferencia_externa"],
                "evasao":                row["evasao"],
                "obito":                 row["obito"],
                "ocupacao_final":        row["ocupacao_final"],
                "editado":               row["editado"],
                "fluxo_id":              row["id"],
            }
            for row in rows
        }
    except Exception as e:
        print(f"[db] Erro ao carregar fluxo: {e}")
        return {}


def salvar_ocupacao_db(data_referencia: date, dados: dict, capacidades: dict):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for cod, d in dados.items():
                cap = capacidades.get(d.get("clinica", ""), None)
                cur.execute("""
                    INSERT INTO bid_ocupacao (data_referencia, str_cod, unidade, capacidade, ocupados)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (data_referencia, str_cod)
                    DO UPDATE SET ocupados=EXCLUDED.ocupados, coletado_em=NOW()
                """, (data_referencia, cod, d.get("clinica", cod), cap, d.get("ocupados", 0)))
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[db] Erro ao salvar ocupação: {e}")
    finally:
        conn.close()
