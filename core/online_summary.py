"""온라인 AI 요약 모듈 (OpenAI / Claude API)"""

from core.offline_summary import summarize_offline


_SYSTEM_PROMPT = """당신은 채팅 내역 요약 전문가입니다.
주어진 채팅 내역을 분석하여 다음을 제공하세요:
1. 핵심 내용 요약 ({length} 길이)
2. 주요 키워드 5개
3. 핵심 결정사항 또는 Action Item (있는 경우)
한국어로 답변하세요.

응답은 반드시 아래 JSON 형식으로만 반환하세요:
{{
  "summary": "핵심 요약 내용",
  "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
  "action_items": ["액션아이템1", "액션아이템2"]
}}"""

_LENGTH_LABEL = {
    "short": "짧게 (3문장 이내)",
    "medium": "보통 (5문장 내외)",
    "long": "자세히 (8문장 이내)",
}


def summarize_online(
    text: str,
    provider: str,
    api_key: str,
    length: str = "medium",
    participants: list[str] | None = None,
) -> dict:
    """
    OpenAI 또는 Anthropic API로 AI 요약을 수행한다.
    API 오류 시 오프라인 모드로 자동 폴백한다.

    Args:
        text: 요약할 채팅 텍스트
        provider: "openai" 또는 "anthropic"
        api_key: API 키
        length: "short" / "medium" / "long"
        participants: 참여자 목록 (없으면 자동 추출)

    Returns:
        {
            "summary": str,
            "keywords": list[str],
            "participants": list[str],
            "action_items": list[str],
            "mode": str  # "openai" / "anthropic" / "offline(fallback)"
        }
    """
    from core.parser import parse_chat, get_participants

    if participants is None:
        messages = parse_chat(text)
        participants = get_participants(messages)

    system_prompt = _SYSTEM_PROMPT.format(length=_LENGTH_LABEL.get(length, "보통"))

    try:
        if provider == "openai":
            result = _call_openai(text, api_key, system_prompt)
            mode = "openai"
        elif provider == "anthropic":
            result = _call_anthropic(text, api_key, system_prompt)
            mode = "anthropic"
        else:
            raise ValueError(f"지원하지 않는 provider: {provider}")

        return {
            "summary": result.get("summary", ""),
            "keywords": result.get("keywords", []),
            "participants": participants,
            "action_items": result.get("action_items", []),
            "mode": mode,
        }

    except Exception:
        # 오프라인 폴백
        offline = summarize_offline(text, length)
        offline["mode"] = "offline(fallback)"
        offline["action_items"] = []
        return offline


def _call_openai(text: str, api_key: str, system_prompt: str) -> dict:
    """OpenAI gpt-4o-mini 모델로 요약을 요청한다."""
    import json
    import openai

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"다음 채팅 내역을 요약해주세요:\n\n{text[:8000]}"},
        ],
        temperature=0.3,
        max_tokens=1000,
    )
    content = response.choices[0].message.content or ""
    return _parse_json_response(content)


def _call_anthropic(text: str, api_key: str, system_prompt: str) -> dict:
    """Anthropic claude-haiku-3-5 모델로 요약을 요청한다."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        system=system_prompt,
        messages=[
            {"role": "user", "content": f"다음 채팅 내역을 요약해주세요:\n\n{text[:8000]}"},
        ],
    )
    content = response.content[0].text if response.content else ""
    return _parse_json_response(content)


def _parse_json_response(content: str) -> dict:
    """AI 응답에서 JSON을 추출한다."""
    import json
    import re

    # JSON 블록 추출 시도
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # 파싱 실패 시 기본값 반환
    return {
        "summary": content.strip(),
        "keywords": [],
        "action_items": [],
    }
