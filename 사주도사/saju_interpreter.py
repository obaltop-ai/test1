"""
사주 AI 해석 모듈
Claude API(anthropic SDK)를 사용해서 사주 분석 결과를 해석합니다.
"""
import os
import json
import anthropic

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GUIDE_PATH = os.path.join(BASE_DIR, "사주·역술 운세 풀이 코드 구현을 위한 핵심 지식 가이드.md")


def _load_guide() -> str:
    with open(GUIDE_PATH, encoding="utf-8") as f:
        return f.read()


def _build_system_prompt(guide: str) -> list[dict]:
    """프롬프트 캐싱을 적용한 시스템 프롬프트 구성"""
    return [
        {
            "type": "text",
            "text": (
                "당신은 사주명리학 전문가입니다. "
                "사용자가 제공하는 사주팔자 데이터를 바탕으로 깊이 있고 실용적인 운세 해석을 제공합니다.\n\n"
                "해석 원칙:\n"
                "1. 일간(日干)을 중심으로 전체 팔자를 해석합니다.\n"
                "2. 십성(十星), 오행(五行), 합충(合沖) 관계를 종합적으로 분석합니다.\n"
                "3. 현재 대운(大運)과 세운(歲運)이 원국에 미치는 영향을 설명합니다.\n"
                "4. 추상적인 이론보다 구체적이고 실생활에 적용 가능한 해석을 제공합니다.\n"
                "5. 한국어로 답변합니다.\n\n"
                "=== 사주명리 핵심 지식 가이드 ===\n\n"
            ) + guide,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def interpret(saju_dict: dict, extra_question: str = "") -> str:
    """
    사주 dict를 받아 Claude API로 AI 해석을 생성합니다.

    Args:
        saju_dict: SajuEngine.to_dict()의 반환값
        extra_question: 추가로 물어볼 질문 (선택)

    Returns:
        AI 해석 텍스트
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")

    client = anthropic.Anthropic(api_key=api_key)
    guide = _load_guide()
    system = _build_system_prompt(guide)

    saju_json = json.dumps(saju_dict, ensure_ascii=False, indent=2)
    user_message = f"""다음은 사주팔자 분석 데이터입니다. 이를 바탕으로 종합적인 사주 해석을 해주세요.

```json
{saju_json}
```

아래 순서로 해석해 주세요:

1. **사주 총평** — 이 사람의 사주가 가진 전체적인 특성과 기질
2. **일간 분석** — 일간의 성격, 강점, 주의할 점
3. **오행·십성 분석** — 오행 분포와 주요 십성이 의미하는 바
4. **신강/신약과 용신** — 신강신약 판정 근거와 용신·희신 방향
5. **합충 분석** — 합충이 이 사람의 삶에 미치는 영향
6. **현재 대운 해석** — 현재 대운이 원국과 어떻게 작용하는지
7. **{saju_dict['세운']['연도']}년 세운 해석** — 올해의 운세 흐름과 주의사항
8. **종합 조언** — 이 사주를 가진 사람에게 실질적으로 도움이 되는 조언
"""

    if extra_question:
        user_message += f"\n\n**추가 질문:** {extra_question}"

    result_parts = []

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for event in stream:
            if hasattr(event, "type"):
                if event.type == "content_block_delta":
                    delta = event.delta
                    if hasattr(delta, "type") and delta.type == "text_delta":
                        print(delta.text, end="", flush=True)
                        result_parts.append(delta.text)

    print()  # 개행
    return "".join(result_parts)


def interpret_with_cache_info(saju_dict: dict, extra_question: str = "") -> tuple[str, dict]:
    """
    해석 + 캐시 사용 정보를 함께 반환합니다.

    Returns:
        (해석 텍스트, usage 정보 dict)
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.")

    client = anthropic.Anthropic(api_key=api_key)
    guide = _load_guide()
    system = _build_system_prompt(guide)

    saju_json = json.dumps(saju_dict, ensure_ascii=False, indent=2)
    user_message = f"""다음은 사주팔자 분석 데이터입니다.

```json
{saju_json}
```

아래 순서로 해석해 주세요:

1. **사주 총평** — 이 사람의 사주가 가진 전체적인 특성과 기질
2. **일간 분석** — 일간의 성격, 강점, 주의할 점
3. **오행·십성 분석** — 오행 분포와 주요 십성이 의미하는 바
4. **신강/신약과 용신** — 신강신약 판정 근거와 용신·희신 방향
5. **합충 분석** — 합충이 이 사람의 삶에 미치는 영향
6. **현재 대운 해석** — 현재 대운이 원국과 어떻게 작용하는지
7. **{saju_dict['세운']['연도']}년 세운 해석** — 올해의 운세 흐름과 주의사항
8. **종합 조언** — 이 사주를 가진 사람에게 실질적으로 도움이 되는 조언
"""

    if extra_question:
        user_message += f"\n\n**추가 질문:** {extra_question}"

    result_parts = []

    with client.messages.stream(
        model="claude-opus-4-7",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for event in stream:
            if hasattr(event, "type"):
                if event.type == "content_block_delta":
                    delta = event.delta
                    if hasattr(delta, "type") and delta.type == "text_delta":
                        print(delta.text, end="", flush=True)
                        result_parts.append(delta.text)

        final = stream.get_final_message()

    print()
    usage = {
        "input_tokens": final.usage.input_tokens,
        "output_tokens": final.usage.output_tokens,
        "cache_creation_tokens": getattr(final.usage, "cache_creation_input_tokens", 0),
        "cache_read_tokens": getattr(final.usage, "cache_read_input_tokens", 0),
    }
    return "".join(result_parts), usage
