// 사주팔자 계산 엔진 (saju_engine.py 포팅)
// 만세력DB 대신 압축 데이터(JEOL_ENC / LUNAR_LENS / LUNAR_LEAPS)를 사용합니다.

const CHEONGAN = ["甲","乙","丙","丁","戊","己","庚","辛","壬","癸"];
const CHEONGAN_KR = ["갑","을","병","정","무","기","경","신","임","계"];
const OHAENG_CG = ["木","木","火","火","土","土","金","金","水","水"];
const UMYANG_CG = [1,0,1,0,1,0,1,0,1,0];

const JIJI = ["子","丑","寅","卯","辰","巳","午","未","申","酉","戌","亥"];
const JIJI_KR = ["자","축","인","묘","진","사","오","미","신","유","술","해"];
const OHAENG_JJ = ["水","土","木","木","土","火","火","土","金","金","土","水"];
const UMYANG_JJ = [1,0,1,0,1,0,1,0,1,0,1,0];
const DDI = ["쥐","소","호랑이","토끼","용","뱀","말","양","원숭이","닭","개","돼지"];

const OHAENG = ["木","火","土","金","水"];
const OHAENG_IDX = {木:0, 火:1, 土:2, 金:3, 水:4};

const JIJANGGAN = {
  "子":[["壬",10],["癸",20]],
  "丑":[["癸",9],["辛",3],["己",18]],
  "寅":[["戊",7],["丙",7],["甲",16]],
  "卯":[["甲",10],["乙",20]],
  "辰":[["乙",9],["癸",3],["戊",18]],
  "巳":[["戊",7],["庚",7],["丙",16]],
  "午":[["丙",10],["己",10],["丁",10]],
  "未":[["丁",9],["乙",3],["己",18]],
  "申":[["戊",7],["壬",7],["庚",16]],
  "酉":[["庚",10],["辛",20]],
  "戌":[["辛",9],["丁",3],["戊",18]],
  "亥":[["戊",7],["甲",7],["壬",16]],
};

const WOLGAN_START = [2,4,6,8,0,2,4,6,8,0];
const SIGAN_START  = [0,2,4,6,8,0,2,4,6,8];

const CHEONGAN_HAP = {"0,5":"土","1,6":"金","2,7":"水","3,8":"木","4,9":"火"};
const JIJI_YUKHAP  = {"0,1":"土","2,11":"木","3,10":"火","4,9":"金","5,8":"水","6,7":"土"};
const JIJI_CHUNG   = [[0,6],[1,7],[2,8],[3,9],[4,10],[5,11]];
const SAMHAP = [[[2,6,10],"火"],[[11,3,7],"木"],[[8,0,4],"水"],[[5,9,1],"金"]];

const SIBSUNG_NAMES = {
  "same_same":"비견","same_diff":"겁재",
  "생_same":"식신","생_diff":"상관",
  "극_same":"편재","극_diff":"정재",
  "피극_same":"편관","피극_diff":"정관",
  "피생_same":"편인","피생_diff":"정인",
};

// 연중 12절(節)의 고정 순서: 소한(丑)부터 대설(子)까지
const JEOL_SEQ = [
  ["소한",1,12],["입춘",2,1],["경칩",3,2],["청명",4,3],
  ["입하",5,4],["망종",6,5],["소서",7,6],["입추",8,7],
  ["백로",9,8],["한로",10,9],["입동",11,10],["대설",0,11],
];

const JEOL_YEAR_MIN = 1900, JEOL_YEAR_MAX = 2100;
const LUNAR_YEAR_MAX = 2050;

// ===== 날짜 유틸 =====
// Python date.toordinal() 과 동일 (0001-01-01 = 1)
function toOrdinal(y, m, d) {
  return Math.floor(Date.UTC(y, m - 1, d) / 86400000) + 719163;
}
function fromOrdinal(o) {
  const dt = new Date((o - 719163) * 86400000);
  return [dt.getUTCFullYear(), dt.getUTCMonth() + 1, dt.getUTCDate()];
}
// 분 단위 절대 시각
function toMinutes(y, m, d, hh, mi) { return toOrdinal(y, m, d) * 1440 + hh * 60 + mi; }
function pad2(n) { return String(n).padStart(2, "0"); }
// 파이썬 round()와 동일한 은행가 반올림 (12.5 → 12, 37.5 → 38)
function pyRound(x) {
  const f = Math.floor(x), diff = x - f;
  if (diff > 0.5) return f + 1;
  if (diff < 0.5) return f;
  return f % 2 === 0 ? f : f + 1;
}

