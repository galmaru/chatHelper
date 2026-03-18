"""API Key 설정 다이얼로그"""

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from ui.widgets import get_font
from utils.config import load_config, save_config


class SettingsDialog(tk.Toplevel):
    """API Key 및 요약 제공자 설정 다이얼로그"""

    def __init__(self, parent: tk.Widget):
        super().__init__(parent)
        self.title("설정")
        self.resizable(False, False)
        self.grab_set()  # 모달
        self._build_ui()
        self._load_settings()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        # 부모 창 중앙에 위치
        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{px}+{py}")

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 제공자 탭
        provider_frame = ttk.Frame(notebook)
        notebook.add(provider_frame, text="요약 제공자")
        self._build_provider_tab(provider_frame)

        # OpenAI 탭
        openai_frame = ttk.Frame(notebook)
        notebook.add(openai_frame, text="OpenAI")
        self._build_api_tab(openai_frame, "openai")

        # Anthropic 탭
        anthropic_frame = ttk.Frame(notebook)
        notebook.add(anthropic_frame, text="Anthropic (Claude)")
        self._build_api_tab(anthropic_frame, "anthropic")

        # 하단 버튼
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Button(btn_frame, text="저장", command=self._save, font=get_font(10), width=8).pack(side=tk.RIGHT, padx=4)
        tk.Button(btn_frame, text="취소", command=self.destroy, font=get_font(10), width=8).pack(side=tk.RIGHT, padx=4)

    def _build_provider_tab(self, frame: ttk.Frame) -> None:
        tk.Label(frame, text="요약 제공자를 선택하세요:", font=get_font(10)).pack(anchor=tk.W, padx=15, pady=(15, 5))

        self._provider_var = tk.StringVar(value="offline")
        options = [
            ("오프라인 전용 (인터넷 불필요)", "offline"),
            ("OpenAI (gpt-4o-mini)", "openai"),
            ("Anthropic (claude-haiku)", "anthropic"),
        ]
        for label, value in options:
            ttk.Radiobutton(
                frame,
                text=label,
                variable=self._provider_var,
                value=value,
            ).pack(anchor=tk.W, padx=30, pady=3)

    def _build_api_tab(self, frame: ttk.Frame, provider: str) -> None:
        label_text = "OpenAI API Key:" if provider == "openai" else "Anthropic API Key:"
        tk.Label(frame, text=label_text, font=get_font(10)).pack(anchor=tk.W, padx=15, pady=(15, 3))

        entry_var = tk.StringVar()
        entry = tk.Entry(frame, textvariable=entry_var, show="*", width=45, font=get_font(10))
        entry.pack(anchor=tk.W, padx=15, pady=3)

        if provider == "openai":
            self._openai_key_var = entry_var
        else:
            self._anthropic_key_var = entry_var

        test_btn = tk.Button(
            frame,
            text="연결 테스트",
            font=get_font(10),
            command=lambda p=provider, v=entry_var: self._test_connection(p, v.get()),
        )
        test_btn.pack(anchor=tk.W, padx=15, pady=5)

        self._test_result_label = tk.Label(frame, text="", font=get_font(9))
        self._test_result_label.pack(anchor=tk.W, padx=15)

    def _load_settings(self) -> None:
        self._provider_var.set(load_config("provider") or "offline")
        self._openai_key_var.set(load_config("openai_api_key") or "")
        self._anthropic_key_var.set(load_config("anthropic_api_key") or "")

    def _save(self) -> None:
        save_config("provider", self._provider_var.get())
        openai_key = self._openai_key_var.get().strip()
        if openai_key:
            save_config("openai_api_key", openai_key)
        anthropic_key = self._anthropic_key_var.get().strip()
        if anthropic_key:
            save_config("anthropic_api_key", anthropic_key)
        messagebox.showinfo("저장 완료", "설정이 저장되었습니다.", parent=self)
        self.destroy()

    def _test_connection(self, provider: str, api_key: str) -> None:
        if not api_key.strip():
            messagebox.showwarning("입력 필요", "API Key를 입력해주세요.", parent=self)
            return

        def _run():
            try:
                if provider == "openai":
                    import openai
                    client = openai.OpenAI(api_key=api_key)
                    client.models.list()
                    result = "✅ OpenAI 연결 성공"
                else:
                    import anthropic
                    client = anthropic.Anthropic(api_key=api_key)
                    client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=5,
                        messages=[{"role": "user", "content": "hi"}],
                    )
                    result = "✅ Anthropic 연결 성공"
            except Exception as e:
                result = f"❌ 연결 실패: {str(e)[:60]}"
            self.after(0, lambda: self._test_result_label.config(text=result))

        threading.Thread(target=_run, daemon=True).start()
        self._test_result_label.config(text="연결 중...")
