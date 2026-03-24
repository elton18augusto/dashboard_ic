from calendar import monthrange
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from vendedor_shared import (
    _load_data,
    _metric_df,
    _render_totais,
    FRANQUIAS
)

st.set_page_config(page_title="Detalhe por mídia", layout="wide")
st.title("Detalhe por mídia (todos)")

# =============================
# 🔹 FILTROS
# =============================

today = date.today()
franquias = FRANQUIAS

cols_select = st.columns(3)

with cols_select[0]:
    franquia_sel = st.selectbox(
        "Franquia",
        franquias,
        index=0,
        format_func=lambda x: f"{x[0]} - {x[1]}",
    )

with cols_select[1]:
    anos = list(range(today.year - 2, today.year + 1))
    ano_sel = st.selectbox(
        "Ano",
        anos,
        index=anos.index(today.year),
    )

with cols_select[2]:
    mes_sel = st.selectbox(
        "Mes",
        list(range(1, 13)),
        index=today.month - 1,
        format_func=lambda m: f"{m:02d}",
    )

params_raw = {
    "cod_franquia": franquia_sel[0],
    "ano": str(ano_sel),
    "mes": f"{mes_sel:02d}",
}

# =============================
# 🔹 CACHE
# =============================

if "df_cache" not in st.session_state:
    st.session_state.df_cache = None

if "params_cache" not in st.session_state:
    st.session_state.params_cache = None

if st.button("Carregar dados"):
    params = params_raw
    df_loaded = _load_data(params)
    st.session_state.df_cache = df_loaded
    st.session_state.params_cache = params

# =============================
# 🔹 DATAFRAME
# =============================

df = st.session_state.df_cache

if df is None:
    st.info("Clique em 'Carregar dados' para executar a consulta.")

elif df.empty:
    st.warning("Consulta retornou 0 linhas.")

