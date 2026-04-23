from facebook_business.adobjects.campaign import Campaign
from datetime import date, timedelta
from typing import Optional
import os
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from dotenv import load_dotenv
import pandas as pd

load_dotenv()


def _get_credentials() -> dict:
    return {
        "app_id": (os.getenv("META_APP_ID") or "").strip(),
        "app_secret": (os.getenv("META_APP_SECRET") or "").strip(),
        "access_token": (os.getenv("META_ACCESS_TOKEN") or "").strip(),
    }


def _get_account_id(franquia: str) -> str:
    key = f"META_ACCOUNT_FRANQUIA_{franquia.upper().replace(' ', '_')}"
    account_id = (os.getenv(key) or "").strip()
    if not account_id:
        raise ValueError(
            f"Account ID não encontrado para franquia: {franquia}")
    return account_id


def get_ad_account(franquia: str) -> AdAccount:
    creds = _get_credentials()
    FacebookAdsApi.init(
        app_id=creds["app_id"],
        app_secret=creds["app_secret"],
        access_token=creds["access_token"],
    )
    account_id = _get_account_id(franquia)
    return AdAccount(account_id)


def get_spend(franquia: str, date_start: str, date_end: str) -> pd.DataFrame:
    """
    Retorna o valor investido no período para a franquia informada.
    date_start e date_end no formato 'YYYY-MM-DD'.
    """
    account = get_ad_account(franquia)

    params = {
        "time_range": {"since": date_start, "until": date_end},
        "level": "account",
        "fields": [
            "spend", "impressions", "clicks", "date_start", "date_stop"
        ],
    }

    insights = account.get_insights(params=params)
    rows = [dict(i) for i in insights]  # type: ignore

    if not rows:
        return pd.DataFrame(columns=["date_start", "date_stop", "spend"])

    df = pd.DataFrame(rows)
    df["spend"] = pd.to_numeric(df["spend"], errors="coerce")
    return df


def get_remaining_budget(
        franquia: str,
        reference_date: Optional[date] = None
) -> dict:
    """
    Calcula o valor estimado a ser investido do dia atual até o final do mês,
    com base no orçamento diário das campanhas ativas.
    reference_date: data de referência (padrão: hoje)
    """
    if reference_date is None:
        reference_date = date.today()

    # Último dia do mês
    if reference_date.month == 12:
        last_day = date(reference_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(reference_date.year,
                        reference_date.month + 1, 1) - timedelta(days=1)

    # Dias restantes incluindo hoje
    days_remaining = (last_day - reference_date).days + 1

    account = get_ad_account(franquia)

    campaigns = account.get_campaigns(fields=[
        Campaign.Field.name,
        Campaign.Field.status,
        Campaign.Field.daily_budget,
        Campaign.Field.lifetime_budget,
    ])

    total_daily_budget = 0.0
    campaign_details = []

    for campaign in campaigns:  # type:ignore
        if campaign.get(Campaign.Field.status) != "ACTIVE":
            continue

        daily_budget = campaign.get(Campaign.Field.daily_budget)
        lifetime_budget = campaign.get(Campaign.Field.lifetime_budget)

        # daily_budget vem em centavos (micros no Meta = centavos * 100)
        if daily_budget:
            daily_value = int(daily_budget) / 100
            total_daily_budget += daily_value
            campaign_details.append({
                "campaign": campaign.get(Campaign.Field.name),
                "daily_budget": daily_value,
                "type": "diário",
            })
        elif lifetime_budget:
            # Orçamento vitalício: não somamos no diário
            campaign_details.append({
                "campaign": campaign.get(Campaign.Field.name),
                "daily_budget": None,
                "type": "vitalício",
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
    date_start = "2026-04-01"
    date_end = "2026-04-30"

    franquia = "SSA"
    spend_df_SSA = get_spend(franquia, date_start, date_end)
    total = spend_df_SSA["spend"].sum().round(2)
    print(f"Total gasto meta ads {franquia}: {total}")

    franquia = "FOR"
    spend_df_FOR = get_spend(franquia, date_start, date_end)
    total = spend_df_FOR["spend"].sum().round(2)
    print(f"Total gasto meta ads {franquia}: {total}")

    print(10*"-")

    for franquia in ["SSA", "FOR"]:
        result = get_remaining_budget(franquia)
        print(f"\n{franquia}:")
        print(f"  Dias restantes: {result['days_remaining']}")
        print(f"  Orçamento diário total (campanhas ativas): "
              f"R$ {result['total_daily_budget']}")
        print(f"  Estimativa até {result['last_day_of_month']}: "
              f"R$ {result['estimated_remaining']}")
