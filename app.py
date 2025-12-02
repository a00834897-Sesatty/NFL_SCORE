import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os

# -------- CONFIG PÁGINA --------
st.set_page_config(page_title="Dashboard NFL", layout="wide")

# -------- ESTILOS (simple) --------
st.markdown("""
<style>
/* Fondo oscuro y texto blanco en toda la app */
[data-testid="stAppViewContainer"] {
    background-color: #050816;
    color: white;
}

/* Casi cualquier elemento de texto */
html, body, [class^="css"], [class*="css"] {
    color: white !important;
}

/* Tabs más legibles */
.stTabs [data-baseweb="tab"] {
    color: white !important;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# -------- TÍTULO + LOGO --------
col_title, col_logo = st.columns([0.85, 0.15])
with col_title:
    st.title("🏈 Dashboard de Análisis de Partidos - NFL")

with col_logo:
    try:
        st.image("LOGO_NFL.png", width=120)
    except Exception:
        pass

# -------- CARGA DE DATOS --------
@st.cache_data
def load_data():
    file_name = "NFL_scores.csv"
    if not os.path.exists(file_name):
        st.error(f"No se encontró '{file_name}'. Súbelo a Colab antes de continuar.")
        raise SystemExit("Archivo no encontrado")

    df = pd.read_csv(file_name)

    # columnas básicas
    needed = [
        "score_home", "score_away", "season", "week",
        "over_under_line", "spread_favorite", "team_home", "team_away"
    ]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        st.error(f"Faltan columnas: {', '.join(missing)}")
        raise SystemExit("Columnas faltantes")

    for c in ["season", "week", "score_home", "score_away",
              "over_under_line", "spread_favorite"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # fechas
    if "schedule_date" in df.columns:
        df["schedule_date"] = pd.to_datetime(df["schedule_date"], errors="coerce")
        df["Year"] = df["schedule_date"].dt.year
        df["Month-Year"] = df["schedule_date"].dt.to_period("M").astype(str)
        df["Week"] = df["schedule_date"].dt.isocalendar().week
    else:
        df["Year"] = df["season"]
        df["Month-Year"] = df["season"].astype(str)
        df["Week"] = df["week"]

    # métricas básicas
    df["total_points"] = df["score_home"] + df["score_away"]
    df["margin_home"] = df["score_home"] - df["score_away"]

    if "schedule_playoff" in df.columns:
        playoff = df["schedule_playoff"].astype(str).str.lower().isin(
            ["1", "true", "yes", "y", "si", "sí"]
        )
        df["Phase"] = np.where(playoff, "Playoffs", "Regular")
    else:
        df["Phase"] = "Regular"

    df["stadium"] = df.get("stadium", "Unknown").fillna("Unknown")
    df["team_home"] = df["team_home"].astype(str)
    df["team_away"] = df["team_away"].astype(str)

    return df

df = load_data()

# -------- KPI INTERACTIVO --------
st.header("📊 KPI Interactivo")

col_range, col_kpi = st.columns([0.6, 0.4])

with col_range:
    season_min = int(df["season"].min())
    season_max = int(df["season"].max())
    rango_temp = st.slider(
        "Rango de temporadas",
        min_value=season_min,
        max_value=season_max,
        value=(season_min, season_max)
    )
    df_kpi = df[df["season"].between(rango_temp[0], rango_temp[1])]

with col_kpi:
    kpi_option = st.selectbox(
        "KPI a mostrar",
        ["Total Games", "Avg Total Points/Game", "Home Win Rate", "Close Games (±3 pts)"]
    )

if df_kpi.empty:
    st.warning("No hay partidos en el rango seleccionado.")
else:
    if kpi_option == "Total Games":
        value = len(df_kpi)
        text = f"{value:,}"
        desc = "Número de partidos en el rango seleccionado."
    elif kpi_option == "Avg Total Points/Game":
        value = df_kpi["total_points"].mean()
        text = f"{value:.1f}"
        desc = "Promedio de puntos totales por partido."
    elif kpi_option == "Home Win Rate":
        value = (df_kpi["margin_home"] > 0).mean() * 100
        text = f"{value:.1f}%"
        desc = "Porcentaje de victorias del local."
    else:
        value = (df_kpi["margin_home"].abs() <= 3).mean() * 100
        text = f"{value:.1f}%"
        desc = "Porcentaje de partidos decididos por 3 puntos o menos."

    st.metric(kpi_option, text)
    st.caption(desc)

st.markdown("---")

# -------- TABS --------
tab1, tab2, tab3 = st.tabs(
    ["Enfrentamientos", "Performance Over Time", "Stadium Analysis"]
)

# ===== TAB 1: ENFRENTAMIENTOS =====
with tab1:
    st.markdown("### Enfrentamientos entre dos equipos")

    teams = sorted(pd.unique(pd.concat([df["team_home"], df["team_away"]], ignore_index=True)))
    c1, c2 = st.columns(2)
    with c1:
        team_a = st.selectbox("Equipo A", teams, index=0)
    with c2:
        team_b = st.selectbox("Equipo B", teams, index=1)

    if team_a == team_b:
        st.info("Selecciona dos equipos diferentes.")
    else:
        mask = (
            ((df["team_home"] == team_a) & (df["team_away"] == team_b)) |
            ((df["team_home"] == team_b) & (df["team_away"] == team_a))
        )
        h2h = df[mask].copy()

        if h2h.empty:
            st.warning(f"No hay partidos entre {team_a} y {team_b}.")
        else:
            if "schedule_date" in h2h.columns:
                h2h = h2h.sort_values("schedule_date")
            else:
                h2h = h2h.sort_values(["season", "week"])

            h2h["winner"] = np.where(
                h2h["margin_home"] > 0, h2h["team_home"],
                np.where(h2h["margin_home"] < 0, h2h["team_away"], "Tie")
            )

            games = len(h2h)
            wins_a = (h2h["winner"] == team_a).sum()
            wins_b = (h2h["winner"] == team_b).sum()
            ties = (h2h["winner"] == "Tie").sum()
            avg_pts = h2h["total_points"].mean()

            st.subheader(f"Historial {team_a} vs {team_b}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Partidos", games)
            c2.metric(f"Victorias {team_a}", wins_a)
            c3.metric(f"Victorias {team_b}", wins_b)
            c4.metric("Empates", ties)
            st.caption(f"Puntos promedio por partido: {avg_pts:.1f}")

            cols = []
            if "schedule_date" in h2h.columns:
                cols.append("schedule_date")
            cols += ["season", "week", "stadium", "team_home", "score_home",
                     "score_away", "team_away", "total_points", "Phase", "winner"]

            st.markdown("#### Detalle de partidos")
            st.dataframe(h2h[cols], use_container_width=True)

# ===== TAB 2: PERFORMANCE OVER TIME =====
with tab2:
    st.markdown("### Performance Over Time")

    c1, c2 = st.columns(2)
    with c1:
        group_col = st.selectbox("Agrupar por", ["Month-Year", "Week", "Year"])
    with c2:
        metric = st.selectbox("KPI", ["Games", "Avg Total Points"], key="time_kpi")

    df_time = df.groupby(group_col).agg(
        Games=("total_points", "count"),
        AvgTotalPoints=("total_points", "mean")
    ).reset_index()

    y_col = "Games" if metric == "Games" else "AvgTotalPoints"
    fig = px.line(df_time, x=group_col, y=y_col, title=f"{metric} por {group_col}", markers=True)
    st.plotly_chart(fig, use_container_width=True)

# ===== TAB 3: STADIUM ANALYSIS =====
with tab3:
    st.markdown("### Stadium Analysis")

    stat_label = st.selectbox("KPI", ["Games", "Avg Total Points"], key="stadium_kpi")
    kpi_col = "Games" if stat_label == "Games" else "AvgTotalPoints"

    df_geo = df.groupby("stadium").agg(
        Games=("total_points", "count"),
        AvgTotalPoints=("total_points", "mean")
    ).reset_index()

    df_geo = df_geo.sort_values(kpi_col, ascending=False).head(20)
    fig2 = px.bar(df_geo, x="stadium", y=kpi_col,
                  title=f"{stat_label} por Stadium",
                  color=kpi_col, color_continuous_scale="Viridis")
    fig2.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig2, use_container_width=True)
