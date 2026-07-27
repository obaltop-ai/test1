"""
사주팔자 계산 엔진
만세력DB의 JSON 데이터를 활용하여 사주(四柱)를 세우고 분석합니다.
"""
import json
import os
from datetime import datetime, date, timedelta

# === 기본 데이터 ===
CHEONGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
CHEONGAN_KR = ["갑", "을", "병", "정", "무", "기", "경", "신", "임", "계"]
OHAENG_CG = ["木", "木", "火", "火", "土", "土", "金", "金", "水", "水"]
UMYANG_CG = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]  # 1=양, 0=음

JIJI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
JIJI_KR = ["자", "축", "인", "묘", "진", "사", "오", "미", "신", "유", "술", "해"]
OHAENG_JJ = ["水", "土", "木", "木", "土", "火", "火", "土", "金", "金", "土", "水"]
UMYANG_JJ = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
DDI = ["쥐", "소", "호랑이", "토끼", "용", "뱀", "말", "양", "원숭이", "닭", "개", "돼지"]

OHAENG = ["木", "火", "土", "金", "水"]
OHAENG_IDX = {o: i for i, o in enumerate(OHAENG)}

# 지장간 데이터: {지지: [(천간, 일수), ...]} — 마지막이 본기(정기)
JIJANGGAN = {
    "子": [("壬", 10), ("癸", 20)],
    "丑": [("癸", 9), ("辛", 3), ("己", 18)],
    "寅": [("戊", 7), ("丙", 7), ("甲", 16)],
    "卯": [("甲", 10), ("乙", 20)],
    "辰": [("乙", 9), ("癸", 3), ("戊", 18)],
    "巳": [("戊", 7), ("庚", 7), ("丙", 16)],
    "午": [("丙", 10), ("己", 10), ("丁", 10)],
    "未": [("丁", 9), ("乙", 3), ("己", 18)],
    "申": [("戊", 7), ("壬", 7), ("庚", 16)],
    "酉": [("庚", 10), ("辛", 20)],
    "戌": [("辛", 9), ("丁", 3), ("戊", 18)],
    "亥": [("戊", 7), ("甲", 7), ("壬", 16)],
}

# 년간오호둔(年干五虎遁) - 년간 → 인월(1월) 월간 시작 인덱스
WOLGAN_START = {0: 2, 1: 4, 2: 6, 3: 8, 4: 0,
                5: 2, 6: 4, 7: 6, 8: 8, 9: 0}

# 일간오자둔(日干五子遁) - 일간 → 자시(子時) 시간 시작 인덱스
SIGAN_START = {0: 0, 1: 2, 2: 4, 3: 6, 4: 8,
               5: 0, 6: 2, 7: 4, 8: 6, 9: 8}

# 천간합
CHEONGAN_HAP = {(0, 5): "土", (1, 6): "金", (2, 7): "水", (3, 8): "木", (4, 9): "火"}

# 지지육합
JIJI_YUKHAP = {(0, 1): "土", (2, 11): "木", (3, 10): "火",
               (4, 9): "金", (5, 8): "水", (6, 7): "土"}

# 지지충
JIJI_CHUNG = [(0, 6), (1, 7), (2, 8), (3, 9), (4, 10), (5, 11)]

# 삼합
SAMHAP = [
    ((2, 6, 10), "火"),   # 寅午戌
    ((11, 3, 7), "木"),   # 亥卯未
    ((8, 0, 4), "水"),    # 申子辰
    ((5, 9, 1), "金"),    # 巳酉丑
]

# 십성 이름
SIBSUNG_NAMES = {
    "same_same": "비견", "same_diff": "겁재",
    "생_same": "식신", "생_diff": "상관",
    "극_same": "편재", "극_diff": "정재",
    "피극_same": "편관", "피극_diff": "정관",
    "피생_same": "편인", "피생_diff": "정인",
}

# === DB 경로 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "만세력DB")


