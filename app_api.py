import os
from collections import Counter
from datetime import date, datetime, time

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://lambda.institutodaconstrucao.com.br"


def _headers() -> dict:
    api_key = os.environ.get("IC_API_KEY")
    if not api_key:
        raise ValueError("A variavel IC_API_KEY nao foi encontrada no .env.")
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-API-Key": api_key,
    }


@st.cache_data(ttl=900)
def get_franchises() -> list[dict]:
    url = f"{BASE_URL}/api/franquias"
    response = requests.get(url=url, headers=_headers(), timeout=30)
    response.raise_for_status()

    data = response.json()
    if not data.get("sucesso", False):
        raise RuntimeError("Falha ao consultar franquias na API.")

    franchises = data.get("dados", [])
    if isinstance(franchises, list):
        return franchises
    return []


@st.cache_data(ttl=900)
def get_contracts(date_start: datetime, date_end: datetime) -> list[dict]:
    url = f"{BASE_URL}/api/v2/contratos"

    contratos_filtrados_data: list[dict] = []
    page_number = 1
    has_next_page = True
    continue_query = True

    while continue_query and has_next_page:
        params = {"pageNumber": page_number}
        response = requests.get(
            url=url,
            headers=_headers(),
            params=params,
            timeout=60,
        )
        response.raise_for_status()

        data = response.json()
        if not data.get("sucesso", False):
            raise RuntimeError("Falha ao consultar contratos na API.")

        payload = data.get("dados", {})
        contratos = payload.get("items", [])

        for contrato in contratos:
            data_insert_str = contrato.get("dataInsert")
            if not data_insert_str:
                continue

            data_insert = datetime.fromisoformat(data_insert_str)
            if date_start <= data_insert <= date_end:
                nome_curso = contrato.get("nomeCurso", "").lower()
                situacao = contrato.get("situacao", "").lower()
                franchise_id = contrato.get("codigoFranquia")

                if situacao not in ("ativo", "encerrado"):
                    continue
                if franchise_id == 2:
                    continue

                contrato["mestre_bool"] = "mestre de obras" in nome_curso
                contrato["data_insert_dt"] = data_insert
                contratos_filtrados_data.append(contrato)
            elif data_insert < date_start:
                continue_query = False
                break

        has_next_page = payload.get("hasNextPage", False)
        page_number += 1

    return contratos_filtrados_data


def apply_custom_style() -> None:
    st.markdown(
        """
        <style>
            .hero {
                padding: 2.0rem 1.5rem;
                border-radius: 10px;
                background: linear-gradient(120deg, #0a3d62, #1e6091);
                color: #ffffff;
                margin-bottom: 3rem;
                box-shadow: 0 8px 24px rgba(11, 61, 98, 0.18);
            }
            .hero h1 {
                font-size: 2.0rem;
            }
            .hero p {
                margin: 0;
                opacity: 0.9;
            }
            .stAppDeployButton {
                display: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def get_franchise_name_map(franchises: list[dict]) -> dict:
    mapping = {}
    for fr in franchises:
        code = fr.get("codigo") or fr.get("id")
        name = fr.get("nomeFantasia") or fr.get("nome") or f"Franquia {code}"
        if code is not None:
            mapping[code] = name
    return mapping


def main() -> None:
    st.set_page_config(
        page_title="IC Dashboard",
        page_icon=":bar_chart:",
        layout="wide",
    )
    apply_custom_style()

    st.markdown(
        """
        <div class="hero">
            <h1>IC Contratos Dashboard</h1>
            <p>Analise de contratos por periodo, curso e franquia.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Filtros")
        today = date.today()
        first_day = today.replace(day=1)
        start_date = st.date_input(
            "Data inicial", value=first_day, format="DD/MM/YYYY")
        end_date = st.date_input(
            "Data final", value=today, format="DD/MM/YYYY")
        only_mestre = st.checkbox("Somente curso Mestre de Obras")

    if start_date > end_date:
        st.error("A data inicial nao pode ser maior que a data final.")
        st.stop()

    date_start = datetime.combine(start_date, time.min)
    date_end = datetime.combine(end_date, time.max)

    try:
        contracts = get_contracts(date_start, date_end)
        franchises = get_franchises()
    except Exception as exc:
        st.error(f"Erro ao carregar dados: {exc}")
        st.stop()

    if only_mestre:
        contracts = [c for c in contracts if c.get("mestre_bool")]

    fr_map = get_franchise_name_map(franchises)
    franchise_options = sorted(
        {fr_map.get(
            c.get("codigoFranquia"), "Nao identificado"
        ) for c in contracts})

    selected_franchise = st.sidebar.selectbox(
        "Franquia",
        options=["Todas"] + franchise_options,
    )

    if selected_franchise != "Todas":
        contracts = [
            c for c in contracts
            if fr_map.get(
                c.get("codigoFranquia"), "Nao identificado"
            ) == selected_franchise
        ]

    total = len(contracts)
    ativos = sum(1 for c in contracts if c.get(
        "situacao", "").lower() == "ativo")
    encerrados = sum(1 for c in contracts if c.get(
        "situacao", "").lower() == "encerrado")
    mestre = sum(1 for c in contracts if c.get("mestre_bool"))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total contratos", total)
    col2.metric("Ativos", ativos)
    col3.metric("Encerrados", encerrados)
    col4.metric("Mestre de Obras", mestre)

    st.divider()

    chart_col, ranking_col = st.columns([2, 1])

    with chart_col:
        st.subheader("Contratos por dia")
        by_day = Counter(c["data_insert_dt"].date().isoformat()
                         for c in contracts if c.get("data_insert_dt"))
        if by_day:
            st.line_chart(
                data={
                    "data": list(by_day.keys()),
                    "quantidade": list(by_day.values()),
                },
                x="data",
                y="quantidade",
            )
        else:
            st.info("Sem dados para o periodo selecionado.")

    with ranking_col:
        st.subheader("Situacao")
        by_status = Counter(c.get("situacao", "Nao informado")
                            for c in contracts)
        if by_status:
            st.bar_chart(
                data={
                    "situacao": list(by_status.keys()),
                    "quantidade": list(by_status.values()),
                },
                x="situacao",
                y="quantidade",
            )
        else:
            st.info("Sem dados para exibir.")

    st.subheader("Detalhamento de contratos")
    table_rows = []
    for c in contracts:
        table_rows.append(
            {
                "Data": c.get("data_insert_dt").strftime(  # type:ignore
                    "%d/%m/%Y %H:%M") if c.get("data_insert_dt") else "",
                "Curso": c.get("nomeCurso", ""),
                "Situacao": c.get("situacao", ""),
                "Franquia": fr_map.get(c.get("codigoFranquia"),
                                       "Nao identificado"),
                "Aluno": c.get("nomePessoa", ""),
                "Contrato": c.get("codigoContrato", ""),
            }
        )

    st.dataframe(
        table_rows,
        width="stretch",
        hide_index=True,
    )


if __name__ == "__main__":
    main()
