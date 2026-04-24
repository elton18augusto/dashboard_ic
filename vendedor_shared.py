import json
from datetime import date

import pandas as pd
import streamlit as st

from db import get_engine, load_sql, query_df

FRANQUIAS = [(119, "Salvador"), (108, "Fortaleza"), (24, "Campo Limpo"), (104, "Guarulhos"), (58, "Americana")]


@st.cache_resource
def _engine():
    return get_engine()


@st.cache_data(show_spinner=True, ttl=300)
def _load_data(params: dict):
    sql_text = load_sql("vendedor.sql")
    return query_df(sql_text, params=params, engine=_engine())


@st.cache_data(show_spinner=True, ttl=300)
def _load_metas(params: dict):
    sql_text = load_sql("metas.sql")
    return query_df(sql_text, params=params, engine=_engine())


def _parse_params(raw: str) -> dict:
    today = date.today()
    default_year = today.year
    default_month = today.month
    default_params = {
        "cod_franquia": 119,
        "ano": default_year,
        "mes": default_month,
    }
    raw = (raw or "").strip()
    if not raw:
        return default_params
    return json.loads(raw)


def _sum_col(df, col):
    if col not in df.columns:
        return 0.0
    return pd.to_numeric(
        df[col], errors="coerce").infer_objects(copy=False).sum()


def _metric_df(
    df, lead_col, contrato_col, fat_col, rec_col,
    days_elapsed, days_total,
    group_col=None
):
    if group_col:
        g = df.groupby(group_col, dropna=False)
        index = g.size().index

        def _group_sum(col):
            if col not in df.columns:
                return pd.Series(0, index=index)
            return pd.to_numeric(g[col].sum(), errors="coerce")

        base = pd.DataFrame({
            "qtd_leads": _group_sum(lead_col),
            "qtd_contratos": _group_sum(contrato_col),
            "faturamento": _group_sum(fat_col),
            "receita": _group_sum(rec_col),
        }).infer_objects(copy=False)
    else:
        base = pd.DataFrame([{
            "qtd_leads": _sum_col(df, lead_col),
            "qtd_contratos": _sum_col(df, contrato_col),
            "faturamento": _sum_col(df, fat_col),
            "receita": _sum_col(df, rec_col),
        }])
    base["conversao"] = (base["qtd_contratos"] /
                         base["qtd_leads"].replace(0, pd.NA)) * 100
    base["conversao"] = base["conversao"].infer_objects(copy=False)
    base["receita_percentual"] = (base["receita"].replace(0, pd.NA) /
                                  base["faturamento"]) * 100
    divisor = days_elapsed if days_elapsed else pd.NA
    base["proj_leads"] = (base["qtd_leads"] / divisor) * days_total
    base["proj_contratos"] = (base["qtd_contratos"] / divisor) * days_total
    base["proj_faturamento"] = (base["faturamento"] / divisor) * days_total
    base["proj_receita"] = (base["receita"] / divisor) * days_total

    return base


def _format_numero_br(valor, decimais: int = 0):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        valor = 0
    modificador = f",.{decimais}f"
    return (f"{valor:{modificador}}"
            .replace(",", "X").replace(".", ",").replace("X", "."))


def _render_totais(label: str, total_df: pd.DataFrame):
    row = total_df.iloc[0].to_dict()
    cols = st.columns(9)
    cols[0].metric(f"{label} Leads",
                   _format_numero_br(row.get("qtd_leads", 0)))
    cols[1].metric(f"{label} Contratos",
                   _format_numero_br(row.get("qtd_contratos", 0)))
    cols[2].metric(f"{label} Fat.",
                   "R$ " + _format_numero_br(row.get("faturamento", 0)))
    cols[3].metric(f"{label} Rec.",
                   "R$ " + _format_numero_br(row.get("receita", 0)),
                   delta=(_format_numero_br(
                       row.get("receita_percentual"), 0) + "% do fat."),
                   delta_arrow="off")
    cols[4].metric(f"{label} Conversao",
                   str(_format_numero_br(row.get("conversao", 0)) + "%"))
    cols[5].metric(f"{label} Proj. Leads",
                   _format_numero_br(row.get("proj_leads", 0)))
    cols[6].metric(f"{label} Proj. Contratos",
                   _format_numero_br(row.get("proj_contratos", 0)))
    cols[7].metric(f"{label} Proj. Fat.",
                   "R$" + _format_numero_br(row.get("proj_faturamento", 0)))
    cols[8].metric(f"{label} Proj. Rec.",
                   "R$" + _format_numero_br(row.get("proj_receita", 0)))


def _highlight_meta_projetada(valor):
    if pd.isna(valor):
        return ""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return ""
    if valor >= 100:
        return "background-color: #d1fae5; color: #065f46;"
    if valor < 75:
        return "background-color: #fee2e2; color: #991b1b;"
    return "background-color: #fef9c3; color: #854d0e;"


def _metric_colors(valor):
    if pd.isna(valor):
        return ("#fef9c3", "#854d0e")
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return ("#fef9c3", "#854d0e")
    if valor >= 100:
        return ("#d1fae5", "#065f46")
    if valor < 75:
        return ("#fee2e2", "#991b1b")
    return ("#fef9c3", "#854d0e")


def _render_colored_metric(container, label, valor):
    bg, fg = _metric_colors(valor)
    container.markdown(
        f"""
        <div style="padding: 12px 14px; border-radius: 8px;
                    background: {bg}; color: {fg};">
            <div style="font-size: 12px; opacity: 0.9;">{label}</div>
            <div style="font-size: 24px; font-weight: 600;">
                {_format_numero_br(valor or 0)}%
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
