"""
일별 간지(日辰) + 음양력 변환 데이터 생성 스크립트
1900~2100년의 모든 날짜에 대해 60갑자 일진과 음력 날짜를 계산합니다.

일진 계산: 1900년 1월 1일 = 甲戌일 (60갑자 index 10) 기준
음양력 변환: korean-lunar-calendar 라이브러리 사용 (KASI 데이터 기반)
"""
import json
from datetime import datetime, timedelta, date

# === 천간/지지 데이터 ===
CHEONGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
CHEONGAN_KR = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]

JIJI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
JIJI_KR = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]

OHAENG_CG = ["木", "木", "火", "火", "土", "土", "金", "金", "水", "水"]
OHAENG_JJ = ["水", "土", "木", "木", "土", "火", "火", "土", "金", "金", "土", "水"]

# 60갑자 배열
GAPJA_60 = []
for i in range(60):
    cg = CHEONGAN[i % 10]
    jj = JIJI[i % 12]
    cg_kr = CHEONGAN_KR[i % 10]
    jj_kr = JIJI_KR[i % 12]
    GAPJA_60.append({
        "hanja": cg + jj,
        "korean": cg_kr + jj_kr,
        "cheongan_idx": i % 10,
        "jiji_idx": i % 12,
        "ohaeng_cg": OHAENG_CG[i % 10],
        "ohaeng_jj": OHAENG_JJ[i % 12],
    })

# 일진 기준: 1900-01-01 = 甲戌(갑술) = 60갑자 인덱스 10
BASE_DATE = date(1900, 1, 1)
BASE_IDX = 10


def get_day_ganji_idx(target_date):
    """특정 날짜의 60갑자 인덱스 반환"""
    delta = (target_date - BASE_DATE).days
    return (BASE_IDX + delta) % 60


def generate_daily_data(start_year=1900, end_year=2100):
    """일별 간지 데이터 생성 (연도별 딕셔너리)"""
    # korean-lunar-calendar 로드 시도
    try:
        from korean_lunar_calendar import KoreanLunarCalendar
        cal = KoreanLunarCalendar()
        has_lunar = True
        # 라이브러리 지원 범위 확인 (1000~2050)
        lunar_min_year = 1900
        lunar_max_year = 2050
        print("  korean-lunar-calendar 로드 성공 (음력 변환 포함)")
    except ImportError:
        has_lunar = False
        print("  korean-lunar-calendar 없음 (간지만 생성)")

    result = {}

    for year in range(start_year, end_year + 1):
        year_data = []
        # 해당 연도의 1/1 ~ 12/31
        d = date(year, 1, 1)
        year_end = date(year, 12, 31)

        while d <= year_end:
            gapja_idx = get_day_ganji_idx(d)
            gapja = GAPJA_60[gapja_idx]

            entry = {
                "solar": d.isoformat(),
                "gapja_idx": gapja_idx,
                "ganji": gapja["hanja"],
                "ganji_kr": gapja["korean"],
                "cg_idx": gapja["cheongan_idx"],
                "jj_idx": gapja["jiji_idx"],
            }

            # 음력 변환 (지원 범위 내)
            if has_lunar and lunar_min_year <= year <= lunar_max_year:
                try:
                    cal.setSolarDate(year, d.month, d.day)
                    lunar_year = cal.lunarYear
                    lunar_month = cal.lunarMonth
                    lunar_day = cal.lunarDay
                    is_leap = cal.isIntercalation
                    entry["lunar"] = f"{lunar_year}-{lunar_month:02d}-{lunar_day:02d}"
                    entry["lunar_leap"] = is_leap
                except Exception:
                    pass

            year_data.append(entry)
            d += timedelta(days=1)

        result[str(year)] = year_data

        if year % 50 == 0:
            print(f"  {year}년 완료... ({len(year_data)}일)")

    return result


if __name__ == "__main__":
    print("일별 간지 + 음양력 데이터 생성 시작 (1900~2100)...")
    data = generate_daily_data(1900, 2100)

    # 일별 간지 저장
    output_path = "만세력DB/daily_ganji.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    import os
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    total_days = sum(len(v) for v in data.values())
    print(f"완료! {len(data)}개 연도, 총 {total_days}일 → {output_path} ({size_mb:.1f} MB)")