// ===== 압축 데이터 디코딩 =====
let _jeolCache = null;
function jeolTable() {
  if (_jeolCache) return _jeolCache;
  const deltas = JEOL_ENC.split(",").map(v => parseInt(v, 36));
  const table = {};
  let k = 0;
  for (let y = JEOL_YEAR_MIN; y <= JEOL_YEAR_MAX; y++) {
    const yearStart = toOrdinal(y, 1, 1) * 1440;
    const rows = [];
    let acc = 0;
    for (let i = 0; i < 12; i++) {
      acc += deltas[k++];
      rows.push({ minutes: yearStart + acc, jjIdx: JEOL_SEQ[i][1], monthNum: JEOL_SEQ[i][2], name: JEOL_SEQ[i][0] });
    }
    table[y] = rows;
  }
  _jeolCache = table;
  return table;
}

let _lunarCache = null;
function lunarTable() {
  if (_lunarCache) return _lunarCache;
  const months = [];   // {ord, year, month, leap, len}
  const leapOf = y => parseInt(LUNAR_LEAPS[y - LUNAR_START_YEAR], 36);
  // 라벨 시퀀스 생성 (1899년 12월부터 시작)
  const labels = [];
  for (let ly = LUNAR_START_YEAR; ly <= LUNAR_YEAR_MAX; ly++) {
    const L = leapOf(ly);
    for (let m = 1; m <= 12; m++) {
      labels.push([ly, m, false]);
      if (L === m) labels.push([ly, m, true]);
    }
  }
  const startIdx = labels.findIndex(l => l[0] === LUNAR_START_YEAR && l[1] === 12 && !l[2]);
  let ord = LUNAR_BASE;
  for (let i = 0; i < LUNAR_LENS.length + 1; i++) {
    const lab = labels[startIdx + i];
    if (!lab) break;
    const len = i < LUNAR_LENS.length ? (LUNAR_LENS[i] === "1" ? 30 : 29) : 29;
    months.push({ ord, year: lab[0], month: lab[1], leap: lab[2], len });
    ord += len;
  }
  _lunarCache = months;
  return months;
}

function solarToLunar(y, m, d) {
  const o = toOrdinal(y, m, d);
  const months = lunarTable();
  if (o < months[0].ord) return null;
  let lo = 0, hi = months.length - 1, found = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (months[mid].ord <= o) { found = mid; lo = mid + 1; } else { hi = mid - 1; }
  }
  if (found < 0) return null;
  const mo = months[found];
  const day = o - mo.ord + 1;
  if (day > mo.len) return null;
  return { text: `${mo.year}-${pad2(mo.month)}-${pad2(day)}`, leap: mo.leap };
}

function lunarToSolar(ly, lm, ld, isLeap) {
  const months = lunarTable();
  const mo = months.find(x => x.year === ly && x.month === lm && x.leap === !!isLeap);
  if (!mo) {
    if (isLeap) {
      const leapMonth = months.find(x => x.year === ly && x.leap);
      throw new Error(leapMonth
        ? `${ly}년의 윤달은 윤${leapMonth.month}월입니다. 윤${lm}월은 없습니다.`
        : `${ly}년에는 윤달이 없습니다.`);
    }
    throw new Error(`음력 ${ly}년 ${lm}월은 지원 범위(1900~2050년) 밖입니다.`);
  }
  if (ld < 1 || ld > mo.len) throw new Error(`음력 ${ly}년 ${lm}월${isLeap ? "(윤달)" : ""}은 ${mo.len}일까지 있습니다.`);
  return fromOrdinal(mo.ord + ld - 1);
}

// ===== 사주 계산 =====
function getSibsung(ilganIdx, targetIdx) {
  const ilOh = OHAENG_CG[ilganIdx], tgOh = OHAENG_CG[targetIdx];
  const suffix = UMYANG_CG[ilganIdx] === UMYANG_CG[targetIdx] ? "same" : "diff";
  const i = OHAENG_IDX[ilOh], t = OHAENG_IDX[tgOh];
  if (ilOh === tgOh)                      return SIBSUNG_NAMES[`same_${suffix}`];
  if (OHAENG[(i + 1) % 5] === tgOh)       return SIBSUNG_NAMES[`생_${suffix}`];
  if (OHAENG[(i + 2) % 5] === tgOh)       return SIBSUNG_NAMES[`극_${suffix}`];
  if (OHAENG[(t + 1) % 5] === ilOh)       return SIBSUNG_NAMES[`피생_${suffix}`];
  if (OHAENG[(t + 2) % 5] === ilOh)       return SIBSUNG_NAMES[`피극_${suffix}`];
  return "unknown";
}

