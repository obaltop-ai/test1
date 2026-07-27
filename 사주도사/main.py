"""
사주도사 CLI
사주 산출 → Claude AI 해석까지 한 번에 실행합니다.

사용법:
  python main.py                          # 대화형 입력
  python main.py --year 1990 --month 5 --day 15 --hour 14 --minute 30 --gender 남
  python main.py --year 1977 --month 3 --day 24 --hour 4 --minute 14 --gender 남 --lunar
  python main.py --no-ai                  # AI 해석 없이 사주만 출력
"""
import argparse
import json
import os
import sys

# Windows 콘솔 UTF-8 출력 설정
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from saju_engine import SajuEngine, OHAENG


def parse_args():
    parser = argparse.ArgumentParser(description="사주도사 - 사주팔자 분석 + AI 해석")
    parser.add_argument("--year",    type=int, help="출생 연도 (예: 1990)")
    parser.add_argument("--month",   type=int, help="출생 월 (예: 5)")
    parser.add_argument("--day",     type=int, help="출생 일 (예: 15)")
    parser.add_argument("--hour",    type=int, help="출생 시 (예: 14)")
    parser.add_argument("--minute",  type=int, default=0, help="출생 분 (기본: 0)")
    parser.add_argument("--gender",  choices=["남", "여"], default="남", help="성별")
    parser.add_argument("--lunar",   action="store_true", help="음력 날짜로 입력")
    parser.add_argument("--leap",    action="store_true", help="윤달 여부 (--lunar와 함께 사용)")
    parser.add_argument("--no-ai",   action="store_true", help="AI 해석 없이 사주만 출력")
    parser.add_argument("--question", type=str, default="", help="AI에게 추가로 물어볼 질문")
    parser.add_argument("--json",    action="store_true", help="사주 데이터를 JSON으로 출력")
    return parser.parse_args()


def interactive_input():
    """대화형으로 생년월일시 입력받기"""
    print("=" * 50)
    print("  사주도사 - 생년월일시 입력")
    print("=" * 50)

    calendar = input("  음력/양력 [양력(기본)/음력]: ").strip()
    is_lunar = calendar in ("음력", "음", "lunar", "l")

    year   = int(input("  출생 연도: ").strip())
    month  = int(input("  출생 월: ").strip())
    day    = int(input("  출생 일: ").strip())
    hour   = int(input("  출생 시 (0~23, 모르면 12): ").strip() or "12")
    minute = int(input("  출생 분 (기본 0): ").strip() or "0")
    gender = input("  성별 [남/여]: ").strip() or "남"

    is_leap = False
    if is_lunar:
        leap_input = input("  윤달 여부 [아니오(기본)/예]: ").strip()
        is_leap = leap_input in ("예", "y", "yes", "윤달")

    return year, month, day, hour, minute, gender, is_lunar, is_leap


