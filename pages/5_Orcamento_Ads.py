from calendar import monthrange
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

import meta_ads
import google_ads
from vendedor_shared import _format_numero_br, FRANQUIAS

# Mapeamento de código de franquia → slug usado nas variáveis de ambiente
# Exemplos: META_ACCOUNT_FRANQUIA_SSA, GOOGLE_CUSTOMER_FRANQUIA_FOR
# Ajuste conforme o seu .env
FRANQUIA_SLUG = {
    119: "SSA",
    108: "FOR",
    24: "CAMPO_LIMPO",
    104: "GUARULHOS",
    58: "AMERICANA",
}

st.set_page_config(page_title="Orçamento Ads", layout="wide")
st.title("Orçamento de Mídia Paga")
st.caption("Acompanhe gastos e projeção de Meta Ads e Google Ads até o final do mês.")

today = date.today()
first_day_str = today.replace(day=1).isoformat()
today_str = today.isoformat()
dias_no_mes = monthrange(today.year, today.month)[1]
dias_decorridos = today.day


@st.cache_data(show_spinner=False, ttl=300)
def _load_meta(slug: str, date_start: str, date_end: str) -> dict:
    try:
        account = meta_ads.get_ad_account(slug)
        params = {
            "time_range": {"since": date_start, "until": date_end},
            "level": "account",
            "time_increment": 1,
            "fields": ["spend", "date_start", "date_stop"],
        }
        insights = account.get_insights(params=params)
        rows = [dict(i) for i in insights]  # type: ignore
        if rows:
            df = pd.DataFrame(rows)
            df["spend"] = pd.to_numeric(df["spend"], errors="coerce")
        else:
            df = pd.DataFrame(columns=["date_start", "spend"])
        budget = meta_ads.get_remaining_budget(slug)
        return {"spend_df": df, "budget": budget, "error": None}
    except Exception as exc:
        return {"spend_df": None, "budget": None, "error": str(exc)}


@st.cache_data(show_spinner=False, ttl=300)
def _load_google(slug: str, date_start: str, date_end: str) -> dict:
    try:
        df = google_ads.get_spend(slug, date_start, date_end)
        budget = google_ads.get_remaining_budget(slug)
        return {"spend_df": df, "budget": budget, "error": None}
    except Exception as exc:
        return {"spend_df": None, "budget": None, "error": str(exc)}


