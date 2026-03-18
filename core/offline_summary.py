"""오프라인 요약 모듈 — TextTiling 기반 주제별 요약

주제 분리 알고리즘 (TextTiling 간소화):
1. 메시지를 슬라이딩 윈도우 블록으로 나눔
2. 인접 블록 간 어휘 유사도(Jaccard) 계산
3. 유사도가 주변보다 낮은 골짜기(valley) = 주제 전환점
4. 각 세그먼트(주제)에서 핵심 발언 + 키워드 추출
"""

import re
from collections import Counter, defaultdict
from core.parser import parse_chat, get_participants


_LENGTH_MAP = {
    "short": 1,   # 주제당 핵심 발언 1개
    "medium": 2,  # 주제당 핵심 발언 2개
    "long": 3,    # 주제당 핵심 발언 3개
}

_STOPWORDS = {
    "이", "가", "을", "를", "은", "는", "에", "의", "과", "와", "도", "로",
    "으로", "에서", "으로서", "한", "하다", "있다", "없다", "것", "수", "그",
    "저", "나", "제", "네", "우리", "너", "그게", "그거", "아", "어", "오",
    "응", "예", "ㅋ", "ㅎ", "ㄷ", "ㅠ", "ㅜ", "the", "a", "an",
    "is", "are", "was", "were", "i", "you", "he", "she", "it", "we",
    "they", "and", "or", "but", "so", "ok", "yes", "no",
}


def summarize_offline(
    text: str,
    length: str = "medium",
    include_senders: set[str] | None = None,
) -> dict:
    """
    오프라인 TextTiling 기반 주제별 요약을 수행한다.

    Args:
        text: 요약할 채팅 텍스트 (원문 전체, 타임스탬프 포함)
        length: "short"(주제당 1문장) / "medium"(2문장) / "long"(3문장)
        include_senders: 요약에 포함할 화자 집합 (None이면 전체)

    Returns:
        {
            "summary": str,
            "topics": list[dict],   # 주제별 상세 결과
            "keywords": list[str],
            "participants": list[str],
            "mode": "offline"
        }
    """
    messages = parse_chat(text)
    participants = get_participants(messages)

    messages = [
        m for m in messages
        if m.get("message", "").strip()
        and (include_senders is None or m.get("sender") in include_senders)
    ]

    if not messages:
        return {
            "summary": "(요약할 내용이 없습니다.)",
            "topics": [],
            "keywords": [],
            "participants": participants,
            "mode": "offline",
        }

    max_per_speaker = _LENGTH_MAP.get(length, 2)

    # 1. 주제 경계 감지 → 세그먼트 분리
    segments = _segment_by_topic(messages)

    # 2. 전체 키워드
    all_text = " ".join(m["message"] for m in messages)
    global_freq = _calc_word_freq(all_text)
    keywords = _top_keywords(global_freq, top_n=5)

    # 3. 세그먼트별 주제 제목 + 화자별 발언 요약
    topics = []
    for i, seg_messages in enumerate(segments):
        seg_text = " ".join(m["message"] for m in seg_messages)
        seg_freq = _calc_word_freq(seg_text)
        seg_keywords = _top_keywords(seg_freq, top_n=3)
        title = _generate_topic_title(seg_keywords)

        # 화자별로 메시지 그룹화 후 축약 (등장 순서 유지)
        per_speaker = _group_and_condense(seg_messages, seg_freq, max_per_speaker)

        topics.append({
            "index": i + 1,
            "title": title,
            "keywords": seg_keywords,
            "per_speaker": per_speaker,   # OrderedDict: {sender: condensed_text}
            "message_count": len(seg_messages),
        })

    # 4. 텍스트 형태 요약 생성
    summary = _build_summary_text(topics)

    return {
        "summary": summary,
        "topics": topics,
        "keywords": keywords,
        "participants": participants,
        "mode": "offline",
    }


