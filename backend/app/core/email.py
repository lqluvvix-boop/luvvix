"""Отправка писем (адаптер). Если SMTP не настроен — код печатается в лог сервера."""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings

log = logging.getLogger("luvvix.email")


def send_email(to: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST:
        log.warning("[DEV EMAIL] to=%s | %s | %s", to, subject, body)
        print(f"\n===== [DEV EMAIL] to: {to}\n{subject}\n{body}\n=====\n", flush=True)
        return

    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        if settings.SMTP_SSL:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT,
                                  context=ssl.create_default_context(), timeout=15) as s:
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                s.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                s.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        log.exception("Не удалось отправить письмо: %s", exc)
        raise RuntimeError("Почтовый сервер недоступен") from exc


def send_code(to: str, code: str, purpose: str) -> None:
    what = "входа" if purpose == "login" else "подтверждения регистрации"
    send_email(
        to,
        f"Luvvix: код {what}",
        f"Ваш код {what}: {code}\nКод действует {settings.TWO_FA_CODE_TTL_MINUTES} мин.\n"
        "Если вы не запрашивали код — просто проигнорируйте письмо.",
    )
