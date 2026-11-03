import csv
import random
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SENDER_EMAIL, DELAY_MIN, DELAY_MAX

CSV_FILE = "leads.csv"

SUBJECT_TEMPLATE = "Вопрос по автоматизации для {{company}}"
BODY_TEMPLATE = """Привет, {{name}}!

Заметил, что вы развиваете компанию {{company}}. Мы помогаем автоматизировать рутину в таких проектах.

Скажите, было бы актуально обсудить, как сократить ручные затраты в вашей нише?

С уважением,
Ваше Имя"""

def send_email(to_email, name, company):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = SUBJECT_TEMPLATE.replace("{{company}}", company)
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email

    text_content = BODY_TEMPLATE.replace("{{name}}", name).replace("{{company}}", company)
    msg.attach(MIMEText(text_content, "plain", "utf-8"))

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
            
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Ошибка отправки на {to_email}: {e}")
        return False

def main():
    if not os_exists(CSV_FILE):
        print(f"Файл {CSV_FILE} не найден.")
        return

    rows = []
    with open(CSV_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        print("База контактов пуста.")
        return

    print(f"🚀 Начинаем рассылку. Всего контактов: {len(rows)}")

    for row in rows:
        if row.get("status") == "sent":
            print(f"⏩ Пропускаем (уже отправлено): {row['email']}")
            continue

        print(f"📩 Отправка для {row['name']} ({row['email']})...", end="", flush=True)
        success = send_email(row["email"], row["name"], row["company"])

        if success:
            row["status"] = "sent"
            print(" Успешно!")
        else:
            row["status"] = "error"

        with open(CSV_FILE, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        delay = random.randint(DELAY_MIN, DELAY_MAX)
        print(f"⏳ Пауза: {delay} сек...\n")
        time.sleep(delay)

    print("✨ Рассылка завершена!")

def os_exists(path):
    import os
    return os.path.exists(path)

if __name__ == "__main__":
    main()
