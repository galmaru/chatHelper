"""공용 커스텀 위젯 모듈"""

import tkinter as tk
from tkinter import ttk


FONT_FAMILY = "맑은 고딕"
FONT_FALLBACK = "sans-serif"


def get_font(size: int = 10, bold: bool = False) -> tuple:
    """플랫폼에 맞는 폰트 튜플을 반환한다."""
    import tkinter.font as tkfont
    try:
        families = tkfont.families()
        family = FONT_FAMILY if FONT_FAMILY in families else FONT_FALLBACK
    except Exception:
        family = FONT_FALLBACK
    weight = "bold" if bold else "normal"
    return (family, size, weight)


class StatusBar(tk.Frame):
    """하단 상태 바 위젯"""

    def __init__(self, master: tk.Widget, **kwargs):
        super().__init__(master, bd=1, relief=tk.SUNKEN, **kwargs)
        self._label = tk.Label(
            self,
            text="파일을 열어주세요.",
            anchor=tk.W,
            font=get_font(9),
            padx=5,
        )
        self._label.pack(fill=tk.X, side=tk.LEFT, expand=True)

        self._mode_label = tk.Label(
            self,
            text="● 오프라인 모드",
            anchor=tk.E,
            font=get_font(9),
            fg="gray",
            padx=8,
        )
        self._mode_label.pack(side=tk.RIGHT)

    def set_text(self, text: str) -> None:
        self._label.config(text=text)

    def set_mode(self, mode: str) -> None:
        """연결 모드 표시를 업데이트한다."""
        if "openai" in mode.lower():
            self._mode_label.config(text="● AI 모드 (OpenAI)", fg="#2a7d2a")
        elif "anthropic" in mode.lower() or "claude" in mode.lower():
            self._mode_label.config(text="● AI 모드 (Claude)", fg="#6b3fa0")
        else:
            self._mode_label.config(text="● 오프라인 모드", fg="gray")


class ScrolledText(tk.Frame):
    """스크롤바가 있는 텍스트 위젯"""

    def __init__(self, master: tk.Widget, readonly: bool = False, **kwargs):
        super().__init__(master)
        font_size = kwargs.pop("font_size", 10)

        self.text = tk.Text(
            self,
            wrap=tk.WORD,
            font=get_font(font_size),
            **kwargs,
        )
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)

        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if readonly:
            self.text.config(state=tk.DISABLED)
        self._readonly = readonly

    def set_text(self, content: str) -> None:
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        if self._readonly:
            self.text.config(state=tk.DISABLED)

    def get_text(self) -> str:
        return self.text.get("1.0", tk.END)

    def set_font_size(self, size: int) -> None:
        self.text.config(font=get_font(size))
