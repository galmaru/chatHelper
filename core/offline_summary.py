"""오프라인 추출 요약 모듈 (TextRank / TF-IDF)"""

import re
import math
from collections import Counter

from core.parser import parse_chat, get_participants


_LENGTH_MAP = {
    "short": 3,
    "medium": 5,
    "long": 8,
}


def summarize_offline(text: str, length: str = "medium") -> dict:
    """
    오프라인 TextRank/TF-IDF 기반 추출 요약을 수행한다.

    Args:
        text: 요약할 채팅 텍스트 (원문 전체)
        length: 요약 길이 - "short"(3문장) / "medium"(5문장) / "long"(8문장)

    Returns:
        {
            "summary": str,
            "keywords": list[str],
            "participants": list[str],
            "mode": "offline"
        }
    """
    sentence_count = _LENGTH_MAP.get(length, 5)

    messages = parse_chat(text)
    participants = get_participants(messages)

    # 메시지 본문만 추출
    all_text = " ".join(msg["message"] for msg in messages if msg.get("message"))

    sentences = _split_sentences(all_text)
    if not sentences:
        return {
            "summary": "(요약할 내용이 없습니다.)",
            "keywords": [],
            "participants": participants,
            "mode": "offline",
        }

    # TF-IDF 기반 키워드 추출
    keywords = _extract_keywords(all_text, top_n=5)

    # TextRank 기반 문장 추출 요약
    if len(sentences) <= sentence_count:
        summary_sentences = sentences
    else:
        scores = _textrank_scores(sentences)
        ranked = sorted(
            range(len(sentences)),
            key=lambda i: scores[i],
            reverse=True,
        )[:sentence_count]
        # 원문 순서 유지
        summary_sentences = [sentences[i] for i in sorted(ranked)]

    summary = " ".join(summary_sentences)

    return {
        "summary": summary,
        "keywords": keywords,
        "participants": participants,
        "mode": "offline",
    }


def _split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리한다."""
    # 한국어/영어 문장 구분자
    pattern = re.compile(r"(?<=[.!?。])\s+|(?<=\n)\s*")
    raw = pattern.split(text)
    sentences = []
    for s in raw:
        s = s.strip()
        if len(s) > 5:  # 너무 짧은 조각 제거
            sentences.append(s)
    return sentences


def _tokenize(text: str) -> list[str]:
    """간단한 토큰화 (공백/구두점 기준)"""
    tokens = re.findall(r"[\w가-힣]+", text.lower())
    # 불용어 제거 (간단한 한국어/영어 불용어)
    stopwords = {
        "이", "가", "을", "를", "은", "는", "에", "의", "과", "와",
        "도", "로", "으로", "에서", "으로서", "한", "하다", "있다",
        "the", "a", "an", "is", "are", "was", "were", "i", "you",
        "he", "she", "it", "we", "they", "and", "or", "but",
    }
    return [t for t in tokens if t not in stopwords and len(t) > 1]


def _extract_keywords(text: str, top_n: int = 5) -> list[str]:
    """TF-IDF 기반 상위 키워드를 추출한다."""
    sentences = _split_sentences(text)
    if not sentences:
        return []

    # 각 문장을 문서로 취급하여 TF-IDF 계산
    tokenized = [_tokenize(s) for s in sentences]
    all_tokens = [t for tokens in tokenized for t in tokens]
    if not all_tokens:
        return []

    tf = Counter(all_tokens)
    total = sum(tf.values())
    tf_scores = {w: c / total for w, c in tf.items()}

    doc_freq = Counter()
    for tokens in tokenized:
        for word in set(tokens):
            doc_freq[word] += 1

    n_docs = len(sentences)
    tfidf = {}
    for word, tf_val in tf_scores.items():
        idf = math.log((n_docs + 1) / (doc_freq.get(word, 0) + 1)) + 1
        tfidf[word] = tf_val * idf

    top_words = sorted(tfidf, key=lambda w: tfidf[w], reverse=True)[:top_n]
    return top_words


def _textrank_scores(sentences: list[str]) -> list[float]:
    """TextRank 알고리즘으로 문장 점수를 계산한다."""
    n = len(sentences)
    tokenized = [set(_tokenize(s)) for s in sentences]

    # 유사도 행렬 구성
    similarity = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            inter = tokenized[i] & tokenized[j]
            denom = math.log(len(tokenized[i]) + 1) + math.log(len(tokenized[j]) + 1)
            if denom > 0 and inter:
                similarity[i][j] = len(inter) / denom

    # PageRank 반복 계산 (15회)
    scores = [1.0 / n] * n
    damping = 0.85
    for _ in range(15):
        new_scores = [(1 - damping) / n] * n
        for i in range(n):
            col_sum = sum(similarity[k][i] for k in range(n))
            if col_sum == 0:
                continue
            for j in range(n):
                if similarity[j][i] > 0:
                    new_scores[i] += damping * scores[j] * (similarity[j][i] / col_sum)
        scores = new_scores

    return scores
