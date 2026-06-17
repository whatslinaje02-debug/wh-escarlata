from utils.db import get_connection

SCHEMA = """

CREATE TABLE IF NOT EXISTS lideres (

    id_lider TEXT PRIMARY KEY,

    nombre TEXT,

    activo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS estructura (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    periodo TEXT NOT NULL,

    id_lider TEXT NOT NULL,

    upline TEXT,

    ramas_directas INTEGER,

    profundidad_red INTEGER,

    volumen_total_red REAL
);

CREATE TABLE IF NOT EXISTS metricas (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    periodo TEXT NOT NULL,

    id_lider TEXT NOT NULL,

    nivel_escarlata TEXT,

    puntos_escarlata INTEGER,

    score_ejecutivo INTEGER,

    puntos_grupales REAL,

    puntos_personales REAL,

    pds INTEGER,

    adps INTEGER,

    dependencia_porcentaje REAL,

    estado_dependencia TEXT,

    activacion_escarlata TEXT,

    estabilidad TEXT,

    periodos_activo INTEGER,

    tendencia_vol REAL,

    crecimiento_pct REAL
);

CREATE TABLE IF NOT EXISTS top6 (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    periodo TEXT NOT NULL,

    id_lider TEXT NOT NULL,

    posicion INTEGER,

    puntos_escarlata INTEGER,

    bono_estimado REAL
);

CREATE TABLE IF NOT EXISTS serie_historica (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    periodo TEXT NOT NULL,

    id_lider TEXT NOT NULL,

    mes TEXT,

    volumen REAL,

    nivel TEXT,

    pds INTEGER,

    adps INTEGER,

    activacion TEXT
);

CREATE TABLE IF NOT EXISTS raw_periodos (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    periodo TEXT,

    upline TEXT,

    id_lider TEXT,

    estado_ciudad TEXT,

    nombre_del_lider TEXT,

    puntos_sig_rango REAL,

    pds REAL,

    adps REAL,

    puntos_personales REAL,

    puntos_grupales REAL,

    puntos_rollover REAL,

    puntos_uninivel REAL,

    asesores_uninivel REAL,

    puntos_generacion_1 REAL,

    asesores_generacion_1 REAL,

    ganancia REAL,

    rango_periodo_2606 TEXT,

    rango_periodo_2605 TEXT,

    rango_periodo_2604 TEXT,

    rango_periodo_2603 TEXT,

    rango_periodo_2602 TEXT,

    rango_periodo_2601 TEXT,

    maximo_rango TEXT
);


CREATE INDEX IF NOT EXISTS idx_metricas_periodo
ON metricas(periodo);

CREATE INDEX IF NOT EXISTS idx_raw_periodo
ON raw_periodos(periodo);

CREATE INDEX IF NOT EXISTS idx_raw_lider
ON raw_periodos(id_lider);

CREATE INDEX IF NOT EXISTS idx_metricas_lider
ON metricas(id_lider);

CREATE INDEX IF NOT EXISTS idx_estructura_periodo
ON estructura(periodo);

CREATE INDEX IF NOT EXISTS idx_estructura_lider
ON estructura(id_lider);

"""

def init_database():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.executescript(SCHEMA)

    conn.commit()

    conn.close()

    print("Base de datos creada correctamente")


if __name__ == "__main__":

    init_database()