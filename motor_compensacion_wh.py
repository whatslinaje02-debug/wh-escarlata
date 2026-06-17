"""
MOTOR DE COMPENSACIÓN ESCARLATA — WHATSHOME v7.0
=================================================
REGLAS FUNDAMENTALES
────────────────────
1. ACTIVACIÓN mensual: 1 PD + 1 ADP + puntos_personales > 0
2. PUNTOS POR PD/ADP:
   PD nuevo=1pt, PD repetido=2pts | ADP nuevo=3pts, ADP repetido=6pts
3. PUNTOS POR RANGO (al subir nivel, solo si activo ese mes):
   → pts al líder + mismos pts a su upline inmediato
   Bronce=30, Plata=40, Oro=50, Platino=60, Diamante=70,
   D.Plus=80, D.Ejecutivo=90, D.Master=100, Partner=110
4. CUATRIMESTRES: Q1=2601-2604, Q2=2605-2608 (reinicio al cambiar)
5. DECRECIMIENTO: si baja de rango vs máximo del Q → 0 pts ese mes
6. TOP 6: los 6 con más puntos en el cuatrimestre. Bono $60,000 proporcional.

NOTA Q1: Solo se calculan puntos de rango (no hay CSV de PDS/ADPS por período).
NOTA Q2: Mayo (2605) tiene datos completos. Los meses siguientes se agregan al cargar CSVs.
"""

import sqlite3, pandas as pd, os

DB_PATH      = os.path.join(os.path.dirname(__file__), "database", "wh_mlm.db")
BONO_TOTAL   = 60_000

CUATRIMESTRES = {
    "Q1_2026": ["2601","2602","2603","2604"],
    "Q2_2026": ["2605","2606","2607","2608"],
}

PUNTOS_RANGO = {1:30,2:40,3:50,4:60,5:70,6:80,7:90,8:100,9:110}
NOMBRE_RANGO = {
    0:"SIN CALIFICAR",1:"BRONCE",2:"PLATA",3:"ORO",4:"PLATINO",
    5:"DIAMANTE",6:"DIAMANTE PLUS",7:"DIAMANTE EJECUTIVO",
    8:"DIAMANTE MASTER",9:"PARTNER DIAMANTE",
}

# ─── CONEXIÓN ───────────────────────────────────────────────────────────────

def get_conn():
    path = DB_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"DB no encontrada: {path}")
    return sqlite3.connect(path)

# ─── CARGA ──────────────────────────────────────────────────────────────────

def cargar_datos(conn):
    # historial_rangos: rango mes a mes (rango_actual 1-9, filtramos basura >9)
    hr = pd.read_sql("SELECT * FROM historial_rangos ORDER BY id_lider, periodo", conn)
    hr["id_lider"]      = hr["id_lider"].astype(str).str.strip()
    hr["periodo"]       = hr["periodo"].astype(str).str.strip()
    hr["rango_actual"]  = pd.to_numeric(hr["rango_actual"],  errors="coerce").fillna(0).astype(int)
    hr["rango_anterior"]= pd.to_numeric(hr["rango_anterior"],errors="coerce").fillna(0).astype(int)
    hr["subio_rango"]   = hr["subio_rango"].fillna(0).astype(int)
    # Filtrar registros basura (totales de columna con rangos imposibles)
    hr = hr[hr["rango_actual"] <= 9].copy()

    # Tabla lideres: nombres reales
    lids = pd.read_sql("SELECT id_lider, nombre FROM lideres", conn)
    lids["id_lider"] = lids["id_lider"].astype(str).str.strip()
    nombre_map = lids.set_index("id_lider")["nombre"].to_dict()

    # raw_periodos: PDS/ADPS del período 2605
    rp = pd.read_sql("SELECT * FROM raw_periodos", conn)
    rp.columns = [c.upper() for c in rp.columns]
    rp["ID"] = rp["ID_LIDER"].apply(
        lambda x: str(int(float(str(x).replace(",","").strip())))
    )
    for col in ["PDS","ADPS","PUNTOS_PERSONALES"]:
        rp[col] = pd.to_numeric(
            rp[col].astype(str).str.replace(",",""), errors="coerce"
        ).fillna(0)
    rp["UPLINE"] = rp["UPLINE"].apply(
        lambda x: str(int(float(str(x).replace(",","").strip())))
        if str(x).strip() not in ("nan","","1") else "ROOT"
    )

    # estructura: upline por período
    est = pd.read_sql(
        "SELECT periodo, id_lider, upline, nombre FROM estructura", conn
    )
    est["id_lider"] = est["id_lider"].astype(str).str.strip()
    est["upline"]   = est["upline"].astype(str).str.strip()
    est["periodo"]  = est["periodo"].astype(str).str.strip()

    # Complementar nombre_map con estructura
    for _, row in est.iterrows():
        lid = row["id_lider"]
        if lid not in nombre_map and row["nombre"]:
            nombre_map[lid] = row["nombre"]

    return hr, rp, est, nombre_map

