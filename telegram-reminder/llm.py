import json
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI

import config

_SYSTEM_PROMPT = """Ты извлекаешь из сообщения пользователя напоминание: о чём напомнить и когда.
Текущее местное время пользователя: {now_local} (часовой пояс {tz}).

Отвечай ТОЛЬКО валидным JSON, без комментариев и без markdown-блоков. Формат:
{{"is_reminder": true, "text": "что напомнить", "datetime": "YYYY-MM-DDTHH:MM:SS"}}

Если сообщение не является напоминанием или в нём нет времени, верни:
{{"is_reminder": false, "text": "", "datetime": null}}

Правила:
- datetime указывай в местном времени пользователя ({tz}), БЕЗ смещения и буквы Z.
- Относительные формулировки («завтра», «послезавтра», «через час», «вечером», «5 числа», «в следующую пятницу») пересчитывай от текущего времени в абсолютную дату и время.
- «вечером» = 19:00, «утром» = 09:00, «днём» = 13:00, «ночью» = 23:00, если точное время не указано.
- «5 числа» — 5-е число текущего или ближайшего будущего месяца.
"""


def _client():
    return OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)


def _parse_json(raw: str):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("` \n")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(raw[start:end + 1])
        raise


def parse_message(text: str):
    """Возвращает (текст_напоминания, dt_local_aware) или None, если это не напоминание."""
    if not config.LLM_API_KEY:
        raise RuntimeError("Не задан LLM_API_KEY. Заполни файл .env.")

    now = datetime.now(ZoneInfo(config.TIMEZONE))
    now_local = now.strftime("%Y-%m-%d %H:%M:%S (%A)")
    system = _SYSTEM_PROMPT.format(now_local=now_local, tz=config.TIMEZONE)

    client = _client()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": text},
    ]

    try:
        resp = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        # Некоторые провайдеры не поддерживают json_object — пробуем без него
        if "response_format" in str(e) or "json_object" in str(e):
            resp = client.chat.completions.create(
                model=config.LLM_MODEL, messages=messages, temperature=0
            )
        else:
            raise

    data = _parse_json(resp.choices[0].message.content)

    if not data.get("is_reminder"):
        return None

    dt_str = data.get("datetime")
    if not dt_str:
        raise ValueError("не удалось определить время")

    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(config.TIMEZONE))

    return data.get("text", "").strip(), dt