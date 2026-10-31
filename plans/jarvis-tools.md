# План: добавление tools в существующего Джарвиса

## Цель

Добавить к существующему голосовому ассистенту на Yandex Cloud AI Studio
поддержку пользовательских инструментов из modules.json.

LLM должна сама выбирать инструмент по запросу пользователя.
Наш Python-код выполняет HTTP-запрос к выбранному модулю и возвращает
результат обратно в LLM.

## Запрещено

- Не использовать GigaChat.
- Не использовать LangChain.
- Не менять существующий OpenAI-клиент Yandex Cloud.
- Не менять модель deepseek-v4-flash/latest.
- Не удалять существующий web_search.
- Не менять формат modules.json.
- Не создавать Flask-сервер.
- Не добавлять распознавание и синтез речи.

## Исходное состояние

Существует файл brain/jarvis_agent.py с функцией ask_jarvis.

Он использует:

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_CLOUD_FOLDER,
    timeout=60.0,
)

и вызывает:

client.responses.create(
    model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
    temperature=0.3,
    instructions=JARVIS_INSTRUCTIONS,
    input=user_text.strip(),
    max_output_tokens=500,
    tools=[
        {
            "type": "web_search",
            "search_context_size": "low"
        }
    ],
)

## Формат modules.json

[
  {
    "module_id": "light-01",
    "description": "Светильник на рабочем столе в спальне.",
    "endpoint": "http://10.177.33.150:8080",
    "tools": [
      {
        "name": "set_color",
        "description": "Меняет цвет света. r, g, b — целые числа от 0 до 255.",
        "method": "POST",
        "path": "/api/color",
        "parameters": {
          "r": "integer",
          "g": "integer",
          "b": "integer"
        }
      }
    ]
  }
]

## Правила выполнения tools

- URL = module.endpoint + tool.path.
- HTTP-метод берётся из tool.method.
- Аргументы передаются в JSON-теле.
- Все параметры из tool.parameters обязательны.
- Если parameters пустой, отправляется JSON {}.
- Ответ модуля ожидается в формате:
  {"text": "готовая фраза"}
- Если есть text, он становится результатом tool.
- Если text нет, весь JSON-ответ сериализуется в строку.
- Модель не знает endpoint и path.
- Модель видит только имя, описание и аргументы tool.

## Файлы

### Создать

plans/jarvis-tools.md — этот план.

jarvis_tools.py — загрузка modules.json, формирование tools,
валидация аргументов и выполнение HTTP-запросов.

modules.json — пример с одним светильником.

### Изменить

Существующий файл brain/jarvis_agent.py:
- подключить jarvis_tools;
- добавить пользовательские tools к web_search;
- обработать function_call;
- выполнить tool;
- вернуть function_call_output в модель;
- получить финальный ответ.

## Этапы

1. Создать jarvis_tools.py.
2. Реализовать загрузку и валидацию modules.json.
3. Преобразовать упрощённые parameters в JSON Schema для Responses API.
4. Сформировать уникальные имена tools:
   {module_id_with_underscores}_{tool_name}.
5. Реализовать execute_tool_call.
6. Обновить ask_jarvis.
7. Добавить пример modules.json.
8. Проверить сценарии:
   - «Сделай свет зелёным» — вызывается light_01_set_color;
   - «Расскажи анекдот» — tool не вызывается;
   - «Найди курс доллара» — используется web_search.

## Важные ограничения

- Python 3.10.
- Не использовать синтаксис Python 3.11+.
- Поддерживать только один function call за один шаг.
- При ошибке tool не падать: возвращать понятную строку ошибки в LLM.
- Не использовать GigaChat и LangChain.