# ─── UTILIDADES ─────────────────────────────────────────────────────────────

def build_upline_map(est, rp, periodo):
    """Mapa id_lider → upline para un período dado."""
    m = {}
    est_p = est[est["periodo"] == periodo]
    for _, r in est_p.iterrows():
        m[r["id_lider"]] = str(r["upline"])
    # Completar con raw_periodos para 2605
    if periodo == "2605":
        for _, r in rp.iterrows():
            lid = r["ID"]
            if lid not in m:
                m[lid] = r["UPLINE"]
    return m

# ─── Q1: SOLO PUNTOS DE RANGO ───────────────────────────────────────────────

def calcular_q1(hr, est, nombre_map):
    periodos = CUATRIMESTRES["Q1_2026"]
    hr_q = hr[hr["periodo"].isin(periodos)].copy()
    disponibles = sorted(hr_q["periodo"].unique())

    print(f"\n{'='*60}")
    print("  Q1_2026 (Enero–Abril) — Puntos por Subida de Rango")
    print(f"  Períodos disponibles: {disponibles}")
    print(f"{'='*60}")

    ids = hr_q["id_lider"].unique()
    pts_propio  = {i: 0 for i in ids}
    pts_upline  = {i: 0 for i in ids}
    detalle     = {i: [] for i in ids}
    rango_max_q = {i: 0 for i in ids}

    upline_por_p = {p: build_upline_map(est, None, p) for p in disponibles}

    for periodo in disponibles:
        umap = upline_por_p[periodo]
        for _, row in hr_q[hr_q["periodo"] == periodo].iterrows():
            lid   = row["id_lider"]
            rango = int(row["rango_actual"])
            subio = bool(row["subio_rango"])
            maximo = rango_max_q.get(lid, 0)

            # Decrecimiento dentro del Q
            if rango < maximo:
                detalle[lid].append(f"{periodo}: ↓ decreció → 0 pts")
                continue

            rango_max_q[lid] = max(maximo, rango)

            if subio and rango >= 1:
                pts = PUNTOS_RANGO.get(rango, 0)
                pts_propio[lid] = pts_propio.get(lid, 0) + pts
                detalle[lid].append(
                    f"{periodo}: ↑ {NOMBRE_RANGO.get(rango,'?')} → +{pts}pts propio"
                )
                upline = umap.get(lid, "")
                if upline and upline not in ("ROOT","1","0","nan",""):
                    pts_upline[upline] = pts_upline.get(upline, 0) + pts
                    detalle.setdefault(upline, []).append(
                        f"{periodo}: hijo {lid} ↑ {NOMBRE_RANGO.get(rango,'?')} → +{pts}pts upline"
                    )

    filas = []
    for lid in ids:
        p = pts_propio.get(lid, 0)
        u = pts_upline.get(lid, 0)
        filas.append({
            "id_lider":            lid,
            "nombre":              nombre_map.get(lid, lid),
            "puntos_rango_propio": p,
            "puntos_rango_upline": u,
            "puntos_pd_adp":       0,
            "total_puntos":        p + u,
            "detalle":             " | ".join(detalle.get(lid, [])),
            "cuatrimestre":        "Q1_2026",
        })
    return pd.DataFrame(filas).sort_values("total_puntos", ascending=False)

# ─── Q2: PUNTOS COMPLETOS ───────────────────────────────────────────────────

