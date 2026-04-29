"""
visualize.py
------------
오피스텔 매매/전월세 분석 차트 생성.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import numpy as np
from pathlib import Path

from config import CHART_DIR

# ------------------------------------------------------------------
# 한글 폰트 설정 (macOS)
# ------------------------------------------------------------------
def _setup_korean_font():
    candidates = [
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/Library/Fonts/NanumGothic.ttf",
    ]
    for fp in candidates:
        if Path(fp).exists():
            prop = fm.FontProperties(fname=fp)
            plt.rcParams["font.family"] = prop.get_name()
            break
    plt.rcParams["axes.unicode_minus"] = False

_setup_korean_font()

COLORS = [
    "#2196F3", "#FF5722", "#4CAF50", "#9C27B0", "#FF9800",
    "#00BCD4", "#E91E63", "#8BC34A", "#3F51B5", "#FFC107",
    "#607D8B", "#795548",
]


# ------------------------------------------------------------------
# 1. 권역별 평당가 추이
# ------------------------------------------------------------------
def plot_zone_trend(trend_df: pd.DataFrame, title: str = "권역별 오피스텔 평당가 추이"):
    if trend_df.empty:
        return
    fig, ax = plt.subplots(figsize=(14, 7))
    groups = trend_df.groupby("zone") if "zone" in trend_df.columns else trend_df.groupby(trend_df.columns[0])

    for i, (name, g) in enumerate(groups):
        g = g.sort_values("ym")
        ax.plot(g["ym"], g["median"], marker="o", markersize=4,
                color=COLORS[i % len(COLORS)], label=name, linewidth=1.5)

    ax.set_xlabel("계약년월")
    ax.set_ylabel("평당가 중위값 (만원)")
    ax.set_title(title)
    _rotate_xlabels(ax, g)
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "trend_zone.png", dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------
# 2. 권역 x 연차별 추이
# ------------------------------------------------------------------
def plot_zone_age_trend(trend_df: pd.DataFrame):
    if trend_df.empty:
        return
    fig, ax = plt.subplots(figsize=(14, 7))
    for i, ((zone, age), g) in enumerate(trend_df.groupby(["zone", "age_segment"])):
        g = g.sort_values("ym")
        ax.plot(g["ym"], g["median"], marker="o", markersize=3,
                color=COLORS[i % len(COLORS)], label=f"{zone} {age}", linewidth=1.2)

    ax.set_xlabel("계약년월")
    ax.set_ylabel("평당가 중위값 (만원)")
    ax.set_title("권역 x 준공연차별 오피스텔 평당가 추이")
    _rotate_xlabels(ax, g)
    ax.legend(loc="best", fontsize=7, ncol=3)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "trend_zone_age.png", dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------
# 3. 역세권별 추이
# ------------------------------------------------------------------
def plot_subway_trend(trend_df: pd.DataFrame):
    if trend_df.empty:
        return
    fig, ax = plt.subplots(figsize=(14, 7))
    for i, (seg, g) in enumerate(trend_df.groupby("subway_segment")):
        g = g.sort_values("ym")
        ax.plot(g["ym"], g["median"], marker="s", markersize=4,
                color=COLORS[i % len(COLORS)], label=seg, linewidth=1.5)

    ax.set_xlabel("계약년월")
    ax.set_ylabel("평당가 중위값 (만원)")
    ax.set_title("역세권 세그먼트별 오피스텔 평당가 추이")
    _rotate_xlabels(ax, g)
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "trend_subway.png", dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------
# 4. 구별 거래량 + 평균 가격 바 차트
# ------------------------------------------------------------------
def plot_region_summary(trade_df: pd.DataFrame):
    if trade_df.empty:
        return
    agg = (
        trade_df.groupby("region")
        .agg(
            count=("price_manwon", "count"),
            median_price=("price_per_pyeong", "median"),
        )
        .sort_values("median_price", ascending=True)
        .reset_index()
    )

    fig, ax1 = plt.subplots(figsize=(12, 8))
    bars = ax1.barh(agg["region"], agg["count"], color="#2196F3", alpha=0.7, label="거래건수")
    ax1.set_xlabel("거래건수")
    ax1.set_title("구별 오피스텔 매매 거래량 및 평당가")

    ax2 = ax1.twiny()
    ax2.plot(agg["median_price"], agg["region"], "r-o", markersize=5, label="평당가 중위값")
    ax2.set_xlabel("평당가 중위값 (만원)", color="red")

    ax1.legend(loc="lower right")
    ax2.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(CHART_DIR / "region_summary.png", dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------
# 5. 월별 전체 거래량 추이
# ------------------------------------------------------------------
def plot_monthly_volume(trade_df: pd.DataFrame):
    if trade_df.empty:
        return
    df = trade_df.dropna(subset=["deal_date"]).copy()
    df["ym"] = df["deal_date"].dt.to_period("M").astype(str)
    vol = df.groupby("ym").size().reset_index(name="count").sort_values("ym")

    fig, ax = plt.subplots(figsize=(14, 5))
    ax.bar(range(len(vol)), vol["count"], color="#4CAF50", alpha=0.8)
    ax.set_xticks(range(len(vol)))
    ax.set_xticklabels(vol["ym"], rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("거래건수")
    ax.set_title("월별 오피스텔 매매 거래량 추이")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "monthly_volume.png", dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------
# 6. 수익률 분포
# ------------------------------------------------------------------
def plot_yield_distribution(yield_df: pd.DataFrame):
    if yield_df.empty:
        return
    fig, ax = plt.subplots(figsize=(12, 6))
    data = yield_df["gross_yield_pct"].dropna()
    data = data[(data > 0) & (data < 15)]  # 이상치 제외
    ax.hist(data, bins=50, color="#FF9800", alpha=0.8, edgecolor="white")
    ax.axvline(data.median(), color="red", linestyle="--", label=f"중위값: {data.median():.2f}%")
    ax.set_xlabel("총 수익률 (%)")
    ax.set_ylabel("단지 수")
    ax.set_title("오피스텔 단지별 임대 수익률 분포")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "yield_distribution.png", dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------
# 7. 면적 세그먼트별 가격 박스플롯
# ------------------------------------------------------------------
def plot_area_boxplot(trade_df: pd.DataFrame):
    if trade_df.empty:
        return
    df = trade_df.dropna(subset=["area_segment", "price_per_pyeong"]).copy()
    order = ["초소형", "소형", "중형", "대형"]
    order = [o for o in order if o in df["area_segment"].unique()]

    fig, ax = plt.subplots(figsize=(10, 6))
    data = [df[df["area_segment"] == seg]["price_per_pyeong"].values for seg in order]
    bp = ax.boxplot(data, labels=order, patch_artist=True, showfliers=False)
    for i, patch in enumerate(bp["boxes"]):
        patch.set_facecolor(COLORS[i % len(COLORS)])
        patch.set_alpha(0.7)
    ax.set_ylabel("평당가 (만원)")
    ax.set_title("면적 세그먼트별 오피스텔 평당가 분포")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "area_boxplot.png", dpi=150)
    plt.close(fig)


# ------------------------------------------------------------------
# helper
# ------------------------------------------------------------------
def _rotate_xlabels(ax, sample_g):
    xticks = ax.get_xticks()
    labels = ax.get_xticklabels()
    if len(labels) > 8:
        for i, label in enumerate(labels):
            if i % 2 != 0:
                label.set_visible(False)
    ax.tick_params(axis="x", rotation=45)


def generate_all_charts(trade_df, trend_zone, trend_zone_age, trend_subway, yield_df):
    """모든 차트 생성."""
    print("[차트] 권역별 평당가 추이")
    plot_zone_trend(trend_zone)

    print("[차트] 권역 x 연차별 추이")
    plot_zone_age_trend(trend_zone_age)

    print("[차트] 역세권별 추이")
    plot_subway_trend(trend_subway)

    print("[차트] 구별 거래량/평당가")
    plot_region_summary(trade_df)

    print("[차트] 월별 거래량")
    plot_monthly_volume(trade_df)

    print("[차트] 수익률 분포")
    plot_yield_distribution(yield_df)

    print("[차트] 면적별 박스플롯")
    plot_area_boxplot(trade_df)

    print(f"[차트] 저장 완료: {CHART_DIR}")