function makePillar(name, cgIdx, jjIdx) {
  const jj = JIJI[jjIdx];
  return {
    name, hanja: CHEONGAN[cgIdx] + jj, korean: CHEONGAN_KR[cgIdx] + JIJI_KR[jjIdx],
    cgIdx, jjIdx, cg: CHEONGAN[cgIdx], jj,
    cgOhaeng: OHAENG_CG[cgIdx], jjOhaeng: OHAENG_JJ[jjIdx],
    cgUmyang: UMYANG_CG[cgIdx] ? "양" : "음",
    jjUmyang: UMYANG_JJ[jjIdx] ? "양" : "음",
    jijanggan: JIJANGGAN[jj],
  };
}

function collectJeol(year) {
  const table = jeolTable(), out = [];
  for (const y of [year - 1, year, year + 1]) {
    if (table[y]) out.push(...table[y]);
  }
  out.sort((a, b) => a.minutes - b.minutes);
  return out;
}

function getSaju(year, month, day, hour, minute, gender = "남") {
  if (year < JEOL_YEAR_MIN + 1 || year > JEOL_YEAR_MAX - 1) {
    throw new Error(`${JEOL_YEAR_MIN + 1}~${JEOL_YEAR_MAX - 1}년 범위만 계산할 수 있습니다.`);
  }
  const birthMin = toMinutes(year, month, day, hour, minute);
  const ord = toOrdinal(year, month, day);

  // 1) 일주 — 60갑자 순환
  const dayGapja = ((ord + GANJI_C) % 60 + 60) % 60;
  const dayCg = dayGapja % 10, dayJj = dayGapja % 12;

  // 2) 년주 — 입춘 기준
  const yearJeol = jeolTable()[year];
  const ipchun = yearJeol[1].minutes;              // JEOL_SEQ[1] = 입춘
  const effYear = birthMin < ipchun ? year - 1 : year;
  const yearGapja = ((effYear - 1984) % 60 + 60) % 60;
  const yearCg = yearGapja % 10, yearJj = yearGapja % 12;

  // 3) 월주 — 절기 기준
  const allJeol = collectJeol(year);
  let monthJj = 1, monthNum = 12;
  for (const j of allJeol) {
    if (j.minutes <= birthMin) { monthJj = j.jjIdx; monthNum = j.monthNum; } else break;
  }
  const monthCg = (WOLGAN_START[yearCg] + ((monthJj - 2) % 12 + 12) % 12) % 10;

  // 4) 시주
  const hourJj = Math.floor((hour + 1) / 2) % 12;
  const hourCg = (SIGAN_START[dayCg] + hourJj) % 10;

  const lunar = solarToLunar(year, month, day);
  const saju = {
    birth: {
      solar: `${year}-${pad2(month)}-${pad2(day)}`,
      time: `${pad2(hour)}:${pad2(minute)}`,
      gender,
      lunar: lunar ? lunar.text : "",
      lunarLeap: lunar ? lunar.leap : false,
    },
    year:  makePillar("년주", yearCg,  yearJj),
    month: makePillar("월주", monthCg, monthJj),
    day:   makePillar("일주", dayCg,   dayJj),
    hour:  makePillar("시주", hourCg,  hourJj),
    ilgan: CHEONGAN[dayCg],
    ilganKr: CHEONGAN_KR[dayCg],
    ilganOhaeng: OHAENG_CG[dayCg],
    ddi: DDI[yearJj],
  };

  saju.sibsung = calcAllSibsung(dayCg, saju);
  saju.ohaengAnalysis = analyzeOhaeng(saju);
  saju.interactions = analyzeInteractions(saju);
  saju.strength = analyzeStrength(dayCg, saju);
  saju.daewoon = calcDaewoon(birthMin, gender, yearCg, monthCg, monthJj, year);
  saju.sewoon = calcSewoon(new Date().getFullYear(), dayCg);
  return saju;
}

function calcAllSibsung(ilganIdx, saju) {
  const out = {};
  for (const key of ["year", "month", "day", "hour"]) {
    const p = saju[key];
    const bongi = p.jijanggan[p.jijanggan.length - 1][0];
    out[key] = {
      천간: key !== "day" ? getSibsung(ilganIdx, p.cgIdx) : "일간(나)",
      지지: getSibsung(ilganIdx, CHEONGAN.indexOf(bongi)),
    };
  }
  return out;
}

