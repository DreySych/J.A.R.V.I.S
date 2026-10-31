import os
import sys
import json

import openai
from dotenv import load_dotenv

from jarvis_tools import load_modules, build_tools, execute_tool_call
from memory import MemoryManager
from memory_tool import MEMORY_TOOL, make_remember_fact
from prompt import build_instructions

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

load_dotenv()

YANDEX_CLOUD_FOLDER = os.getenv("YANDEX_FOLDER_ID")
YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_AI_TOKEN")
YANDEX_CLOUD_MODEL = "deepseek-v4.1-flash"

if not YANDEX_CLOUD_FOLDER:
    raise RuntimeError("В .env не задан YANDEX_FOLDER_ID")

if not YANDEX_CLOUD_API_KEY:
    raise RuntimeError("В .env не задан YANDEX_AI_TOKEN")

_REGISTRY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "modules_registry.json"
)

client = openai.OpenAI(
    api_key=YANDEX_CLOUD_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_CLOUD_FOLDER,
    timeout=60.0,
)

_memory = MemoryManager()
_remember_fact = make_remember_fact(_memory)

MEMORY_TOOL_NAME = "remember_fact"
MAX_MEMORY_CALLS = 3

def register_memory_tool(all_tools, tool_registry):
    all_tools.append(MEMORY_TOOL)

def to_api_items(messages):
    items = []
    for m in messages:
        if m.get("type") == "tool":
            items.append({
                "role": "assistant",
                "content": f"[{m.get('name')}] {m.get('content')}",
            })
        elif m.get("role") in ("user", "assistant") and m.get("content"):
            items.append({"role": m["role"], "content": m["content"]})
    return items

def ask_jarvis(user_text):

    if not user_text or not user_text.strip():
        return "Сэр, сформулируйте запрос, пожалуйста."

    modules = load_modules(_REGISTRY_PATH)
    all_tools, tool_registry = build_tools(modules)
    register_memory_tool(all_tools, tool_registry)
    all_tools.insert(0, {
        "type": "web_search",
        "search_context_size": "low",
    })

    turn = _memory.add_user(user_text.strip())
    conversation = to_api_items(_memory.get_history())

    max_iterations = 5
    output_text = ""
    for iteration in range(max_iterations):
        try:
            response = client.responses.create(
                model=f"gpt://{YANDEX_CLOUD_FOLDER}/{YANDEX_CLOUD_MODEL}",
                temperature=0.3,
                instructions=build_instructions(_memory),
                input=conversation,
                max_output_tokens=1500,
                tools=all_tools,
            )
        except Exception as e:
            print("API error:", str(e))
            raise

        output_text = getattr(response, "output_text", "")

        if hasattr(response, "output") and response.output:
            calls = [
                item for item in (getattr(response, "output", None) or [])
                if getattr(item, "type", None) == "function_call"
            ]

            if calls:
                action_done = False
                memory_calls = 0

                for item in calls:
                    call_id = getattr(item, "call_id", "")
                    name = getattr(item, "name", "")
                    arguments_str = getattr(item, "arguments", "")

                    try:
                        arguments_dict = json.loads(arguments_str or "{}")
                    except (json.JSONDecodeError, TypeError):
                        arguments_dict = {}

                    if name == MEMORY_TOOL_NAME:
                        if memory_calls >= MAX_MEMORY_CALLS:
                            result = "Отклонено: слишком много фактов за один ответ."
                        else:
                            memory_calls += 1
                            result = _remember_fact(**arguments_dict)
                    elif action_done:
                        result = "Отклонено: за один ответ разрешён только один инструмент."
                    else:
                        result = execute_tool_call(name, arguments_dict, tool_registry)
                        action_done = True
                        _memory.add_tool(name, result, turn)

                    conversation.append({
                        "type": "function_call",
                        "call_id": call_id,
                        "name": name,
                        "arguments": arguments_str,
                    })
                    conversation.append({
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": result,
                    })

                continue

        if not output_text:
            return "Сэр, мне не удалось сформировать ответ. Попробуйте повторить запрос."

        _memory.add_assistant(output_text, turn)

        print("Ответ J.A.R.V.I.S.:", output_text)
        return output_text

    if output_text:
        return output_text
    return "Сэр, мне не удалось сформировать ответ. Попробуйте повторить запрос."


if __name__ == "__main__":
    user_text = ("Узнай официальный курс доллара США к российскому рублю на сегодня по данным Банка России. "
                 "Назови курс, дату его действия и укажи, что это официальный курс ЦБ.")
    print(ask_jarvis(user_text))