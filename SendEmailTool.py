import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config_loader import config_loader

# 从配置文件获取邮件设置
gmail_user = config_loader.EMAIL_GMAIL_USER
app_password = config_loader.EMAIL_APP_PASSWORD

to_email = ""

def send_email(gmail_user, app_password, to_email, subject, body="这是一封测试邮件。", app_name=None, body_type="plain"):
    msg = MIMEMultipart()
    # 如果提供了 app_name，使用带显示名称的格式
    if app_name:
        msg["From"] = f"{app_name} <{gmail_user}>"
    else:
        msg["From"] = gmail_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, body_type))

    # Gmail SMTP 服务器
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(gmail_user, app_password)
    server.sendmail(gmail_user, to_email, msg.as_string())
    server.quit()

if __name__ == "__main__":
    try:
        send_email(gmail_user, app_password, to_email, "测试邮件主题", "这是一封测试邮件。")
        print("邮件发送成功！")

    except Exception as e:
        print("发送失败：", e)