else:
    # =============================
    # 🔹 CONFIG
    # =============================

    midia_col = "midia"
    curso_col = "curso_agrupado"
    lead_col = "qtd_leads"
    contrato_col = "qtd_contratos"
    fat_col = "vl_faturado"
    rec_col = "vl_recebido"

    params_cache = st.session_state.params_cache or {}

    try:
        ano = int(params_cache.get("ano", date.today().year))
        mes = int(params_cache.get("mes", date.today().month))
    except (TypeError, ValueError):
        ano = date.today().year
        mes = date.today().month

    dias_no_mes = monthrange(ano, mes)[1]

    if ano == date.today().year and mes == date.today().month:
        dias_decorridos = date.today().day
    else:
        dias_decorridos = dias_no_mes

    todos_dias = pd.date_range(
        start=date(ano, mes, 1),
        periods=dias_no_mes,
        freq="D",
    )

    # =============================
    # 🔹 LISTA DE MÍDIAS
    # =============================

    midias = (
        df[midia_col]
        .astype(str)
        .fillna("")
        .tolist()
    )

    midias = [
        m for m in midias
        if m and m.strip() and m.strip().lower() not in {"none", "nan"}
    ]

    midias = sorted(set(midias))

    st.header("Mídias", divider="yellow")

    # =============================
    # 🔹 LOOP PRINCIPAL
    # =============================

    for midia in midias:
        st.subheader(midia, divider="blue")

        try:
            df_sel = df[df[midia_col].astype(str) == midia]

            # =============================
            # 🔹 TOTAIS
            # =============================

            total_midia = _metric_df(
                df=df_sel,
                lead_col=lead_col,
                contrato_col=contrato_col,
                fat_col=fat_col,
                rec_col=rec_col,
                days_elapsed=dias_decorridos,
                days_total=dias_no_mes,
            )

            _render_totais("Total", total_midia)

            # =============================
            # 🔹 EVOLUÇÃO DIÁRIA
            # =============================

            df_dia_sel = df_sel.copy()
            df_dia_sel["dt"] = pd.to_datetime(
                df_dia_sel["dt"], errors="coerce"
            )
            df_dia_sel = df_dia_sel.dropna(subset=["dt"])

            diario_sel = (
                df_dia_sel.groupby("dt", dropna=False)
                .agg(
                    qtd_leads=("qtd_leads", "sum"),
                    qtd_contratos=("qtd_contratos", "sum"),
                )
                .reset_index()
            )

            diario_sel = (
                diario_sel.set_index("dt")
                .reindex(todos_dias, fill_value=0)
                .rename_axis("dt")
                .reset_index()
            )

            diario_sel["qtd_leads_acum"] = diario_sel["qtd_leads"].cumsum()
            diario_sel["qtd_contratos_acum"] = (
                diario_sel["qtd_contratos"].cumsum()
            )

            diario_sel["conversao"] = (
                diario_sel["qtd_contratos_acum"] /
                diario_sel["qtd_leads_acum"].replace(0, pd.NA)
            ) * 100

            base_chart_sel = alt.Chart(diario_sel).encode(
                x=alt.X("dt:T", title=None)
            )

            bars_sel = base_chart_sel.transform_fold(
                ["qtd_leads", "qtd_contratos"],
                as_=["serie", "valor"],
            ).mark_bar(size=18).encode(
                xOffset="serie:N",
                y=alt.Y("valor:Q", title=None, axis=None),
                color=alt.Color(
                    "serie:N",
                    title=None,
                    legend=alt.Legend(
                        orient="top-right",
                        direction="horizontal",
                        columns=2,
                    ),
                    scale=alt.Scale(
                        domain=["qtd_leads", "qtd_contratos"],
                        range=["#bbc0c9", "#f59e0b"],
                    ),
                ),
            )

            bars_text_sel = bars_sel.transform_filter(
                "isValid(datum.valor) && datum.valor != 0"
            ).mark_text(
                dy=-6,
                fill="#353535",
                fontSize=14,
            ).encode(
                text=alt.Text("valor:Q", format=",.0f"),
            )

            line_sel = base_chart_sel.mark_line(
                color="#2563eb", strokeWidth=2
            ).encode(
                y=alt.Y("conversao:Q"),
            )

            line_points_sel = base_chart_sel.mark_point(
                color="#2563eb", size=40
            ).encode(
                y=alt.Y("conversao:Q"),
            )

            line_text_sel = base_chart_sel.transform_filter(
                "isValid(datum.conversao) && datum.conversao != 0"
            ).transform_calculate(
                conversao_label="format(datum.conversao, '.0f') + '%'"
            ).mark_text(
                dy=-10,
                fill="#353535",
                fontSize=14,
            ).encode(
                y=alt.Y("conversao:Q"),
                text="conversao_label:N",
            )

            baseline_sel = alt.Chart(diario_sel).mark_rule(
                color="#B8B8B8"
            ).encode(y=alt.datum(0))

            chart_sel = alt.layer(
                alt.layer(baseline_sel, bars_sel, bars_text_sel),
                alt.layer(line_sel, line_points_sel, line_text_sel),
            ).resolve_scale(y="independent").encode(
                y=alt.Y(title=None, axis=None)
            )

            st.altair_chart(chart_sel, width="stretch")

            # =============================
            # 🔹 POR CURSO
            # =============================

            st.subheader("Performance por curso")

            por_curso = _metric_df(
                df=df_sel,
                lead_col=lead_col,
                contrato_col=contrato_col,
                fat_col=fat_col,
                rec_col=rec_col,
                days_elapsed=dias_decorridos,
                days_total=dias_no_mes,
                group_col=curso_col,
            )

            por_curso = (
                por_curso
                .reset_index()
                .sort_values("qtd_contratos", ascending=False)
            )

            st.dataframe(
                por_curso,
                width="stretch",
                hide_index=True,
                column_config={
                    "qtd_leads": st.column_config.NumberColumn(
                        "Leads", format="%,.0f"),
                    "qtd_contratos": st.column_config.NumberColumn(
                        "Contratos", format="%,.0f"),
                    "faturamento": st.column_config.NumberColumn(
                        "Faturamento", format="R$ %,.2f"),
                    "receita": st.column_config.NumberColumn(
                        "Receita", format="R$ %,.2f"),
                    "proj_leads": st.column_config.NumberColumn(
                        "Proj. Leads", format="%,.0f"),
                    "proj_contratos": st.column_config.NumberColumn(
                        "Proj. Contratos", format="%,.0f"),
                    "proj_faturamento": st.column_config.NumberColumn(
                        "Proj. Faturamento", format="R$ %,.2f"),
                    "proj_receita": st.column_config.NumberColumn(
                        "Proj. Receita", format="R$ %,.2f"),
                    "conversao": st.column_config.NumberColumn(
                        "Conversão", format="%.0f %%"),
                    "receita_percentual": st.column_config.NumberColumn(
                        "Receita %", format="%.0f %%"),
                },
            )

        except Exception as exc:
            st.warning(f"Erro ao processar mídia {midia}: {exc}")
