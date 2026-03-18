"""채팅 요약기 앱 진입점"""

import logging
import os
import sys
import tkinter as tk

# 개발 환경에서 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import get_config_dir
from ui.main_window import MainWindow


def _setup_logging() -> None:
    """로그 파일을 설정한다. 스택 트레이스는 파일에만 기록한다."""
    log_dir = get_config_dir()
    log_path = os.path.join(log_dir, "app.log")
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )


def main() -> None:
    _setup_logging()

    root = tk.Tk()
    root.title("채팅 요약기")

    # DPI 스케일링 (Windows 고DPI 환경)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
