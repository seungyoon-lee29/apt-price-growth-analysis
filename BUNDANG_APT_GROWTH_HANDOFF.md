# Bundang Apartment Growth Analysis Handoff

Generated: 2026-04-29 Asia/Seoul

## Current Goal

분당구 아파트 매매 실거래가로 특정 기준 시점 대비 가격 상승률을 비교한다.

핵심 질문:

- `2017년 5월 가격이 2022년 5월이 되었을 때 얼마나 올랐는가?`
- `2025년 6월 가격이 현재 시점 가격이 되었을 때 얼마나 올랐는가?`
- 단월 비교와 3개월 창 비교를 모두 산출한다.
- 거래량이 너무 적은 단지는 별도 필터링해서 본다.

## Political Period Labels Used In This Analysis

사용자 지정 분석 라벨:

- `2017년 5월 ~ 2022년 5월`: 문재인 정부 기간
- `2025년 6월 ~ 현재`: 이재명 정부 기간

이 라벨은 가격 상승률 비교 기간을 부르는 이름으로 사용한다.

## Data Source

- API: `국토교통부_아파트 매매 실거래가 상세 자료`
- Endpoint: `RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev`
- Region: `성남시 분당구`
- `LAWD_CD`: `41135`
- API key env name used: `MOLIT_APT_TRADE_DETAIL_API_KEY`

## Important Implementation Note

`scripts/analyze_bundang_apt_growth.py` was previously added for reusable analysis, but was removed during cleanup because its XML cache behavior could mislead later reruns.

Known caveat:

- The removed script's XML cache could cache only the first API page for a month.
- Current saved results were produced with no-cache API fetches for the policy comparison windows.
- If continuing this work with new regions or periods, recreate a clean no-cache/page-complete analysis script rather than restoring the removed script.

## Calculation Methods Used

### Method 1: Exact Month-To-Month

Question answered:

- `2017년 5월 -> 2022년 5월`

Formula:

```text
growth_pct = 2022-05 median price_per_pyeong / 2017-05 median price_per_pyeong - 1
```

Outputs:

- `output/reports/bundang_apt_growth_201705_vs_202205_by_dong.csv`
- `output/reports/bundang_apt_growth_201705_vs_202205_by_apt.csv`
- `output/reports/bundang_apt_growth_201705_vs_202205_by_apt_avg_volume.csv`

Key result, by dong:

- 정자동: +161.01%
- 이매동: +149.39%
- 삼평동: +144.67%
- 분당동: +139.17%
- 구미동: +134.16%
- 수내동: +130.22%
- 서현동: +124.09%
- 판교동: +121.57%
- 백현동: +108.28%
- 운중동: +91.88%
- 금곡동: +86.03%
- 야탑동: +81.04%

Important caveat:

- 2022년 5월 거래량은 59건으로 적어서 단지별 결과는 표본 수를 같이 봐야 한다.

### Method 2: Centered 3-Month Window

Question answered:

- `2017년 5월 무렵 가격 -> 2022년 5월 무렵 가격`

Window:

- Base: `2017-04-01 ~ 2017-06-30`
- End: `2022-04-01 ~ 2022-06-30`

Formula:

```text
growth_pct = end-window median price_per_pyeong / base-window median price_per_pyeong - 1
```

API rows fetched no-cache:

- 201704: 716
- 201705: 1,404
- 201706: 1,292
- 202204: 231
- 202205: 174
- 202206: 74

Outputs:

- `output/reports/bundang_apt_trades_201704_201706_202204_202206.csv`
- `output/reports/bundang_apt_growth_201704_201706_vs_202204_202206_by_dong.csv`
- `output/reports/bundang_apt_growth_201704_201706_vs_202204_202206_by_apt.csv`
- `output/reports/bundang_apt_growth_201704_201706_vs_202204_202206_by_apt_avg_volume.csv`

Key result, by dong:

- 금곡동: +148.48%
- 이매동: +143.31%
- 분당동: +132.13%
- 수내동: +131.07%
- 서현동: +126.92%
- 삼평동: +125.71%
- 정자동: +124.42%
- 구미동: +119.38%
- 야탑동: +114.70%
- 백현동: +113.35%
- 운중동: +111.01%
- 판교동: +79.77%

Filtered apartment method:

- Keep only apartments with transactions in both windows.
- `two_window_count = base_count + end_count`
- Average `two_window_count`: 25.58
- Average-or-above output: `bundang_apt_growth_201704_201706_vs_202204_202206_by_apt_avg_volume.csv`

## Interpretation Guidance

- Use Method 1 when the user specifically asks for exact `2017년 5월` vs `2022년 5월`.
- Use Method 2 as the more stable price movement estimate because it reduces noise from low monthly transaction counts.
- For apartment-level rankings, always show `base_count`, `end_count`, and total count because several high-growth entries can be driven by small end-window sample sizes.

