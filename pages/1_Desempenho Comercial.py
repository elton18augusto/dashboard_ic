from calendar import monthrange
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from vendedor_shared import (
    _format_numero_br,
    _highlight_meta_projetada,
    _load_data,
    _load_metas,
    _metric_df,
    _render_colored_metric,
    _render_totais,
)


st.set_page_config(page_title="Dashboard - Vendedores", layout="wide")
st.title("Dashboard - Vendedores")
st.caption("Analise geral, por vendedor e por curso.")

today = date.today()
franquias = [(119, "Salvador"), (108, "Fortaleza")]
cols_select = st.columns(4)
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
if "df_cache" not in st.session_state:
    st.session_state.df_cache = None
if "params_cache" not in st.session_state:
    st.session_state.params_cache = None
params_raw = {
    "cod_franquia": franquia_sel[0],
    "ano": str(ano_sel),
    "mes": f"{mes_sel:02d}",
}
with cols_select[3]:
    if st.button("Carregar dados"):
        params = params_raw
        df_loaded = _load_data(params)
        st.session_state.df_cache = df_loaded
        st.session_state.params_cache = params

df = st.session_state.df_cache
if df is None:
    st.info("Clique em 'Carregar dados' para executar a consulta.")
elif df.empty:
    st.warning("Consulta retornou 0 linhas.")
