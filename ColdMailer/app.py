import csv
import json
import os
import queue
import random
import smtplib
import threading
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, Response, jsonify, render_template, request, send_file

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "leads.csv")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Хранилище настроек
# ---------------------------------------------------------------------------
DEFAULT_SETTINGS = {
    "smtp_host": "smtp.yandex.ru",
    "smtp_port": 465,
    "smtp_user": "",
    "smtp_pass": "",
    "sender_email": "",
    "sender_name": "",
    "delay_min": 15,
    "delay_max": 35,
    "subject": "Вопрос по автоматизации для {{company}}",
    "body": (
        "Привет, {{name}}!\n\n"
        "Заметил, что вы развиваете компанию {{company}}. Мы помогаем автоматизировать рутину "
        "в таких проектах.\n\n"
        "Скажите, было бы актуально обсудить, как сократить ручные затраты в вашей нише?\n\n"
        "С уважением,\n{{sender_name}}"
    ),
}


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            return merged
        except Exception:
            pass
    return dict(DEFAULT_SETTINGS)


def save_settings(data):
    merged = load_settings()
    for key in DEFAULT_SETTINGS:
        if key in data:
            merged[key] = data[key]
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged


# ---------------------------------------------------------------------------
# Работа с контактами
# ---------------------------------------------------------------------------
def read_leads():
    if not os.path.exists(CSV_FILE):
        return []
    rows = []
    with open(CSV_FILE, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def write_leads(rows):
    if not rows:
        return
    with open(CSV_FILE, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Состояние рассылки + очередь событий для живого прогресса
# ---------------------------------------------------------------------------
class Campaign:
    def __init__(self):
        self.running = False
        self.subscribers = []
        self.lock = threading.Lock()

    def subscribe(self):
        q = queue.Queue()
        with self.lock:
            self.subscribers.append(q)
        return q

    def unsubscribe(self, q):
        with self.lock:
            if q in self.subscribers:
                self.subscribers.remove(q)

    def emit(self, event):
        with self.lock:
            for q in list(self.subscribers):
                q.put(event)


campaign = Campaign()


def render_template_text(template, lead, settings):
    text = template
    for key, value in lead.items():
        text = text.replace("{{" + key + "}}", str(value or ""))
    text = text.replace("{{sender_name}}", settings.get("sender_name", ""))
    return text


def send_one(settings, to_email, subject, body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings["sender_email"]
    msg["To"] = to_email
    msg.attach(MIMEText(body, "plain", "utf-8"))

    port = int(settings["smtp_port"])
    if port == 465:
        server = smtplib.SMTP_SSL(settings["smtp_host"], port, timeout=30)
    else:
        server = smtplib.SMTP(settings["smtp_host"], port, timeout=30)
        server.starttls()
    server.login(settings["smtp_user"], settings["smtp_pass"])
    server.sendmail(settings["sender_email"], to_email, msg.as_string())
    server.quit()


def campaign_worker(settings):
    rows = read_leads()
    total = len(rows)
    sent = 0
    errors = 0

    campaign.emit({"type": "start", "total": total})

    for index, row in enumerate(rows):
        if row.get("status") == "sent":
            campaign.emit({"type": "skip", "email": row.get("email", ""), "index": index})
            continue

        email = row.get("email", "").strip()
        subject = render_template_text(settings["subject"], row, settings)
        body = render_template_text(settings["body"], row, settings)

        try:
            send_one(settings, email, subject, body)
            row["status"] = "sent"
            sent += 1
            campaign.emit({"type": "sent", "email": email, "index": index})
        except Exception as e:
            row["status"] = "error"
            errors += 1
            campaign.emit({"type": "error", "email": email, "index": index, "message": str(e)})

        write_leads(rows)

        if index < total - 1:
            delay = random.randint(int(settings["delay_min"]), int(settings["delay_max"]))
            campaign.emit({"type": "delay", "seconds": delay, "index": index})
            time.sleep(delay)

    campaign.emit({"type": "done", "sent": sent, "errors": errors})
    campaign.running = False


# ---------------------------------------------------------------------------
# Маршруты
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return Response(status=204)


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "POST":
        saved = save_settings(request.get_json(force=True) or {})
        return jsonify(saved)
    return jsonify(load_settings())


@app.route("/api/leads", methods=["GET"])
def api_leads():
    return jsonify(read_leads())


@app.route("/api/leads/upload", methods=["POST"])
def api_leads_upload():
    if "file" not in request.files:
        return jsonify({"error": "Файл не выбран"}), 400
    file = request.files["file"]
    content = file.read().decode("utf-8-sig")
    lines = content.splitlines()
    if not lines:
        return jsonify({"error": "Пустой файл"}), 400

    reader = csv.DictReader(lines)
    rows = [dict(r) for r in reader]
    for row in rows:
        row.setdefault("status", "pending")
        if not row.get("status"):
            row["status"] = "pending"
    write_leads(rows)
    return jsonify({"count": len(rows), "leads": rows})


@app.route("/api/leads/clear", methods=["POST"])
def api_leads_clear():
    write_leads([{"email": "", "name": "", "company": "", "status": "pending"}])
    return jsonify({"ok": True})


@app.route("/api/start", methods=["POST"])
def api_start():
    if campaign.running:
        return jsonify({"error": "Рассылка уже идёт"}), 400
    settings = load_settings()
    if not settings["smtp_user"] or not settings["smtp_pass"]:
        return jsonify({"error": "Заполните SMTP-данные в настройках"}), 400
    campaign.running = True
    thread = threading.Thread(target=campaign_worker, args=(settings,), daemon=True)
    thread.start()
    return jsonify({"ok": True})


@app.route("/api/progress")
def api_progress():
    def stream():
        q = campaign.subscribe()
        try:
            while True:
                try:
                    event = q.get(timeout=25)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                    if event.get("type") == "done":
                        break
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            campaign.unsubscribe(q)

    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/status")
def api_status():
    return jsonify({"running": campaign.running})


@app.route("/api/test", methods=["POST"])
def api_test():
    settings = load_settings()
    if not settings["smtp_user"] or not settings["smtp_pass"]:
        return jsonify({"error": "Заполните SMTP-данные в настройках"}), 400
    try:
        port = int(settings["smtp_port"])
        if port == 465:
            server = smtplib.SMTP_SSL(settings["smtp_host"], port, timeout=15)
        else:
            server = smtplib.SMTP(settings["smtp_host"], port, timeout=15)
            server.starttls()
        server.login(settings["smtp_user"], settings["smtp_pass"])
        server.quit()
        return jsonify({"message": "SMTP-соединение установлено, авторизация успешна ✓"})
    except Exception as e:
        return jsonify({"error": f"Не удалось подключиться: {e}"}), 400


if __name__ == "__main__":
    print("\n  ColdMailer запущен. Откройте http://127.0.0.1:5000\n")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