## Lee Jae-myung Period Analysis

User-defined period:

- `2025년 6월 ~ 현재`

Most recent run date:

- 2026-04-29 Asia/Seoul

Preferred stable method:

- Base window: `2025-06-01 ~ 2025-08-31`
- End window: `2026-02-01 ~ 2026-04-30` using data available as of 2026-04-29
- Formula: `end-window median price_per_pyeong / base-window median price_per_pyeong - 1`

No-cache API rows fetched:

- 202506: 1,431
- 202507: 251
- 202508: 368
- 202602: 282
- 202603: 235
- 202604: 162

Outputs:

- `output/reports/bundang_apt_trades_202506_202508_202602_202604.csv`
- `output/reports/bundang_apt_growth_202506_202508_vs_202602_202604_by_dong.csv`
- `output/reports/bundang_apt_growth_202506_202508_vs_202602_202604_by_apt.csv`
- `output/reports/bundang_apt_growth_202506_202508_vs_202602_202604_by_apt_avg_volume.csv`
- Reference exact month output: `output/reports/bundang_apt_growth_202506_vs_202604_by_dong.csv`

Key result, 3-month window by dong:

- 분당동: +54.82%
- 정자동: +54.30%
- 구미동: +50.23%
- 서현동: +41.22%
- 운중동: +34.06%
- 수내동: +33.40%
- 야탑동: +32.97%
- 금곡동: +28.69%
- 이매동: +28.27%
- 백현동: +17.14%
- 삼평동: +13.51%
- 대장동: +8.37%
- 판교동: +4.55%

Reference exact month by dong, `2025-06 -> 2026-04`:

- 정자동: +52.22%
- 구미동: +48.15%
- 수내동: +43.26%
- 삼평동: +40.08%
- 야탑동: +34.91%
- 이매동: +31.77%
- 금곡동: +31.61%
- 서현동: +30.78%
- 분당동: +23.01%
- 운중동: +20.35%
- 백현동: +19.99%
- 대장동: +11.64%
- 판교동: +11.53%

## Moon-Like Remaining Upside Projection

Question:

- 이재명 정부 기간 가격 상승이 문재인 정부 기간과 같은 총상승률에 도달한다고 보면, 현재 가격에서 얼마나 더 상승여력이 남았는가?

User-specified term:

- 이재명 정부: `2025-06-03 ~ 2030-06-03`

Overall Bundang 3-month-window basis:

- 문재인 정부 비교: `2017-04~06 -> 2022-04~06`
- 이재명 정부 현재 비교: `2025-06~08 -> 2026-02~04`

Overall Bundang result:

- 문재인 정부 5년 총상승률: +120.34%
- 문재인 정부 연평균 상승률(CAGR): +17.12%
- 이재명 정부 현재까지 상승률: +30.77%
- 이재명 정부 현재까지 연율화 상승률: +34.57%
- 문재인 정부 총상승률과 같아진다고 볼 때 현재 이후 잔여 상승률: +68.50%
- 현재 6억 아파트가 문재인 정부식 총상승률 목표에 도달할 경우: 약 10.11억

Reference projection if current annualized pace continues mechanically until 2030-06-03:

- 현재 이후 잔여 상승률: +237.37%
- 현재 6억 기준: 약 20.24억
- This is a mechanical extrapolation only and likely too aggressive because the current period is short and high-volatility.

Output:

- `output/reports/bundang_apt_upside_moon_like_vs_lee_current_by_dong.csv`

## Suwon Yeongtong Comparison

Region:

- 수원시 영통구
- `LAWD_CD`: `41117`

Same methods as Bundang were applied.

Outputs:

- `output/reports/suwon_yeongtong_apt_trades_policy_windows.csv`
- `output/reports/suwon_yeongtong_apt_growth_201704_201706_vs_202204_202206_by_dong.csv`
- `output/reports/suwon_yeongtong_apt_growth_202506_202508_vs_202602_202604_by_dong.csv`
- `output/reports/suwon_yeongtong_apt_growth_201704_201706_vs_202204_202206_by_apt.csv`
- `output/reports/suwon_yeongtong_apt_growth_202506_202508_vs_202602_202604_by_apt.csv`
- `output/reports/suwon_yeongtong_apt_growth_201704_201706_vs_202204_202206_by_apt_avg_volume.csv`
- `output/reports/suwon_yeongtong_apt_growth_202506_202508_vs_202602_202604_by_apt_avg_volume.csv`
- `output/reports/suwon_yeongtong_apt_upside_moon_like_vs_lee_current_by_dong.csv`

API rows fetched:

- 201704: 458
- 201705: 610
- 201706: 637
- 202204: 197
- 202205: 163
- 202206: 107
- 202506: 852
- 202507: 379
- 202508: 369
- 202602: 522
- 202603: 571
- 202604: 497

