import pandas as pd
from utils.db import get_connection


# =========================
# RESULTADO PRINCIPAL
# =========================

def obtener_resultado():

    conn = get_connection()

    query = """
    SELECT *
    FROM resultado_motor_oficial
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    return df


# =========================
# ESTRUCTURA MLM
# =========================

def obtener_estructura():

    conn = get_connection()

    query = """
    SELECT *
    FROM estructura_mlm
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    return df


# =========================
# TOP6 ESCARLATA
# =========================

def obtener_top6():

    conn = get_connection()

    query = """
    SELECT *
    FROM top6_escarlata
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    return df


# =========================
# HISTÓRICO
# =========================

def obtener_historico():

    conn = get_connection()

    query = """
    SELECT *
    FROM serie_historica
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    return df


# =========================
# PERIODOS DISPONIBLES
# =========================

def obtener_periodos():

    conn = get_connection()

    query = """
    SELECT DISTINCT periodo
    FROM resultado_motor_oficial
    ORDER BY periodo
    """

    df = pd.read_sql_query(query, conn)

    conn.close()

    return sorted(df["periodo"].astype(str).tolist())