def print_saju_summary(saju: dict, engine: SajuEngine):
    """사주원국 요약 출력"""
    b = saju["birth"]
    print()
    print("=" * 60)
    print("  사주팔자 분석 결과")
    print(f"  양력: {b['solar']} {b['time']}  |  음력: {b['lunar']}")
    print(f"  성별: {b['gender']}  |  띠: {saju['ddi']}띠")
    print(f"  일간: {saju['ilgan']}({saju['ilgan_kr']}) - {saju['ilgan_ohaeng']}")
    print("=" * 60)

    print()
    print("  [사주 원국]")
    print("  ┌────────┬────────┬────────┬────────┐")
    print("  │  시주  │  일주  │  월주  │  년주  │")
    print("  ├────────┼────────┼────────┼────────┤")

    order = ["hour", "day", "month", "year"]
    pillars = [saju[k] for k in order]

    row = "  │"
    for i, p in enumerate(pillars):
        ss = saju["sibsung"][order[i]]["천간"]
        row += f" {p['cg']}({ss[:2]}) │"
    print(row)

    row = "  │"
    for p in pillars:
        row += f"  {p['korean']}  │"
    print(row)

    row = "  │"
    for i, p in enumerate(pillars):
        ss = saju["sibsung"][order[i]]["지지"]
        row += f" {p['jj']}({ss[:2]}) │"
    print(row)
    print("  └────────┴────────┴────────┴────────┘")

    print()
    print("  [오행 분포]")
    for oh in OHAENG:
        a = saju["ohaeng_analysis"][oh]
        bar = "#" * a["count"] + "." * (8 - a["count"])
        print(f"    {oh}: {bar} {a['count']}개 ({a['percent']}%) - {a['level']}")

    s = saju["strength"]
    print()
    print(f"  [신강/신약] {s['strength']} (총점 {s['score']})")
    deuk = "O" if s["deukryeong"] else "X"
    print(f"    득령: {deuk}  득지: {s['deukji']}/4  득세: {s['deukse']}/3")
    print(f"    → {s['yongsin_desc']}")

    inter = saju["interactions"]
    has_inter = any(inter.values())
    print()
    print("  [합·충 관계]")
    if has_inter:
        for key in ["천간합", "지지충", "지지육합", "삼합"]:
            for item in inter[key]:
                detail = item.get("detail", "")
                pinfo  = item.get("pillars", "")
                print(f"    {key}: {pinfo} {detail}")
    else:
        print("    특별한 합·충 관계 없음")

    dw = saju["daewoon"]
    print()
    print(f"  [대운] ({dw['direction']}, {dw['start_age']}세 시작)")
    birth_year = int(b["solar"][:4])
    current_year = saju["sewoon"]["year"]
    current_age = current_year - birth_year
    for d in dw["list"]:
        marker = "  ← 현재" if d["age"] <= current_age < d["age"] + 10 else ""
        print(f"    {d['age_range']:>8s}  {d['hanja']}({d['korean']})  {d['cg_ohaeng']}/{d['jj_ohaeng']}{marker}")

    sw = saju["sewoon"]
    print()
    print(f"  [{sw['year']}년 세운] {sw['hanja']}({sw['korean']}) - {sw['cg_ohaeng']}/{sw['jj_ohaeng']}")
    print(f"    일간 기준 십성: {sw['sibsung']}")
    print("=" * 60)


def main():
    args = parse_args()

    # 입력값 결정
    if args.year:
        year, month, day = args.year, args.month, args.day
        hour, minute = args.hour, args.minute
        gender = args.gender
        is_lunar = args.lunar
        is_leap = args.leap
    else:
        year, month, day, hour, minute, gender, is_lunar, is_leap = interactive_input()

    # 엔진 초기화
    engine = SajuEngine()

    # 음력 → 양력 변환
    if is_lunar:
        print(f"음력 {year}-{month:02d}-{day:02d} → 양력으로 변환 중...")
        try:
            year, month, day = engine.lunar_to_solar(year, month, day, is_leap)
            print(f"변환 완료: 양력 {year}-{month:02d}-{day:02d}")
        except ValueError as e:
            print(f"오류: {e}")
            sys.exit(1)

    # 사주 계산
    try:
        saju = engine.get_saju(year, month, day, hour, minute, gender)
    except ValueError as e:
        print(f"사주 계산 오류: {e}")
        sys.exit(1)

    # JSON 출력 모드
    if args.json:
        saju_dict = engine.to_dict(saju)
        print(json.dumps(saju_dict, ensure_ascii=False, indent=2))
        return

    # 사주 원국 출력
    print_saju_summary(saju, engine)

    # AI 해석
    if args.no_ai:
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\nANTHROPIC_API_KEY 환경변수가 없어 AI 해석을 건너뜁니다.")
        print("설정 방법: export ANTHROPIC_API_KEY='your-key-here'")
        return

    from saju_interpreter import interpret_with_cache_info

    print()
    print("=" * 60)
    print("  Claude AI 사주 해석")
    print("=" * 60)
    print()

    saju_dict = engine.to_dict(saju)

    try:
        _, usage = interpret_with_cache_info(saju_dict, extra_question=args.question)
        print()
        print("-" * 40)
        print(f"  [토큰 사용] 입력: {usage['input_tokens']} | 출력: {usage['output_tokens']}"
              f" | 캐시 생성: {usage['cache_creation_tokens']} | 캐시 읽기: {usage['cache_read_tokens']}")
    except Exception as e:
        print(f"\nAI 해석 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
