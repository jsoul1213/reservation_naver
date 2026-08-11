"""Tkinter desktop interface for macOS (and development platforms)."""

from __future__ import annotations

import logging
import os
import queue
import tkinter as tk
from dataclasses import replace
from datetime import datetime
from tkinter import messagebox, ttk

from config import AppConfig, load_config, save_config
from monitor import MonitorEvent, MonitorService
from reservation_checker import ReservationState


class ReservationMonitorGUI:
    def __init__(
        self,
        root: tk.Tk,
        logger: logging.Logger,
        log_queue: queue.Queue[str],
    ) -> None:
        self.root = root
        self.logger = logger
        self.log_queue = log_queue
        self.event_queue: queue.Queue[MonitorEvent] = queue.Queue()
        self.service: MonitorService | None = None
        self.saved_config = load_config()

        self.root.title("Reservation Monitor")
        self.root.geometry("780x780")
        self.root.minsize(720, 680)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.url_var = tk.StringVar(value=self.saved_config.reservation_url)
        self.interval_var = tk.StringVar(value=str(self.saved_config.check_interval))
        self.macos_var = tk.BooleanVar(value=self.saved_config.macos_notification_enabled)
        self.sound_var = tk.BooleanVar(value=self.saved_config.sound_enabled)
        self.email_enabled_var = tk.BooleanVar(value=self.saved_config.email_enabled)
        self.recipient_var = tk.StringVar(value=self.saved_config.email_recipient)
        self.smtp_host_var = tk.StringVar(value=self.saved_config.smtp_host)
        self.smtp_port_var = tk.StringVar(value=str(self.saved_config.smtp_port))
        self.smtp_username_var = tk.StringVar(value=self.saved_config.smtp_username)
        self.smtp_sender_var = tk.StringVar(value=self.saved_config.smtp_sender)
        self.smtp_password_var = tk.StringVar(
            value=os.environ.get("RESERVATION_MONITOR_SMTP_PASSWORD", "")
        )
        self.available_selector_var = tk.StringVar(value=self.saved_config.available_selector)
        self.sold_out_selector_var = tk.StringVar(value=self.saved_config.sold_out_selector)

        self.run_status_var = tk.StringVar(value="● 중지됨")
        self.current_state_var = tk.StringVar(value=ReservationState.UNKNOWN.value)
        self.last_checked_var = tk.StringVar(value="-")
        self.last_detection_var = tk.StringVar(value="-")
        self.error_var = tk.StringVar(value="-")

        self._build()
        self.root.after(100, self._drain_queues)

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)

        title = ttk.Label(outer, text="네이버 예약 취소표 모니터", font=("TkDefaultFont", 18, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 16))

        ttk.Label(outer, text="예약 URL").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(outer, textvariable=self.url_var).grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=(12, 0), pady=5
        )
        ttk.Label(outer, text="확인 주기").grid(row=2, column=0, sticky="w", pady=5)
        interval = ttk.Frame(outer)
        interval.grid(row=2, column=1, columnspan=2, sticky="w", padx=(12, 0), pady=5)
        ttk.Entry(interval, textvariable=self.interval_var, width=8).pack(side="left")
        ttk.Label(interval, text="초 (최소 2초)").pack(side="left", padx=8)

        button_bar = ttk.Frame(outer)
        button_bar.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(14, 14))
        self.start_button = ttk.Button(button_bar, text="모니터링 시작", command=self._start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(button_bar, text="중지", command=self._stop, state="disabled")
        self.stop_button.pack(side="left", padx=8)

        status = ttk.LabelFrame(outer, text="상태", padding=12)
        status.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        status.columnconfigure(1, weight=1)
        status_items = [
            ("실행 상태", self.run_status_var),
            ("현재 상태", self.current_state_var),
            ("마지막 확인", self.last_checked_var),
            ("마지막 감지", self.last_detection_var),
            ("오류", self.error_var),
        ]
        for row, (label, variable) in enumerate(status_items):
            ttk.Label(status, text=label).grid(row=row, column=0, sticky="nw", pady=2)
            ttk.Label(status, textvariable=variable, wraplength=560).grid(
                row=row, column=1, sticky="w", padx=(14, 0), pady=2
            )

        notification = ttk.LabelFrame(outer, text="알림", padding=12)
        notification.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        ttk.Checkbutton(notification, text="macOS 알림", variable=self.macos_var).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(notification, text="사운드", variable=self.sound_var).grid(row=0, column=1, sticky="w", padx=14)
        ttk.Checkbutton(notification, text="이메일", variable=self.email_enabled_var).grid(row=0, column=2, sticky="w")
        ttk.Label(notification, text="수신 주소").grid(row=1, column=0, sticky="w", pady=(10, 3))
        ttk.Entry(notification, textvariable=self.recipient_var, width=44).grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=(10, 3)
        )
        notification.columnconfigure(2, weight=1)

        advanced = ttk.LabelFrame(outer, text="고급 설정 (SMTP / DOM 선택자)", padding=12)
        advanced.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(0, 12))
        advanced.columnconfigure(1, weight=1)
        fields = [
            ("SMTP 서버", self.smtp_host_var, False),
            ("SMTP 포트", self.smtp_port_var, False),
            ("SMTP 사용자", self.smtp_username_var, False),
            ("보내는 주소", self.smtp_sender_var, False),
            ("SMTP 앱 비밀번호", self.smtp_password_var, True),
            ("예약 가능 CSS", self.available_selector_var, False),
            ("매진 CSS", self.sold_out_selector_var, False),
        ]
        for row, (label, variable, secret) in enumerate(fields):
            ttk.Label(advanced, text=label).grid(row=row, column=0, sticky="w", pady=2)
            ttk.Entry(advanced, textvariable=variable, show="•" if secret else "").grid(
                row=row, column=1, sticky="ew", padx=(12, 0), pady=2
            )
        ttk.Label(
            advanced,
            text="앱 비밀번호는 설정 파일에 저장하지 않습니다. 선택자는 실제 페이지 확인 후 필요할 때만 입력하세요.",
            wraplength=610,
        ).grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(7, 0))

        log_frame = ttk.LabelFrame(outer, text="로그", padding=8)
        log_frame.grid(row=7, column=0, columnspan=3, sticky="nsew")
        outer.rowconfigure(7, weight=1)
        self.log_text = tk.Text(log_frame, height=9, state="disabled", wrap="word")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _config_from_form(self) -> AppConfig:
        try:
            interval = float(self.interval_var.get().strip())
            smtp_port = int(self.smtp_port_var.get().strip())
        except ValueError as exc:
            raise ValueError("확인 주기와 SMTP 포트에는 숫자를 입력하세요.") from exc
        return replace(
            self.saved_config,
            reservation_url=self.url_var.get().strip(),
            check_interval=interval,
            macos_notification_enabled=self.macos_var.get(),
            sound_enabled=self.sound_var.get(),
            email_enabled=self.email_enabled_var.get(),
            email_recipient=self.recipient_var.get().strip(),
            smtp_host=self.smtp_host_var.get().strip(),
            smtp_port=smtp_port,
            smtp_username=self.smtp_username_var.get().strip(),
            smtp_sender=self.smtp_sender_var.get().strip(),
            available_selector=self.available_selector_var.get().strip(),
            sold_out_selector=self.sold_out_selector_var.get().strip(),
        )

    def _start(self) -> None:
        if self.service and self.service.is_running:
            return
        try:
            config = self._config_from_form()
        except ValueError as exc:
            messagebox.showerror("입력 오류", str(exc))
            return
        errors = config.validate()
        if errors:
            messagebox.showerror("설정 오류", "\n".join(f"• {error}" for error in errors))
            return
        if (
            config.email_enabled
            and not self.smtp_password_var.get()
            and not os.environ.get("RESERVATION_MONITOR_SMTP_PASSWORD")
        ):
            messagebox.showerror(
                "설정 오류",
                "이메일 알림을 사용하려면 SMTP 앱 비밀번호를 입력하세요. 비밀번호는 저장되지 않습니다.",
            )
            return
        self.saved_config = config
        try:
            save_config(config)
        except OSError as exc:
            messagebox.showerror("설정 저장 실패", str(exc))
            return
        self.error_var.set("-")
        self.service = MonitorService(
            config=config,
            smtp_password=self.smtp_password_var.get(),
            logger=self.logger,
            callback=self.event_queue.put,
        )
        self.service.start()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

    def _stop(self) -> None:
        if self.service:
            self.service.stop()
        self.stop_button.configure(state="disabled")
        self.run_status_var.set("● 중지 중...")

    def _handle_event(self, event: MonitorEvent) -> None:
        if event.kind == "started":
            self.run_status_var.set("● 모니터링 중")
        elif event.kind == "stopped":
            self.run_status_var.set("● 중지됨")
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
        elif event.kind == "state" and event.state is not None:
            self.current_state_var.set(event.state.value)
            if event.checked_at:
                self.last_checked_var.set(event.checked_at.strftime("%Y-%m-%d %H:%M:%S"))
            if event.message:
                stamp = (event.checked_at or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
                self.last_detection_var.set(f"{stamp} · {event.state.value}")
            self.error_var.set("-")
        elif event.kind == "error":
            self.current_state_var.set(ReservationState.UNKNOWN.value)
            if event.checked_at:
                self.last_checked_var.set(event.checked_at.strftime("%Y-%m-%d %H:%M:%S"))
            self.error_var.set(event.message or "알 수 없는 오류")
        elif event.kind == "login":
            self.current_state_var.set(ReservationState.UNKNOWN.value)
            self.run_status_var.set("● 로그인 대기 중")
            self.error_var.set(event.message)

    def _drain_queues(self) -> None:
        try:
            while True:
                self._handle_event(self.event_queue.get_nowait())
        except queue.Empty:
            pass
        try:
            while True:
                line = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", line + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._drain_queues)

    def _on_close(self) -> None:
        if self.service:
            self.service.stop()
        self.root.destroy()
