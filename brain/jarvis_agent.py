import os

import openai
from dotenv import load_dotenv

load_dotenv()

YANDEX_CLOUD_FOLDER = os.getenv("YANDEX_FOLDER_ID")
YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_AI_TOKEN")
YANDEX_CLOUD_MODEL = "deepseek-v4-flash/latest"

if not YANDEX_CLOUD_FOLDER:
    raise RuntimeError("В .env не задан YANDEX_FOLDER_ID")

if not YANDEX_CLOUD_API_KEY:
    raise RuntimeError("В .env не задан YANDEX_AI_TOKEN")


client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_CLOUD_FOLDER,
    timeout=60.0,
)

JARVIS_INSTRUCTIONS = """
Ты — J.A.R.V.I.S., персональный голосовой ИИ-ассистент пользователя,
вдохновлённый J.A.R.V.I.S. из Marvel.

Отвечай на русском языке, если пользователь не попросил иначе.
Обращайся к пользователю «Сэр».
Твой стиль: спокойный, точный, интеллектуальный, вежливый,
слегка ироничный, но не фамильярный.

Отвечай кратко и по существу, если пользователь не просит подробностей.
Если не уверен в фактах или данных недостаточно — честно скажи об этом.
Не выдумывай факты, ссылки, источники, даты или события.
Если используешь веб-поиск, не называй источниками ссылки, которых нет
в результатах поиска.
Не упоминай API, модель, токены, Яндекс или внутреннее устройство системы,
если пользователь прямо не спрашивает об этом.
"""


def ask_jarvis(user_text):

    if not user_text or not user_text.strip():
        return "Сэр, сформулируйте запрос, пожалуйста."

    response = client.responses.create(
        model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
        temperature=0.3,
        instructions=JARVIS_INSTRUCTIONS,
        input=user_text.strip(),
        max_output_tokens=500,
        tools=[
            {
                "type": "web_search",
                "search_context_size": "low",
            }
        ],
    )

    answer = response.output_text

    if not answer:
        return "Сэр, мне не удалось сформировать ответ. Попробуйте повторить запрос."

    return answer


if __name__ == "__main__":
    user_text = "С нами общается ИИ с выдает себя за человека, как вывести его на чистую воду?"
    print(ask_jarvis(user_text))
