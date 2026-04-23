from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

from db import load_sql, query_df
from vendedor_shared import FRANQUIAS, _engine


st.set_page_config(page_title="Dashboard - Alunos Presentes", layout="wide")
st.title("Dashboard - Alunos Presentes")
st.caption(
    "Quantidade de alunos presentes por mês e curso nos últimos 12 meses."
)


@st.cache_data(show_spinner=True, ttl=300)
def _load_presenca(params: dict) -> pd.DataFrame:
    sql_text = load_sql("qtd_alunos.sql")
    return query_df(sql_text, params=params, engine=_engine())


def _start_period() -> tuple[int, int]:
    today = date.today()
    month_index = (today.year * 12 + today.month - 1) - 11
    return divmod(month_index, 12)[0], divmod(month_index, 12)[1] + 1


def _prepare_chart_data(df: pd.DataFrame) -> pd.DataFrame:
    cursos = {
        "el": "EL",
        "pl": "PL",
        "sol": "SOL",
        "cftv": "CFTV",
        "ped": "PED",
        "ar": "AR",
        "mo": "MO",
        "gp": "GP",
        "vn": "VN",
        "outros": "Outros",
    }
    data = df.copy()
    data["periodo"] = pd.to_datetime(data["periodo"] + "-01", errors="coerce")
    value_cols = [col for col in cursos if col in data.columns]
    for col in value_cols:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

    long_df = data.melt(
        id_vars=["periodo"],
        value_vars=value_cols,
        var_name="curso",
        value_name="qtd_presentes",
    )
    long_df["curso"] = long_df["curso"].map(cursos).fillna(long_df["curso"])
    return long_df.sort_values(["periodo", "curso"]).reset_index(drop=True)


ano_inicio, mes_inicio = _start_period()

franquia_sel = st.selectbox(
    "Franquia",
    FRANQUIAS,
    index=0,
    format_func=lambda x: f"{x[0]} - {x[1]}",
)

params = {
    "cod_franquia": franquia_sel[0],
    "ano": str(ano_inicio),
    "mes": f"{mes_inicio:02d}",
}

df = _load_presenca(params)

if df.empty:
    st.warning("Consulta retornou 0 linhas para o período selecionado.")
else:
    chart_df = _prepare_chart_data(df)
    total_df = (
        chart_df.groupby("periodo", as_index=False)["qtd_presentes"]
        .sum()
        .sort_values("periodo")
    )  # type: ignore

    total_base_chart = alt.Chart(total_df).encode(
        x=alt.X("periodo:T", title="Mês", axis=alt.Axis(format="%m/%Y")),
        y=alt.Y("qtd_presentes:Q", title="Total de alunos presentes"),
        tooltip=[
            alt.Tooltip("periodo:T", title="Mês", format="%m/%Y"),
            alt.Tooltip("qtd_presentes:Q", title="Presentes", format=",.0f"),
        ],
    ).properties(height=320)
    total_line = total_base_chart.mark_line(point=True, color="#2563eb")
    total_labels = total_base_chart.mark_text(
        dy=-10,
        fontSize=11,
        color="#2563eb",
    ).encode(
        text=alt.Text("qtd_presentes:Q", format=",.0f"),
    )
    total_chart = alt.layer(total_line, total_labels)

    st.subheader("Total mensal")
    st.altair_chart(total_chart, width="stretch")

    st.subheader("Por curso")
    base_chart = (
        alt.Chart(chart_df)
        .encode(
            x=alt.X("periodo:T", title="Mês", axis=alt.Axis(format="%m/%Y")),
            y=alt.Y("qtd_presentes:Q", title="Alunos presentes"),
            color=alt.Color("curso:N", title="Curso"),
            tooltip=[
                alt.Tooltip("periodo:T", title="Mês", format="%m/%Y"),
                alt.Tooltip("curso:N", title="Curso"),
                alt.Tooltip("qtd_presentes:Q",
                            title="Presentes", format=",.0f"),
            ],
        ).properties(height=420)
    )
    line = base_chart.mark_line(point=True)
    labels = base_chart.mark_text(
        dy=-10,
        fontSize=11,
    ).encode(
        text=alt.Text("qtd_presentes:Q", format=",.0f"),
    )

    chart = alt.layer(line, labels)

    st.altair_chart(chart, width="stretch")
    # st.dataframe(
    #     chart_df,
    #     width="stretch",
    #     hide_index=True,
    #     column_config={
    #         "periodo": st.column_config.DateColumn("Mês", format="MM/YYYY"),
    #         "curso": st.column_config.TextColumn("Curso"),
    #         "qtd_presentes": st.column_config.NumberColumn(
    #             "Alunos presentes", format="%,.0f"
    #         ),
    #     },
    # )
