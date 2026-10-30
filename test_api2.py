import os
import json
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

# Test 1: minimal — just model + input string
print("=" * 60)
print("Test 1: input as simple string")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        input="Привет",
    )
    print("SUCCESS:", r.output_text[:100] if r.output_text else "(no text)")
except Exception as e:
    print("FAIL:", e)

# Test 2: with instructions
print("\n" + "=" * 60)
print("Test 2: input string + instructions")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        instructions="Отвечай кратко.",
        input="Привет",
    )
    print("SUCCESS:", r.output_text[:100] if r.output_text else "(no text)")
except Exception as e:
    print("FAIL:", e)

# Test 3: with web_search
print("\n" + "=" * 60)
print("Test 3: input string + web_search")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        input="Привет",
        tools=[{"type": "web_search", "search_context_size": "low"}],
    )
    print("SUCCESS:", r.output_text[:100] if r.output_text else "(no text)")
except Exception as e:
    print("FAIL:", e)

# Test 4: input as list with input_message
print("\n" + "=" * 60)
print("Test 4: input as input_message list")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        input=[{
            "type": "input_message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Привет"}],
        }],
    )
    print("SUCCESS:", r.output_text[:100] if r.output_text else "(no text)")
except Exception as e:
    print("FAIL:", e)

# Test 5: input_message + instructions + web_search
print("\n" + "=" * 60)
print("Test 5: input_message + instructions + web_search")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        instructions="Отвечай кратко.",
        input=[{
            "type": "input_message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Привет"}],
        }],
        tools=[{"type": "web_search", "search_context_size": "low"}],
    )
    print("SUCCESS:", r.output_text[:100] if r.output_text else "(no text)")
except Exception as e:
    print("FAIL:", e)

# Test 6: input_message + instructions + function tool
print("\n" + "=" * 60)
print("Test 6: input_message + instructions + function tool")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        instructions="Отвечай кратко.",
        input=[{
            "type": "input_message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Привет"}],
        }],
        tools=[{
            "type": "function",
            "name": "test_tool",
            "description": "Test tool",
            "parameters": {
                "type": "object",
                "properties": {"x": {"type": "integer"}},
                "required": ["x"],
            },
        }],
    )
    print("SUCCESS:", r.output_text[:100] if r.output_text else "(no text)")
except Exception as e:
    print("FAIL:", e)

# Test 7: all together like ask_jarvis
print("\n" + "=" * 60)
print("Test 7: all together (like ask_jarvis)")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        temperature=0.3,
        instructions="Ты — J.A.R.V.I.S.",
        input=[{
            "type": "input_message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Привет"}],
        }],
        max_output_tokens=500,
        tools=[
            {"type": "web_search", "search_context_size": "low"},
            {
                "type": "function",
                "name": "light_01_set_color",
                "description": "Меняет цвет света. r, g, b — целые числа от 0 до 255.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "r": {"type": "integer"},
                        "g": {"type": "integer"},
                        "b": {"type": "integer"},
                    },
                    "required": ["r", "g", "b"],
                },
            },
        ],
    )
    print("SUCCESS:", r.output_text[:100] if r.output_text else "(no text)")
except Exception as e:
    print("FAIL:", e)
