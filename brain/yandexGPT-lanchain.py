import os
import requests
from dotenv import load_dotenv

load_dotenv()

IAM_TOKEN = os.getenv("YANDEX_AI_TOKEN")
FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")

url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {IAM_TOKEN}",
    "x-folder-id": FOLDER_ID,
}

payload = {
    "modelUri": f"gpt://{FOLDER_ID}/yandexgpt/latest",
    "completionOptions": {
        "stream": False,
        "temperature": 0.3,
        "maxTokens": 200,
    },
    "messages": [
        {
            "role": "user",
            "text": "Привет! Ответь одним предложением, кто ты и что умеешь.",
        }
    ],
}

resp = requests.post(url, headers=headers, json=payload, timeout=15)
print("Статус:", resp.status_code)

if resp.status_code == 200:
    data = resp.json()
    answer = data["result"]["alternatives"][0]["message"]["text"]
    print("Ответ YandexGPT:")
    print(answer)
else:
    print("Тело ответа:", resp.text)