"""채팅 형식 파싱 모듈"""

import re
from typing import Optional


def parse_chat(text: str) -> list[dict]:
    """
    채팅 텍스트를 파싱하여 메시지 목록으로 반환한다.

    지원 형식:
    - 카카오톡: [2024-01-01 12:00] 홍길동 : 메시지
    - 라인: 홍길동 (오전 12:00)\\n메시지
    - WhatsApp: 2024-01-01 12:00:00 - 홍길동: 메시지
    - 일반 텍스트: 폴백 처리

    Args:
        text: 파싱할 채팅 텍스트

    Returns:
        메시지 딕셔너리 목록. 각 항목:
        {"sender": str, "timestamp": str | None, "message": str}
    """
    parsers = [
        _parse_kakao,
        _parse_line,
        _parse_whatsapp,
    ]

    for parser in parsers:
        messages = parser(text)
        if messages:
            return messages

    # 폴백: 전체 텍스트를 단일 메시지로 처리
    return [{"sender": "알 수 없음", "timestamp": None, "message": text.strip()}]


def _parse_kakao(text: str) -> list[dict]:
    """카카오톡 형식 파싱: [2024-01-01 12:00] 홍길동 : 메시지"""
    pattern = re.compile(
        r"\[(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)\]\s+(.+?)\s*:\s*(.*)"
    )
    messages = []
    for line in text.splitlines():
        m = pattern.match(line.strip())
        if m:
            messages.append({
                "sender": m.group(2).strip(),
                "timestamp": m.group(1).strip(),
                "message": m.group(3).strip(),
            })

    if len(messages) < 2:
        return []
    return messages


def _parse_line(text: str) -> list[dict]:
    """라인 형식 파싱: 홍길동 (오전/오후 12:00)\\n메시지"""
    pattern = re.compile(
        r"^(.+?)\s+\((오전|오후|AM|PM)?\s*(\d{1,2}:\d{2})\)\s*$"
    )
    messages = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = pattern.match(lines[i].strip())
        if m and i + 1 < len(lines):
            sender = m.group(1).strip()
            ampm = m.group(2) or ""
            time_str = m.group(3)
            timestamp = f"{ampm} {time_str}".strip()
            message_lines = []
            i += 1
            while i < len(lines) and not pattern.match(lines[i].strip()):
                message_lines.append(lines[i])
                i += 1
            messages.append({
                "sender": sender,
                "timestamp": timestamp,
                "message": "\n".join(message_lines).strip(),
            })
        else:
            i += 1

    if len(messages) < 2:
        return []
    return messages


def _parse_whatsapp(text: str) -> list[dict]:
    """WhatsApp 형식 파싱: 2024-01-01 12:00:00 - 홍길동: 메시지"""
    pattern = re.compile(
        r"(\d{4}[.\-/]\d{1,2}[.\-/]\d{1,2}[\s,]+\d{1,2}:\d{2}(?::\d{2})?)\s*[-–]\s*(.+?):\s*(.*)"
    )
    messages = []
    for line in text.splitlines():
        m = pattern.match(line.strip())
        if m:
            messages.append({
                "sender": m.group(2).strip(),
                "timestamp": m.group(1).strip(),
                "message": m.group(3).strip(),
            })

    if len(messages) < 2:
        return []
    return messages


def get_participants(messages: list[dict]) -> list[str]:
    """
    메시지 목록에서 참여자 목록을 추출한다.

    Args:
        messages: parse_chat()의 반환값

    Returns:
        중복 제거된 참여자 이름 목록 (등장 순서 유지)
    """
    seen = set()
    participants = []
    for msg in messages:
        sender = msg.get("sender", "")
        if sender and sender not in seen:
            seen.add(sender)
            participants.append(sender)
    return participants
