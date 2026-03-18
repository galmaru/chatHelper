"""설정 저장/불러오기 모듈 (API Key 포함)"""

import base64
import json
import os
import sys


def _get_config_dir() -> str:
    """설정 파일 저장 디렉토리를 반환한다."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        config_dir = os.path.join(appdata, "ChatSummarizer")
    else:
        # macOS / Linux 개발 환경
        config_dir = os.path.join(os.path.expanduser("~"), ".ChatSummarizer")

    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def _get_config_path() -> str:
    return os.path.join(_get_config_dir(), "config.json")


def _load_all() -> dict:
    path = _get_config_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_all(data: dict) -> None:
    path = _get_config_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_config(key: str, value: str) -> None:
    """
    설정 값을 저장한다. API Key는 base64 인코딩으로 난독화한다.

    Args:
        key: 설정 키
        value: 저장할 값
    """
    data = _load_all()
    if key.endswith("_api_key"):
        value = base64.b64encode(value.encode("utf-8")).decode("ascii")
    data[key] = value
    _save_all(data)


def load_config(key: str) -> str:
    """
    설정 값을 불러온다. API Key는 자동으로 디코딩한다.

    Args:
        key: 설정 키

    Returns:
        설정 값 문자열, 없으면 빈 문자열
    """
    data = _load_all()
    value = data.get(key, "")
    if not value:
        return ""
    if key.endswith("_api_key"):
        try:
            value = base64.b64decode(value.encode("ascii")).decode("utf-8")
        except Exception:
            pass
    return value


def get_config_dir() -> str:
    """설정 디렉토리 경로를 반환한다 (로그 파일 경로 등에서 사용)."""
    return _get_config_dir()
