import os
from dotenv import load_dotenv
import openai

load_dotenv()

YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_AI_TOKEN = os.getenv("YANDEX_AI_TOKEN")

client = openai.OpenAI(
    api_key=YANDEX_AI_TOKEN,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_FOLDER_ID,
    timeout=60.0,
)

print("Test 1: simple string input")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        input="Привет",
    )
    print("OK:", r.output_text[:100])
except Exception as e:
    print("FAIL:", e)

print("\nTest 2: with web_search tool")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        input="Привет",
        tools=[{"type": "web_search", "search_context_size": "low"}],
    )
    print("OK:", r.output_text[:100])
except Exception as e:
    print("FAIL:", e)

print("\nTest 3: with custom function tool")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        input="Привет",
        tools=[{
            "type": "function",
            "name": "test_tool",
            "description": "A test tool",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "integer"}},
                "required": ["x"],
            },
        }],
    )
    print("OK:", r.output_text[:100])
except Exception as e:
    print("FAIL:", e)
