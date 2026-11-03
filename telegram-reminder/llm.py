import json
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI

import config

_RU_WEEKDAYS = [
    "понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"
]
_RU_MONTHS = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря"
]


def _now_context():
    now = datetime.now(ZoneInfo(config.TIMEZONE))
    weekday = _RU_WEEKDAYS[now.weekday()]
    date_ru = f"{now.day} {_RU_MONTHS[now.month - 1]} {now.year}"
    return now, weekday, date_ru


_SYSTEM_PROMPT = """Ты извлекаешь из сообщения пользователя напоминание: о чём напомнить и когда.
Сегодня: {date_ru} ({weekday}), часовой пояс {tz}. Текущее время: {now_local}.

Отвечай ТОЛЬКО валидным JSON, без комментариев и без markdown-блоков. Формат:
{{"is_reminder": true, "text": "что напомнить", "datetime": "YYYY-MM-DDTHH:MM:SS"}}

Если сообщение не является напоминанием или в нём вообще нет указания на время, верни:
{{"is_reminder": false, "text": "", "datetime": null}}

Правила (строго):
- datetime указывай в местном времени пользователя ({tz}), БЕЗ смещения и буквы Z.
- datetime ОБЯЗАТЕЛЬНО заполнен для любого напоминания — не оставляй пустым.
- Пересчитывай относительное время в абсолютную дату от сегодняшней даты:
  «завтра» = {date_ru} + 1 день, «послезавтра» = +2 дня, «через час» = текущее время + 1 час.
- «5 числа» = 5-е число ближайшего будущего месяца (если 5-е уже прошло — 5-е следующего месяца).
- Дни недели: «в пятницу»/«в следующую пятницу» = ближайшая наступающая пятница, которая ещё не наступила (сегодняшний день не считается).
- «вечером» = 19:00, «утром» = 09:00, «днём»/«в обед» = 13:00, «ночью» = 23:00, если точное время не указано.
- Если точное время указано явно («завтра вечером в 18:00») — используй его, а не слово-уточнение.
"""


def _client():
    return OpenAI(
        api_key=config.LLM_API_KEY,
        base_url=config.LLM_BASE_URL,
        timeout=config.LLM_TIMEOUT,
        max_retries=1,
    )


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

    now, weekday, date_ru = _now_context()
    now_local = now.strftime("%H:%M:%S")
    system = _SYSTEM_PROMPT.format(
        date_ru=date_ru, weekday=weekday, now_local=now_local, tz=config.TIMEZONE
    )

    client = _client()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": text},
    ]

    # response_format json_object не задаём намеренно: reasoning-модели
    # (например Nemotron) могут его игнорировать или сломаться. Парсим JSON сами.
    resp = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=messages,
        temperature=0,
        max_tokens=config.LLM_MAX_TOKENS,
    )

    content = resp.choices[0].message.content
    if not content:
        raise ValueError("модель вернула пустой ответ")

    data = _parse_json(content)

    if not data.get("is_reminder"):
        return None

    dt_str = data.get("datetime")
    if not dt_str:
        raise ValueError("не удалось определить время")

    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(config.TIMEZONE))

    return data.get("text", "").strip(), dt