def _status_bar(gasto: float, proj_total: float, orcamento_alvo: float):
    pct_proj = proj_total / orcamento_alvo * 100
    pct_gasto = gasto / orcamento_alvo * 100
    if pct_proj >= 100:
        bg, fg = "#fee2e2", "#991b1b"
        msg = (
            f"Projeção acima do orçamento em "
            f"R$ {_format_numero_br(proj_total - orcamento_alvo, 2)}"
        )
    elif pct_proj >= 90:
        bg, fg = "#fef9c3", "#854d0e"
        msg = f"Projeção próxima do orçamento ({_format_numero_br(pct_proj, 1)}%)"
    else:
        bg, fg = "#d1fae5", "#065f46"
        msg = f"Dentro do orçamento – projeção: {_format_numero_br(pct_proj, 1)}%"

    st.markdown(
        f"""
        <div style="padding:10px 14px; border-radius:8px;
                    background:{bg}; color:{fg}; margin-bottom:6px;">
            <strong>{msg}</strong><br>
            <small>
                Alvo: R$&nbsp;{_format_numero_br(orcamento_alvo, 2)}
                &nbsp;|&nbsp;
                Gasto: R$&nbsp;{_format_numero_br(gasto, 2)}
                ({_format_numero_br(pct_gasto, 1)}%)
                &nbsp;|&nbsp;
                Projeção: R$&nbsp;{_format_numero_br(proj_total, 2)}
                ({_format_numero_br(pct_proj, 1)}%)
            </small>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(min(pct_gasto / 100, 1.0))


def _spend_chart(
    spend_df: pd.DataFrame,
    date_col: str,
    proj_total: float,
    dias_restantes: int,
    orcamento_alvo: float,
):
    chart_df = spend_df[[date_col, "spend"]].copy()
    chart_df.columns = ["data", "spend"]
    chart_df["data"] = pd.to_datetime(chart_df["data"])
    chart_df = chart_df.sort_values("data").reset_index(drop=True)
    chart_df["gasto_acumulado"] = chart_df["spend"].cumsum()

    area = (
        alt.Chart(chart_df)
        .mark_area(color="#f59e0b", opacity=0.35, line={"color": "#f59e0b", "strokeWidth": 2})
        .encode(
            x=alt.X("data:T", title=None),
            y=alt.Y("gasto_acumulado:Q", title="Gasto acumulado (R$)"),
            tooltip=[
                alt.Tooltip("data:T", title="Data", format="%d/%m"),
                alt.Tooltip("spend:Q", title="Gasto diário (R$)", format=",.2f"),
                alt.Tooltip("gasto_acumulado:Q", title="Acumulado (R$)", format=",.2f"),
            ],
        )
    )

    layers: list = [area]

    # Linha pontilhada de projeção (de hoje até fim do mês)
    if dias_restantes > 1 and not chart_df.empty:
        last_date = chart_df["data"].iloc[-1]
        last_acum = chart_df["gasto_acumulado"].iloc[-1]
        end_date = pd.Timestamp(date(today.year, today.month, dias_no_mes))
        proj_df = pd.DataFrame(
            {"data": [last_date, end_date], "gasto_acumulado": [last_acum, proj_total]}
        )
        proj_line = (
            alt.Chart(proj_df)
            .mark_line(color="#f59e0b", strokeDash=[6, 4], strokeWidth=2)
            .encode(x="data:T", y="gasto_acumulado:Q")
        )
        layers.append(proj_line)

    # Linha horizontal do orçamento alvo
    if orcamento_alvo > 0:
        rule_df = pd.DataFrame({"y": [orcamento_alvo]})
        rule = (
            alt.Chart(rule_df)
            .mark_rule(color="#991b1b", strokeDash=[5, 3], strokeWidth=1.5)
            .encode(y="y:Q")
        )
        layers.append(rule)

    chart = alt.layer(*layers).resolve_scale(y="shared")
    st.altair_chart(chart, use_container_width=True)


def _render_platform(data: dict, label: str, cor: str, orcamento_alvo: float):
    st.header(label, divider=cor)

    if data["error"]:
        st.error(f"Erro ao carregar dados: {data['error']}")
        return

    spend_df: pd.DataFrame | None = data["spend_df"]
    budget: dict = data["budget"]

    gasto_mtd = (
        float(spend_df["spend"].sum())
        if spend_df is not None and not spend_df.empty
        else 0.0
    )
    est_restante = budget["estimated_remaining"]
    proj_total = round(gasto_mtd + est_restante, 2)
    orc_diario = budget["total_daily_budget"]
    dias_rest = budget["days_remaining"]

    # KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Gasto no mês", f"R$ {_format_numero_br(gasto_mtd, 2)}")
    c2.metric("Estimativa restante", f"R$ {_format_numero_br(est_restante, 2)}")
    c3.metric("Projeção total", f"R$ {_format_numero_br(proj_total, 2)}")
    c4.metric("Orçamento diário", f"R$ {_format_numero_br(orc_diario, 2)}")
    c5.metric("Dias restantes", str(dias_rest))

    if orcamento_alvo > 0:
        _status_bar(gasto_mtd, proj_total, orcamento_alvo)

    # Gráfico de gasto acumulado
    if spend_df is not None and not spend_df.empty:
        date_col = "date_start" if "date_start" in spend_df.columns else "date"
        _spend_chart(spend_df, date_col, proj_total, dias_rest, orcamento_alvo)

    # Tabela de campanhas
    campaigns = budget.get("campaigns", [])
    if campaigns:
        with st.expander(f"Campanhas ativas ({len(campaigns)})"):
            camp_df = pd.DataFrame(campaigns)
            st.dataframe(
                camp_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "campaign": st.column_config.TextColumn("Campanha", width="large"),
                    "daily_budget": st.column_config.NumberColumn(
                        "Orç. Diário", format="R$ %,.2f"
                    ),
                    "type": st.column_config.TextColumn("Tipo"),
                },
            )
    elif not budget.get("error"):
        st.info("Nenhuma campanha ativa encontrada.")


# ── Filtros ───────────────────────────────────────────────────────────────────

cols_select = st.columns([2, 2, 2, 1])
with cols_select[0]:
    franquia_sel = st.selectbox(
        "Franquia",
        FRANQUIAS,
        index=0,
        format_func=lambda x: f"{x[0]} - {x[1]}",
    )
with cols_select[1]:
    orc_meta = st.number_input(
        "Orçamento Meta (R$/mês)",
        min_value=0.0,
        value=0.0,
        step=500.0,
        format="%.2f",
        help="Deixe em 0 para não comparar com alvo",
    )
with cols_select[2]:
    orc_google = st.number_input(
        "Orçamento Google (R$/mês)",
        min_value=0.0,
        value=0.0,
        step=500.0,
        format="%.2f",
        help="Deixe em 0 para não comparar com alvo",
    )
with cols_select[3]:
    load_btn = st.button("Carregar dados", use_container_width=True)

if "ads_cache" not in st.session_state:
    st.session_state.ads_cache = None

if load_btn:
    slug = FRANQUIA_SLUG.get(franquia_sel[0], franquia_sel[1].upper())
    with st.spinner("Carregando Meta Ads e Google Ads..."):
        meta_data = _load_meta(slug, first_day_str, today_str)
        google_data = _load_google(slug, first_day_str, today_str)
    st.session_state.ads_cache = {
        "franquia": franquia_sel,
        "meta": meta_data,
        "google": google_data,
    }

# ── Exibição ──────────────────────────────────────────────────────────────────

cache = st.session_state.ads_cache
if cache is None:
    st.info("Clique em 'Carregar dados' para executar a consulta.")
else:
    nome = cache["franquia"][1]
    st.subheader(
        f"{nome} — {today.replace(day=1).strftime('%d/%m/%Y')} a {today.strftime('%d/%m/%Y')}"
        f"  ({dias_decorridos} de {dias_no_mes} dias)"
    )

    _render_platform(cache["meta"], "Meta Ads", "orange", orc_meta)
    _render_platform(cache["google"], "Google Ads", "blue", orc_google)
