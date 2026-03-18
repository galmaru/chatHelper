"""파일 로드 및 인코딩 처리 모듈"""

import chardet


class FileTooLargeError(Exception):
    """파일 크기가 50MB를 초과할 때 발생하는 예외"""
    pass


def load_file(path: str) -> str:
    """
    텍스트 파일을 읽어 문자열로 반환한다.

    Args:
        path: 읽을 파일 경로

    Returns:
        파일 내용 문자열

    Raises:
        FileTooLargeError: 파일이 50MB 초과인 경우
        FileNotFoundError: 파일이 존재하지 않는 경우
        UnicodeDecodeError: 인코딩 감지 및 디코딩 모두 실패한 경우
    """
    import os

    if not os.path.exists(path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    file_size = os.path.getsize(path)
    max_size = 50 * 1024 * 1024  # 50MB
    if file_size > max_size:
        raise FileTooLargeError(f"파일 크기({file_size // 1024 // 1024}MB)가 50MB를 초과합니다.")

    with open(path, "rb") as f:
        raw_data = f.read()

    detected = chardet.detect(raw_data)
    encoding = detected.get("encoding") or "utf-8"

    # 우선순위: 감지된 인코딩 → UTF-8 → EUC-KR → CP949 순으로 시도
    encodings_to_try = [encoding, "utf-8-sig", "utf-8", "euc-kr", "cp949"]
    seen = set()
    for enc in encodings_to_try:
        if enc and enc.lower() not in seen:
            seen.add(enc.lower())
            try:
                return raw_data.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue

    raise UnicodeDecodeError(
        "unknown", raw_data, 0, len(raw_data),
        "파일 인코딩을 인식할 수 없습니다."
    )


def detect_encoding(path: str) -> str:
    """
    파일의 인코딩을 감지하여 반환한다.

    Args:
        path: 검사할 파일 경로

    Returns:
        감지된 인코딩 문자열 (예: 'utf-8', 'euc-kr')
    """
    with open(path, "rb") as f:
        raw_data = f.read(10000)  # 처음 10KB만 샘플링
    detected = chardet.detect(raw_data)
    return detected.get("encoding") or "utf-8"
