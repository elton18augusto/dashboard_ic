from typing import Optional
from datetime import date, timedelta
import os
from dotenv import load_dotenv
import pandas as pd
from google.ads.googleads.client import GoogleAdsClient
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()


def _get_refresh_token(secret_file: str):
    flow = InstalledAppFlow.from_client_secrets_file(
        secret_file,
        scopes=['https://www.googleapis.com/auth/adwords']
    )

    credentials = flow.run_local_server()
    return print(f"Refresh Token: {credentials.refresh_token}")


def _build_config(franquia: str) -> dict:
    key = f"GOOGLE_CUSTOMER_FRANQUIA_{franquia.upper().replace(' ', '_')}"
    customer_id = (os.getenv(key) or "").strip()
    if not customer_id:
        raise ValueError(
            f"Customer ID não encontrado para franquia: {franquia}")

    return {
        "developer_token": (os.getenv("GOOGLE_DEVELOPER_TOKEN") or "").strip(),
        "client_id": (os.getenv("GOOGLE_CLIENT_ID") or "").strip(),
        "client_secret": (os.getenv("GOOGLE_CLIENT_SECRET") or "").strip(),
        "refresh_token": (os.getenv("GOOGLE_REFRESH_TOKEN") or "").strip(),
        "login_customer_id": customer_id,
        "use_proto_plus": True,
    }


def get_client(franquia: str) -> tuple[GoogleAdsClient, str]:
    config = _build_config(franquia)
    customer_id = config["login_customer_id"]
    client = GoogleAdsClient.load_from_dict(config)
    return client, customer_id


def get_spend(franquia: str, date_start: str, date_end: str) -> pd.DataFrame:
    """
    Retorna o valor investido no período para a franquia informada.
    date_start e date_end no formato 'YYYY-MM-DD'.
    """
    client, customer_id = get_client(franquia)
    ga_service = client.get_service("GoogleAdsService")

    query = f"""
        SELECT
            segments.date,
            metrics.cost_micros
        FROM campaign
        WHERE segments.date BETWEEN '{date_start}' AND '{date_end}'
    """

    response = ga_service.search_stream(customer_id=customer_id, query=query)

    rows = []
    for batch in response:
        for row in batch.results:
            rows.append({
                "date": row.segments.date,
                # cost_micros divide por 1M para chegar no valor real
                "spend": row.metrics.cost_micros / 1_000_000,
            })

    if not rows:
        return pd.DataFrame(columns=["date", "spend"])

    return pd.DataFrame(rows)


def get_remaining_budget(
        franquia: str,
        reference_date: Optional[date] = None
) -> dict:
    """
    Calcula o valor estimado a ser investido do dia atual até o final do mês,
    com base no orçamento diário das campanhas ativas.
    """
    if reference_date is None:
        reference_date = date.today()

    # Último dia do mês
    if reference_date.month == 12:
        last_day = date(reference_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(reference_date.year,
                        reference_date.month + 1, 1) - timedelta(days=1)

    days_remaining = (last_day - reference_date).days + 1

    client, customer_id = get_client(franquia)
    ga_service = client.get_service("GoogleAdsService")

    query = """
        SELECT
            campaign.name,
            campaign.status,
            campaign_budget.amount_micros,
            campaign_budget.type,
            metrics.cost_micros
        FROM campaign
        WHERE campaign.status = 'ENABLED'
        AND segments.date DURING LAST_7_DAYS
    """

    response = ga_service.search_stream(customer_id=customer_id, query=query)

    total_daily_budget = 0.0
    campaign_details = []

    for batch in response:
        for row in batch.results:
            # Ignora campanhas sem gasto nos últimos 7 dias
            if row.metrics.cost_micros == 0:
                continue

            budget_type = row.campaign_budget.type_.name
            amount_micros = row.campaign_budget.amount_micros
            daily_value = amount_micros / 1_000_000

            if budget_type == "FIXED":
                campaign_details.append({
                    "campaign": row.campaign.name,
                    "daily_budget": None,
                    "type": "fixo",
                })
            else:
                total_daily_budget += daily_value
                campaign_details.append({
                    "campaign": row.campaign.name,
                    "daily_budget": round(daily_value, 2),
                    "type": "diário",
                })

    estimated_remaining = round(total_daily_budget * days_remaining, 2)

    return {
        "franquia": franquia,
        "reference_date": reference_date.isoformat(),
        "last_day_of_month": last_day.isoformat(),
        "days_remaining": days_remaining,
        "total_daily_budget": round(total_daily_budget, 2),
        "estimated_remaining": estimated_remaining,
        "campaigns": campaign_details,
    }


if __name__ == "__main__":
    # _get_refresh_token(
    #     'client_secret_372801041853-jemiiel3lmodmfmo4f88n30r8i8tari6\
    #         .apps.googleusercontent.com.json'
    # )

    date_start = "2026-04-01"
    date_end = "2026-04-30"

    franquia = "SSA"
    spend_df = get_spend(franquia, date_start, date_end)
    total = spend_df["spend"].sum().round(2)
    print(f"Total gasto google ads {franquia}: {total}")

    franquia = "FOR"
    spend_df = get_spend(franquia, date_start, date_end)
    total = spend_df["spend"].sum().round(2)
    print(f"Total gasto google ads {franquia}: {total}")

    print("\n--- Orçamento restante no mês (Google Ads) ---")
    for franquia in ["SSA", "FOR"]:
        result = get_remaining_budget(franquia)
        print(f"\n{franquia}:")
        print(f"  Dias restantes: {result['days_remaining']}")
        print(f"  Orçamento diário total (campanhas ativas): "
              f"R$ {result['total_daily_budget']}")
        print(f"  Estimativa até {result['last_day_of_month']}: "
              f"R$ {result['estimated_remaining']}")