def calcular_q2(hr, rp, est, nombre_map):
    periodos = CUATRIMESTRES["Q2_2026"]
    hr_q = hr[hr["periodo"].isin(periodos)].copy()
    disponibles = sorted(hr_q["periodo"].unique())

    print(f"\n{'='*60}")
    print("  Q2_2026 (Mayo–Agosto) — PD/ADP + Rango")
    print(f"  Períodos con historial: {disponibles}")
    print(f"  Períodos con PDS/ADPS : ['2605']")
    print(f"{'='*60}")

    # PDS/ADPS indexados por id_lider (solo 2605)
    pda_2605 = rp.set_index("ID")[["PDS","ADPS","PUNTOS_PERSONALES"]].to_dict("index")

    ids = hr_q["id_lider"].unique()
    pts_propio  = {i: 0 for i in ids}
    pts_upline  = {i: 0 for i in ids}
    pts_pda     = {i: 0 for i in ids}
    detalle     = {i: [] for i in ids}
    rango_max_q = {i: 0 for i in ids}
    pds_prev    = {i: 0 for i in ids}
    adps_prev   = {i: 0 for i in ids}

    for periodo in disponibles:
        umap = build_upline_map(est, rp, periodo)
        tiene_pda = (periodo == "2605")

        for _, row in hr_q[hr_q["periodo"] == periodo].iterrows():
            lid   = row["id_lider"]
            rango = int(row["rango_actual"])
            subio = bool(row["subio_rango"])
            maximo = rango_max_q.get(lid, 0)

            # Decrecimiento dentro del Q
            if rango < maximo:
                detalle[lid].append(f"{periodo}: ↓ decreció → 0 pts")
                continue

            rango_max_q[lid] = max(maximo, rango)

            # Activación y PDS/ADPS
            if tiene_pda and lid in pda_2605:
                d      = pda_2605[lid]
                pds_m  = float(d.get("PDS", 0) or 0)
                adps_m = float(d.get("ADPS", 0) or 0)
                pp_m   = float(d.get("PUNTOS_PERSONALES", 0) or 0)
                activo = (pds_m >= 1) and (adps_m >= 1) and (pp_m > 0)
            else:
                pds_m = adps_m = 0
                activo = False

            # Puntos PD/ADP (solo si activo)
            if activo:
                pds_n  = max(pds_m  - pds_prev.get(lid, 0), 0)
                pds_r  = pds_m - pds_n
                adps_n = max(adps_m - adps_prev.get(lid, 0), 0)
                adps_r = adps_m - adps_n
                p_pda  = pds_n*1 + pds_r*2 + adps_n*3 + adps_r*6
                pts_pda[lid] = pts_pda.get(lid, 0) + p_pda
                pds_prev[lid]  = pds_m
                adps_prev[lid] = adps_m
                detalle[lid].append(
                    f"{periodo}: ✓ activo | PD {int(pds_n)}n+{int(pds_r)}r "
                    f"ADP {int(adps_n)}n+{int(adps_r)}r → +{int(p_pda)}pts PD/ADP"
                )
            elif tiene_pda:
                detalle[lid].append(f"{periodo}: ✗ no activo → 0 pts PD/ADP")

            # Puntos por rango (subida dentro del Q)
            if subio and rango >= 1 and (activo or not tiene_pda):
                pts = PUNTOS_RANGO.get(rango, 0)
                pts_propio[lid] = pts_propio.get(lid, 0) + pts
                detalle[lid].append(
                    f"{periodo}: ↑ {NOMBRE_RANGO.get(rango,'?')} → +{pts}pts rango"
                )
                upline = umap.get(lid, "")
                if upline and upline not in ("ROOT","1","0","nan",""):
                    pts_upline[upline] = pts_upline.get(upline, 0) + pts
                    detalle.setdefault(upline, []).append(
                        f"{periodo}: hijo {lid} ↑ {NOMBRE_RANGO.get(rango,'?')} → +{pts}pts upline"
                    )

    filas = []
    for lid in ids:
        p = pts_propio.get(lid, 0)
        u = pts_upline.get(lid, 0)
        d = pts_pda.get(lid, 0)
        filas.append({
            "id_lider":            lid,
            "nombre":              nombre_map.get(lid, lid),
            "puntos_pd_adp":       d,
            "puntos_rango_propio": p,
            "puntos_rango_upline": u,
            "total_puntos":        p + u + d,
            "detalle":             " | ".join(detalle.get(lid, [])),
            "cuatrimestre":        "Q2_2026",
        })
    return pd.DataFrame(filas).sort_values("total_puntos", ascending=False)

