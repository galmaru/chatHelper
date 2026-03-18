"""인터넷 연결 상태 감지 모듈"""

import socket


def check_internet(timeout: float = 3.0) -> bool:
    """
    인터넷 연결 여부를 확인한다.

    Google DNS(8.8.8.8:53)에 소켓 연결을 시도하여 빠르게 감지한다.

    Args:
        timeout: 연결 시도 제한 시간 (초)

    Returns:
        인터넷 연결 가능 시 True, 아니면 False
    """
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(("8.8.8.8", 53))
        return True
    except OSError:
        return False
