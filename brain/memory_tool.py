import re

MEMORY_TOOL = {
    "type": "function",
    "name": "remember_fact",
    "description": (
        "Сохраняет устойчивый факт о пользователе: имя, город, часовой пояс, "
        "предпочтения, привычки, распорядок. Вызывай только когда пользователь "
        "сообщает что-то постоянное о себе, а не разовую просьбу. Один вызов — "
        "один факт."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Ключ латиницей в snake_case"},
            "value": {"type": "string", "description": "Значение, 2-5 слов"},
        },
        "required": ["key", "value"],
        "additionalProperties": False,
    },
    "strict": True,
}


def make_remember_fact(memory):
    def remember_fact(key: str, value: str) -> str:
        key = re.sub(r"[^0-9a-zA-Zа-яА-Я_]+", "_", str(key).strip().lower())
        key = key.strip("_")[:40]
        value = str(value).strip().strip("\"'")[:300]
        if not key or not value:
            return "Не сохранил: пустой ключ или значение."
        memory.set_fact(key, value)
        return f"Запомнил: {key}."
    return remember_fact