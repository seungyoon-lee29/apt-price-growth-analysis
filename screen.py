"""
screen.py
---------
enriched DataFrame 기반 분석.

1) 세그먼트별 월별 평당가 중위값/평균/YoY
2) 월세 수익률 추정
3) 같은 단지 내 저평가 거래 탐지 (z-score 기반)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ------------------------------------------------------------------
# 1. 세그먼트 x 월 가격 추이
# ------------------------------------------------------------------
def monthly_price_trend(
    trade_df: pd.DataFrame,
    group_cols: list[str],
    price_col: str = "price_per_pyeong",
) -> pd.DataFrame:
    if trade_df.empty:
        return pd.DataFrame()

    df = trade_df.dropna(subset=[price_col, "deal_date"]).copy()
    df["ym"] = df["deal_date"].dt.to_period("M").astype(str)

    agg = (
        df.groupby(group_cols + ["ym"])[price_col]
        .agg(median="median", mean="mean", count="count")
        .reset_index()
    )
    agg = agg.sort_values(group_cols + ["ym"])
    agg["yoy_pct"] = (
        agg.groupby(group_cols)["median"].pct_change(periods=12) * 100
    )
    return agg


# ------------------------------------------------------------------
# 2. 월세 수익률 추정
# ------------------------------------------------------------------
def estimate_rental_yield(
    trade_df: pd.DataFrame,
    rent_df: pd.DataFrame,
    conversion_rate: float = 0.055,
    match_cols: tuple[str, ...] = ("region", "dong", "building_name"),
) -> pd.DataFrame:
    if trade_df.empty or rent_df.empty:
        return pd.DataFrame()

    monthly_rent_only = rent_df[rent_df["contract_type"] == "월세"].copy()
    if monthly_rent_only.empty:
        return pd.DataFrame()

    monthly_rent_only["annual_rent_equiv"] = (
        monthly_rent_only["deposit_manwon"].fillna(0) * conversion_rate
        + monthly_rent_only["monthly_rent"].fillna(0) * 12
    )
    monthly_rent_only["annual_rent_per_m2"] = (
        monthly_rent_only["annual_rent_equiv"] / monthly_rent_only["area_m2"]
    )

    rent_agg = (
        monthly_rent_only.groupby(list(match_cols))
        .agg(
            annual_rent_per_m2=("annual_rent_per_m2", "median"),
            rent_count=("annual_rent_per_m2", "count"),
        )
        .reset_index()
    )

    trade_copy = trade_df.copy()
    trade_copy["price_per_m2"] = trade_copy["price_manwon"] / trade_copy["area_m2"]
    trade_agg = (
        trade_copy.groupby(list(match_cols))
        .agg(
            price_per_m2=("price_per_m2", "median"),
            trade_count=("price_per_m2", "count"),
            latest_trade=("deal_date", "max"),
        )
        .reset_index()
    )

    merged = trade_agg.merge(rent_agg, on=list(match_cols), how="inner")
    merged["gross_yield_pct"] = merged["annual_rent_per_m2"] / merged["price_per_m2"] * 100
    return merged.sort_values("gross_yield_pct", ascending=False)


# ------------------------------------------------------------------
# 3. 단지 내 저평가 거래 탐지
# ------------------------------------------------------------------
def find_underpriced_trades(
    trade_df: pd.DataFrame,
    lookback_months: int = 6,
    min_samples: int = 3,
    z_threshold: float = -1.2,
    price_col: str = "price_per_pyeong",
) -> pd.DataFrame:
    if trade_df.empty:
        return trade_df

    df = trade_df.dropna(subset=[price_col, "deal_date"]).copy()
    cutoff = df["deal_date"].max() - pd.DateOffset(months=lookback_months)
    df = df[df["deal_date"] >= cutoff]

    df["building_key"] = (
        df["region"].astype(str) + "|"
        + df["dong"].astype(str) + "|"
        + df["building_name"].astype(str)
    )

    stats = (
        df.groupby("building_key")[price_col]
        .agg(["mean", "std", "count"])
        .reset_index()
        .rename(columns={"mean": "bld_mean", "std": "bld_std", "count": "bld_count"})
    )
    df = df.merge(stats, on="building_key", how="left")
    df = df[df["bld_count"] >= min_samples]
    df["z_score"] = (df[price_col] - df["bld_mean"]) / df["bld_std"].replace(0, np.nan)

    under = df[df["z_score"] <= z_threshold].sort_values("z_score")

    cols = [
        "deal_date", "region", "dong", "building_name", "area_m2", "floor",
        "price_manwon", price_col, "bld_mean", "z_score",
    ]
    if "age_years" in under.columns:
        cols.append("age_years")
    if "subway_segment" in under.columns:
        cols.append("subway_segment")

    return under[[c for c in cols if c in under.columns]].reset_index(drop=True)


# ------------------------------------------------------------------
# 4. 최종 스크리닝
# ------------------------------------------------------------------
def screen(
    trade_df: pd.DataFrame,
    yield_df: pd.DataFrame,
    trend_df: pd.DataFrame,
    segment_cols: tuple[str, ...] = ("zone", "age_segment"),
) -> pd.DataFrame:
    if trade_df.empty:
        return pd.DataFrame()

    df = trade_df.copy()
    df["pp_rank"] = df.groupby(list(segment_cols))["price_per_pyeong"].rank(pct=True)

    bld = (
        df.groupby(["region", "dong", "building_name"] + list(segment_cols))
        .agg(
            median_pp=("price_per_pyeong", "median"),
            pp_rank=("pp_rank", "median"),
            trade_count=("price_per_pyeong", "count"),
            last_deal=("deal_date", "max"),
        )
        .reset_index()
    )

    if not yield_df.empty:
        yield_copy = yield_df.copy()
        yield_copy["yield_rank"] = yield_copy.groupby("region")["gross_yield_pct"].rank(
            pct=True, ascending=False
        )
        bld = bld.merge(
            yield_copy[["region", "dong", "building_name", "gross_yield_pct", "yield_rank"]],
            on=["region", "dong", "building_name"],
            how="left",
        )

    if not trend_df.empty:
        seg_in_trend = [c for c in segment_cols if c in trend_df.columns]
        if seg_in_trend:
            latest = (
                trend_df.sort_values("ym")
                .groupby(seg_in_trend)
                .tail(1)[list(seg_in_trend) + ["yoy_pct"]]
            )
            bld = bld.merge(latest, on=seg_in_trend, how="left")

    mask = (
        (bld["pp_rank"] <= 0.30)
        & (bld.get("yield_rank", pd.Series(1.0, index=bld.index)) <= 0.30)
        & (bld["trade_count"] >= 2)
    )
    return bld[mask].sort_values(
        "gross_yield_pct" if "gross_yield_pct" in bld.columns else "median_pp",
        ascending=False,
    )
