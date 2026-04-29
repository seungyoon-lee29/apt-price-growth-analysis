"""
서울 오피스텔 월별 가격/거래량 추이 분석.

- 지역: 서울특별시
- 역세권 구분: 역세권(1급+일반) / 비역세권
- 면적 구간: 40㎡ 이하 / 40~60㎡ / 60~85㎡
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MPLCONFIG_DIR = BASE_DIR / ".mplconfig"
MPLCONFIG_DIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPLCONFIG_DIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd

from config import CHART_DIR, REPORT_DIR

AREA_ORDER = ["40㎡ 이하", "40~60㎡", "60~85㎡"]
SUBWAY_ORDER = ["역세권", "비역세권"]
SUBWAY_COLORS = {
    "역세권": "#1565C0",
    "비역세권": "#EF6C00",
}
METRIC_ORDER = ["매매", "전세", "월세"]


def setup_korean_font() -> None:
    candidates = [
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/NanumGothic.ttf",
    ]
    for font_path in candidates:
        if Path(font_path).exists():
            prop = fm.FontProperties(fname=font_path)
            plt.rcParams["font.family"] = prop.get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    trade = pd.read_csv(REPORT_DIR / "trade_enriched.csv", parse_dates=["deal_date"])
    rent = pd.read_csv(REPORT_DIR / "rent_enriched.csv", parse_dates=["deal_date"])

    trade = trade[trade["sido"] == "서울특별시"].copy()
    rent = rent[rent["sido"] == "서울특별시"].copy()
    return trade, rent


def add_requested_segments(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["subway_group"] = out["subway_segment"].map(
        {
            "1급역세권": "역세권",
            "일반역세권": "역세권",
            "비역세권": "비역세권",
        }
    )
    out["area_bucket"] = pd.cut(
        out["area_m2"],
        bins=[0, 40, 60, 85],
        labels=AREA_ORDER,
        right=True,
        include_lowest=True,
    )
    out = out[out["subway_group"].isin(SUBWAY_ORDER)].copy()
    out = out[out["area_bucket"].notna()].copy()
    out["area_bucket"] = pd.Categorical(out["area_bucket"], categories=AREA_ORDER, ordered=True)
    return out


def monthly_price_trend(df: pd.DataFrame, value_col: str, metric: str) -> pd.DataFrame:
    base = add_requested_segments(df)
    base = base.dropna(subset=["deal_date", value_col]).copy()
    base["ym"] = base["deal_date"].dt.to_period("M").astype(str)

    trend = (
        base.groupby(["ym", "subway_group", "area_bucket"], observed=True)[value_col]
        .agg(median="median", mean="mean", count="count")
        .reset_index()
        .sort_values(["area_bucket", "subway_group", "ym"])
    )
    trend["metric"] = metric
    return trend


def monthly_volume_trend(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    base = add_requested_segments(df)
    base = base.dropna(subset=["deal_date"]).copy()
    base["ym"] = base["deal_date"].dt.to_period("M").astype(str)

    trend = (
        base.groupby(["ym", "subway_group", "area_bucket"], observed=True)
        .size()
        .reset_index(name="volume")
        .sort_values(["area_bucket", "subway_group", "ym"])
    )
    trend["metric"] = metric
    return trend


def save_csv(df: pd.DataFrame, filename: str) -> Path:
    path = REPORT_DIR / filename
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def _format_thousands(x: float, _: int) -> str:
    return f"{int(x):,}"


def plot_price_grid(
    trend_df: pd.DataFrame,
    *,
    title: str,
    ylabel: str,
    filename: str,
) -> Path:
    fig, axes = plt.subplots(1, len(AREA_ORDER), figsize=(18, 5), sharey=False)

    for ax, area_bucket in zip(axes, AREA_ORDER):
        subset = trend_df[trend_df["area_bucket"] == area_bucket]
        for subway_group in SUBWAY_ORDER:
            line = subset[subset["subway_group"] == subway_group].sort_values("ym")
            if line.empty:
                continue
            ax.plot(
                line["ym"],
                line["median"],
                marker="o",
                linewidth=2,
                markersize=4,
                color=SUBWAY_COLORS[subway_group],
                label=subway_group,
            )
        ax.set_title(area_bucket)
        ax.set_xlabel("계약년월")
        ax.grid(alpha=0.3)
        ax.tick_params(axis="x", rotation=45, labelsize=8)
        ax.yaxis.set_major_formatter(FuncFormatter(_format_thousands))

    axes[0].set_ylabel(ylabel)
    axes[0].legend(loc="best")
    fig.suptitle(title)
    fig.tight_layout()

    path = CHART_DIR / filename
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_volume_grid(volume_df: pd.DataFrame, filename: str) -> Path:
    fig, axes = plt.subplots(len(METRIC_ORDER), len(AREA_ORDER), figsize=(18, 12), sharex=False, sharey=False)

    for row_idx, metric in enumerate(METRIC_ORDER):
        metric_df = volume_df[volume_df["metric"] == metric]
        for col_idx, area_bucket in enumerate(AREA_ORDER):
            ax = axes[row_idx, col_idx]
            subset = metric_df[metric_df["area_bucket"] == area_bucket]
            for subway_group in SUBWAY_ORDER:
                line = subset[subset["subway_group"] == subway_group].sort_values("ym")
                if line.empty:
                    continue
                ax.plot(
                    line["ym"],
                    line["volume"],
                    marker="o",
                    linewidth=2,
                    markersize=3,
                    color=SUBWAY_COLORS[subway_group],
                    label=subway_group,
                )
            if row_idx == 0:
                ax.set_title(area_bucket)
            if col_idx == 0:
                ax.set_ylabel(f"{metric}\n거래건수")
            ax.grid(alpha=0.3)
            ax.tick_params(axis="x", rotation=45, labelsize=8)
            ax.yaxis.set_major_formatter(FuncFormatter(_format_thousands))

    handles, labels = axes[0, 0].get_legend_handles_labels()
    if handles:
        fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False)
    fig.suptitle("서울 오피스텔 거래량 추이: 역세권/비역세권 x 면적 구간")
    fig.tight_layout(rect=(0, 0, 1, 0.97))

    path = CHART_DIR / filename
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def build_change_summary(trend_df: pd.DataFrame, value_col: str, series_name: str) -> pd.DataFrame:
    rows = []
    for (subway_group, area_bucket), group in trend_df.groupby(
        ["subway_group", "area_bucket"], observed=True
    ):
        group = group.sort_values("ym").reset_index(drop=True)
        if group.empty:
            continue
        first = group.iloc[0]
        latest = group.iloc[-1]
        change_pct = None
        if pd.notna(first[value_col]) and first[value_col] != 0 and pd.notna(latest[value_col]):
            change_pct = (latest[value_col] / first[value_col] - 1) * 100
        rows.append(
            {
                "series": series_name,
                "subway_group": subway_group,
                "area_bucket": area_bucket,
                "start_ym": first["ym"],
                "start_value": first[value_col],
                "latest_ym": latest["ym"],
                "latest_value": latest[value_col],
                "change_pct": change_pct,
                "latest_count": latest["count"] if "count" in latest.index else latest.get("volume"),
            }
        )
    return pd.DataFrame(rows).sort_values(["series", "area_bucket", "subway_group"])


def main() -> None:
    setup_korean_font()
    trade, rent = load_inputs()

    sale_trend = monthly_price_trend(trade, "price_manwon", "매매")
    jeonse_trend = monthly_price_trend(rent[rent["contract_type"] == "전세"], "deposit_manwon", "전세")
    wolse_trend = monthly_price_trend(rent[rent["contract_type"] == "월세"], "monthly_rent", "월세")

    sale_volume = monthly_volume_trend(trade, "매매")
    jeonse_volume = monthly_volume_trend(rent[rent["contract_type"] == "전세"], "전세")
    wolse_volume = monthly_volume_trend(rent[rent["contract_type"] == "월세"], "월세")
    volume_trend = pd.concat([sale_volume, jeonse_volume, wolse_volume], ignore_index=True)

    save_csv(sale_trend, "seoul_sale_trend_subway_area.csv")
    save_csv(jeonse_trend, "seoul_jeonse_trend_subway_area.csv")
    save_csv(wolse_trend, "seoul_wolse_trend_subway_area.csv")
    save_csv(volume_trend, "seoul_volume_trend_subway_area.csv")

    summary = pd.concat(
        [
            build_change_summary(sale_trend, "median", "매매가격"),
            build_change_summary(jeonse_trend, "median", "전세가격"),
            build_change_summary(wolse_trend, "median", "월세가격"),
            build_change_summary(sale_volume, "volume", "매매거래량"),
            build_change_summary(jeonse_volume, "volume", "전세거래량"),
            build_change_summary(wolse_volume, "volume", "월세거래량"),
        ],
        ignore_index=True,
    )
    save_csv(summary, "seoul_trend_change_summary.csv")

    plot_price_grid(
        sale_trend,
        title="서울 오피스텔 매매가격 추이: 역세권/비역세권 x 면적 구간",
        ylabel="매매가격 중위값 (만원)",
        filename="seoul_sale_trend_subway_area.png",
    )
    plot_price_grid(
        jeonse_trend,
        title="서울 오피스텔 전세가격 추이: 역세권/비역세권 x 면적 구간",
        ylabel="전세보증금 중위값 (만원)",
        filename="seoul_jeonse_trend_subway_area.png",
    )
    plot_price_grid(
        wolse_trend,
        title="서울 오피스텔 월세가격 추이: 역세권/비역세권 x 면적 구간",
        ylabel="월세 중위값 (만원)",
        filename="seoul_wolse_trend_subway_area.png",
    )
    plot_volume_grid(
        volume_trend,
        filename="seoul_volume_trend_subway_area.png",
    )

    print("서울 오피스텔 세부 추이 분석 완료")
    print(f"- 리포트: {REPORT_DIR}")
    print(f"- 차트: {CHART_DIR}")


if __name__ == "__main__":
    main()
