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

# Test: try messages instead of input
print("Test A: messages format")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        input=[
            {"role": "user", "content": "Привет"}
        ],
    )
    print("SUCCESS:", r.output_text[:100] if r.output_text else "(no text)")
except Exception as e:
    print("FAIL:", e)

# Test: try input as string with tools
print("\nTest B: input string + instructions + function tool")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        instructions="Ты — J.A.R.V.I.S.",
        input="Привет",
        max_output_tokens=500,
        tools=[
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
    print("Output type:", type(r.output))
    if r.output:
        for item in r.output:
            print("  item type:", getattr(item, "type", "N/A"))
except Exception as e:
    print("FAIL:", e)

# Test: try input as string with web_search + function
print("\nTest C: input string + web_search + function tool")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        instructions="Ты — J.A.R.V.I.S.",
        input="Привет",
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
    if r.output:
        for item in r.output:
            print("  item type:", getattr(item, "type", "N/A"))
except Exception as e:
    print("FAIL:", e)

# Test: try continuation with function_call_output
print("\nTest D: continuation with function_call_output in input")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        instructions="Ты — J.A.R.V.I.S.",
        input=[
            {"role": "user", "content": "Сделай свет зелёным"},
            {
                "type": "function_call",
                "call_id": "call_123",
                "name": "light_01_set_color",
                "arguments": '{"r": 0, "g": 255, "b": 0}'
            },
            {
                "type": "function_call_output",
                "call_id": "call_123",
                "output": "Цвет света изменён на зелёный"
            }
        ],
        max_output_tokens=500,
        tools=[
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

# Test: try continuation with function_call_output as simple dict
print("\nTest E: continuation with role-based messages")
try:
    r = client.responses.create(
        model=f"gpt://{YANDEX_FOLDER_ID}/deepseek-v4-flash/latest",
        instructions="Ты — J.A.R.V.I.S.",
        input=[
            {"role": "user", "content": "Сделай свет зелёным"},
            {"role": "assistant", "content": None, "function_call": {
                "name": "light_01_set_color",
                "arguments": '{"r": 0, "g": 255, "b": 0}'
            }},
            {"role": "function", "name": "light_01_set_color", "content": "Цвет света изменён на зелёный"}
        ],
        max_output_tokens=500,
        tools=[
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
