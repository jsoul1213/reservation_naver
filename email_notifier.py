"""SMTP email delivery. This module has no dependency on the GUI."""

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage


class EmailNotifier:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        sender: str,
        recipient: str,
        use_tls: bool = True,
        timeout: float = 12.0,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.sender = sender or username
        self.recipient = recipient
        self.use_tls = use_tls
        self.timeout = timeout

    def send_availability(self, reservation_url: str) -> None:
        message = EmailMessage()
        message["Subject"] = "[취소표 감지] 네이버 예약 가능 상태 발생"
        message["From"] = self.sender
        message["To"] = self.recipient
        message.set_content(
            "네이버 예약 페이지에서 예약 가능한 상태가 감지되었습니다.\n\n"
            "즉시 예약 페이지를 확인하세요.\n\n"
            f"예약 페이지:\n{reservation_url}\n"
        )

        context = ssl.create_default_context()
        with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
            server.ehlo()
            if self.use_tls:
                server.starttls(context=context)
                server.ehlo()
            if self.username:
                server.login(self.username, self.password)
            server.send_message(message)