# ─── TOP 6 Y BONO ───────────────────────────────────────────────────────────

def top6_y_bono(df, label):
    # Excluir registros sin nombre real
    elegibles = df[
        (df["total_puntos"] > 0) &
        (df["nombre"].str.strip() != "") &
        (~df["nombre"].str.upper().isin(["SIN NOMBRE","SIN_NOMBRE"]))
    ].head(6).copy()
    total = elegibles["total_puntos"].sum()
    elegibles["bono_estimado"] = (
        (elegibles["total_puntos"] / total * BONO_TOTAL).round(2)
        if total > 0 else 0.0
    )
    elegibles["posicion"]      = range(1, len(elegibles) + 1)
    elegibles["cuatrimestre"]  = label
    return elegibles

# ─── IMPRIMIR ───────────────────────────────────────────────────────────────

def imprimir_top6(top6, label):
    print(f"\n{'─'*65}")
    print(f"  🏆 TOP 6 — {label}")
    print(f"{'─'*65}")
    if top6.empty:
        print("  Sin líderes elegibles aún.")
        return
    print(f"  {'#':<3} {'LÍDER':<42} {'PTS':>5}  {'BONO':>12}")
    print(f"  {'─'*3} {'─'*42} {'─'*5}  {'─'*12}")
    for _, r in top6.iterrows():
        print(
            f"  {int(r['posicion']):<3} {str(r['nombre'])[:42]:<42} "
            f"{int(r['total_puntos']):>5}  ${r['bono_estimado']:>10,.2f}"
        )
    print(f"\n  Bono total: ${BONO_TOTAL:,.0f}  |  Puntos totales: {int(top6['total_puntos'].sum())}")

# ─── PERSISTIR ──────────────────────────────────────────────────────────────

def persistir(conn, df_q1, df_q2, t6q1, t6q2):
    df_q1.to_sql("escarlata_q1_2026", conn, if_exists="replace", index=False)
    df_q2.to_sql("escarlata_q2_2026", conn, if_exists="replace", index=False)
    t6q1.to_sql ("top6_q1_2026",      conn, if_exists="replace", index=False)
    t6q2.to_sql ("top6_q2_2026",      conn, if_exists="replace", index=False)
    print("\n💾 Tablas guardadas: escarlata_q1_2026, escarlata_q2_2026, top6_q1_2026, top6_q2_2026")

# ─── PIPELINE ───────────────────────────────────────────────────────────────

def ejecutar_motor():
    print("\n" + "="*65)
    print("  MOTOR ESCARLATA WHATSHOME v7.0")
    print("="*65)

    conn = get_conn()
    hr, rp, est, nombre_map = cargar_datos(conn)

    print(f"\n📂 Datos cargados:")
    print(f"   historial_rangos : {len(hr)} registros | períodos: {sorted(hr['periodo'].unique().tolist())}")
    print(f"   raw_periodos     : {len(rp)} líderes")
    print(f"   estructura       : {len(est)} registros")
    print(f"   lideres (nombres): {len(nombre_map)}")

    df_q1 = calcular_q1(hr, est, nombre_map)
    df_q2 = calcular_q2(hr, rp, est, nombre_map)

    t6q1 = top6_y_bono(df_q1, "Q1_2026")
    t6q2 = top6_y_bono(df_q2, "Q2_2026")

    imprimir_top6(t6q1, "Q1_2026 — Enero a Abril 2026")
    imprimir_top6(t6q2, "Q2_2026 — Mayo 2026 (en curso)")

    print(f"\n{'─'*65}")
    print("  📊 RESUMEN")
    print(f"{'─'*65}")
    print(f"  Q1 — Líderes con puntos : {len(df_q1[df_q1['total_puntos']>0])}")
    print(f"  Q1 — Máx puntos         : {df_q1['total_puntos'].max():.0f}")
    print(f"  Q2 — Líderes con puntos : {len(df_q2[df_q2['total_puntos']>0])}")
    print(f"  Q2 — Máx puntos         : {df_q2['total_puntos'].max():.0f}")

    persistir(conn, df_q1, df_q2, t6q1, t6q2)
    conn.close()
    return df_q1, df_q2, t6q1, t6q2


if __name__ == "__main__":
    ejecutar_motor()