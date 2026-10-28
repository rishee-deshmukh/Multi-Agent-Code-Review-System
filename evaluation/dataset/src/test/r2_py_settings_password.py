import smtplib
from email.message import EmailMessage

SETTINGS = {
    "host": "mail.example.com",
    "port": 587,
    "username": "notifier@example.com",
    "password": "Summer2024!notify",  # @label hardcoded_credentials high
    "use_tls": True,
}


def send(to, subject, body):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = SETTINGS["username"], to, subject
    msg.set_content(body)
    with smtplib.SMTP(SETTINGS["host"], SETTINGS["port"]) as smtp:
        if SETTINGS["use_tls"]:
            smtp.starttls()
        smtp.login(SETTINGS["username"], SETTINGS["password"])
        smtp.send_message(msg)
