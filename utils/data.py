import pandas as pd
import requests


def fetch_data_from_api(station_code: str, params: dict):
    try:
        r = requests.get(
            f"https://hydro.eaufrance.fr/sitehydro/ajax/{station_code}/series",
            params=params,
        )
        if r.status_code == 200 and len(r.json()["series"]["data"]) > 0:
            return r.json()["series"]["data"], None
        else:
            return None, r.json()
    except Exception as e:
        return None, e


def get_sorted_spaced_maxes(data, n: int, delta: int):
    df = pd.DataFrame(data)[["t", "v"]]
    df["t"] = pd.to_datetime(df["t"], format="%Y-%m-%dT%H:%M:%SZ")
    maxes = df[
        (df["v"] > df["v"].shift(1)) & (df["v"] >= df["v"].shift(-1))
    ].reset_index(drop=True)

    delta_days_before_next = maxes["t"].shift(-1).isna() | (
        maxes["t"].shift(-1) - maxes["t"] > pd.Timedelta(days=delta)
    )
    delta_days_after_prev = maxes["t"].shift(1).isna() | (
        maxes["t"] - maxes["t"].shift(1) > pd.Timedelta(days=delta)
    )
    greater_than_next = maxes["v"].shift(-1).isna() | (
        maxes["v"] > maxes["v"].shift(-1)
    )
    greater_than_prev = maxes["v"].shift(1).isna() | (maxes["v"] > maxes["v"].shift(1))

    spaced_maxes = maxes[
        (greater_than_next | delta_days_before_next)
        & (greater_than_prev | delta_days_after_prev)
    ].reset_index(drop=True)
    return (
        spaced_maxes.sort_values(by=["v"], ascending=False)
        .reset_index(drop=True)
        .head(n)
    )


def generate_hourly_params(start: pd.Timestamp, end: pd.Timestamp):
    return {
        "hydro_series[startAt]": start.strftime("%d/%m/%Y"),
        "hydro_series[endAt]": end.strftime("%d/%m/%Y"),
        "hydro_series[variableType]": "simple_and_interpolated_and_hourly_variable",
        "hydro_series[simpleAndInterpolatedAndHourlyVariable]": "Q",
        "hydro_series[statusData]": "validated",
    }


def generate_daily_params(start: pd.Timestamp, end: pd.Timestamp):
    return {
        "hydro_series[startAt]": start.strftime("%d/%m/%Y"),
        "hydro_series[endAt]": end.strftime("%d/%m/%Y"),
        "hydro_series[variableType]": "daily_variable",
        "hydro_series[dailyVariable]": "QIXnJ",
        "hydro_series[statusData]": "validated",
    }