class SajuEngine:
    def __init__(self):
        """만세력DB 로드"""
        print("만세력DB 로딩 중...")
        with open(os.path.join(DB_DIR, "solar_terms.json"), "r", encoding="utf-8") as f:
            self.solar_terms = json.load(f)
        with open(os.path.join(DB_DIR, "daily_ganji.json"), "r", encoding="utf-8") as f:
            self.daily_ganji = json.load(f)
        print("만세력DB 로딩 완료!")

    # ========================
    # 사주 세우기 (四柱 立命式)
    # ========================

    def get_saju(self, year, month, day, hour, minute, gender="남"):
        """
        사주팔자를 세웁니다.
        Args:
            year, month, day: 양력 생년월일
            hour, minute: 출생 시간
            gender: "남" 또는 "여"
        Returns: dict with 사주 정보
        """
        birth_dt = datetime(year, month, day, hour, minute)

        # 1) 일주 (DB에서 조회)
        day_data = self._get_day_data(year, month, day)
        day_cg_idx = day_data["cg_idx"]
        day_jj_idx = day_data["jj_idx"]

        # 2) 년주 (입춘 기준)
        effective_year = self._get_effective_year(year, month, day, hour, minute)
        year_gapja_idx = (effective_year - 1984) % 60  # 1984=갑자년
        year_cg_idx = year_gapja_idx % 10
        year_jj_idx = year_gapja_idx % 12

        # 3) 월주 (절기 기준)
        month_jj_idx, month_num = self._get_month_jiji(year, month, day, hour, minute)
        month_cg_start = WOLGAN_START[year_cg_idx]
        month_offset = (month_jj_idx - 2) % 12  # 寅=2 기준
        month_cg_idx = (month_cg_start + month_offset) % 10

        # 4) 시주
        hour_jj_idx = self._hour_to_jiji(hour)
        hour_cg_start = SIGAN_START[day_cg_idx]
        hour_cg_idx = (hour_cg_start + hour_jj_idx) % 10

        # 사주 조합
        saju = {
            "birth": {
                "solar": f"{year}-{month:02d}-{day:02d}",
                "time": f"{hour:02d}:{minute:02d}",
                "gender": gender,
                "lunar": day_data.get("lunar", ""),
                "lunar_leap": day_data.get("lunar_leap", False),
            },
            "year": self._make_pillar("년주", year_cg_idx, year_jj_idx),
            "month": self._make_pillar("월주", month_cg_idx, month_jj_idx),
            "day": self._make_pillar("일주", day_cg_idx, day_jj_idx),
            "hour": self._make_pillar("시주", hour_cg_idx, hour_jj_idx),
            "ilgan": CHEONGAN[day_cg_idx],
            "ilgan_kr": CHEONGAN_KR[day_cg_idx],
            "ilgan_ohaeng": OHAENG_CG[day_cg_idx],
            "ddi": DDI[year_jj_idx],
        }

        # 십성 계산
        saju["sibsung"] = self._calc_all_sibsung(day_cg_idx, saju)

        # 오행 분석
        saju["ohaeng_analysis"] = self._analyze_ohaeng(saju)

        # 합/충 분석
        saju["interactions"] = self._analyze_interactions(saju)

        # 격국/용신 (간략)
        saju["strength"] = self._analyze_strength(day_cg_idx, saju)

        # 대운
        saju["daewoon"] = self._calc_daewoon(
            birth_dt, gender, year_cg_idx, month_cg_idx, month_jj_idx, year, month_num
        )

        # 세운 (현재 연도)
        current_year = datetime.now().year
        saju["sewoon"] = self._calc_sewoon(current_year, day_cg_idx)

        return saju

    # ========================
    # 내부 계산 메서드
    # ========================

    def _get_day_data(self, year, month, day):
        """DB에서 특정 날짜의 일진 데이터 조회"""
        year_data = self.daily_ganji.get(str(year))
        if not year_data:
            raise ValueError(f"{year}년 데이터가 없습니다.")
        day_of_year = (date(year, month, day) - date(year, 1, 1)).days
        return year_data[day_of_year]

    def _get_effective_year(self, year, month, day, hour, minute):
        """입춘 기준 유효 연도 결정"""
        terms = self.solar_terms.get(str(year), [])
        ipchun = None
        for t in terms:
            if t["name"] == "입춘":
                ipchun = datetime.strptime(t["datetime_kst"], "%Y-%m-%d %H:%M:%S")
                break
        if ipchun and datetime(year, month, day, hour, minute) < ipchun:
            return year - 1
        return year

    def _get_month_jiji(self, year, month, day, hour, minute):
        """절기 기준 월지 결정"""
        birth_dt = datetime(year, month, day, hour, minute)

        # 해당 연도 + 전후 연도의 절기를 모두 수집
        all_jeol = []
        for y in [year - 1, year, year + 1]:
            terms = self.solar_terms.get(str(y), [])
            for t in terms:
                if t.get("is_jeol"):
                    dt = datetime.strptime(t["datetime_kst"], "%Y-%m-%d %H:%M:%S")
                    all_jeol.append((dt, JIJI.index(t["wolji"]), t["month_num"]))

        all_jeol.sort(key=lambda x: x[0])

        # 생일 직전의 절(節) 찾기
        result_jj_idx = 1  # 기본값: 丑(축) = 12월
        result_month_num = 12
        for dt, jj_idx, mnum in all_jeol:
            if dt <= birth_dt:
                result_jj_idx = jj_idx
                result_month_num = mnum
            else:
                break

        return result_jj_idx, result_month_num

    def _hour_to_jiji(self, hour):
        """시간 → 지지 인덱스 (23시=子, 1시=丑, ...)"""
        return ((hour + 1) // 2) % 12

    def _make_pillar(self, name, cg_idx, jj_idx):
        """기둥(柱) 정보 생성"""
        jj_name = JIJI[jj_idx]
        return {
            "name": name,
            "hanja": CHEONGAN[cg_idx] + jj_name,
            "korean": CHEONGAN_KR[cg_idx] + JIJI_KR[jj_idx],
            "cg_idx": cg_idx,
            "jj_idx": jj_idx,
            "cg": CHEONGAN[cg_idx],
            "jj": jj_name,
            "cg_ohaeng": OHAENG_CG[cg_idx],
            "jj_ohaeng": OHAENG_JJ[jj_idx],
            "cg_umyang": "양" if UMYANG_CG[cg_idx] else "음",
            "jj_umyang": "양" if UMYANG_JJ[jj_idx] else "음",
            "jijanggan": JIJANGGAN[jj_name],
        }

    # ========================
    # 십성(十星) 계산
    # ========================

    def _get_sibsung(self, ilgan_idx, target_cg_idx):
        """일간과 대상 천간의 십성 계산"""
        il_oh = OHAENG_CG[ilgan_idx]
        tg_oh = OHAENG_CG[target_cg_idx]
        same_uy = UMYANG_CG[ilgan_idx] == UMYANG_CG[target_cg_idx]
        suffix = "same" if same_uy else "diff"

        il_idx = OHAENG_IDX[il_oh]
        tg_idx = OHAENG_IDX[tg_oh]

        if il_oh == tg_oh:
            return SIBSUNG_NAMES[f"same_{suffix}"]
        elif OHAENG[(il_idx + 1) % 5] == tg_oh:  # 내가 생
            return SIBSUNG_NAMES[f"생_{suffix}"]
        elif OHAENG[(il_idx + 2) % 5] == tg_oh:  # 내가 극
            return SIBSUNG_NAMES[f"극_{suffix}"]
        elif OHAENG[(tg_idx + 1) % 5] == il_oh:  # 나를 생
            return SIBSUNG_NAMES[f"피생_{suffix}"]
        elif OHAENG[(tg_idx + 2) % 5] == il_oh:  # 나를 극
            return SIBSUNG_NAMES[f"피극_{suffix}"]
        return "unknown"

    def _calc_all_sibsung(self, ilgan_idx, saju):
        """사주 전체 십성 계산"""
        result = {}
        for pillar_key in ["year", "month", "day", "hour"]:
            p = saju[pillar_key]
            cg_ss = self._get_sibsung(ilgan_idx, p["cg_idx"])
            # 지지는 본기(정기)로 십성 계산
            jjg = p["jijanggan"]
            bongi = jjg[-1][0]  # 본기 천간
            bongi_idx = CHEONGAN.index(bongi)
            jj_ss = self._get_sibsung(ilgan_idx, bongi_idx)

            result[pillar_key] = {
                "천간": cg_ss if pillar_key != "day" else "일간(나)",
                "지지": jj_ss,
            }
        return result

    # ========================
    # 오행 분석
    # ========================

    def _analyze_ohaeng(self, saju):
        """사주 내 오행 분포 분석"""
        count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        for key in ["year", "month", "day", "hour"]:
            p = saju[key]
            count[p["cg_ohaeng"]] += 1
            count[p["jj_ohaeng"]] += 1

        total = sum(count.values())
        analysis = {}
        for oh, c in count.items():
            pct = round(c / total * 100)
            if c == 0:
                level = "없음"
            elif c <= 1:
                level = "약"
            elif c <= 2:
                level = "보통"
            else:
                level = "강"
            analysis[oh] = {"count": c, "percent": pct, "level": level}

        return analysis

    # ========================
    # 합·충 분석
    # ========================

    def _analyze_interactions(self, saju):
        """천간합, 지지충, 지지합 분석"""
        pillars = [saju[k] for k in ["year", "month", "day", "hour"]]
        results = {"천간합": [], "지지충": [], "지지육합": [], "삼합": []}

        # 천간합
        for i in range(len(pillars)):
            for j in range(i + 1, len(pillars)):
                pair = (min(pillars[i]["cg_idx"], pillars[j]["cg_idx"]),
                        max(pillars[i]["cg_idx"], pillars[j]["cg_idx"]))
                if pair in CHEONGAN_HAP:
                    results["천간합"].append({
                        "pillars": f"{pillars[i]['name']}↔{pillars[j]['name']}",
                        "detail": f"{pillars[i]['cg']}+{pillars[j]['cg']}→{CHEONGAN_HAP[pair]}",
                    })

        # 지지충
        for i in range(len(pillars)):
            for j in range(i + 1, len(pillars)):
                pair = (min(pillars[i]["jj_idx"], pillars[j]["jj_idx"]),
                        max(pillars[i]["jj_idx"], pillars[j]["jj_idx"]))
                if pair in [tuple(sorted(p)) for p in JIJI_CHUNG]:
                    results["지지충"].append({
                        "pillars": f"{pillars[i]['name']}↔{pillars[j]['name']}",
                        "detail": f"{pillars[i]['jj']}↔{pillars[j]['jj']}",
                    })

        # 지지육합
        for i in range(len(pillars)):
            for j in range(i + 1, len(pillars)):
                pair = (min(pillars[i]["jj_idx"], pillars[j]["jj_idx"]),
                        max(pillars[i]["jj_idx"], pillars[j]["jj_idx"]))
                if pair in JIJI_YUKHAP:
                    results["지지육합"].append({
                        "pillars": f"{pillars[i]['name']}↔{pillars[j]['name']}",
                        "detail": f"{pillars[i]['jj']}+{pillars[j]['jj']}→{JIJI_YUKHAP[pair]}",
                    })

        # 삼합 체크
        jj_set = set(p["jj_idx"] for p in pillars)
        for (a, b, c), element in SAMHAP:
            matched = jj_set & {a, b, c}
            if len(matched) >= 2:
                names = [JIJI[x] for x in sorted(matched)]
                full = "완전삼합" if len(matched) == 3 else "반삼합"
                results["삼합"].append({
                    "detail": f"{''.join(names)} → {element}局 ({full})",
                })

        return results

    # ========================
    # 신강/신약 판단
    # ========================

    def _analyze_strength(self, ilgan_idx, saju):
        """일간의 신강/신약 간략 판단"""
        il_oh = OHAENG_CG[ilgan_idx]
        il_oh_idx = OHAENG_IDX[il_oh]

        # 득령: 월지가 일간을 생하거나 동일 오행인지
        month_jj_oh = saju["month"]["jj_ohaeng"]
        deukryeong = (month_jj_oh == il_oh) or (OHAENG[(OHAENG_IDX[month_jj_oh] + 1) % 5] == il_oh)

        # 득지: 지지 중 일간과 같거나 생해주는 오행 개수
        support_count = 0
        for key in ["year", "month", "day", "hour"]:
            jj_oh = saju[key]["jj_ohaeng"]
            if jj_oh == il_oh or OHAENG[(OHAENG_IDX[jj_oh] + 1) % 5] == il_oh:
                support_count += 1

        # 득세: 천간 중 일간과 같거나 생해주는 오행 개수 (일간 제외)
        cg_support = 0
        for key in ["year", "month", "hour"]:
            cg_oh = saju[key]["cg_ohaeng"]
            if cg_oh == il_oh or OHAENG[(OHAENG_IDX[cg_oh] + 1) % 5] == il_oh:
                cg_support += 1

        score = (1 if deukryeong else 0) + support_count + cg_support
        if score >= 4:
            strength = "신강(身强)"
            yongsin_desc = f"일간 {CHEONGAN[ilgan_idx]}({il_oh})의 힘이 강하므로, 설기(泄氣)하거나 극(剋)하는 오행이 필요"
        elif score <= 2:
            strength = "신약(身弱)"
            yongsin_desc = f"일간 {CHEONGAN[ilgan_idx]}({il_oh})의 힘이 약하므로, 생(生)해주는 오행이 필요"
        else:
            strength = "중화(中和)"
            yongsin_desc = f"일간 {CHEONGAN[ilgan_idx]}({il_oh})의 힘이 비교적 균형적"

        return {
            "strength": strength,
            "deukryeong": deukryeong,
            "deukji": support_count,
            "deukse": cg_support,
            "score": score,
            "yongsin_desc": yongsin_desc,
        }

    # ========================
    # 대운(大運) 계산
    # ========================

    def _calc_daewoon(self, birth_dt, gender, year_cg_idx, month_cg_idx, month_jj_idx, birth_year, month_num):
        """대운 계산"""
        umyang = UMYANG_CG[year_cg_idx]
        # 양남·음녀 = 순행, 음남·양녀 = 역행
        forward = (gender == "남" and umyang == 1) or (gender == "여" and umyang == 0)

        # 절기까지 날수 계산
        all_jeol = []
        for y in [birth_year - 1, birth_year, birth_year + 1]:
            terms = self.solar_terms.get(str(y), [])
            for t in terms:
                if t.get("is_jeol"):
                    dt = datetime.strptime(t["datetime_kst"], "%Y-%m-%d %H:%M:%S")
                    all_jeol.append(dt)
        all_jeol.sort()

        if forward:
            # 다음 절기까지
            delta_days = 0
            for jdt in all_jeol:
                if jdt > birth_dt:
                    delta_days = (jdt - birth_dt).days
                    break
        else:
            # 이전 절기까지
            delta_days = 0
            for jdt in reversed(all_jeol):
                if jdt <= birth_dt:
                    delta_days = (birth_dt - jdt).days
                    break

        daewoon_start_age = round(delta_days / 3)

        # 월주의 60갑자 인덱스 계산
        month_gapja_idx = None
        for i in range(60):
            if i % 10 == month_cg_idx and i % 12 == month_jj_idx:
                month_gapja_idx = i
                break

        daewoon_list = []
        for i in range(1, 10):  # 9개 대운
            if forward:
                idx = (month_gapja_idx + i) % 60
            else:
                idx = (month_gapja_idx - i) % 60
            cg_idx = idx % 10
            jj_idx = idx % 12
            age = daewoon_start_age + (i - 1) * 10
            daewoon_list.append({
                "age": age,
                "age_range": f"{age}~{age + 9}세",
                "hanja": CHEONGAN[cg_idx] + JIJI[jj_idx],
                "korean": CHEONGAN_KR[cg_idx] + JIJI_KR[jj_idx],
                "cg_ohaeng": OHAENG_CG[cg_idx],
                "jj_ohaeng": OHAENG_JJ[jj_idx],
            })

        return {
            "direction": "순행" if forward else "역행",
            "start_age": daewoon_start_age,
            "list": daewoon_list,
        }

    # ========================
    # 세운(歲運)
    # ========================

    def _calc_sewoon(self, target_year, ilgan_idx):
        """특정 연도의 세운 계산"""
        year_gapja_idx = (target_year - 1984) % 60
        cg_idx = year_gapja_idx % 10
        jj_idx = year_gapja_idx % 12
        sibsung = self._get_sibsung(ilgan_idx, cg_idx)

        return {
            "year": target_year,
            "hanja": CHEONGAN[cg_idx] + JIJI[jj_idx],
            "korean": CHEONGAN_KR[cg_idx] + JIJI_KR[jj_idx],
            "cg_ohaeng": OHAENG_CG[cg_idx],
            "jj_ohaeng": OHAENG_JJ[jj_idx],
            "sibsung": sibsung,
        }

    # ========================
    # AI 해석용 dict 변환
    # ========================

    def to_dict(self, saju):
        """AI 해석에 적합한 구조화된 dict 반환"""
        b = saju["birth"]
        dw = saju["daewoon"]
        sw = saju["sewoon"]
        s = saju["strength"]
        inter = saju["interactions"]

        pillars = {}
        for key, label in [("year", "년주"), ("month", "월주"), ("day", "일주"), ("hour", "시주")]:
            p = saju[key]
            ss = saju["sibsung"][key]
            pillars[label] = {
                "한자": p["hanja"],
                "한글": p["korean"],
                "천간": {"글자": p["cg"], "오행": p["cg_ohaeng"], "음양": p["cg_umyang"], "십성": ss["천간"]},
                "지지": {"글자": p["jj"], "오행": p["jj_ohaeng"], "음양": p["jj_umyang"], "십성": ss["지지"]},
                "지장간": [{"천간": cg, "일수": d} for cg, d in p["jijanggan"]],
            }

        ohaeng = {oh: {"개수": v["count"], "비율": f"{v['percent']}%", "강도": v["level"]}
                  for oh, v in saju["ohaeng_analysis"].items()}

        interactions = {}
        for k in ["천간합", "지지충", "지지육합", "삼합"]:
            if inter[k]:
                interactions[k] = [item.get("detail", "") or item.get("pillars", "") for item in inter[k]]

        birth_year = int(b["solar"][:4])
        current_age = sw["year"] - birth_year
        current_daewoon = None
        for d in dw["list"]:
            if d["age"] <= current_age < d["age"] + 10:
                current_daewoon = d
                break

        return {
            "출생정보": {
                "양력": f"{b['solar']} {b['time']}",
                "음력": b["lunar"],
                "성별": b["gender"],
                "띠": saju["ddi"] + "띠",
            },
            "일간": {
                "천간": saju["ilgan"],
                "한글": saju["ilgan_kr"],
                "오행": saju["ilgan_ohaeng"],
            },
            "사주원국": pillars,
            "오행분포": ohaeng,
            "신강신약": {
                "판정": s["strength"],
                "득령": s["deukryeong"],
                "득지": f"{s['deukji']}/4",
                "득세": f"{s['deukse']}/3",
                "총점": s["score"],
                "용신방향": s["yongsin_desc"],
            },
            "합충관계": interactions if interactions else {"결과": "특별한 합충 없음"},
            "대운": {
                "방향": dw["direction"],
                "시작나이": dw["start_age"],
                "현재대운": current_daewoon,
                "전체목록": dw["list"],
            },
            "세운": {
                "연도": sw["year"],
                "한자": sw["hanja"],
                "한글": sw["korean"],
                "천간오행": sw["cg_ohaeng"],
                "지지오행": sw["jj_ohaeng"],
                "십성": sw["sibsung"],
            },
        }

    def lunar_to_solar(self, lunar_year, lunar_month, lunar_day, is_leap=False):
        """음력→양력 변환 (만세력DB 역검색)"""
        target = f"{lunar_year}-{lunar_month:02d}-{lunar_day:02d}"
        for year_key in [str(lunar_year), str(lunar_year + 1)]:
            for entry in self.daily_ganji.get(year_key, []):
                if entry["lunar"] == target and entry["lunar_leap"] == is_leap:
                    parts = entry["solar"].split("-")
                    return int(parts[0]), int(parts[1]), int(parts[2])
        raise ValueError(f"음력 {target} (윤달={is_leap})에 해당하는 양력 날짜를 찾을 수 없습니다.")

    # ========================
    # 출력 포맷
    # ========================

    def print_saju(self, saju):
        """사주 결과를 보기 좋게 출력"""
        b = saju["birth"]
        print("=" * 60)
        print(f"  사주팔자 분석 결과")
        print(f"  양력: {b['solar']} {b['time']}  |  음력: {b['lunar']}")
        print(f"  성별: {b['gender']}  |  띠: {saju['ddi']}띠")
        print(f"  일간: {saju['ilgan']}({saju['ilgan_kr']}) - {saju['ilgan_ohaeng']}")
        print("=" * 60)

        # 사주 표
        print()
        print("  ┌────────┬────────┬────────┬────────┐")
        print("  │  시주  │  일주  │  월주  │  년주  │")
        print("  ├────────┼────────┼────────┼────────┤")

        pillars = [saju["hour"], saju["day"], saju["month"], saju["year"]]

        # 천간
        row = "  │"
        for p in pillars:
            ss = saju["sibsung"][["hour", "day", "month", "year"][pillars.index(p)]]["천간"]
            row += f" {p['cg']}({ss[:2]}) │"
        print(row)

        # 한글
        row = "  │"
        for p in pillars:
            row += f"  {p['korean']}  │"
        print(row)

        # 지지
        row = "  │"
        for p in pillars:
            ss = saju["sibsung"][["hour", "day", "month", "year"][pillars.index(p)]]["지지"]
            row += f" {p['jj']}({ss[:2]}) │"
        print(row)

        print("  └────────┴────────┴────────┴────────┘")

        # 오행 분석
        print()
        print("  【오행 분포】")
        for oh in OHAENG:
            a = saju["ohaeng_analysis"][oh]
            bar = "#" * a["count"] + "." * (8 - a["count"])
            print(f"    {oh}: {bar} {a['count']}개 ({a['percent']}%) - {a['level']}")

        # 신강/신약
        print()
        s = saju["strength"]
        print(f"  【신강/신약】 {s['strength']}")
        print(f"    득령: {'○' if s['deukryeong'] else '✕'}  득지: {s['deukji']}/4  득세: {s['deukse']}/3")
        print(f"    → {s['yongsin_desc']}")

        # 합·충
        print()
        print("  【합·충 관계】")
        inter = saju["interactions"]
        for key in ["천간합", "지지충", "지지육합", "삼합"]:
            if inter[key]:
                for item in inter[key]:
                    detail = item.get("detail", "")
                    pillars_info = item.get("pillars", "")
                    print(f"    {key}: {pillars_info} {detail}")
        if not any(inter.values()):
            print("    특별한 합·충 관계 없음")

        # 대운
        print()
        dw = saju["daewoon"]
        print(f"  【대운】 ({dw['direction']}, {dw['start_age']}세 시작)")
        for d in dw["list"]:
            print(f"    {d['age_range']:>8s}  {d['hanja']}({d['korean']})  {d['cg_ohaeng']}/{d['jj_ohaeng']}")

        # 세운
        print()
        sw = saju["sewoon"]
        print(f"  【{sw['year']}년 세운】 {sw['hanja']}({sw['korean']}) - {sw['sibsung']}")
        print("=" * 60)


# === 메인 실행 ===
if __name__ == "__main__":
    engine = SajuEngine()

    # 테스트: 예시 생년월일
    print()
    print("테스트 사주 분석 (1990년 5월 15일 14시 30분, 남성)")
    print()
    saju = engine.get_saju(1990, 5, 15, 14, 30, "남")
    engine.print_saju(saju)
