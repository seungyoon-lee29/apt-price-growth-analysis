"""
pipeline.py
-----------
CSV 기반 오피스텔 가격 스크리닝 파이프라인.

실행:
    python pipeline.py
    python pipeline.py --skip-geocode   # 지오코딩 스킵 (캐시 사용)
"""

import argparse
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from load_csv import load_officetel_trade, load_officetel_rent, load_subway_stations
from geocode import geocode_buildings
from enrich import add_age_segment, add_area_segment, add_zone, add_subway_segment
from screen import monthly_price_trend, estimate_rental_yield, find_underpriced_trades, screen
from visualize import generate_all_charts
from config import REPORT_DIR, CHART_DIR


def run(skip_geocode: bool = False):
    print("=" * 60)
    print("  서울 오피스텔 가격 스크리닝 파이프라인")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. CSV 로드
    # ------------------------------------------------------------------
    print("\n[1/6] CSV 데이터 로드")
    trade = load_officetel_trade()
    rent = load_officetel_rent()
    stations = load_subway_stations()
    print(f"  매매: {len(trade):,}건 | 전월세: {len(rent):,}건 | 지하철역: {len(stations)}개")
    print(f"  매매 기간: {trade['deal_ym'].min()} ~ {trade['deal_ym'].max()}")
    print(f"  지역: {trade['region'].nunique()}개 구/시")

    # ------------------------------------------------------------------
    # 2. 세그먼트 부착 (연차/면적/권역)
    # ------------------------------------------------------------------
    print("\n[2/6] 세그먼트 분류")
    trade = add_age_segment(trade)
    trade = add_area_segment(trade)
    trade = add_zone(trade)
    rent = add_age_segment(rent)
    rent = add_area_segment(rent)
    rent = add_zone(rent)
    print(f"  연차: {trade['age_segment'].value_counts().to_dict()}")
    print(f"  면적: {trade['area_segment'].value_counts().to_dict()}")
    print(f"  권역: {trade['zone'].value_counts().to_dict()}")

    # ------------------------------------------------------------------
    # 3. 지오코딩 + 역세권 판정
    # ------------------------------------------------------------------
    print("\n[3/6] 지오코딩 & 역세권 판정")
    geocoded = geocode_buildings(trade, rent, skip_api=skip_geocode)
    trade = add_subway_segment(trade, stations, geocoded)
    rent = add_subway_segment(rent, stations, geocoded)
    print(f"  역세권: {trade['subway_segment'].value_counts().to_dict()}")

    # ------------------------------------------------------------------
    # 4. 분석
    # ------------------------------------------------------------------
    print("\n[4/6] 가격 추이 & 수익률 분석")

    # 권역별 추이
    trend_zone = monthly_price_trend(trade, ["zone"])
    trend_zone_age = monthly_price_trend(trade, ["zone", "age_segment"])
    trend_subway = monthly_price_trend(trade, ["subway_segment"])
    trend_area = monthly_price_trend(trade, ["area_segment"])

    # 수익률
    yield_df = estimate_rental_yield(trade, rent)
    print(f"  수익률 산출 단지: {len(yield_df)}개")

    # 저평가 거래
    under = find_underpriced_trades(trade)
    print(f"  저평가 의심 거래: {len(under)}건")

    # 최종 스크리닝
    screened = screen(trade, yield_df, trend_zone_age)
    print(f"  스크리닝 통과 단지: {len(screened)}개")

    # ------------------------------------------------------------------
    # 5. 리포트 저장
    # ------------------------------------------------------------------
    print("\n[5/6] 리포트 저장")

    trend_zone.to_csv(REPORT_DIR / "trend_zone.csv", index=False, encoding="utf-8-sig")
    trend_zone_age.to_csv(REPORT_DIR / "trend_zone_age.csv", index=False, encoding="utf-8-sig")
    trend_subway.to_csv(REPORT_DIR / "trend_subway.csv", index=False, encoding="utf-8-sig")
    trend_area.to_csv(REPORT_DIR / "trend_area.csv", index=False, encoding="utf-8-sig")
    yield_df.to_csv(REPORT_DIR / "rental_yield.csv", index=False, encoding="utf-8-sig")
    under.to_csv(REPORT_DIR / "underpriced_trades.csv", index=False, encoding="utf-8-sig")
    screened.to_csv(REPORT_DIR / "screened.csv", index=False, encoding="utf-8-sig")

    # 전체 enriched 데이터도 저장
    trade.to_csv(REPORT_DIR / "trade_enriched.csv", index=False, encoding="utf-8-sig")
    rent.to_csv(REPORT_DIR / "rent_enriched.csv", index=False, encoding="utf-8-sig")

    print(f"  저장 위치: {REPORT_DIR}")

    # ------------------------------------------------------------------
    # 6. 차트 생성
    # ------------------------------------------------------------------
    print("\n[6/6] 차트 생성")
    generate_all_charts(trade, trend_zone, trend_zone_age, trend_subway, yield_df)

    # ------------------------------------------------------------------
    # 요약 출력
    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("  파이프라인 완료!")
    print("=" * 60)
    print(f"\n리포트: {REPORT_DIR}")
    print(f"차트:   {CHART_DIR}")
    print(f"\n주요 결과:")
    print(f"  - 매매 거래 {len(trade):,}건 분석")
    print(f"  - 전월세 거래 {len(rent):,}건 분석")

    if not yield_df.empty:
        median_yield = yield_df["gross_yield_pct"].median()
        print(f"  - 중위 임대수익률: {median_yield:.2f}%")

    if not screened.empty:
        print(f"  - 저평가+고수익 스크리닝 단지: {len(screened)}개")
        print("\n  [상위 10 스크리닝 단지]")
        top = screened.head(10)
        for _, r in top.iterrows():
            name = f"{r['region']} {r['dong']} {r['building_name']}"
            yld = r.get("gross_yield_pct", 0)
            pp = r.get("median_pp", 0)
            print(f"    {name} | 평당가 {pp:,.0f}만 | 수익률 {yld:.1f}%")

    return {
        "trade": trade,
        "rent": rent,
        "trend_zone": trend_zone,
        "trend_zone_age": trend_zone_age,
        "yield": yield_df,
        "screened": screened,
        "underpriced": under,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--skip-geocode", action="store_true", help="지오코딩 스킵")
    args = p.parse_args()
    run(skip_geocode=args.skip_geocode)
