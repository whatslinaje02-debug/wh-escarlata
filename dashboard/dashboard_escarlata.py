"""
ESCARLATA EXECUTIVE DASHBOARD — WHATSHOME v7.0 DEFINITIVO
==========================================================
Lee directamente desde SQLite.
Tablas fuente: escarlata_q1_2026, escarlata_q2_2026,
               top6_q1_2026, top6_q2_2026,
               serie_historica, lideres, estructura, raw_periodos

Ejecutar:
  py motor_compensacion_wh.py        (primero)
  py -m streamlit run dashboard/dashboard_escarlata.py
"""

import sqlite3
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(
    page_title="ESCARLATA · WHATSHOME",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  .block-container{padding-top:1.2rem}
  h1{color:#e84040} h2,h3{color:#ff6b6b}
  div[data-testid="metric-container"]{
      background:#1a1a2e;border-radius:8px;padding:8px
  }
</style>
""", unsafe_allow_html=True)

# =========================================================
# CONSTANTES
# =========================================================

DB_PATH    = Path("database/wh_mlm.db")
BONO_TOTAL = 60_000

ORDEN_MESES = [
    "Enero 2026","Febrero 2026","Marzo 2026","Abril 2026","Mayo 2026"
]

NOMBRE_RANGO = {
    0:"SIN CALIFICAR",1:"BRONCE",2:"PLATA",3:"ORO",4:"PLATINO",
    5:"DIAMANTE",6:"DIAMANTE PLUS",7:"DIAMANTE EJECUTIVO",
    8:"DIAMANTE MASTER",9:"PARTNER DIAMANTE",
}
ORDEN_NIVELES = [
    "BRONCE","PLATA","ORO","PLATINO","DIAMANTE",
    "DIAMANTE PLUS","DIAMANTE EJECUTIVO","DIAMANTE MASTER",
    "PARTNER DIAMANTE","SIN CALIFICAR",
]
COLOR_NIVELES = {
    "BRONCE":"#cd7f32","PLATA":"#aaa9ad","ORO":"#ffd700",
    "PLATINO":"#e5e4e2","DIAMANTE":"#b9f2ff","DIAMANTE PLUS":"#5ce1e6",
    "DIAMANTE EJECUTIVO":"#38b6ff","DIAMANTE MASTER":"#7ed4fc",
    "PARTNER DIAMANTE":"#ff66c4","SIN CALIFICAR":"#444444",
}
COLOR_EST = {
    "ESTABLE":"#2ecc71","MODERADA":"#f39c12",
    "INESTABLE":"#e74c3c","SIN HISTORIA":"#888888"
}

# =========================================================
# CONEXIÓN
# =========================================================

def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def tabla_existe(conn, nombre):
    r = conn.execute(
        f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{nombre}'"
    ).fetchone()
    return r[0] > 0

# =========================================================
# CARGA DE DATOS
# =========================================================

@st.cache_data(ttl=120)
def cargar_datos():
    conn = get_conn()

    # ── Escarlata Q1 ──────────────────────────────────────────────────
    if tabla_existe(conn, "escarlata_q1_2026"):
        q1 = pd.read_sql("SELECT * FROM escarlata_q1_2026", conn)
    else:
        q1 = pd.DataFrame()

    # ── Escarlata Q2 ──────────────────────────────────────────────────
    if tabla_existe(conn, "escarlata_q2_2026"):
        q2 = pd.read_sql("SELECT * FROM escarlata_q2_2026", conn)
    else:
        q2 = pd.DataFrame()

    # ── TOP 6 Q1 ──────────────────────────────────────────────────────
    if tabla_existe(conn, "top6_q1_2026"):
        t6q1 = pd.read_sql("SELECT * FROM top6_q1_2026", conn)
    else:
        t6q1 = pd.DataFrame()

    # ── TOP 6 Q2 ──────────────────────────────────────────────────────
    if tabla_existe(conn, "top6_q2_2026"):
        t6q2 = pd.read_sql("SELECT * FROM top6_q2_2026", conn)
    else:
        t6q2 = pd.DataFrame()

    # ── Serie histórica ───────────────────────────────────────────────
    serie = pd.read_sql(
        "SELECT ID, NOMBRE_DEL_LIDER, PERIODO, MES, VOLUMEN, NIVEL, PDS, ADPS, ACTIVACION "
        "FROM serie_historica",
        conn
    )
    serie.columns = [c.upper() for c in serie.columns]
    serie["VOLUMEN"] = pd.to_numeric(serie["VOLUMEN"], errors="coerce").fillna(0)
    serie["MES"] = pd.Categorical(serie["MES"], categories=ORDEN_MESES, ordered=True)
    serie = serie.sort_values(["ID","MES"])

    # ── Historial rangos (solo válidos 1-9) ───────────────────────────
    hr = pd.read_sql(
        "SELECT periodo, id_lider, rango_anterior, rango_actual, "
        "nombre_anterior, nombre_actual, subio_rango "
        "FROM historial_rangos",
        conn
    )
    hr["rango_actual"] = pd.to_numeric(hr["rango_actual"], errors="coerce").fillna(0).astype(int)
    hr["subio_rango"]  = hr["subio_rango"].fillna(0).astype(int)
    hr = hr[hr["rango_actual"] <= 9].copy()
    hr["nombre_actual"] = hr["rango_actual"].map(NOMBRE_RANGO).fillna("SIN CALIFICAR")

    # ── Líderes ───────────────────────────────────────────────────────
    lideres = pd.read_sql("SELECT id_lider, nombre, region, activo FROM lideres", conn)

    # ── Raw periodos (Mayo 2605) ──────────────────────────────────────
    rp = pd.read_sql(
        "SELECT id_lider, upline, pds, adps, puntos_personales, "
        "puntos_grupales, puntos_rollover, estado_ciudad "
        "FROM raw_periodos WHERE periodo='2605'",
        conn
    )
    rp.columns = [c.upper() for c in rp.columns]
    rp["ID"] = rp["ID_LIDER"].apply(
        lambda x: str(int(float(str(x).replace(",","")))) if str(x).strip() not in ("nan","") else "0"
    )
    for col in ["PDS","ADPS","PUNTOS_PERSONALES","PUNTOS_GRUPALES","PUNTOS_ROLLOVER"]:
        rp[col] = pd.to_numeric(rp[col], errors="coerce").fillna(0)

    rp["ACTIVACION"] = (
        (rp["PDS"] >= 1) & (rp["ADPS"] >= 1) & (rp["PUNTOS_PERSONALES"] > 0)
    ).map({True:"SI", False:"NO"})

    rp["DEPENDENCIA_PCT"] = rp.apply(
        lambda r: round(r["PUNTOS_ROLLOVER"]/r["PUNTOS_GRUPALES"]*100, 1)
        if r["PUNTOS_GRUPALES"] > 0 else 0.0, axis=1
    )
    rp["ESTADO_DEP"] = rp["DEPENDENCIA_PCT"].apply(
        lambda v: "RIESGO" if v >= 50 else ("MEDIA" if v >= 20 else "SALUDABLE")
    )

    def nivel_vol(v):
        if v >= 10_000_000: return "PARTNER DIAMANTE"
        if v >=  5_000_000: return "DIAMANTE MASTER"
        if v >=  2_500_000: return "DIAMANTE EJECUTIVO"
        if v >=  1_200_000: return "DIAMANTE PLUS"
        if v >=    600_000: return "DIAMANTE"
        if v >=    300_000: return "PLATINO"
        if v >=    150_000: return "ORO"
        if v >=     60_000: return "PLATA"
        if v >=     25_000: return "BRONCE"
        return "SIN CALIFICAR"
    rp["NIVEL"] = rp["PUNTOS_GRUPALES"].apply(nivel_vol)

    conn.close()
    return q1, q2, t6q1, t6q2, serie, hr, lideres, rp


# =========================================================
# HEADER
# =========================================================

st.title("🔥 ESCARLATA EXECUTIVE DASHBOARD")
st.caption("Whatshome · Motor de Inteligencia MLM v7.0 · Enero–Mayo 2026")

if not DB_PATH.exists():
    st.error("⚠️ No se encontró `database/wh_mlm.db` — verifica la ruta del proyecto.")
    st.stop()

try:
    q1, q2, t6q1, t6q2, serie, hr, lideres, rp = cargar_datos()
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.stop()

motor_ejecutado = not t6q1.empty or not t6q2.empty

if not motor_ejecutado:
    st.warning("⚠️ Ejecuta primero el motor: `py motor_compensacion_wh.py`")

# =========================================================
# SELECTOR DE CUATRIMESTRE
# =========================================================

st.sidebar.header("⚙️ Configuración")
q_sel = st.sidebar.radio(
    "Cuatrimestre activo",
    ["Q2 2026 — Mayo (actual)", "Q1 2026 — Enero a Abril (histórico)"],
    index=0
)
es_q2 = q_sel.startswith("Q2")
df_q   = q2  if es_q2 else q1
t6_act = t6q2 if es_q2 else t6q1
label_q = "Q2 2026 (Mayo en curso)" if es_q2 else "Q1 2026 (Enero–Abril)"

# =========================================================
# SEC 1 — KPIs  (cambian según el cuatrimestre seleccionado)
# =========================================================

st.subheader(f"📊 KPIs — {label_q}")

# ── Períodos del cuatrimestre activo ──────────────────────────────────────
if es_q2:
    periodos_q = ["2605","2606","2607","2608"]
else:
    periodos_q = ["2601","2602","2603","2604"]

# ── KPIs que dependen del cuatrimestre ───────────────────────────────────
hr_q = hr[hr["periodo"].isin(periodos_q)]

# Activos: líderes con ACTIVACION=SI en al menos un período del Q
# Para Q2 usamos raw_periodos (tiene PDS/ADPS reales de mayo)
# Para Q1 usamos la serie histórica
if es_q2:
    activos_q = len(rp[rp["ACTIVACION"] == "SI"])
    vol_total  = rp["PUNTOS_GRUPALES"].sum()
    lbl_activos = "ACTIVOS MAYO"
    lbl_vol     = "VOLUMEN TOTAL MAYO"
else:
    # En Q1 calculamos activos como líderes que tuvieron ACTIVACION=SI en algún mes
    serie_q1 = serie[serie["PERIODO"].isin(["2601","2602","2603","2604"])]
    _act_q1 = serie_q1.copy()
    _act_q1["ACTIVACION"] = _act_q1["ACTIVACION"].astype(str).str.strip().str.upper()
    _ids_activos_q1 = set(_act_q1.loc[_act_q1["ACTIVACION"] == "SI", "ID"].unique())
    activos_q = len(_ids_activos_q1)
    vol_total = serie_q1.groupby("ID")["VOLUMEN"].max().sum()  # pico de volumen Q1
    lbl_activos = "ACTIVOS Q1"
    lbl_vol     = "VOLUMEN PICO Q1"

# ── KPIs fijos (no dependen del cuatrimestre) ─────────────────────────────
total_lideres = len(lideres)
con_puntos_q  = len(df_q[df_q["total_puntos"] > 0]) if not df_q.empty else 0
max_pts_q     = int(df_q["total_puntos"].max())      if not df_q.empty else 0
riesgo_cnt    = len(rp[rp["ESTADO_DEP"] == "RIESGO"])
subidas_q     = len(hr_q[hr_q["subio_rango"] == 1])

c1,c2,c3,c4,c5,c6,c7,c8 = st.columns(8)
c1.metric("TOTAL LÍDERES",    total_lideres)
c2.metric(lbl_activos,        activos_q)
c3.metric("CON PUNTOS",       con_puntos_q)
c4.metric("MÁX PUNTOS",       max_pts_q)
c5.metric("ELEGIBLES TOP 6",  len(t6_act))
c6.metric(lbl_vol,            f"{vol_total:,.0f}")
c7.metric("EN RIESGO",        riesgo_cnt)
c8.metric(f"SUBIDAS {('Q2' if es_q2 else 'Q1')}", subidas_q)

st.divider()

# =========================================================
# SEC 2 — TOP 6 Y BONO
# =========================================================

st.subheader(f"🏆 TOP 6 — {label_q}  ·  Bono ${BONO_TOTAL:,.0f}")

if t6_act.empty:
    st.info("Sin datos. Ejecuta el motor primero.")
else:
    col1, col2 = st.columns([3,2])

    # Tabla
    cols_t6 = [c for c in [
        "posicion","nombre","total_puntos","puntos_pd_adp",
        "puntos_rango_propio","puntos_rango_upline","bono_estimado","cuatrimestre"
    ] if c in t6_act.columns]
    col1.dataframe(t6_act[cols_t6], use_container_width=True, hide_index=True)

    # Gráfica
    fig_b = px.bar(
        t6_act.sort_values("bono_estimado"),
        x="bono_estimado", y="nombre", orientation="h",
        text="bono_estimado",
        title=f"💰 Distribución Bono — {label_q}",
        labels={"bono_estimado":"Bono ($)","nombre":""},
        color="bono_estimado",
        color_continuous_scale=["#c0392b","#e67e22","#f1c40f","#2ecc71"],
    )
    fig_b.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
    fig_b.update_layout(showlegend=False, height=300, margin=dict(r=90), coloraxis_showscale=False)
    col2.plotly_chart(fig_b, use_container_width=True)

    # Detalle de puntos
    with st.expander("📋 Ver desglose de puntos por logro"):
        for _, r in t6_act.iterrows():
            st.markdown(
                f"**#{int(r['posicion'])} {r['nombre']}** — "
                f"{int(r['total_puntos'])} pts · ${r['bono_estimado']:,.2f}"
            )
            if "detalle" in r and r["detalle"]:
                for item in str(r["detalle"]).split(" | "):
                    if item.strip():
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• {item}")
            st.markdown("---")

st.divider()

# =========================================================
# SEC 3 — COMPARACIÓN Q1 vs Q2
# =========================================================

st.subheader("⚖️ Comparación Q1 vs Q2")

if not q1.empty and not q2.empty:
    comp = q1[["id_lider","nombre","total_puntos"]].rename(
        columns={"total_puntos":"pts_q1"}
    ).merge(
        q2[["id_lider","total_puntos"]].rename(columns={"total_puntos":"pts_q2"}),
        on="id_lider", how="outer"
    ).fillna(0)
    comp["diferencia"] = comp["pts_q2"] - comp["pts_q1"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Mejoraron en Q2",  len(comp[comp["diferencia"]>0]))
    col2.metric("Igual en Q2",      len(comp[comp["diferencia"]==0]))
    col3.metric("Bajaron en Q2",    len(comp[comp["diferencia"]<0]))

    top_comp = comp[comp["nombre"].str.strip()!=""].sort_values("pts_q1", ascending=False).head(15)
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Bar(
        name="Q1 (Ene–Abr)", y=top_comp["nombre"], x=top_comp["pts_q1"],
        orientation="h", marker_color="#3498db"
    ))
    fig_comp.add_trace(go.Bar(
        name="Q2 (Mayo)", y=top_comp["nombre"], x=top_comp["pts_q2"],
        orientation="h", marker_color="#e74c3c"
    ))
    fig_comp.update_layout(
        barmode="group", height=500,
        title="Top 15 — Puntos Q1 vs Q2",
        xaxis_title="Puntos Escarlata",
        margin=dict(l=10)
    )
    st.plotly_chart(fig_comp, use_container_width=True)
else:
    st.info("Ejecuta el motor para ver la comparación Q1 vs Q2.")

st.divider()

# =========================================================
# SEC 4 — SUBIDAS DE RANGO
# =========================================================

st.subheader("🏅 Subidas de Rango")

tab_r1, tab_r2 = st.tabs(["Q1 — Enero a Abril", "Q2 — Mayo"])

with tab_r1:
    sub_q1 = hr[
        hr["periodo"].isin(["2601","2602","2603","2604"]) &
        (hr["subio_rango"]==1)
    ].sort_values("periodo")

    if len(sub_q1):
        # Resumen por período
        res_p = sub_q1.groupby("periodo").size().reset_index(name="subidas")
        fig_sp = px.bar(
            res_p, x="periodo", y="subidas", text="subidas",
            title="Subidas de rango por mes — Q1",
            labels={"periodo":"Período","subidas":"Líderes que subieron"},
            color="subidas", color_continuous_scale="Reds",
        )
        fig_sp.update_traces(textposition="outside")
        fig_sp.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig_sp, use_container_width=True)

        # Tabla
        sub_q1_show = sub_q1.merge(
            lideres[["id_lider","nombre","region"]],
            on="id_lider", how="left"
        )
        st.dataframe(
            sub_q1_show[["periodo","nombre","region","nombre_actual"]].rename(
                columns={"periodo":"Mes","nombre":"Líder",
                         "region":"Región","nombre_actual":"Nuevo Rango"}
            ),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Sin subidas de rango registradas en Q1.")

with tab_r2:
    sub_q2 = hr[(hr["periodo"]=="2605") & (hr["subio_rango"]==1)]
    if len(sub_q2):
        sub_q2_show = sub_q2.merge(lideres[["id_lider","nombre","region"]], on="id_lider", how="left")
        st.dataframe(
            sub_q2_show[["nombre","region","nombre_actual"]].rename(
                columns={"nombre":"Líder","region":"Región","nombre_actual":"Nuevo Rango"}
            ),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Sin subidas de rango registradas en Mayo 2026 aún.")

st.divider()

# =========================================================
# SEC 5 — ANÁLISIS HISTÓRICO
# =========================================================

st.subheader("📅 Análisis Histórico — Enero a Mayo 2026")

tab_evo, tab_cre, tab_act_mes = st.tabs([
    "📈 Evolución de Volumen",
    "🚀 Crecimiento Ene→May",
    "✅ Activación por Mes",
])

# ── Evolución ─────────────────────────────────────────────────────────────────
with tab_evo:
    lideres_disp = (
        serie[serie["NOMBRE_DEL_LIDER"] != "SIN NOMBRE"]
        .groupby("NOMBRE_DEL_LIDER")["VOLUMEN"].mean()
        .sort_values(ascending=False).index.tolist()
    )
    default_l = (
        t6_act["nombre"].tolist() if not t6_act.empty and "nombre" in t6_act.columns
        else lideres_disp[:6]
    )
    sel = st.multiselect(
        "Selecciona líderes:",
        options=lideres_disp,
        default=[l for l in default_l if l in lideres_disp][:6],
    )
    if sel:
        df_evo = serie[serie["NOMBRE_DEL_LIDER"].isin(sel)]
        fig_evo = px.line(
            df_evo, x="MES", y="VOLUMEN", color="NOMBRE_DEL_LIDER",
            markers=True,
            title="Evolución de Volumen Grupal — Enero a Mayo 2026",
            labels={"MES":"Mes","VOLUMEN":"Puntos Grupales","NOMBRE_DEL_LIDER":"Líder"},
        )
        fig_evo.update_traces(line=dict(width=2.5))
        fig_evo.update_layout(height=420)
        st.plotly_chart(fig_evo, use_container_width=True)

        pivot = df_evo.pivot_table(
            index="NOMBRE_DEL_LIDER", columns="MES", values="VOLUMEN", aggfunc="sum"
        ).reset_index()
        pivot.columns.name = None
        st.dataframe(pivot, use_container_width=True, hide_index=True)
    else:
        st.info("Selecciona al menos un líder.")

# ── Crecimiento ───────────────────────────────────────────────────────────────
with tab_cre:
    vol_ene = serie[serie["MES"]=="Enero 2026"][["NOMBRE_DEL_LIDER","VOLUMEN"]].rename(columns={"VOLUMEN":"ENE"})
    vol_may = serie[serie["MES"]=="Mayo 2026"][["NOMBRE_DEL_LIDER","VOLUMEN"]].rename(columns={"VOLUMEN":"MAY"})
    cre = vol_ene.merge(vol_may, on="NOMBRE_DEL_LIDER", how="inner")
    cre = cre[(cre["ENE"]>0)&(cre["NOMBRE_DEL_LIDER"]!="SIN NOMBRE")]
    cre["CREC_%"] = ((cre["MAY"]-cre["ENE"])/cre["ENE"]*100).round(1)

    col1, col2 = st.columns(2)
    fig_cre = px.bar(
        cre.sort_values("CREC_%",ascending=False).head(15).sort_values("CREC_%"),
        x="CREC_%", y="NOMBRE_DEL_LIDER", orientation="h",
        color="CREC_%", color_continuous_scale=["#e74c3c","#f39c12","#2ecc71"],
        text="CREC_%", title="🚀 Top 15 crecimiento (%)",
    )
    fig_cre.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig_cre.update_layout(showlegend=False, height=480, coloraxis_showscale=False)
    col1.plotly_chart(fig_cre, use_container_width=True)

    fig_cai = px.bar(
        cre.sort_values("CREC_%").head(10).sort_values("CREC_%",ascending=False),
        x="CREC_%", y="NOMBRE_DEL_LIDER", orientation="h",
        color="CREC_%", color_continuous_scale=["#e74c3c","#f39c12","#2ecc71"],
        text="CREC_%", title="📉 Top 10 mayor caída (%)",
    )
    fig_cai.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig_cai.update_layout(showlegend=False, height=380, coloraxis_showscale=False)
    col2.plotly_chart(fig_cai, use_container_width=True)

    st.dataframe(
        cre.sort_values("CREC_%",ascending=False)
        .rename(columns={"ENE":"Vol Enero","MAY":"Vol Mayo","CREC_%":"Crec. (%)"}),
        use_container_width=True, hide_index=True
    )

# ── Activación ────────────────────────────────────────────────────────────────
with tab_act_mes:
    act_m = (
        serie[serie["NOMBRE_DEL_LIDER"]!="SIN NOMBRE"]
        .groupby("MES")["ACTIVACION"].value_counts().reset_index()
    )
    act_m.columns = ["MES","ACTIVACION","TOTAL"]
    fig_act = px.bar(
        act_m, x="MES", y="TOTAL", color="ACTIVACION",
        color_discrete_map={"SI":"#2ecc71","NO":"#e74c3c"},
        barmode="group", title="Líderes Activos vs Inactivos por Mes",
        category_orders={"MES":ORDEN_MESES},
    )
    st.plotly_chart(fig_act, use_container_width=True)

    _s = serie[serie["NOMBRE_DEL_LIDER"]!="SIN NOMBRE"].copy()
    tasa = _s.groupby("MES")["ACTIVACION"].apply(
        lambda x: round((x=="SI").sum()/len(x)*100,1)
    ).reset_index()
    tasa.columns = ["MES","TASA_%"]
    fig_tasa = px.line(
        tasa, x="MES", y="TASA_%", markers=True,
        title="Tasa de Activación Mensual (%)",
        category_orders={"MES":ORDEN_MESES},
    )
    fig_tasa.update_traces(line=dict(color="#2ecc71", width=3))
    fig_tasa.update_layout(height=280)
    st.plotly_chart(fig_tasa, use_container_width=True)

st.divider()

# =========================================================
# SEC 6 — RED MAYO 2026
# =========================================================

st.subheader("🕸️ Red MLM — Mayo 2026")

tab_red1, tab_red2, tab_red3 = st.tabs([
    "📊 Distribución Niveles",
    "⚠️ Roll Over / Dependencia",
    "🔍 Búsqueda de Líder",
])

with tab_red1:
    col1, col2 = st.columns(2)

    niv_cnt = rp["NIVEL"].value_counts().reindex(ORDEN_NIVELES, fill_value=0).reset_index()
    niv_cnt.columns = ["NIVEL","TOTAL"]
    niv_cnt = niv_cnt[niv_cnt["TOTAL"]>0]
    fig_niv = px.bar(
        niv_cnt, x="NIVEL", y="TOTAL", text="TOTAL",
        color="NIVEL", color_discrete_map=COLOR_NIVELES,
        title="Distribución por Nivel Escarlata — Mayo 2026",
    )
    fig_niv.update_traces(textposition="outside")
    fig_niv.update_layout(showlegend=False, xaxis_tickangle=-30, height=380)
    col1.plotly_chart(fig_niv, use_container_width=True)

    dep_cnt = rp["ESTADO_DEP"].value_counts().reset_index()
    dep_cnt.columns = ["ESTADO","TOTAL"]
    fig_dep = px.pie(
        dep_cnt, names="ESTADO", values="TOTAL",
        color="ESTADO",
        color_discrete_map={"SALUDABLE":"#2ecc71","MEDIA":"#f39c12","RIESGO":"#e74c3c"},
        title="Salud MLM — Roll Over Mayo 2026", hole=0.4,
    )
    col2.plotly_chart(fig_dep, use_container_width=True)

    # Top volumen
    top_vol = rp.nlargest(15,"PUNTOS_GRUPALES")[["ID","PUNTOS_GRUPALES","NIVEL","ACTIVACION","ESTADO_DEP"]]
    top_vol = top_vol.merge(lideres[["id_lider","nombre"]], left_on="ID", right_on="id_lider", how="left")
    top_vol["NOMBRE"] = top_vol["nombre"].fillna(top_vol["ID"])
    fig_vol = px.bar(
        top_vol.sort_values("PUNTOS_GRUPALES"),
        x="PUNTOS_GRUPALES", y="NOMBRE", orientation="h",
        color="NIVEL", color_discrete_map=COLOR_NIVELES,
        title="Top 15 — Volumen Grupal Mayo 2026",
    )
    fig_vol.update_layout(showlegend=False, height=480)
    st.plotly_chart(fig_vol, use_container_width=True)

with tab_red2:
    riesgo_df = rp[rp["ESTADO_DEP"]=="RIESGO"].copy()
    riesgo_df = riesgo_df.merge(lideres[["id_lider","nombre","region"]], left_on="ID", right_on="id_lider", how="left")
    riesgo_df["NOMBRE"] = riesgo_df["nombre"].fillna(riesgo_df["ID"])

    st.metric("Líderes con Roll Over > 50%", len(riesgo_df))

    if len(riesgo_df):
        fig_riesgo = px.bar(
            riesgo_df.sort_values("DEPENDENCIA_PCT", ascending=False).head(20).sort_values("DEPENDENCIA_PCT"),
            x="DEPENDENCIA_PCT", y="NOMBRE", orientation="h",
            color="DEPENDENCIA_PCT",
            color_continuous_scale=["#f39c12","#e74c3c"],
            text="DEPENDENCIA_PCT",
            title="Top 20 — Mayor Dependencia de Roll Over (%)",
        )
        fig_riesgo.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_riesgo.update_layout(showlegend=False, coloraxis_showscale=False, height=500)
        st.plotly_chart(fig_riesgo, use_container_width=True)

        st.dataframe(
            riesgo_df[["NOMBRE","region","DEPENDENCIA_PCT","PUNTOS_GRUPALES","NIVEL","ACTIVACION"]]
            .rename(columns={"NOMBRE":"Líder","region":"Región",
                             "DEPENDENCIA_PCT":"Dep. %","PUNTOS_GRUPALES":"Volumen",
                             "NIVEL":"Nivel","ACTIVACION":"Activo"})
            .sort_values("Dep. %", ascending=False),
            use_container_width=True, hide_index=True
        )

with tab_red3:
    busqueda = st.text_input("🔍 Busca por nombre o ID")
    if busqueda:
        mask_s = (
            serie["NOMBRE_DEL_LIDER"].str.contains(busqueda.upper(), na=False) |
            serie["ID"].astype(str).str.contains(busqueda, na=False)
        )
        res_s = serie[mask_s][["NOMBRE_DEL_LIDER","MES","VOLUMEN","NIVEL","ACTIVACION"]].copy()
        if len(res_s):
            st.markdown(f"**Historial de {res_s['NOMBRE_DEL_LIDER'].iloc[0]}:**")
            st.dataframe(res_s, use_container_width=True, hide_index=True)

            # Gráfica individual
            fig_ind = px.line(
                res_s, x="MES", y="VOLUMEN", markers=True,
                title=f"Evolución — {res_s['NOMBRE_DEL_LIDER'].iloc[0]}",
            )
            fig_ind.update_traces(line=dict(color="#e84040", width=3))
            st.plotly_chart(fig_ind, use_container_width=True)

            # Puntos Escarlata Q1 y Q2
            lid_id = serie[mask_s]["ID"].iloc[0]
            col1, col2 = st.columns(2)
            if not q1.empty:
                r_q1 = q1[q1["id_lider"]==lid_id]
                col1.metric("Puntos Q1", int(r_q1["total_puntos"].iloc[0]) if len(r_q1) else 0)
            if not q2.empty:
                r_q2 = q2[q2["id_lider"]==lid_id]
                col2.metric("Puntos Q2", int(r_q2["total_puntos"].iloc[0]) if len(r_q2) else 0)
        else:
            st.warning("Sin resultados.")

st.divider()

# =========================================================
# SEC 7 — TABLA COMPLETA ESCARLATA
# =========================================================

st.subheader(f"📋 Tabla Completa — {label_q}")

if not df_q.empty:
    cols_show = [c for c in [
        "nombre","total_puntos","puntos_pd_adp",
        "puntos_rango_propio","puntos_rango_upline",
    ] if c in df_q.columns]
    df_show = df_q[df_q["total_puntos"]>0][cols_show].copy()
    df_show.columns = [
        c.replace("total_puntos","Total Pts")
        .replace("puntos_pd_adp","Pts PD/ADP")
        .replace("puntos_rango_propio","Pts Rango Propio")
        .replace("puntos_rango_upline","Pts Rango Upline")
        .replace("nombre","Líder")
        for c in df_show.columns
    ]
    st.dataframe(df_show, use_container_width=True, hide_index=True)
else:
    st.info("Sin datos. Ejecuta el motor primero.")

st.divider()
st.caption("WHATSHOME · ESCARLATA ENGINE v7.0 · Motor de Inteligencia MLM Ejecutiva")