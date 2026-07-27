"""
24절기(Solar Terms) 데이터 생성 스크립트
ephem 라이브러리를 사용하여 1900~2100년 24절기의 정확한 날짜/시각을 계산합니다.
"""
import ephem
import json
import math
from datetime import datetime, timedelta

# 24절기: (이름, 태양황경도, 대략적인 월/일)
SOLAR_TERMS = [
    ("소한", 285, (1, 6)),
    ("대한", 300, (1, 20)),
    ("입춘", 315, (2, 4)),
    ("우수", 330, (2, 19)),
    ("경칩", 345, (3, 6)),
    ("춘분", 0,   (3, 21)),
    ("청명", 15,  (4, 5)),
    ("곡우", 30,  (4, 20)),
    ("입하", 45,  (5, 6)),
    ("소만", 60,  (5, 21)),
    ("망종", 75,  (6, 6)),
    ("하지", 90,  (6, 21)),
    ("소서", 105, (7, 7)),
    ("대서", 120, (7, 23)),
    ("입추", 135, (8, 7)),
    ("처서", 150, (8, 23)),
    ("백로", 165, (9, 8)),
    ("추분", 180, (9, 23)),
    ("한로", 195, (10, 8)),
    ("상강", 210, (10, 23)),
    ("입동", 225, (11, 7)),
    ("소설", 240, (11, 22)),
    ("대설", 255, (12, 7)),
    ("동지", 270, (12, 22)),
]

# 12절(節) - 월주 결정에 사용되는 절기와 해당 월지
JEOL_TO_WOLJI = {
    "입춘": ("寅", 1), "경칩": ("卯", 2), "청명": ("辰", 3),
    "입하": ("巳", 4), "망종": ("午", 5), "소서": ("未", 6),
    "입추": ("申", 7), "백로": ("酉", 8), "한로": ("戌", 9),
    "입동": ("亥", 10), "대설": ("子", 11), "소한": ("丑", 12),
}


def sun_longitude(date):
    """주어진 ephem.Date의 태양 황경(도) 반환 - 지구 중심 황도 좌표"""
    sun = ephem.Sun()
    sun.compute(date)
    ecl = ephem.Ecliptic(sun)
    return math.degrees(float(ecl.lon))


def find_solar_term_date(year, target_lng, approx_month, approx_day):
    """특정 연도에서 태양 황경이 target_lng에 도달하는 정확한 시각 계산 (뉴턴법)"""
    # 대략적인 날짜에서 시작
    guess = ephem.Date(f"{year}/{approx_month}/{approx_day}")

    # 뉴턴 방법으로 수렴 (최대 50회)
    for _ in range(50):
        lng = sun_longitude(guess)
        # 차이 계산 (-180 ~ +180 범위로 정규화)
        diff = (lng - target_lng + 180) % 360 - 180
        if abs(diff) < 0.00001:  # 약 0.04초 정밀도
            break
        # 태양은 하루에 약 1도 이동
        guess -= diff  # diff도 단위 → 일 단위로 대략 보정

    return guess


def generate_solar_terms(start_year=1900, end_year=2100):
    """전체 연도 범위의 24절기 데이터 생성"""
    result = {}

    for year in range(start_year, end_year + 1):
        year_data = []

        for name, lng, (approx_m, approx_d) in SOLAR_TERMS:
            try:
                edate = find_solar_term_date(year, lng, approx_m, approx_d)
                dt = ephem.Date(edate).datetime()
                # UTC → KST (UTC+9)
                kst = dt + timedelta(hours=9)

                entry = {
                    "name": name,
                    "sun_longitude": lng,
                    "date": kst.strftime("%Y-%m-%d"),
                    "time": kst.strftime("%H:%M"),
                    "datetime_kst": kst.strftime("%Y-%m-%d %H:%M:%S"),
                }

                # 12절(節)인 경우 월지 정보 추가
                if name in JEOL_TO_WOLJI:
                    wolji, month_num = JEOL_TO_WOLJI[name]
                    entry["is_jeol"] = True
                    entry["wolji"] = wolji
                    entry["month_num"] = month_num
                else:
                    entry["is_jeol"] = False

                year_data.append(entry)
            except Exception as e:
                print(f"Error: {year} {name} ({lng}) - {e}")

        result[str(year)] = year_data

        if year % 50 == 0:
            print(f"  {year}년 완료...")

    return result


if __name__ == "__main__":
    print("24절기 데이터 생성 시작 (1900~2100)...")
    data = generate_solar_terms(1900, 2100)

    output_path = "만세력DB/solar_terms.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total_entries = sum(len(v) for v in data.values())
    print(f"완료! {len(data)}개 연도, 총 {total_entries}개 절기 → {output_path}")