Overall Yeongtong result:

- 문재인 정부 3개월 창 총상승률: +95.76%
- 문재인 정부 연평균 상승률(CAGR): +14.38%
- 이재명 정부 현재 3개월 창 상승률: +1.74%
- 이재명 정부 현재까지 연율화 상승률: +1.93%
- 문재인 정부 총상승률과 같아진다고 볼 때 현재 이후 잔여 상승률: +92.41%
- 현재 6억 아파트가 문재인 정부식 총상승률 목표에 도달할 경우: 약 11.54억
- 현재 속도 단순 연장 시 2030-06-03 가격: 약 6.49억

Moon-period 3-month window by dong:

- 망포동: +166.92%
- 원천동: +117.30%
- 하동: +90.66%
- 매탄동: +89.79%
- 영통동: +87.73%
- 이의동: +83.82%
- 신동: +72.72%

Lee-period current 3-month window by dong:

- 매탄동: +8.87%
- 영통동: +6.41%
- 하동: +5.36%
- 신동: +3.93%
- 망포동: -4.29%
- 이의동: -11.66%
- 원천동: -18.35%

## Gwanggyo Sub-Area Check

광교는 영통구 데이터 안에서 두 가지 기준으로 별도 확인했다.

Definitions:

- `gwanggyo_dong_area`: `이의동`, `하동`, `원천동`
- `gwanggyo_named_apts`: 단지명에 `광교` 포함

Outputs:

- `output/reports/gwanggyo_area_growth_summary.csv`
- `output/reports/gwanggyo_dong_area_growth_201704_201706_vs_202204_202206_by_dong.csv`
- `output/reports/gwanggyo_dong_area_growth_202506_202508_vs_202602_202604_by_dong.csv`
- `output/reports/gwanggyo_dong_area_apt_growth_202506_202508_vs_202602_202604_avg_volume.csv`
- `output/reports/gwanggyo_named_apts_apt_growth_202506_202508_vs_202602_202604_avg_volume.csv`

Overall result:

- 광교 생활권(`이의동/하동/원천동`)
  - 문재인 정부 3개월 창 상승률: +86.20%
  - 이재명 정부 현재 3개월 창 상승률: -6.38%
  - 문재인 정부식 총상승률까지 간다고 볼 때 현재 이후 잔여 상승률: +98.88%
  - 현재 6억 기준 문재인 정부식 목표가: 약 11.93억
  - 현재 속도 단순 연장 시 2030-06-03 가격: 약 4.45억
- 광교명 단지(`apt_name` contains `광교`)
  - 문재인 정부 3개월 창 상승률: +92.77%
  - 이재명 정부 현재 3개월 창 상승률: +2.34%
  - 문재인 정부식 총상승률까지 간다고 볼 때 현재 이후 잔여 상승률: +88.36%
  - 현재 6억 기준 문재인 정부식 목표가: 약 11.30억
  - 현재 속도 단순 연장 시 2030-06-03 가격: 약 6.66억

광교 생활권 동별:

- 문재인 정부 3개월 창
  - 원천동: +117.30%
  - 하동: +90.66%
  - 이의동: +83.82%
- 이재명 정부 현재 3개월 창
  - 하동: +5.36%
  - 이의동: -11.66%
  - 원천동: -18.35%

광교명 단지 중 이재명 정부 현재 평균거래량 이상 상승률 상위:

- 광교호반베르디움: +24.37%
- 광교센트럴뷰: +19.32%
- 광교더리브: +15.93%
- 광교더포레스트: +11.11%
- 광교아이파크: +10.43%
- 광교중흥에스클래스: +2.28%
- 광교e편한세상: +1.82%

## Mixed-Use Apartment Exclusion Update

Generated: 2026-04-29 Asia/Seoul

User request:

- 주상복합 아파트를 제외한 버전으로 분당구, 수원시 영통구, 광교를 다시 계산한다.

Method:

- 국토부 아파트 실거래가 API 자체에는 `주상복합 여부` 필드가 없다.
- 보수적 제외 리스트를 별도 CSV로 만들었다.
- 기사/매물/단지 정보에서 주상복합으로 명시된 단지와 정자동 주상복합촌으로 기사에서 묶여 언급된 단지를 제외했다.
- 애매한 단지는 과도한 오분류를 피하기 위해 제외하지 않았다.

Exclusion list:

- `output/reports/mixed_use_exclusion_list.csv`

Removed trade files:

- `output/reports/bundang_apt_trades_policy_windows_removed_mixed_use.csv`
- `output/reports/suwon_yeongtong_apt_trades_policy_windows_removed_mixed_use.csv`

### Bundang, No Mixed-Use

Outputs:

- `output/reports/bundang_apt_trades_policy_windows_no_mixed_use.csv`
- `output/reports/bundang_apt_growth_201704_201706_vs_202204_202206_by_dong_no_mixed_use.csv`
- `output/reports/bundang_apt_growth_202506_202508_vs_202602_202604_by_dong_no_mixed_use.csv`
- `output/reports/bundang_apt_upside_moon_like_vs_lee_current_by_dong_no_mixed_use.csv`

Overall:

- Removed trades: 304
- 문재인 정부 3개월 창 상승률: +121.58%
- 이재명 정부 현재 3개월 창 상승률: +31.51%
- 문재인 정부식 총상승률까지 간다고 볼 때 현재 이후 잔여 상승률: +68.49%
- 현재 6억 기준 문재인 정부식 목표가: 약 10.11억
- 현재 속도 단순 연장 시 2030-06-03 가격: 약 20.77억

이재명 정부 현재 동별, 주상복합 제외:

- 정자동: +57.46%
- 분당동: +54.82%
- 구미동: +49.60%
- 서현동: +40.84%
- 야탑동: +34.42%
- 수내동: +34.28%
- 운중동: +33.43%
- 금곡동: +28.38%
- 이매동: +26.65%
- 백현동: +21.54%
- 삼평동: +20.35%
- 대장동: +9.17%
- 판교동: +5.27%

### Suwon Yeongtong, No Mixed-Use

Outputs:

- `output/reports/suwon_yeongtong_apt_trades_policy_windows_no_mixed_use.csv`
- `output/reports/suwon_yeongtong_apt_growth_201704_201706_vs_202204_202206_by_dong_no_mixed_use.csv`
- `output/reports/suwon_yeongtong_apt_growth_202506_202508_vs_202602_202604_by_dong_no_mixed_use.csv`
- `output/reports/suwon_yeongtong_apt_upside_moon_like_vs_lee_current_by_dong_no_mixed_use.csv`

Overall:

- Removed trades: 197
- 문재인 정부 3개월 창 상승률: +94.38%
- 이재명 정부 현재 3개월 창 상승률: +2.20%
- 문재인 정부식 총상승률까지 간다고 볼 때 현재 이후 잔여 상승률: +90.20%
- 현재 6억 기준 문재인 정부식 목표가: 약 11.41억
- 현재 속도 단순 연장 시 2030-06-03 가격: 약 6.62억

이재명 정부 현재 동별, 주상복합 제외:

- 하동: +12.40%
- 매탄동: +8.87%
- 영통동: +6.35%
- 신동: +3.93%
- 원천동: -1.23%
- 망포동: -4.29%
- 이의동: -13.02%

### Gwanggyo, No Mixed-Use

Definitions:

- `gwanggyo_dong_area_no_mixed_use`: 이의동, 하동, 원천동 after mixed-use exclusion
- `gwanggyo_named_apts_no_mixed_use`: apartment names containing `광교` after mixed-use exclusion

Outputs:

- `output/reports/gwanggyo_area_growth_summary_no_mixed_use.csv`
- `output/reports/gwanggyo_dong_area_growth_201704_201706_vs_202204_202206_by_dong_no_mixed_use.csv`
- `output/reports/gwanggyo_dong_area_growth_202506_202508_vs_202602_202604_by_dong_no_mixed_use.csv`

Overall:

- 광교 생활권, 주상복합 제외
  - 문재인 정부 3개월 창 상승률: +75.86%
  - 이재명 정부 현재 3개월 창 상승률: -3.29%
  - 문재인 정부식 총상승률까지 잔여 상승률: +81.84%
  - 현재 6억 기준 문재인 정부식 목표가: 약 10.91억
- 광교명 단지, 주상복합 제외
  - 문재인 정부 3개월 창 상승률: +82.27%
  - 이재명 정부 현재 3개월 창 상승률: -3.59%
  - 문재인 정부식 총상승률까지 잔여 상승률: +89.06%
  - 현재 6억 기준 문재인 정부식 목표가: 약 11.34억

광교 생활권 이재명 정부 현재 동별, 주상복합 제외:

- 하동: +12.40%
- 원천동: -1.23%
- 이의동: -13.02%

## Cleanup Note

Cleanup performed: 2026-04-29 Asia/Seoul

Removed:

- Browser/playwright logs: `.playwright-mcp`
- Matplotlib cache: `.mplconfig`
- Stale API XML cache: `output/api_cache`
- Old chart output: `output/charts`
- Superseded Seoul/officetel reports and earlier non-filtered/intermediate apartment reports
- Removed outdated `scripts/analyze_bundang_apt_growth.py` because of cache pagination risk

Kept:

- Raw downloaded CSV files in the project root
- Current handoff document
- Current `no_mixed_use` apartment analysis outputs
- `mixed_use_exclusion_list.csv`
- Naver helper scripts and original pipeline source files