function analyzeOhaeng(saju) {
  const count = {木:0, 火:0, 土:0, 金:0, 水:0};
  for (const key of ["year", "month", "day", "hour"]) {
    count[saju[key].cgOhaeng]++;
    count[saju[key].jjOhaeng]++;
  }
  const total = Object.values(count).reduce((a, b) => a + b, 0);
  const out = {};
  for (const oh of OHAENG) {
    const c = count[oh];
    const level = c === 0 ? "없음" : c <= 1 ? "약" : c <= 2 ? "보통" : "강";
    out[oh] = { count: c, percent: pyRound(c / total * 100), level };
  }
  return out;
}

function analyzeInteractions(saju) {
  const pillars = ["year", "month", "day", "hour"].map(k => saju[k]);
  const r = { 천간합: [], 지지충: [], 지지육합: [], 삼합: [] };
  const chungSet = new Set(JIJI_CHUNG.map(p => [...p].sort((a, b) => a - b).join(",")));

  for (let i = 0; i < pillars.length; i++) {
    for (let j = i + 1; j < pillars.length; j++) {
      const a = pillars[i], b = pillars[j];
      const cgKey = [Math.min(a.cgIdx, b.cgIdx), Math.max(a.cgIdx, b.cgIdx)].join(",");
      if (CHEONGAN_HAP[cgKey]) {
        r.천간합.push({ pillars: `${a.name}↔${b.name}`, detail: `${a.cg}+${b.cg}→${CHEONGAN_HAP[cgKey]}` });
      }
      const jjKey = [Math.min(a.jjIdx, b.jjIdx), Math.max(a.jjIdx, b.jjIdx)].join(",");
      if (chungSet.has(jjKey)) {
        r.지지충.push({ pillars: `${a.name}↔${b.name}`, detail: `${a.jj}↔${b.jj}` });
      }
      if (JIJI_YUKHAP[jjKey]) {
        r.지지육합.push({ pillars: `${a.name}↔${b.name}`, detail: `${a.jj}+${b.jj}→${JIJI_YUKHAP[jjKey]}` });
      }
    }
  }

  const jjSet = new Set(pillars.map(p => p.jjIdx));
  for (const [trio, element] of SAMHAP) {
    const matched = trio.filter(x => jjSet.has(x)).sort((a, b) => a - b);
    if (matched.length >= 2) {
      const names = matched.map(x => JIJI[x]).join("");
      r.삼합.push({ detail: `${names} → ${element}局 (${matched.length === 3 ? "완전삼합" : "반삼합"})` });
    }
  }
  return r;
}

function analyzeStrength(ilganIdx, saju) {
  const ilOh = OHAENG_CG[ilganIdx];
  const supports = oh => oh === ilOh || OHAENG[(OHAENG_IDX[oh] + 1) % 5] === ilOh;

  const deukryeong = supports(saju.month.jjOhaeng);
  let deukji = 0;
  for (const k of ["year", "month", "day", "hour"]) if (supports(saju[k].jjOhaeng)) deukji++;
  let deukse = 0;
  for (const k of ["year", "month", "hour"]) if (supports(saju[k].cgOhaeng)) deukse++;

  const score = (deukryeong ? 1 : 0) + deukji + deukse;
  let strength, yongsinDesc;
  if (score >= 4) {
    strength = "신강(身强)";
    yongsinDesc = `일간 ${CHEONGAN[ilganIdx]}(${ilOh})의 힘이 강하므로, 설기(泄氣)하거나 극(剋)하는 오행이 필요`;
  } else if (score <= 2) {
    strength = "신약(身弱)";
    yongsinDesc = `일간 ${CHEONGAN[ilganIdx]}(${ilOh})의 힘이 약하므로, 생(生)해주는 오행이 필요`;
  } else {
    strength = "중화(中和)";
    yongsinDesc = `일간 ${CHEONGAN[ilganIdx]}(${ilOh})의 힘이 비교적 균형적`;
  }
  return { strength, deukryeong, deukji, deukse, score, yongsinDesc };
}

