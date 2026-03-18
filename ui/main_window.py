"""메인 윈도우 레이아웃 모듈"""

import logging
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core.file_loader import FileTooLargeError, load_file
from core.parser import parse_chat, get_participants
from core.summarizer import summarize
from ui.widgets import ScrolledText, StatusBar, get_font
from utils.config import load_config, save_config, get_config_dir


logger = logging.getLogger(__name__)

RECENT_FILES_MAX = 5


class MainWindow(tk.Frame):
    """채팅 요약 앱 메인 윈도우 프레임"""

    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master
        self._current_text: str = ""
        self._current_messages: list[dict] = []
        self._summary_font_size: int = 10
        self._recent_files: list[str] = self._load_recent_files()
        self._build_ui()
        self._restore_window_size()
        self._update_mode_display()

    # ──────────────────────────────────────────
    # UI 구성
    # ──────────────────────────────────────────

    def _build_ui(self) -> None:
        self.master.title("채팅 요약기")
        self.master.geometry("900x600")
        self.master.minsize(700, 450)
        self.pack(fill=tk.BOTH, expand=True)

        self._build_menu()
        self._build_toolbar()
        self._build_panels()
        self._build_status_bar()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        # 파일 메뉴
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="파일", menu=file_menu)
        file_menu.add_command(label="열기", accelerator="Ctrl+O", command=self._open_file)
        self._recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="최근 파일", menu=self._recent_menu)
        self._rebuild_recent_menu()
        file_menu.add_separator()
        file_menu.add_command(label="저장", accelerator="Ctrl+S", command=self._save_result)
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self._on_close)

        # 설정 메뉴
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="설정", menu=settings_menu)
        settings_menu.add_command(label="API 설정...", command=self._open_settings)

        # 단축키
        self.master.bind("<Control-o>", lambda e: self._open_file())
        self.master.bind("<Control-s>", lambda e: self._save_result())
        self.master.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_toolbar(self) -> None:
        toolbar = tk.Frame(self, bd=1, relief=tk.RAISED)
        toolbar.pack(fill=tk.X, side=tk.TOP)

        tk.Button(
            toolbar, text="파일 열기", font=get_font(10), command=self._open_file
        ).pack(side=tk.LEFT, padx=4, pady=3)

        self._file_path_var = tk.StringVar(value="파일을 선택하세요")
        tk.Label(
            toolbar,
            textvariable=self._file_path_var,
            font=get_font(9),
            fg="gray",
            anchor=tk.W,
        ).pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)

        tk.Button(
            toolbar, text="⚙ 설정", font=get_font(10), command=self._open_settings
        ).pack(side=tk.RIGHT, padx=4, pady=3)

    def _build_panels(self) -> None:
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # ── 좌측: 원문 미리보기 ──
        left_frame = tk.LabelFrame(paned, text="원문 미리보기", font=get_font(9))
        paned.add(left_frame, weight=1)
        self._preview_text = ScrolledText(left_frame, readonly=True, font_size=10, bg="#fafafa")
        self._preview_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ── 우측: 요약 결과 ──
        right_frame = tk.LabelFrame(paned, text="요약 결과", font=get_font(9))
        paned.add(right_frame, weight=1)
        self._build_right_panel(right_frame)

    def _build_right_panel(self, parent: tk.Widget) -> None:
        # 요약 옵션 행
        option_frame = tk.Frame(parent)
        option_frame.pack(fill=tk.X, padx=6, pady=(6, 2))

        tk.Label(option_frame, text="요약 길이:", font=get_font(10)).pack(side=tk.LEFT)
        self._length_var = tk.StringVar(value="medium")
        for label, val in [("짧게", "short"), ("보통", "medium"), ("자세히", "long")]:
            ttk.Radiobutton(
                option_frame, text=label, variable=self._length_var, value=val
            ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            option_frame,
            text="요약 시작",
            font=get_font(10, bold=True),
            command=self._start_summary,
        ).pack(side=tk.RIGHT, padx=4)

        # 필터 행 (참여자)
        self._filter_frame = tk.Frame(parent)
        self._filter_frame.pack(fill=tk.X, padx=6)
        self._participant_vars: dict[str, tk.BooleanVar] = {}

        # 프로그레스 바
        self._progress = ttk.Progressbar(parent, mode="indeterminate")
        self._progress.pack(fill=tk.X, padx=6, pady=2)

        # 요약 결과 텍스트
        self._result_text = ScrolledText(parent, readonly=True, font_size=self._summary_font_size, bg="#fff")
        self._result_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 2))

        # 하단 버튼 행
        bottom_frame = tk.Frame(parent)
        bottom_frame.pack(fill=tk.X, padx=6, pady=(0, 6))

        tk.Button(bottom_frame, text="복사", font=get_font(9), command=self._copy_result).pack(side=tk.LEFT, padx=2)
        tk.Button(bottom_frame, text="저장", font=get_font(9), command=self._save_result).pack(side=tk.LEFT, padx=2)
        tk.Button(bottom_frame, text="A+", font=get_font(9), command=lambda: self._change_font(1)).pack(side=tk.RIGHT)
        tk.Button(bottom_frame, text="A-", font=get_font(9), command=lambda: self._change_font(-1)).pack(side=tk.RIGHT, padx=2)

    def _build_status_bar(self) -> None:
        self._status_bar = StatusBar(self)
        self._status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # ──────────────────────────────────────────
    # 파일 열기
    # ──────────────────────────────────────────

    def _open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="채팅 파일 열기",
            filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")],
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str) -> None:
        def _run():
            try:
                text = load_file(path)
                messages = parse_chat(text)
                participants = get_participants(messages)
                self.after(0, lambda: self._on_file_loaded(path, text, messages, participants))
            except FileTooLargeError as e:
                self.after(0, lambda: messagebox.showerror("파일 오류", str(e)))
            except FileNotFoundError:
                self.after(0, lambda: messagebox.showerror("파일 오류", "파일을 찾을 수 없습니다. 파일이 이동되었거나 삭제되었을 수 있습니다."))
            except UnicodeDecodeError:
                self.after(0, lambda: messagebox.showerror("인코딩 오류", "파일 인코딩을 인식할 수 없습니다. 인코딩을 직접 선택해 주세요."))
            except Exception as e:
                logger.exception("파일 로드 오류")
                self.after(0, lambda: messagebox.showerror("오류", f"파일을 불러오는 중 오류가 발생했습니다:\n{e}"))

        threading.Thread(target=_run, daemon=True).start()

    def _on_file_loaded(self, path: str, text: str, messages: list, participants: list) -> None:
        self._current_text = text
        self._current_messages = messages
        self._file_path_var.set(os.path.basename(path))

        self._preview_text.set_text(text)

        lines = text.count("\n") + 1
        enc = "자동 감지"
        self._status_bar.set_text(
            f"파일: {os.path.basename(path)} | {lines}줄 | 인코딩: {enc} | 참여자 {len(participants)}명"
        )

        self._build_participant_filters(participants)
        self._add_recent_file(path)

        # 자동 요약 시작
        self._start_summary()

    def _build_participant_filters(self, participants: list[str]) -> None:
        for widget in self._filter_frame.winfo_children():
            widget.destroy()
        self._participant_vars.clear()

        if not participants:
            return

        tk.Label(self._filter_frame, text="참여자 필터:", font=get_font(9)).pack(side=tk.LEFT)
        for name in participants:
            var = tk.BooleanVar(value=True)
            self._participant_vars[name] = var
            ttk.Checkbutton(
                self._filter_frame, text=name, variable=var
            ).pack(side=tk.LEFT, padx=2)

    # ──────────────────────────────────────────
    # 요약
    # ──────────────────────────────────────────

    def _start_summary(self) -> None:
        if not self._current_text:
            messagebox.showwarning("파일 없음", "먼저 파일을 열어주세요.")
            return

        # 참여자 필터 적용
        filtered_messages = self._current_messages
        if self._participant_vars:
            active = {name for name, var in self._participant_vars.items() if var.get()}
            filtered_messages = [m for m in self._current_messages if m.get("sender") in active]

        text = "\n".join(m.get("message", "") for m in filtered_messages) if filtered_messages else self._current_text

        self._progress.start(10)
        self._result_text.set_text("요약 중...")

        def _run():
            try:
                result = summarize(text, length=self._length_var.get())
                self.after(0, lambda: self._on_summary_done(result))
            except Exception as e:
                logger.exception("요약 오류")
                self.after(0, lambda: self._on_summary_error(str(e)))

        threading.Thread(target=_run, daemon=True).start()

    def _on_summary_done(self, result: dict) -> None:
        self._progress.stop()
        self._last_result = result

        mode = result.get("mode", "offline")
        keywords = ", ".join(result.get("keywords", []))
        participants = ", ".join(result.get("participants", []))
        action_items = result.get("action_items", [])

        output = []
        output.append(f"[요약 모드: {mode}]")
        output.append("")
        output.append("■ 핵심 요약")
        output.append(result.get("summary", ""))
        output.append("")
        output.append(f"■ 키워드: {keywords}")
        output.append(f"■ 참여자: {participants}")
        if action_items:
            output.append("")
            output.append("■ Action Items")
            for item in action_items:
                output.append(f"  • {item}")

        self._result_text.set_text("\n".join(output))
        self._status_bar.set_mode(mode)

    def _on_summary_error(self, error_msg: str) -> None:
        self._progress.stop()
        messagebox.showerror("요약 실패", f"AI 요약에 실패했습니다. 오프라인 모드로 전환합니다.\n{error_msg}")

    # ──────────────────────────────────────────
    # 저장 / 복사
    # ──────────────────────────────────────────

    def _copy_result(self) -> None:
        text = self._result_text.get_text().strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self._status_bar.set_text("클립보드에 복사되었습니다.")

    def _save_result(self) -> None:
        result = getattr(self, "_last_result", None)
        if not result:
            messagebox.showwarning("저장 불가", "먼저 요약을 실행해주세요.")
            return

        path = filedialog.asksaveasfilename(
            title="요약 저장",
            defaultextension=".md",
            filetypes=[("마크다운", "*.md"), ("텍스트", "*.txt"), ("모든 파일", "*.*")],
        )
        if not path:
            return

        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        mode = result.get("mode", "offline")
        summary = result.get("summary", "")
        keywords = result.get("keywords", [])
        action_items = result.get("action_items", [])
        file_name = self._file_path_var.get()

        if path.endswith(".md"):
            content = f"# 채팅 요약\n"
            content += f"**파일**: {file_name}\n"
            content += f"**요약 일시**: {now}\n"
            content += f"**요약 모드**: {mode}\n\n"
            content += f"## 핵심 요약\n{summary}\n\n"
            if keywords:
                content += f"## 키워드\n{', '.join(keywords)}\n\n"
            if action_items:
                content += "## Action Items\n"
                for item in action_items:
                    content += f"- {item}\n"
        else:
            content = self._result_text.get_text()

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self._status_bar.set_text(f"저장 완료: {os.path.basename(path)}")
        except OSError as e:
            messagebox.showerror("저장 실패", str(e))

    # ──────────────────────────────────────────
    # 기타 기능
    # ──────────────────────────────────────────

    def _change_font(self, delta: int) -> None:
        self._summary_font_size = max(8, min(20, self._summary_font_size + delta))
        self._result_text.set_font_size(self._summary_font_size)

    def _open_settings(self) -> None:
        from ui.settings_dialog import SettingsDialog
        SettingsDialog(self.master)
        self.after(300, self._update_mode_display)

    def _update_mode_display(self) -> None:
        provider = load_config("provider") or "offline"
        self._status_bar.set_mode(provider)

    def _on_close(self) -> None:
        self._save_window_size()
        self.master.destroy()

    def _save_window_size(self) -> None:
        geometry = self.master.geometry()
        save_config("window_geometry", geometry)

    def _restore_window_size(self) -> None:
        geometry = load_config("window_geometry")
        if geometry:
            try:
                self.master.geometry(geometry)
            except Exception:
                pass

    def _load_recent_files(self) -> list[str]:
        import json
        raw = load_config("recent_files")
        if not raw:
            return []
        try:
            return json.loads(raw)
        except Exception:
            return []

    def _add_recent_file(self, path: str) -> None:
        import json
        if path in self._recent_files:
            self._recent_files.remove(path)
        self._recent_files.insert(0, path)
        self._recent_files = self._recent_files[:RECENT_FILES_MAX]
        save_config("recent_files", json.dumps(self._recent_files))
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.delete(0, tk.END)
        for path in self._recent_files:
            self._recent_menu.add_command(
                label=os.path.basename(path),
                command=lambda p=path: self._load_file(p),
            )
        if not self._recent_files:
            self._recent_menu.add_command(label="(없음)", state=tk.DISABLED)
