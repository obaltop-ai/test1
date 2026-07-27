# 사주도사 웹 버전

`사주도사/` 의 파이썬 CLI를 휴대폰에서 쓸 수 있도록 단일 HTML 페이지로 포팅한 것입니다.
외부 요청 없이 파일 하나로 동작하므로, 브라우저로 열기만 하면 됩니다.

## 파일

| 경로 | 설명 |
|---|---|
| `saju.html` | 배포용 결과물. 데이터·엔진·UI가 모두 인라인된 단일 파일 (50KB) |
| `build/template.html` | UI 템플릿. `/*__DATA__*/`, `/*__ENGINE__*/` 자리에 아래 두 파일을 끼워 넣습니다 |
| `build/saju_data.js` | 만세력 압축 데이터 (12KB) |
| `build/saju_engine.js` | `saju_engine.py` 의 JavaScript 포팅 |
| `build/verify.js` | 파이썬 원본과 계산 결과를 대조하는 검증 스크립트 |
| `build/uitest.js`, `build/edge.js` | 브라우저 렌더링·예외 처리 테스트 |

## 만세력 데이터를 10.3MB → 12KB로 줄인 방법

원본 `만세력DB/` 는 10.3MB라 웹에 그대로 싣기 어려워 두 가지로 대체했습니다.

**일간지 (9.3MB → 0)** — 60갑자는 하루씩 순환할 뿐이라 표가 필요 없습니다.

```
갑자 인덱스 = (양력 날짜의 ordinal + 14) % 60
```

1900~2100년 전체 73,414일에 대해 원본 DB와 대조했고 불일치 0건입니다.

**절기 (1MB → 9.6KB)** — 월주 판정에 쓰이는 12절(節)만 남기고, 연초 자정 기준 분(分) 오프셋을
델타 인코딩 후 base36으로 적었습니다. 24절기 중 중기(中氣)는 사주 계산에 쓰이지 않습니다.

**음력 (1.9KB)** — 음력 월 시작일만 있으면 되므로, 월 길이를 29일/30일 1비트로 적고
연도별 윤달 번호를 따로 두었습니다.

## 검증

파이썬 원본과 결과가 같은지 `to_dict()` 출력 전체를 문자열 비교했습니다.

```bash
cd web/build
python3 ...   # expected.json 생성 (verify.js 주석 참고)
node verify.js
```

1901~2049년 무작위 4,000건 + 입춘 경계·자시·윤년 등 경계 60건, 총 4,060건 전수 일치합니다.

포팅 중 실제로 갈렸던 부분이 하나 있습니다. 파이썬 `round()` 는 은행가 반올림이라
`round(12.5) == 12` 인데 자바스크립트 `Math.round(12.5)` 는 13입니다.
오행 비율(8분의 1 = 12.5%)에서 차이가 나서 `pyRound()` 로 맞췄습니다.

## 원본과 다른 점

- **AI 해석은 페이지 안에서 실행되지 않습니다.** 브라우저에서 API 키를 다루는 것이 안전하지
  않고, 배포 환경이 외부 요청을 차단하기 때문입니다. 대신 `해석 프롬프트 복사` 버튼이
  `saju_interpreter.py` 와 같은 형식의 프롬프트를 만들어 주므로, Claude 앱에 붙여넣으면 됩니다.
- **입력 범위는 1901~2099년입니다.** 음력 표기는 원본 DB와 마찬가지로 2050년까지만 나옵니다.
- 출생 시각을 모를 때 낮 12시로 계산하는 선택지를 넣었습니다. 이 경우 시주가 실제와
  다를 수 있다는 안내를 함께 띄웁니다.

## 고칠 때

`build/template.html` 이나 `build/saju_engine.js` 를 고친 뒤 다시 끼워 넣으면 됩니다.

```bash
cd web
python3 -c "
html = open('build/template.html', encoding='utf-8').read()
data = open('build/saju_data.js', encoding='utf-8').read()
eng  = open('build/saju_engine.js', encoding='utf-8').read()
open('saju.html', 'w', encoding='utf-8').write(
    html.replace('/*__DATA__*/', data).replace('/*__ENGINE__*/', eng))
"
```

엔진을 고쳤다면 `node verify.js` 로 파이썬 원본과 여전히 같은 값이 나오는지 확인하세요.
