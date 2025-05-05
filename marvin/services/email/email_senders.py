import smtplib
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email import message
from email.utils import formatdate
from uuid import uuid4

from html2text import html2text

from marvin.services import BaseService

SMTP_TIMEOUT = 10
"""Timeout in seconds for SMTP connection"""


@dataclass(slots=True)
class EmailOptions:
    host: str
    port: int
    username: str | None = None
    password: str | None = None
    tls: bool = False
    ssl: bool = False


@dataclass(slots=True)
class SMTPResponse:
    success: bool
    message: str
    errors: typing.Any


@dataclass(slots=True)
class Message:
    subject: str
    html: str
    mail_from_name: str
    mail_from_address: str

    def send(self, to: str, smtp: EmailOptions) -> SMTPResponse:
        msg = message.EmailMessage()
        msg["Subject"] = self.subject
        msg["From"] = f"{self.mail_from_name} <{self.mail_from_address}>"
        msg["To"] = to
        msg["Date"] = formatdate(localtime=True)
        msg.add_alternative(html2text(self.html), subtype="plain")
        msg.add_alternative(self.html, subtype="html")

        try:
            message_id = f"<{uuid4()}@{self.mail_from_address.split('@')[1]}>"
        except IndexError:
            # this should never happen with a valid email address,
            # but we let the SMTP server handle it instead of raising it here
            message_id = f"<{uuid4()}@{self.mail_from_address}>"

        msg["Message-ID"] = message_id
        msg["MIME-Version"] = "1.0"

        if smtp.ssl:
            with smtplib.SMTP_SSL(smtp.host, smtp.port, timeout=SMTP_TIMEOUT) as server:
                if smtp.username and smtp.password:
                    server.login(smtp.username, smtp.password)

                errors = server.send_message(msg)
        else:
            with smtplib.SMTP(smtp.host, smtp.port, timeout=SMTP_TIMEOUT) as server:
                if smtp.tls:
                    server.starttls()
                if smtp.username and smtp.password:
                    server.login(smtp.username, smtp.password)
                errors = server.send_message(msg)

        return SMTPResponse(errors == {}, "Message Sent", errors=errors)


class ABCEmailSender(ABC):
    @abstractmethod
    def send(self, email_to: str, subject: str, html: str) -> bool: ...


class DefaultEmailSender(ABCEmailSender, BaseService):
    """
    DefaultEmailSender is the default email sender for Marvin. It uses the SMTP _settings
    from the config file to send emails via the python standard library. It supports
    both TLS and SSL connections.
    """

    def send(self, email_to: str, subject: str, html: str) -> bool:
        if self._settings.SMTP_FROM_EMAIL is None or self._settings.SMTP_FROM_NAME is None:
            raise ValueError("SMTP_FROM_EMAIL and SMTP_FROM_NAME must be set in the config file.")

        message = Message(
            subject=subject,
            html=html,
            mail_from_name=self._settings.SMTP_FROM_NAME,
            mail_from_address=self._settings.SMTP_FROM_EMAIL,
        )

        if self._settings.SMTP_HOST is None or self._settings.SMTP_PORT is None:
            raise ValueError("SMTP_HOST, SMTP_PORT must be set in the config file.")

        smtp_options = EmailOptions(
            self._settings.SMTP_HOST,
            int(self._settings.SMTP_PORT),
            tls=self._settings.SMTP_AUTH_STRATEGY.upper() == "TLS" if self._settings.SMTP_AUTH_STRATEGY else False,
            ssl=self._settings.SMTP_AUTH_STRATEGY.upper() == "SSL" if self._settings.SMTP_AUTH_STRATEGY else False,
        )

        if self._settings.SMTP_USER:
            smtp_options.username = self._settings.SMTP_USER
        if self._settings.SMTP_PASSWORD:
            smtp_options.password = self._settings.SMTP_PASSWORD

        response = message.send(to=email_to, smtp=smtp_options)
        self.logger.debug(f"send email result: {response}")

        if not response.success:
            self.logger.error(f"send email error: {response}")

        return response.success
