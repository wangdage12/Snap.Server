import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr
from urllib import error, request

from app.config_loader import config_loader

RESEND_API_URL = "https://api.resend.com/emails"
SUPPORTED_EMAIL_PROVIDERS = {"gmail", "resend"}


def _build_user_agent(app_name: str | None = None) -> str:
    product_name = (app_name or config_loader.EMAIL_APP_NAME or "Snap.Server").strip()
    product_name = product_name.replace(" ", "-") or "Snap.Server"
    return f"{product_name}/1.0 (Python urllib)"


def _normalize_sender_address(address: str) -> str:
    candidate = (address or "").strip()
    if not candidate:
        return candidate

    if "@" in candidate or "<" in candidate or ">" in candidate:
        return candidate

    if " " not in candidate and "." in candidate:
        return f"no-reply@{candidate}"

    return candidate


def _parse_email_address(address: str) -> tuple[str | None, str | None]:
    normalized_address = _normalize_sender_address(address)
    display_name, email_address = parseaddr(normalized_address)
    email_address = email_address.strip()
    display_name = display_name.strip()
    if not email_address:
        return None, None
    return display_name or None, email_address


def _format_from_header(
    from_email: str,
    app_name: str | None = None,
    ascii_only_name: bool = False,
) -> str:
    existing_name, email_address = _parse_email_address(from_email)
    if not email_address:
        raise ValueError(
            "邮件发件人格式无效，请将 EMAIL.FROM_EMAIL 配置为 email@example.com 或 Name <email@example.com>"
        )

    display_name = (app_name or existing_name or "").strip()
    if ascii_only_name and display_name and not display_name.isascii():
        display_name = ""

    if display_name:
        return formataddr((display_name, email_address))
    return email_address


def _build_smtp_message(
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    body_type: str = "plain",
    app_name: str | None = None,
    text_body: str | None = None,
) -> MIMEMultipart:
    msg = MIMEMultipart("alternative") if body_type == "html" and text_body else MIMEMultipart()
    msg["From"] = _format_from_header(from_email, app_name)
    msg["To"] = to_email
    msg["Subject"] = subject

    if body_type == "html" and text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(body, "html", "utf-8"))
    else:
        msg.attach(MIMEText(body, body_type, "utf-8"))

    return msg


def _send_via_gmail_smtp(
    gmail_user: str,
    app_password: str,
    to_email: str,
    subject: str,
    body: str,
    app_name: str | None = None,
    body_type: str = "plain",
    text_body: str | None = None,
) -> None:
    if not gmail_user or not app_password:
        raise ValueError("Gmail SMTP 邮件配置不完整，请检查 EMAIL.GMAIL_USER 和 EMAIL.APP_PASSWORD")

    msg = _build_smtp_message(
        gmail_user,
        to_email,
        subject,
        body,
        body_type=body_type,
        app_name=app_name,
        text_body=text_body,
    )

    server = smtplib.SMTP("smtp.gmail.com", 587)
    try:
        server.starttls()
        server.login(gmail_user, app_password)
        server.sendmail(gmail_user, to_email, msg.as_string())
    finally:
        server.quit()


def _send_via_resend(
    api_key: str,
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    app_name: str | None = None,
    body_type: str = "plain",
    text_body: str | None = None,
    reply_to: str | None = None,
) -> dict:
    if not api_key or not from_email:
        raise ValueError("Resend 邮件配置不完整，请检查 EMAIL.RESEND_API_KEY 和 EMAIL.FROM_EMAIL")

    payload = {
        "from": _format_from_header(from_email, app_name, ascii_only_name=True),
        "to": [to_email],
        "subject": subject,
    }

    if body_type == "html":
        payload["html"] = body
        if text_body:
            payload["text"] = text_body
    else:
        payload["text"] = body

    if reply_to:
        payload["reply_to"] = reply_to

    req = request.Request(
        RESEND_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": _build_user_agent(app_name),
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=15) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body) if response_body else {}
    except error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Resend API 请求失败: HTTP {exc.code}, {error_body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Resend API 网络请求失败: {exc.reason}") from exc


def send_email(
    to_email: str,
    subject: str,
    body: str = "这是一封测试邮件。",
    app_name: str | None = None,
    body_type: str = "plain",
    text_body: str | None = None,
    reply_to: str | None = None,
):
    provider = (config_loader.EMAIL_PROVIDER or "gmail").strip().lower()

    if provider not in SUPPORTED_EMAIL_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_EMAIL_PROVIDERS))
        raise ValueError(f"不支持的邮件服务提供商: {provider}，支持的值为: {supported}")

    if provider == "resend":
        return _send_via_resend(
            config_loader.EMAIL_RESEND_API_KEY,
            config_loader.EMAIL_FROM_EMAIL,
            to_email,
            subject,
            body,
            app_name=app_name,
            body_type=body_type,
            text_body=text_body,
            reply_to=reply_to or config_loader.EMAIL_REPLY_TO,
        )

    return _send_via_gmail_smtp(
        config_loader.EMAIL_GMAIL_USER,
        config_loader.EMAIL_APP_PASSWORD,
        to_email,
        subject,
        body,
        app_name=app_name,
        body_type=body_type,
        text_body=text_body,
    )


if __name__ == "__main__":
    target_email = ""
    try:
        send_email(target_email, "测试邮件主题", "这是一封测试邮件。")
        print("邮件发送成功！")
    except Exception as e:
        print("发送失败：", e)