else:
    vendedor_col = 'vendedor'
    curso_col = 'curso_agrupado'
    lead_col = 'qtd_leads'
    contrato_col = 'qtd_contratos'
    fat_col = 'vl_faturado'
    rec_col = 'vl_recebido'
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

    st.header("Performance geral", divider="yellow")

    geral = _metric_df(
        df=df,
        lead_col=lead_col,
        contrato_col=contrato_col,
        fat_col=fat_col,
        rec_col=rec_col,
        days_elapsed=dias_decorridos,
        days_total=dias_no_mes,
    )
    _render_totais("Total", geral)

    df_dia = df.copy()
    df_dia["dt"] = pd.to_datetime(df_dia["dt"], errors="coerce")
    df_dia = df_dia.dropna(subset=["dt"])
    diario = (df_dia.groupby("dt", dropna=False)
              .agg(qtd_leads=("qtd_leads", "sum"),
                   qtd_contratos=("qtd_contratos", "sum"))
              .reset_index())

    dias_no_mes = monthrange(ano, mes)[1]
    todos_dias = pd.date_range(
        start=date(ano, mes, 1),
        periods=dias_no_mes,
        freq="D",
    )
    diario = (diario.set_index("dt")
              .reindex(todos_dias, fill_value=0)
              .rename_axis("dt")
              .reset_index())
    diario["qtd_leads_acum"] = diario["qtd_leads"].cumsum()
    diario["qtd_contratos_acum"] = diario["qtd_contratos"].cumsum()
    diario["conversao"] = (
        diario["qtd_contratos_acum"] /
        diario["qtd_leads_acum"].replace(0, pd.NA)
    ) * 100

    base_chart = alt.Chart(diario).encode(
        x=alt.X("dt:T", title=None)
    )
    bars = base_chart.transform_fold(
        ["qtd_leads", "qtd_contratos"],
        as_=["serie", "valor"],
    ).mark_bar(size=18).encode(
        xOffset="serie:N",
        y=alt.Y("valor:Q", title=None, axis=None),
        color=alt.Color(
            "serie:N",
            title=None,
            legend=alt.Legend(orient="top-right",
                              direction="horizontal", columns=2),
            scale=alt.Scale(
                domain=["qtd_leads", "qtd_contratos"],
                range=["#bbc0c9", "#f59e0b"],
            ),
        ),
    )
    bars_text = bars.transform_filter(
        "isValid(datum.valor) && datum.valor != 0"
    ).mark_text(
        dy=-6,
        fill="#353535",
        fontSize=14,
    ).encode(
        text=alt.Text("valor:Q", format=",.0f"),
    )
    line = base_chart.mark_line(color="#2563eb", strokeWidth=2).encode(
        y=alt.Y("conversao:Q"),
    )
    line_points = base_chart.mark_point(color="#2563eb", size=40).encode(
        y=alt.Y("conversao:Q"),
    )
    line_text = base_chart.transform_filter(
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

    baseline = alt.Chart(diario).mark_rule(
        color="#B8B8B8").encode(y=alt.datum(0))
    bar_layer = alt.layer(baseline, bars, bars_text)
    line_layer = alt.layer(line, line_points, line_text)
    chart = alt.layer(
        bar_layer,
        line_layer,
    ).resolve_scale(y="independent").encode(y=alt.Y(title=None, axis=None))
    st.altair_chart(chart, width='stretch')

    st.header("Performance por curso", divider="yellow")
    curso = _metric_df(
        df=df,
        lead_col=lead_col,
        contrato_col=contrato_col,
        fat_col=fat_col,
        rec_col=rec_col,
        days_elapsed=dias_decorridos,
        days_total=dias_no_mes,
        group_col=curso_col)
    curso = curso.reset_index().sort_values(
        "qtd_contratos", ascending=False)
    total_curso_geral = _metric_df(
        df=df,
        lead_col=lead_col,
        contrato_col=contrato_col,
        fat_col=fat_col,
        rec_col=rec_col,
        days_elapsed=dias_decorridos,
        days_total=dias_no_mes,
    )
    st.dataframe(curso,
                 width='stretch',
                 hide_index=True,
                 column_config={
                     "qtd_leads": st.column_config.NumberColumn(
                         "Leads", format="%,.0f"
                     ),
                     "qtd_contratos": st.column_config.NumberColumn(
                         "Contratos", format="%,.0f"
                     ),
                     "faturamento": st.column_config.NumberColumn(
                         "Faturamento", format="R$ %,.2f"
                     ),
                     "receita": st.column_config.NumberColumn(
                         "Receita", format="R$ %,.2f"
                     ),
                     "proj_leads": st.column_config.NumberColumn(
                         "Proj. Leads", format="%,.0f"
                     ),
                     "proj_contratos": st.column_config.NumberColumn(
                         "Proj. Contratos", format="%,.0f"
                     ),
                     "proj_faturamento": st.column_config.NumberColumn(
                         "Proj. Faturamento", format="R$ %,.2f"
                     ),
                     "proj_receita": st.column_config.NumberColumn(
                         "Proj. Receita", format="R$ %,.2f"
                     ),
                     "conversao": st.column_config.NumberColumn(
                         "Conversão", format="%.0f %%"
                     ),
                     "receita_percentual": st.column_config.NumberColumn(
                         "Receita %", format="%.0f %%"
                     ),
                 }
                 )

    params_cache = st.session_state.params_cache or {}
    meta_df = (_load_metas(params_cache)
               if params_cache else pd.DataFrame())
    if not meta_df.empty:
        meta_df = (meta_df.groupby("curso_agrupado", dropna=False)
                   .agg(meta_qtd=("meta_qtd", "sum"),
                        meta_fat=("meta_fat", "sum"))
                   .reset_index())
    else:
        meta_df = pd.DataFrame(
            columns=["curso_agrupado", "meta_qtd", "meta_fat"]
        )

    curso_meta = curso.copy()
    curso_meta = curso_meta.reset_index()
    meta_view = curso_meta[
        [curso_col, "qtd_contratos", "proj_contratos",
         "faturamento", "proj_faturamento"]
    ].merge(
        meta_df,
        left_on=curso_col,
        right_on="curso_agrupado",
        how="left",
    )
    meta_view["curso_agrupado"] = meta_view["curso_agrupado"].fillna(
        meta_view[curso_col]
    )

    meta_view["qtd_contratos"] = pd.to_numeric(
        meta_view["qtd_contratos"], errors="coerce"
    ).fillna(0)
    meta_view["proj_contratos"] = pd.to_numeric(
        meta_view["proj_contratos"], errors="coerce"
    ).fillna(0)
    meta_view["atingimento_qtd"] = (
        meta_view["qtd_contratos"] /
        meta_view["meta_qtd"].replace(0, pd.NA)
    ) * 100
    meta_view["faturamento"] = pd.to_numeric(
        meta_view["faturamento"], errors="coerce"
    ).fillna(0)
    meta_view["proj_faturamento"] = pd.to_numeric(
        meta_view["proj_faturamento"], errors="coerce"
    ).fillna(0)
    meta_view["atingimento_fat"] = (
        meta_view["faturamento"] /
        meta_view["meta_fat"].replace(0, pd.NA)
    ) * 100

    meta_view["meta_qtd_projetada"] = (
        meta_view["proj_contratos"] /
        meta_view["meta_qtd"].replace(0, pd.NA)
    ) * 100

    meta_view["meta_fat_projetada"] = (
        meta_view["proj_faturamento"] /
        meta_view["meta_fat"].replace(0, pd.NA)
    ) * 100

    st.header("Performance geral das metas", divider="yellow")
    if meta_df.empty:
        st.info("Não há metas cadastradas para este período.")
    else:
        total_meta_qtd = pd.to_numeric(
            meta_view["meta_qtd"], errors="coerce"
        ).sum()
        total_meta_fat = pd.to_numeric(
            meta_view["meta_fat"], errors="coerce"
        ).sum()
        total_contratos = meta_view["qtd_contratos"].sum()
        total_faturamento = meta_view["faturamento"].sum()
        total_proj_contratos = meta_view["proj_contratos"].sum()
        total_proj_fat = meta_view["proj_faturamento"].sum()

        total_ating_qtd = (
            (total_contratos / total_meta_qtd) * 100
            if total_meta_qtd > 0 else 0
        )
        total_ating_fat = (
            (total_faturamento / total_meta_fat) * 100
            if total_meta_fat > 0 else 0
        )
        total_meta_qtd_proj = (
            (total_proj_contratos / total_meta_qtd) * 100
            if total_meta_qtd > 0 else 0
        )
        total_meta_fat_proj = (
            (total_proj_fat / total_meta_fat) * 100
            if total_meta_fat > 0 else 0
        )

        cols_meta = st.columns(6)
        cols_meta[0].metric(
            "Contratos",
            f"{_format_numero_br(total_contratos)}"
        )
        cols_meta[1].metric(
            "Atingimento (contratos)",
            f"{_format_numero_br(total_ating_qtd)}%"
        )
        cols_meta[2].metric(
            "Faturamento",
            f"R$ {_format_numero_br(total_faturamento)}"
        )
        cols_meta[3].metric(
            "Atingimento (faturamento)",
            f"{_format_numero_br(total_ating_fat)}%"
        )
        _render_colored_metric(
            cols_meta[4],
            "Meta Qtd projetada",
            total_meta_qtd_proj,
        )
        _render_colored_metric(
            cols_meta[5],
            "Meta Fat projetada",
            total_meta_fat_proj,
        )

        st.subheader("Atingimento de meta por curso")
        meta_view = meta_view.reset_index(drop=True).sort_values(
            "meta_qtd", ascending=False)
        meta_table = meta_view[[
            "curso_agrupado",
            "meta_qtd",
            "qtd_contratos",
            "atingimento_qtd",
            "faturamento",
            "meta_fat",
            "atingimento_fat",
            "meta_qtd_projetada",
            "meta_fat_projetada",
        ]]
        meta_table = meta_table.style.map(
            _highlight_meta_projetada,
            subset=["meta_qtd_projetada", "meta_fat_projetada"],
        )
        st.dataframe(
            meta_table,
            width='stretch',
            hide_index=True,
            column_config={
                "curso_agrupado": st.column_config.TextColumn(
                    "Curso agrupado"
                ),
                "meta_qtd": st.column_config.NumberColumn(
                    "Meta (contratos)", format="%,.0f"
                ),
                "qtd_contratos": st.column_config.NumberColumn(
                    "Contratos", format="%,.0f"
                ),
                "atingimento_qtd": st.column_config.NumberColumn(
                    "Atingimento (contratos)", format="%.0f %%"
                ),
                "faturamento": st.column_config.NumberColumn(
                    "Faturamento", format="R$ %,.2f"
                ),
                "receita": st.column_config.NumberColumn(
                    "Receita", format="R$ %,.2f"
                ),
                "meta_fat": st.column_config.NumberColumn(
                    "Meta (faturamento)", format="R$ %,.2f"
                ),
                "atingimento_fat": st.column_config.NumberColumn(
                    "Atingimento (faturamento)", format="%.0f %%"
                ),
                "meta_qtd_projetada": st.column_config.NumberColumn(
                    "Meta Qtd projetada", format="%.0f %%"
                ),
                "meta_fat_projetada": st.column_config.NumberColumn(
                    "Meta Fat projetada", format="%.0f %%"
                ),
            },
        )

    st.header("Performance por vendedor", divider="yellow")
    por_vendedor = _metric_df(
        df=df,
        lead_col=lead_col,
        contrato_col=contrato_col,
        fat_col=fat_col,
        rec_col=rec_col,
        days_elapsed=dias_decorridos,
        days_total=dias_no_mes,
        group_col=vendedor_col)
    por_vendedor = por_vendedor.reset_index().sort_values(
        "qtd_contratos", ascending=False)
    st.dataframe(por_vendedor,
                 width='stretch',
                 hide_index=True,
                 column_config={
                     "qtd_leads": st.column_config.NumberColumn(
                         "Leads", format="%,.0f"
                     ),
                     "qtd_contratos": st.column_config.NumberColumn(
                         "Contratos", format="%,.0f"
                     ),
                     "faturamento": st.column_config.NumberColumn(
                         "Faturamento", format="R$ %,.2f"
                     ),
                     "receita": st.column_config.NumberColumn(
                         "Receita", format="R$ %,.2f"
                     ),
                     "proj_leads": st.column_config.NumberColumn(
                         "Proj. Leads", format="%,.0f"
                     ),
                     "proj_contratos": st.column_config.NumberColumn(
                         "Proj. Contratos", format="%,.0f"
                     ),
                     "proj_faturamento": st.column_config.NumberColumn(
                         "Proj. Faturamento", format="R$ %,.2f"
                     ),
                     "proj_receita": st.column_config.NumberColumn(
                         "Proj. Receita", format="R$ %,.2f"
                     ),
                     "conversao": st.column_config.NumberColumn(
                         "Conversão", format="%.0f %%"
                     ),
                     "receita_percentual": st.column_config.NumberColumn(
                         "Receita %", format="%.0f %%"
                     ),
                 }
                 )

    st.header("Análise por curso e mídia", divider="yellow")

    midia_col = "midia"

    # 🔹 Métricas por curso + mídia
    curso_midia = _metric_df(
        df=df,
        lead_col=lead_col,
        contrato_col=contrato_col,
        fat_col=fat_col,
        rec_col=rec_col,
        days_elapsed=dias_decorridos,
        days_total=dias_no_mes,
        group_col=[curso_col, midia_col],
    )

    curso_midia = (
        curso_midia
        .reset_index()
        .sort_values("qtd_contratos", ascending=False)
    )

    # 🔹 Filtro por curso (opcional - melhora usabilidade)
    cursos_disponiveis = sorted(
        df[curso_col].dropna().unique())  # type: ignore
    curso_sel = st.selectbox(
        "Filtrar curso",
        ["Todos"] + cursos_disponiveis,
        key="curso_midia_filtro"
    )

    if curso_sel != "Todos":
        curso_midia = curso_midia[curso_midia[curso_col] == curso_sel]

    # 🔹 Pivot (visão executiva)
    pivot = curso_midia.pivot_table(
        index=curso_col,
        columns=midia_col,
        values="qtd_contratos",
        aggfunc="sum",
        fill_value=0,
    )

    st.subheader("Contratos por curso x mídia")
    st.dataframe(pivot, width="stretch")

    # 🔹 Tabela detalhada
    st.subheader("Detalhamento")
    st.dataframe(
        curso_midia,
        width="stretch",
        hide_index=True,
        column_config={
            curso_col: st.column_config.TextColumn("Curso"),
            midia_col: st.column_config.TextColumn("Mídia"),
            "qtd_leads": st.column_config.NumberColumn(
                "Leads", format="%,.0f"
            ),
            "qtd_contratos": st.column_config.NumberColumn(
                "Contratos", format="%,.0f"
            ),
            "faturamento": st.column_config.NumberColumn(
                "Faturamento", format="R$ %,.2f"
            ),
            "receita": st.column_config.NumberColumn(
                "Receita", format="R$ %,.2f"
            ),
            "conversao": st.column_config.NumberColumn(
                "Conversão", format="%.1f %%"
            ),
        },
    )

# st.header("Análise Individual por Vendedor", divider="yellow")
# vendedor_sel = st.selectbox(
#     "Vendedor para detalhar",
#     por_vendedor[vendedor_col].astype(str).tolist(),
#     key="vendedor_sel",
# )
# df_sel = df[df[vendedor_col].astype(str) == vendedor_sel]

# total_curso = _metric_df(
#     df=df_sel,
#     lead_col=lead_col,
#     contrato_col=contrato_col,
#     fat_col=fat_col,
#     rec_col=rec_col,
#     days_elapsed=dias_decorridos,
#     days_total=dias_no_mes,
# )
# _render_totais("Total", total_curso)

# st.subheader("Evolucao diaria (vendedor selecionado)")
# df_dia_sel = df_sel.copy()
# df_dia_sel["dt"] = pd.to_datetime(df_dia_sel["dt"], errors="coerce")
# df_dia_sel = df_dia_sel.dropna(subset=["dt"])
# diario_sel = (df_dia_sel.groupby("dt", dropna=False)
#               .agg(qtd_leads=("qtd_leads", "sum"),
#                    qtd_contratos=("qtd_contratos", "sum"))
#               .reset_index())

# diario_sel = (diario_sel.set_index("dt")
#               .reindex(todos_dias, fill_value=0)
#               .rename_axis("dt")
#               .reset_index())
# diario_sel["qtd_leads_acum"] = diario_sel["qtd_leads"].cumsum()
# diario_sel["qtd_contratos_acum"] = diario_sel["qtd_contratos"].cumsum()
# diario_sel["conversao"] = (
#     diario_sel["qtd_contratos_acum"] /
#     diario_sel["qtd_leads_acum"].replace(0, pd.NA)
# ) * 100

# base_chart_sel = alt.Chart(diario_sel).encode(
#     x=alt.X("dt:T", title=None)
# )
# bars_sel = base_chart_sel.transform_fold(
#     ["qtd_leads", "qtd_contratos"],
#     as_=["serie", "valor"],
# ).mark_bar(size=18).encode(
#     xOffset="serie:N",
#     y=alt.Y("valor:Q", title=None, axis=None),
#     color=alt.Color(
#         "serie:N",
#         title=None,
#         legend=alt.Legend(orient="top-right",
#                           direction="horizontal", columns=2),
#         scale=alt.Scale(
#             domain=["qtd_leads", "qtd_contratos"],
#             range=["#bbc0c9", "#f59e0b"],
#         ),
#     ),
# )
# bars_text_sel = bars_sel.transform_filter(
#     "isValid(datum.valor) && datum.valor != 0"
# ).mark_text(
#     dy=-6,
#     fill="#353535",
#     fontSize=14,
# ).encode(
#     text=alt.Text("valor:Q", format=",.0f"),
# )
# line_sel = base_chart_sel.mark_line(color="#2563eb", strokeWidth=2).encode(
#     y=alt.Y("conversao:Q"),
# )
# line_points_sel = base_chart_sel.mark_point(
#     color="#2563eb", size=40
# ).encode(
#     y=alt.Y("conversao:Q"),
# )
# line_text_sel = base_chart_sel.transform_filter(
#     "isValid(datum.conversao) && datum.conversao != 0"
# ).transform_calculate(
#     conversao_label="format(datum.conversao, '.0f') + '%'"
# ).mark_text(
#     dy=-10,
#     fill="#353535",
#     fontSize=14,
# ).encode(
#     y=alt.Y("conversao:Q"),
#     text="conversao_label:N",
# )

# baseline_sel = alt.Chart(diario_sel).mark_rule(
#     color="#B8B8B8"
# ).encode(y=alt.datum(0))
# bar_layer_sel = alt.layer(baseline_sel, bars_sel, bars_text_sel)
# line_layer_sel = alt.layer(line_sel, line_points_sel, line_text_sel)
# chart_sel = alt.layer(
#     bar_layer_sel,
#     line_layer_sel,
# ).resolve_scale(y="independent").encode(
#     y=alt.Y(title=None, axis=None))
# st.altair_chart(chart_sel, width='stretch')

# por_curso = _metric_df(
#     df=df_sel,
#     lead_col=lead_col,
#     contrato_col=contrato_col,
#     fat_col=fat_col,
#     rec_col=rec_col,
#     days_elapsed=dias_decorridos,
#     days_total=dias_no_mes,
#     group_col=curso_col)
# por_curso = por_curso.reset_index().sort_values(
#     "qtd_contratos", ascending=False)

# st.dataframe(por_curso,
#              width='stretch',
#              hide_index=True,
#              column_config={
#                  "qtd_leads": st.column_config.NumberColumn(
#                      "Leads", format="%,.0f"
#                  ),
#                  "qtd_contratos": st.column_config.NumberColumn(
#                      "Contratos", format="%,.0f"
#                  ),
#                  "faturamento": st.column_config.NumberColumn(
#                      "Faturamento", format="R$ %,.2f"
#                  ),
#                  "receita": st.column_config.NumberColumn(
#                      "Receita", format="R$ %,.2f"
#                  ),
#                  "proj_leads": st.column_config.NumberColumn(
#                      "Proj. Leads", format="%,.0f"
#                  ),
#                  "proj_contratos": st.column_config.NumberColumn(
#                      "Proj. Contratos", format="%,.0f"
#                  ),
#                  "proj_faturamento": st.column_config.NumberColumn(
#                      "Proj. Faturamento", format="R$ %,.2f"
#                  ),
#                  "proj_receita": st.column_config.NumberColumn(
#                      "Proj. Receita", format="R$ %,.2f"
#                  ),
#                  "conversao": st.column_config.NumberColumn(
#                      "Conversão", format="%.0f %%"
#                  ),
#                  "receita_percentual": st.column_config.NumberColumn(
#                      "Receita %", format="%.0f %%"
#                  ),
#              }
#              )

if st.checkbox("Mostrar dados brutos"):
    st.subheader("Dados brutos")
    st.dataframe(df, width='stretch')