def _segment_by_topic(messages: list[dict], window: int = 3) -> list[list[dict]]:
    """
    TextTiling 방식으로 메시지를 주제별 세그먼트로 분리한다.

    인접한 두 윈도우 블록의 어휘 유사도(Jaccard)가 주변보다
    낮은 골짜기(valley) 지점을 주제 전환점으로 판단한다.

    메시지 수가 적으면 단일 세그먼트로 반환한다.
    """
    n = len(messages)

    # 메시지가 너무 적으면 분리하지 않음
    if n < window * 2 + 1:
        return [messages]

    # 각 경계 지점(i와 i+1 사이)의 유사도 계산
    scores = []
    for i in range(window, n - window):
        left_tokens = set(_tokenize(" ".join(m["message"] for m in messages[i - window:i])))
        right_tokens = set(_tokenize(" ".join(m["message"] for m in messages[i:i + window])))
        if not left_tokens and not right_tokens:
            scores.append((i, 1.0))
            continue
        jaccard = len(left_tokens & right_tokens) / len(left_tokens | right_tokens) if (left_tokens | right_tokens) else 1.0
        scores.append((i, jaccard))

    if not scores:
        return [messages]

    # 골짜기(valley) 감지: 양옆보다 낮은 지점
    avg_score = sum(s for _, s in scores) / len(scores)
    boundaries = []
    for k in range(1, len(scores) - 1):
        _, prev_s = scores[k - 1]
        pos, curr_s = scores[k]
        _, next_s = scores[k + 1]
        if curr_s < prev_s and curr_s < next_s and curr_s < avg_score * 0.85:
            boundaries.append(pos)

    if not boundaries:
        return [messages]

    # 경계로 세그먼트 분리
    segments = []
    prev = 0
    for b in boundaries:
        segments.append(messages[prev:b])
        prev = b
    segments.append(messages[prev:])

    # 너무 짧은 세그먼트(1개)는 앞 세그먼트에 합치기
    merged = []
    for seg in segments:
        if merged and len(seg) <= 1:
            merged[-1].extend(seg)
        else:
            merged.append(seg)

    return merged if merged else [messages]


def _calc_word_freq(text: str) -> dict[str, float]:
    """단어 빈도(TF)를 계산한다."""
    tokens = _tokenize(text)
    if not tokens:
        return {}
    counter = Counter(tokens)
    total = sum(counter.values())
    return {w: c / total for w, c in counter.items()}


def _score_message(message: str, word_freq: dict[str, float]) -> float:
    """메시지 중요도 점수 = 단어 빈도 합 / 단어 수 + 길이 보너스."""
    tokens = _tokenize(message)
    if not tokens:
        return 0.0
    import math
    score = sum(word_freq.get(t, 0) for t in tokens) / len(tokens)
    return score + math.log(len(tokens) + 1) * 0.05


def _top_keywords(word_freq: dict[str, float], top_n: int = 5) -> list[str]:
    """빈도 상위 키워드를 반환한다."""
    return sorted(word_freq, key=lambda w: word_freq[w], reverse=True)[:top_n]


def _generate_topic_title(keywords: list[str]) -> str:
    """키워드로 자연스러운 주제 제목을 생성한다.
    예) ["맥주", "잠"] → "맥주 잠 얘기"
    """
    if not keywords:
        return "기타 얘기"
    # 상위 2개 키워드로 제목 구성
    key_words = keywords[:2]
    return " ".join(key_words) + " 얘기"


def _group_and_condense(
    seg_messages: list[dict],
    seg_freq: dict[str, float],
    max_per_speaker: int,
) -> dict[str, str]:
    """주제 내 화자별 메시지를 묶어 축약한다.

    - 짧은 메시지(10자 이하) 여러 개 → ". " 으로 이어 붙임
    - 긴 메시지가 여러 개 → 점수 높은 상위 N개 선택 후 이어 붙임
    - 등장 순서 유지
    """
    from collections import OrderedDict

    # 화자 등장 순서 유지하며 메시지 수집
    speaker_msgs: dict[str, list[str]] = OrderedDict()
    for m in seg_messages:
        sender = m.get("sender", "알 수 없음")
        msg = m.get("message", "").strip()
        if not msg:
            continue
        if sender not in speaker_msgs:
            speaker_msgs[sender] = []
        speaker_msgs[sender].append(msg)

    result: dict[str, str] = OrderedDict()
    for sender, msgs in speaker_msgs.items():
        if not msgs:
            continue

        short = [m for m in msgs if len(m) <= 10]
        long_ = [m for m in msgs if len(m) > 10]

        parts = []
        # 짧은 메시지는 전부 이어 붙임
        if short:
            parts.append(". ".join(short))
        # 긴 메시지는 점수 순 상위 N개
        if long_:
            scored = sorted(long_, key=lambda m: _score_message(m, seg_freq), reverse=True)
            parts.extend(scored[:max_per_speaker])

        result[sender] = ". ".join(parts)

    return result


def _build_summary_text(topics: list[dict]) -> str:
    """주제별 요약을 사람이 읽기 좋은 텍스트로 변환한다.

    출력 형식:
        주제1. 맥주 잠 얘기
        표수한: 맥주를 애매하게 마셧더니 잠을 못잠
        조혜원: 저도 어제 그랬어요
    """
    lines = []
    for topic in topics:
        lines.append(f"주제{topic['index']}. {topic['title']}")
        for sender, condensed in topic["per_speaker"].items():
            lines.append(f"{sender}: {condensed}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _tokenize(text: str) -> list[str]:
    """공백/구두점 기준 토큰화 + 불용어 제거."""
    tokens = re.findall(r"[가-힣a-zA-Z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]
