"""
파이프라인 로직 스모크 테스트.
실제 API 호출 없이 mock 데이터로 enrich + screen 이 동작하는지 확인.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

from src import enrich, screen

# ------------------------------------------------------------------
# Mock 거래 데이터: 서울 3개 구 × 12개월 × 단지 4개
# ------------------------------------------------------------------
rng = np.random.default_rng(42)

regions = ["강남구", "마포구", "노원구"]
zone_map = {"강남구": "강남권", "마포구": "마용성", "노원구": "동북권"}
buildings = [
    # (region, dong, name, build_year, base_pp)
    ("강남구", "역삼동", "A오피스텔",  2023, 4500),
    ("강남구", "삼성동", "B오피스텔",  2010, 3700),
    ("마포구", "공덕동", "C오피스텔",  2022, 3200),
    ("마포구", "상수동", "D오피스텔",  2005, 2400),
    ("노원구", "상계동", "E오피스텔",  2024, 1800),
    ("노원구", "중계동", "F오피스텔",  2000, 1300),
]

rows = []
for ym in pd.period_range("2024-01", "2026-04", freq="M"):
    for region, dong, name, byear, base_pp in buildings:
        for _ in range(rng.integers(2, 6)):
            area = float(rng.choice([24, 35, 45, 60, 85]))
            # 시간이 지날수록 오르는 추세 + 잡음
            months_from_start = (ym.year - 2024) * 12 + (ym.month - 1)
            trend_factor = 1 + 0.005 * months_from_start
            pp = base_pp * trend_factor * rng.normal(1.0, 0.06)
            price = pp * area * 0.3025
            rows.append(
                dict(
                    region=region,
                    dong=dong,
                    building_name=name,
                    area_m2=area,
                    price_manwon=round(price),
                    floor=int(rng.integers(2, 20)),
                    build_year=byear,
                    deal_date=pd.Timestamp(year=ym.year, month=ym.month, day=int(rng.integers(1, 28))),
                )
            )

trade = pd.DataFrame(rows)
trade["price_per_pyeong"] = trade["price_manwon"] / (trade["area_m2"] * 0.3025)

# Mock 전월세
rent_rows = []
for region, dong, name, byear, base_pp in buildings:
    for _ in range(30):
        area = float(rng.choice([24, 35, 45, 60]))
        deposit = float(rng.choice([1000, 2000, 3000, 5000]))
        monthly = float(rng.choice([50, 70, 90, 120, 150]))
        rent_rows.append(
            dict(
                region=region, dong=dong, building_name=name,
                area_m2=area, deposit_manwon=deposit, monthly_rent=monthly,
                floor=int(rng.integers(2, 20)), build_year=byear,
                deal_date=pd.Timestamp("2026-02-15"),
                contract_type="월세",
            )
        )
rent = pd.DataFrame(rent_rows)

# ------------------------------------------------------------------
# Enrich
# ------------------------------------------------------------------
print("=" * 60)
print("1. Enrich")
print("=" * 60)
trade = enrich.add_age_segment(trade, ref_year=2026)
trade = enrich.add_area_segment(trade)
trade = enrich.add_zone(trade)
rent = enrich.add_age_segment(rent, ref_year=2026)
rent = enrich.add_zone(rent)
trade["subway_segment"] = "미상"  # 지오코딩 스킵

print(trade[["region", "zone", "building_name", "age_years", "age_segment", "area_segment"]].head(8))
print()
print("세그먼트 분포:")
print(trade.groupby(["zone", "age_segment"]).size().rename("거래건수"))

# ------------------------------------------------------------------
# 가격 추이
# ------------------------------------------------------------------
print()
print("=" * 60)
print("2. 권역×연차별 월별 평당가 추이 (샘플)")
print("=" * 60)
trend = screen.monthly_price_trend(trade, ["zone", "age_segment"])
print(trend.head(10))

# ------------------------------------------------------------------
# 임대 수익률
# ------------------------------------------------------------------
print()
print("=" * 60)
print("3. 단지별 임대 수익률 추정")
print("=" * 60)
y = screen.estimate_rental_yield(trade, rent)
print(y)

# ------------------------------------------------------------------
# 저평가 거래 탐지
# ------------------------------------------------------------------
print()
print("=" * 60)
print("4. 저평가 거래 (z-score <= -1.5)")
print("=" * 60)
under = screen.find_underpriced_trades(trade, lookback_months=6, min_samples=3, z_threshold=-1.3)
print(under.head(10))

# ------------------------------------------------------------------
# 최종 스크리닝
# ------------------------------------------------------------------
print()
print("=" * 60)
print("5. 최종 스크리닝")
print("=" * 60)
result = screen.screen(trade, y, trend, segment_cols=("zone", "age_segment"))
print(result)