function calcDaewoon(birthMin, gender, yearCg, monthCg, monthJj, birthYear) {
  const forward = (gender === "남" && UMYANG_CG[yearCg] === 1) || (gender === "여" && UMYANG_CG[yearCg] === 0);
  const allJeol = collectJeol(birthYear);

  let deltaDays = 0;
  if (forward) {
    for (const j of allJeol) {
      if (j.minutes > birthMin) { deltaDays = Math.floor((j.minutes - birthMin) / 1440); break; }
    }
  } else {
    for (let i = allJeol.length - 1; i >= 0; i--) {
      if (allJeol[i].minutes <= birthMin) { deltaDays = Math.floor((birthMin - allJeol[i].minutes) / 1440); break; }
    }
  }
  const startAge = pyRound(deltaDays / 3);

  let monthGapja = 0;
  for (let i = 0; i < 60; i++) if (i % 10 === monthCg && i % 12 === monthJj) { monthGapja = i; break; }

  const list = [];
  for (let i = 1; i <= 9; i++) {
    const idx = ((forward ? monthGapja + i : monthGapja - i) % 60 + 60) % 60;
    const cg = idx % 10, jj = idx % 12;
    const age = startAge + (i - 1) * 10;
    list.push({
      age, ageRange: `${age}~${age + 9}세`,
      hanja: CHEONGAN[cg] + JIJI[jj], korean: CHEONGAN_KR[cg] + JIJI_KR[jj],
      cgOhaeng: OHAENG_CG[cg], jjOhaeng: OHAENG_JJ[jj],
    });
  }
  return { direction: forward ? "순행" : "역행", startAge, list };
}

function calcSewoon(targetYear, ilganIdx) {
  const g = ((targetYear - 1984) % 60 + 60) % 60;
  const cg = g % 10, jj = g % 12;
  return {
    year: targetYear,
    hanja: CHEONGAN[cg] + JIJI[jj], korean: CHEONGAN_KR[cg] + JIJI_KR[jj],
    cgOhaeng: OHAENG_CG[cg], jjOhaeng: OHAENG_JJ[jj],
    sibsung: getSibsung(ilganIdx, cg),
  };
}

// AI 해석용 구조화 데이터 (saju_engine.py의 to_dict와 동일 구조)
function toDict(saju) {
  const b = saju.birth, dw = saju.daewoon, sw = saju.sewoon, s = saju.strength;
  const pillars = {};
  for (const [key, label] of [["year","년주"],["month","월주"],["day","일주"],["hour","시주"]]) {
    const p = saju[key], ss = saju.sibsung[key];
    pillars[label] = {
      한자: p.hanja, 한글: p.korean,
      천간: { 글자: p.cg, 오행: p.cgOhaeng, 음양: p.cgUmyang, 십성: ss.천간 },
      지지: { 글자: p.jj, 오행: p.jjOhaeng, 음양: p.jjUmyang, 십성: ss.지지 },
      지장간: p.jijanggan.map(([cg, d]) => ({ 천간: cg, 일수: d })),
    };
  }
  const ohaeng = {};
  for (const [oh, v] of Object.entries(saju.ohaengAnalysis)) {
    ohaeng[oh] = { 개수: v.count, 비율: `${v.percent}%`, 강도: v.level };
  }
  const interactions = {};
  for (const k of ["천간합","지지충","지지육합","삼합"]) {
    if (saju.interactions[k].length) {
      interactions[k] = saju.interactions[k].map(it => it.detail || it.pillars);
    }
  }
  const birthYear = parseInt(b.solar.slice(0, 4), 10);
  const currentAge = sw.year - birthYear;
  const currentDaewoon = dw.list.find(d => d.age <= currentAge && currentAge < d.age + 10) || null;

  return {
    출생정보: { 양력: `${b.solar} ${b.time}`, 음력: b.lunar, 성별: b.gender, 띠: saju.ddi + "띠" },
    일간: { 천간: saju.ilgan, 한글: saju.ilganKr, 오행: saju.ilganOhaeng },
    사주원국: pillars,
    오행분포: ohaeng,
    신강신약: {
      판정: s.strength, 득령: s.deukryeong,
      득지: `${s.deukji}/4`, 득세: `${s.deukse}/3`,
      총점: s.score, 용신방향: s.yongsinDesc,
    },
    합충관계: Object.keys(interactions).length ? interactions : { 결과: "특별한 합충 없음" },
    대운: {
      방향: dw.direction, 시작나이: dw.startAge,
      현재대운: currentDaewoon && {
        age: currentDaewoon.age, age_range: currentDaewoon.ageRange,
        hanja: currentDaewoon.hanja, korean: currentDaewoon.korean,
        cg_ohaeng: currentDaewoon.cgOhaeng, jj_ohaeng: currentDaewoon.jjOhaeng,
      },
      전체목록: dw.list.map(d => ({
        age: d.age, age_range: d.ageRange, hanja: d.hanja,
        korean: d.korean, cg_ohaeng: d.cgOhaeng, jj_ohaeng: d.jjOhaeng,
      })),
    },
    세운: {
      연도: sw.year, 한자: sw.hanja, 한글: sw.korean,
      천간오행: sw.cgOhaeng, 지지오행: sw.jjOhaeng, 십성: sw.sibsung,
    },
  };
}
