"""요약 엔진 통합 인터페이스"""

from core.offline_summary import summarize_offline
from core.online_summary import summarize_online
from utils.network import check_internet
from utils.config import load_config


def summarize(
    text: str,
    length: str = "medium",
    force_offline: bool = False,
    include_senders: set[str] | None = None,
) -> dict:
    """
    상황에 따라 오프라인 또는 온라인 요약을 수행한다.

    Args:
        text: 요약할 텍스트 (원본 그대로)
        length: "short" / "medium" / "long"
        force_offline: True면 인터넷 연결과 무관하게 오프라인 요약 수행
        include_senders: 요약에 포함할 화자 집합 (None이면 전체)

    Returns:
        요약 결과 딕셔너리
    """
    if force_offline:
        return summarize_offline(text, length, include_senders=include_senders)

    provider = load_config("provider") or "offline"
    api_key = load_config(f"{provider}_api_key") or ""

    if provider == "offline" or not api_key:
        return summarize_offline(text, length, include_senders=include_senders)

    if not check_internet():
        result = summarize_offline(text, length, include_senders=include_senders)
        result["mode"] = "offline(no_internet)"
        return result

    return summarize_online(text, provider, api_key, length)
